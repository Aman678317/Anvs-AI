"""Realtime Gateway Connection and Session State Manager."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from packages.contracts import BaseWSFrame, ParticipantRole, WSServerCaptionFrame

logger = logging.getLogger(__name__)


@dataclass
class ClientSession:
    """Represents an active client WebSocket session."""

    websocket: Any
    participant_id: str
    user_id: str
    tenant_id: str
    role: ParticipantRole
    listening_language: str = "eng"
    display_name: str = ""
    spoken_language: str = "eng"
    connected_at: float = field(default_factory=time.time)


class ConnectionManager:
    """Manages active meeting WebSocket connections, session state, and personalized routing."""

    def __init__(self) -> None:
        # Structure: {meeting_id: {participant_id: ClientSession}}
        self._rooms: dict[str, dict[str, ClientSession]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        meeting_id: str,
        participant_id: str,
        session: ClientSession,
    ) -> None:
        """Registers an active participant WebSocket session within a meeting room."""
        async with self._lock:
            if meeting_id not in self._rooms:
                self._rooms[meeting_id] = {}
            self._rooms[meeting_id][participant_id] = session
            logger.info(
                "Participant %s joined meeting %s (listening: %s)",
                participant_id,
                meeting_id,
                session.listening_language,
            )

    async def disconnect(
        self,
        meeting_id: str,
        participant_id: str,
    ) -> ClientSession | None:
        """Unregisters and removes a participant session from the meeting."""
        async with self._lock:
            room = self._rooms.get(meeting_id)
            if not room:
                return None
            session = room.pop(participant_id, None)
            if not room:
                self._rooms.pop(meeting_id, None)
            if session:
                logger.info(
                    "Participant %s disconnected from meeting %s",
                    participant_id,
                    meeting_id,
                )
            return session

    def get_session(self, meeting_id: str, participant_id: str) -> ClientSession | None:
        """Retrieves a specific participant session if connected."""
        return self._rooms.get(meeting_id, {}).get(participant_id)

    def get_meeting_sessions(self, meeting_id: str) -> list[ClientSession]:
        """Returns all active client sessions for a given meeting."""
        return list(self._rooms.get(meeting_id, {}).values())

    def get_participant_count(self, meeting_id: str) -> int:
        """Returns the count of connected participants in a meeting."""
        return len(self._rooms.get(meeting_id, {}))

    async def set_listening_language(
        self,
        meeting_id: str,
        participant_id: str,
        language: str,
    ) -> bool:
        """Dynamically updates a participant's target listening language preference."""
        session = self.get_session(meeting_id, participant_id)
        if not session:
            return False
        session.listening_language = language.lower()
        logger.info(
            "Updated listening language for participant %s to %s",
            participant_id,
            language,
        )
        return True

    async def send_to_participant(
        self,
        meeting_id: str,
        participant_id: str,
        frame: BaseWSFrame,
    ) -> bool:
        """Sends a WebSocket frame directly to a targeted participant."""
        session = self.get_session(meeting_id, participant_id)
        if not session:
            return False
        try:
            payload = frame.model_dump_json()
            await session.websocket.send_text(payload)
            return True
        except Exception as e:
            logger.warning(
                "Failed to send frame to participant %s: %s",
                participant_id,
                e,
            )
            return False

    async def broadcast_to_meeting(
        self,
        meeting_id: str,
        frame: BaseWSFrame,
        exclude_participant_id: str | None = None,
    ) -> int:
        """Broadcasts a frame to all participants in a meeting room, optionally excluding sender."""
        sessions = self.get_meeting_sessions(meeting_id)
        if not sessions:
            return 0

        payload = frame.model_dump_json()
        deliveries = 0

        for session in sessions:
            if exclude_participant_id and session.participant_id == exclude_participant_id:
                continue
            try:
                await session.websocket.send_text(payload)
                deliveries += 1
            except Exception as e:
                logger.warning(
                    "Error broadcasting frame to participant %s: %s",
                    session.participant_id,
                    e,
                )

        return deliveries

    async def route_caption(
        self,
        meeting_id: str,
        source_language: str,
        target_language: str,
        original_frame: WSServerCaptionFrame,
        translated_frame: WSServerCaptionFrame,
    ) -> int:
        """Routes personalized captions based on each client's listening_language.

        - Listeners matching source_language receive original speech captions.
        - Listeners matching target_language receive translated captions.
        """
        sessions = self.get_meeting_sessions(meeting_id)
        if not sessions:
            return 0

        src_lang = source_language.lower()
        tgt_lang = target_language.lower()
        orig_payload = original_frame.model_dump_json()
        trans_payload = translated_frame.model_dump_json()

        delivered = 0
        for session in sessions:
            listener_lang = session.listening_language.lower()
            try:
                if listener_lang == src_lang:
                    await session.websocket.send_text(orig_payload)
                    delivered += 1
                elif listener_lang == tgt_lang:
                    await session.websocket.send_text(trans_payload)
                    delivered += 1
            except Exception as e:
                logger.warning(
                    "Failed caption routing to participant %s: %s",
                    session.participant_id,
                    e,
                )

        return delivered

    async def deliver_caption_event(
        self,
        meeting_id: str,
        frame: WSServerCaptionFrame,
    ) -> int:
        """Delivers a single caption frame to listeners whose language matches the caption.

        - If target_language matches source_language, delivered to source_language listeners.
        - Otherwise, delivered to target_language listeners.
        """
        sessions = self.get_meeting_sessions(meeting_id)
        if not sessions:
            return 0

        target_match = frame.target_language.lower()
        payload = frame.model_dump_json()
        delivered = 0

        for session in sessions:
            if session.listening_language.lower() == target_match:
                try:
                    await session.websocket.send_text(payload)
                    delivered += 1
                except Exception as e:
                    logger.warning(
                        "Failed delivering caption to participant %s: %s",
                        session.participant_id,
                        e,
                    )

        return delivered
