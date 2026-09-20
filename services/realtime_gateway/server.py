"""FastAPI WebSocket Server and Protocol Router for Realtime Gateway."""

import asyncio
from datetime import UTC, datetime
import json
import logging
import time
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from packages.auth.tokens import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    verify_session_ticket,
)
from packages.config import settings
from packages.contracts import (
    MeetingStatus,
    ParticipantContract,
    WSClientJoinFrame,
    WSClientMessageType,
    WSClientPingFrame,
    WSClientQueryAssistantFrame,
    WSClientSetLanguageFrame,
    WSServerErrorFrame,
    WSServerParticipantJoinedFrame,
    WSServerParticipantLeftFrame,
    WSServerPongFrame,
    WSServerRoomStateFrame,
)
from packages.event_schema import (
    STREAM_ASSISTANT,
    AssistantQueryEvent,
    RedisStreamBus,
    get_stream_key,
)
from services.realtime_gateway.manager import ClientSession, ConnectionManager

logger = logging.getLogger(__name__)


def create_realtime_gateway_app(
    manager: ConnectionManager | None = None,
    stream_bus: RedisStreamBus | None = None,
) -> FastAPI:
    """Factory creating the Realtime Gateway FastAPI application."""
    app = FastAPI(
        title="Multilingual AI Meeting Platform - Realtime WebSocket Gateway",
        description="WebSocket server for real-time bilingual subtitles, state, and room events.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ws_manager = manager or ConnectionManager()

    @app.get("/healthz", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "realtime-gateway",
            "version": "1.0.0",
        }

    @app.websocket("/ws/meetings/{meeting_id}")
    async def meeting_websocket_endpoint(
        websocket: WebSocket,
        meeting_id: str,
    ) -> None:
        await websocket.accept()

        # Phase 1: Await and validate initial WSClientJoinFrame
        try:
            raw_text = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        except TimeoutError:
            err = WSServerErrorFrame(
                code="HANDSHAKE_TIMEOUT",
                message="Join frame not received within handshake timeout.",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=1008)
            return

        try:
            msg_dict = json.loads(raw_text)
            if msg_dict.get("type") != WSClientMessageType.JOIN:
                raise ValueError("Expected JOIN message type")
            join_frame = WSClientJoinFrame.model_validate(msg_dict)
        except Exception as e:
            err = WSServerErrorFrame(
                code="INVALID_JOIN_FRAME",
                message=f"First message must be a valid JOIN frame: {e}",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=1008)
            return

        # Phase 2: Verify signed session ticket (Dual-Token Invariant)
        try:
            ticket = verify_session_ticket(join_frame.ticket)
        except TokenExpiredError:
            err = WSServerErrorFrame(
                code="AUTH_EXPIRED",
                message="Session ticket has expired.",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=1008)
            return
        except (InvalidTokenError, AuthenticationError) as e:
            err = WSServerErrorFrame(
                code="AUTH_FAILED",
                message=f"Session ticket verification failed: {e}",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=1008)
            return

        # Verify meeting scoping
        if ticket.meeting_id != meeting_id:
            err = WSServerErrorFrame(
                code="FORBIDDEN_ROOM",
                message="Session ticket is not authorized for this meeting.",
            )
            await websocket.send_text(err.model_dump_json())
            await websocket.close(code=1008)
            return

        # Phase 3: Register participant session and broadcast presence
        session = ClientSession(
            websocket=websocket,
            participant_id=join_frame.participant_id,
            user_id=ticket.user_id,
            tenant_id=ticket.tenant_id,
            role=ticket.role,
            listening_language="eng",
            spoken_language="eng",
        )
        await ws_manager.connect(meeting_id, join_frame.participant_id, session)

        active_sessions = ws_manager.get_meeting_sessions(meeting_id)
        participant_contracts = [
            ParticipantContract(
                participant_id=s.participant_id,
                user_id=s.user_id,
                display_name=s.display_name or s.participant_id,
                role=s.role,
                spoken_language=s.spoken_language,
                listening_language=s.listening_language,
                is_muted=False,
                is_video_enabled=True,
                joined_at=datetime.fromtimestamp(s.connected_at, tz=UTC),
            )
            for s in active_sessions
        ]

        # Send initial room state to connecting participant
        room_state = WSServerRoomStateFrame(
            state_version=1,
            status=MeetingStatus.ACTIVE,
            participants=participant_contracts,
        )
        await websocket.send_text(room_state.model_dump_json())

        # Notify peers about new participant
        new_participant = ParticipantContract(
            participant_id=session.participant_id,
            user_id=session.user_id,
            display_name=session.display_name or session.participant_id,
            role=session.role,
            spoken_language=session.spoken_language,
            listening_language=session.listening_language,
            is_muted=False,
            is_video_enabled=True,
            joined_at=datetime.fromtimestamp(session.connected_at, tz=UTC),
        )
        joined_frame = WSServerParticipantJoinedFrame(
            state_version=1,
            participant=new_participant,
        )
        await ws_manager.broadcast_to_meeting(
            meeting_id,
            joined_frame,
            exclude_participant_id=session.participant_id,
        )

        # Phase 4: Message Loop
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    payload = json.loads(msg_text)
                except Exception:
                    continue

                msg_type = payload.get("type")

                if msg_type == WSClientMessageType.PING:
                    ping_frame = WSClientPingFrame.model_validate(payload)
                    pong_frame = WSServerPongFrame(timestamp_ms=ping_frame.timestamp_ms)
                    await websocket.send_text(pong_frame.model_dump_json())

                elif msg_type == WSClientMessageType.SET_LISTENING_LANGUAGE:
                    lang_frame = WSClientSetLanguageFrame.model_validate(payload)
                    await ws_manager.set_listening_language(
                        meeting_id,
                        session.participant_id,
                        lang_frame.listening_language,
                    )

                elif msg_type == WSClientMessageType.QUERY_ASSISTANT:
                    asst_frame = WSClientQueryAssistantFrame.model_validate(payload)
                    if stream_bus:
                        await stream_bus.publish(
                            stream=get_stream_key(meeting_id, STREAM_ASSISTANT),
                            event=AssistantQueryEvent(
                                event_id=str(uuid.uuid4()),
                                timestamp_ms=int(time.time() * 1000),
                                meeting_id=meeting_id,
                                tenant_id=session.tenant_id,
                                query_id=asst_frame.query_id,
                                participant_id=session.participant_id,
                                question=asst_frame.question,
                            ),
                        )

                elif msg_type == WSClientMessageType.CHAT_MESSAGE:
                    # Reserved for chat broadcast / persistence
                    pass

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected for participant %s", session.participant_id)
        except Exception as e:
            logger.warning("WebSocket error for participant %s: %s", session.participant_id, e)
        finally:
            await ws_manager.disconnect(meeting_id, session.participant_id)
            left_frame = WSServerParticipantLeftFrame(
                state_version=1,
                participant_id=session.participant_id,
            )
            await ws_manager.broadcast_to_meeting(meeting_id, left_frame)

    return app


# Default singleton app instance
app = create_realtime_gateway_app()
