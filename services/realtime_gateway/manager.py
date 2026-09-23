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
    last_heartbeat_at: float = field(default_factory=time.time)
    message_timestamps: list[float] = field(default_factory=list)
    rate_limit_max_msgs: int = 50
    rate_limit_window_sec: float = 1.0

    def check_rate_limit(self) -> bool:
        """Check if incoming frame rate exceeds configured threshold per window."""
        now = time.time()
        cutoff = now - self.rate_limit_window_sec
        self.message_timestamps = [ts for ts in self.message_timestamps if ts > cutoff]
        self.message_timestamps.append(now)
        return len(self.message_timestamps) <= self.rate_limit_max_msgs


class ConnectionManager:
    """Manages active meeting WebSocket connections, session state, and personalized routing."""

    def __init__(self, redis_client: Any = None) -> None:
        # Structure: {meeting_id: {participant_id: ClientSession}}
        self._rooms: dict[str, dict[str, ClientSession]] = {}
        self._room_state_versions: dict[str, int] = {}
        self._room_history: dict[str, list[dict[str, Any]]] = {}
        self._max_history_per_room: int = 100
        self._lock = asyncio.Lock()
        self.redis_client = redis_client

    def next_state_version(self, meeting_id: str) -> int:
        """Increments and returns the next monotonic state version for the meeting."""
        current = self._room_state_versions.get(meeting_id, 0) + 1
        self._room_state_versions[meeting_id] = current
        return current

    def get_state_version(self, meeting_id: str) -> int:
        """Returns the current state version for the meeting without incrementing."""
        return self._room_state_versions.get(meeting_id, 1)

    def record_frame(
        self,
        meeting_id: str,
        frame: BaseWSFrame,
        state_version: int | None = None,
    ) -> None:
        """Buffers a published server frame in the room's sliding history for client resync."""
        if meeting_id not in self._room_history:
            self._room_history[meeting_id] = []
        payload = frame.model_dump()
        if state_version is not None:
            payload["state_version"] = state_version
        elif "state_version" not in payload:
            payload["state_version"] = self.get_state_version(meeting_id)

        history = self._room_history[meeting_id]
        history.append(payload)
        if len(history) > self._max_history_per_room:
            self._room_history[meeting_id] = history[-self._max_history_per_room :]

    def get_missed_frames(
        self,
        meeting_id: str,
        from_version: int,
    ) -> tuple[int, list[dict[str, Any]], bool]:
        """Returns missed frames since from_version.

        Returns:
            tuple of (current_state_version, missed_frames, full_snapshot_required)
            If from_version is 0 or precedes the buffer window, full_snapshot_required is True.
        """
        current_version = self.get_state_version(meeting_id)
        if from_version <= 0:
            return current_version, [], True

        history = self._room_history.get(meeting_id, [])
        if not history:
            return current_version, [], False

        oldest_version = history[0].get("state_version", 1)
        if from_version < oldest_version:
            # Client has fallen too far behind buffer; requires full room state snapshot
            return current_version, [], True

        missed = [f for f in history if f.get("state_version", 0) > from_version]
        return current_version, missed, False


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

        if self.redis_client:
            try:
                await self.redis_client.sadd(f"presence:meeting:{meeting_id}", participant_id)
                await self.redis_client.set(
                    f"presence:meeting:{meeting_id}:{participant_id}",
                    session.user_id,
                    ex=300,
                )
            except Exception as e:
                logger.warning("Redis presence update failed for %s: %s", participant_id, e)

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

        if self.redis_client and session:
            try:
                await self.redis_client.srem(f"presence:meeting:{meeting_id}", participant_id)
                await self.redis_client.delete(f"presence:meeting:{meeting_id}:{participant_id}")
            except Exception as e:
                logger.warning("Redis presence cleanup failed for %s: %s", participant_id, e)

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

    def get_active_participants_count(self, meeting_id: str) -> int:
        """Returns the count of connected participants in a meeting (alias for API consistency)."""
        return self.get_participant_count(meeting_id)

    async def get_cluster_participant_count(self, meeting_id: str) -> int:
        """Returns total participant count across all gateway instances via Redis (P1-05)."""
        if self.redis_client:
            try:
                count = await self.redis_client.scard(f"presence:meeting:{meeting_id}")
                return int(count)
            except Exception as e:
                logger.warning("Failed querying Redis presence count for %s: %s", meeting_id, e)
        return self.get_participant_count(meeting_id)

    def get_stale_sessions(self, max_idle_sec: float = 60.0) -> list[tuple[str, str]]:
        """Identify sessions that haven't sent a heartbeat within max_idle_sec."""
        now = time.time()
        stale: list[tuple[str, str]] = []
        for meeting_id, room in self._rooms.items():
            for participant_id, session in room.items():
                if now - session.last_heartbeat_at > max_idle_sec:
                    stale.append((meeting_id, participant_id))
        return stale

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

        self.record_frame(meeting_id, frame)
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
