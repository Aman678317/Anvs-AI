"""End-to-End Multi-User Meeting Lifecycle & Polyglot Caption Routing Test (PR-19).

Validates complete multi-user meeting lifecycle across Host and 3 multilingual attendees:
Room creation, dual-token join handshakes, real-time STT transcription, NMT multi-target
fan-out, TTS 20 kHz watermarked synthesis, RAG assistant citation provenance, and termination.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from starlette.websockets import WebSocket

from packages.audio.watermark import detect_watermark
from packages.auth.models import AuthenticatedUser
from packages.contracts import ParticipantRole, WSClientMessageType, WSServerMessageType
from packages.contracts.rest import CreateMeetingRequest, JoinMeetingRequest
from packages.contracts.websocket import WSClientJoinFrame
from packages.database.models import Meeting
from packages.event_schema.events import (
    AssistantQueryEvent,
    AudioSegmentEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from services.api.routers.rooms import create_room, end_room, join_room
from services.assistant_worker.consumer import AssistantConsumer
from services.assistant_worker.engine import MockAssistantEngine
from services.realtime_gateway.manager import ClientSession, ConnectionManager
from services.realtime_gateway.subscriber import RedisStreamSubscriber
from services.stt_worker.engine import MockSTTEngine
from services.translation_worker.engine import MockNMTEngine
from services.tts_worker.engine import MockTTSEngine


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiuser_polyglot_meeting_lifecycle() -> None:
    """Simulates an entire polyglot meeting session from creation to teardown."""
    tenant_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())
    host_user = AuthenticatedUser(
        user_id=host_id,
        tenant_id=tenant_id,
        email="host@enterprise.com",
        role=ParticipantRole.HOST,
    )

    # 1. Host Provisions Room
    create_req = CreateMeetingRequest(
        title="Q4 Polyglot Strategic Sync",
        host_spoken_language="eng",
        host_listening_language="eng",
    )
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    room_resp = await create_room(
        payload=create_req,
        current_user=host_user,
        session=mock_session,
    )
    meeting_id = room_resp.meeting_id
    assert room_resp.status.value == "SCHEDULED"

    # Setup database meeting instance for subsequent room operations
    target_uuid = uuid.UUID(meeting_id)
    meeting_obj = Meeting(
        id=target_uuid,
        tenant_id=uuid.UUID(tenant_id),
        created_by=uuid.UUID(host_id),
        title=create_req.title,
        status="SCHEDULED",
        state_version=1,
        host_spoken_language="eng",
        host_listening_language="eng",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = meeting_obj
    mock_session.execute.return_value = mock_result

    # 2. Host & 3 Multilingual Participants Join
    attendees_meta = [
        {"id": host_id, "role": ParticipantRole.HOST, "lang": "eng"},
        {"id": str(uuid.uuid4()), "role": ParticipantRole.PARTICIPANT, "lang": "spa"},
        {"id": str(uuid.uuid4()), "role": ParticipantRole.PARTICIPANT, "lang": "fra"},
        {"id": str(uuid.uuid4()), "role": ParticipantRole.PARTICIPANT, "lang": "deu"},
    ]

    conn_manager = ConnectionManager()

    for att in attendees_meta:
        join_req = JoinMeetingRequest(
            display_name=f"User-{att['lang']}",
            spoken_language=att["lang"],
            listening_language=att["lang"],
        )
        user_ctx = AuthenticatedUser(
            user_id=att["id"],
            tenant_id=tenant_id,
            email=f"{att['lang']}@enterprise.com",
            role=att["role"],
        )
        join_resp = await join_room(
            meeting_id=meeting_id,
            payload=join_req,
            current_user=user_ctx,
            session=mock_session,
        )
        assert join_resp.livekit_token is not None
        assert join_resp.ws_ticket is not None

        # Verify WebSocket join frame contract
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=join_resp.ws_ticket,
            participant_id=att["id"],
        )
        assert join_frame.ticket == join_resp.ws_ticket

        # Connect to Realtime WebSocket Connection Manager
        mock_ws = AsyncMock(spec=WebSocket)
        client_session = ClientSession(
            websocket=mock_ws,
            participant_id=att["id"],
            user_id=att["id"],
            tenant_id=tenant_id,
            role=att["role"],
            listening_language=att["lang"],
        )
        await conn_manager.connect(
            meeting_id=meeting_id,
            participant_id=att["id"],
            session=client_session,
        )
        assert client_session.participant_id == att["id"]

    assert conn_manager.get_active_participants_count(meeting_id) == 4

    # 3. Host Speaks (STT Inference)
    stt_engine = MockSTTEngine(default_phrase="We are expanding international operations.")
    dummy_audio = np.zeros(16000, dtype=np.float32)
    stt_result = await stt_engine.transcribe_segment(
        dummy_audio,
        sample_rate=16000,
        language="eng",
    )

    source_segment_id = str(uuid.uuid4())
    source_event = SourceSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1710000000000,
        meeting_id=meeting_id,
        session_id=str(uuid.uuid4()),
        participant_id=host_id,
        source_segment_id=source_segment_id,
        language="eng",
        text=stt_result.text,
        is_final=True,
        confidence=0.98,
        start_ms=0,
        end_ms=2500,
    )
    assert source_event.source_segment_id == source_segment_id

    # 4. NMT Multi-Target Fan-out
    nmt_engine = MockNMTEngine()
    subscriber = RedisStreamSubscriber(manager=conn_manager)
    subscriber_captions: list[dict] = []

    for target_lang in ["spa", "fra", "deu"]:
        nmt_res = await nmt_engine.translate(
            text=source_event.text,
            source_lang="eng",
            target_lang=target_lang,
        )
        trans_event = TranslationSegmentEvent(
            event_id=str(uuid.uuid4()),
            timestamp_ms=1710000000000,
            meeting_id=meeting_id,
            source_segment_id=source_segment_id,
            source_language="eng",
            target_language=target_lang,
            translated_text=nmt_res.translated_text,
            is_final=True,
            latency_ms=45,
        )
        # Lineage Invariant #2: source_segment_id strictly preserved
        assert trans_event.source_segment_id == source_segment_id

        # Route caption to listening participants
        caption_frame = await subscriber.handle_translation_segment(trans_event)
        assert caption_frame.type == WSServerMessageType.CAPTION_UPDATE
        assert caption_frame.source_segment_id == source_segment_id
        subscriber_captions.append(trans_event.model_dump())

    # Verify all 3 target translations were generated
    assert len(subscriber_captions) == 3

    # 5. TTS Synthesis with 20 kHz Ultrasonic Watermark (Invariant #3)
    tts_engine = MockTTSEngine()
    tts_result = await tts_engine.synthesize(
        text=subscriber_captions[0]["translated_text"],
        language="spa",
    )
    assert tts_result.watermarked is True
    assert detect_watermark(tts_result.audio_pcm, sample_rate=48000) is True

    audio_event = AudioSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1710000000000,
        meeting_id=meeting_id,
        source_segment_id=source_segment_id,
        target_language="spa",
        audio_uri="base64://dummy-audio",
        duration_ms=int(tts_result.duration_ms),
        watermarked=True,
    )
    assert audio_event.watermarked is True

    # 6. In-Meeting RAG Copilot Query with Citation Provenance
    assistant_engine = MockAssistantEngine()
    assistant_consumer = AssistantConsumer(stream_bus=AsyncMock(), engine=assistant_engine)
    # Index completed transcript segment
    await assistant_consumer.process_transcript_message(
        stream_name="events:transcripts",
        message_id="1-0",
        raw_payload=source_event.model_dump(mode="json"),
        meeting_id=meeting_id,
    )

    query_event = AssistantQueryEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1710000000000,
        meeting_id=meeting_id,
        query_id=str(uuid.uuid4()),
        participant_id=attendees_meta[1]["id"],
        question="What operations are expanding?",
    )
    query_emb = assistant_engine.embed_text(query_event.question)
    retrieved_segments = assistant_consumer.vector_store.similarity_search(
        query_embedding=query_emb,
        meeting_id=meeting_id,
        threshold=0.1,
    )
    answer = await assistant_engine.answer_query(
        query=query_event.question,
        retrieved_segments=retrieved_segments,
        query_id=query_event.query_id,
    )
    assert answer.query_id == query_event.query_id
    assert source_segment_id in answer.citations

    # 7. Host Ends Meeting
    end_resp = await end_room(
        meeting_id=meeting_id,
        current_user=host_user,
        session=mock_session,
    )
    assert end_resp["status"] == "ENDED"

    # Clean disconnect all sessions
    for att in attendees_meta:
        await conn_manager.disconnect(meeting_id, att["id"])
    assert conn_manager.get_active_participants_count(meeting_id) == 0
