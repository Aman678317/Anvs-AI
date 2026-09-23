"""LiveKit WebRTC SFU Integration, Token Management, and Webhook Dispatch Service."""

import base64
import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from jose import jwt
from sqlalchemy import select

from packages.config import settings
from packages.contracts import ParticipantRole
from packages.database.models import Meeting

logger = logging.getLogger(__name__)


class LiveKitService:
    """Manages LiveKit room lifecycles, role-based WebRTC access tokens, and webhook events."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.url = url or settings.livekit_url
        self.api_key = api_key or settings.livekit_api_key
        self.api_secret = api_secret or settings.livekit_api_secret
        self._livekit_api: Any = None

        # Attempt initializing LiveKit Twirp client if SDK is installed
        try:
            from livekit import api as lk_api

            # Initialize LiveKitAPI client
            self._livekit_api = lk_api.LiveKitAPI(
                url=self.url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            )
            logger.info("LiveKit Twirp API client initialized for %s", self.url)
        except Exception as exc:
            logger.debug("LiveKit SDK initialization skipped (running in local/mock mode): %s", exc)
            self._livekit_api = None

    def generate_token(
        self,
        room_name: str,
        identity: str,
        name: str,
        role: ParticipantRole,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int = 3600,
    ) -> str:
        """Generate a cryptographically signed LiveKit WebRTC access token.

        Enforces media publishing permissions based on ParticipantRole:
        - HOST / MODERATOR / PARTICIPANT:
          can_publish=True, can_subscribe=True, can_publish_data=True
        - GUEST: can_publish=False (listen-only), can_subscribe=True, can_publish_data=False
        """
        now = int(time.time())
        exp = now + ttl_seconds

        can_publish = role in {
            ParticipantRole.HOST,
            ParticipantRole.MODERATOR,
            ParticipantRole.PARTICIPANT,
        }
        can_publish_data = can_publish

        meta_payload = metadata or {}
        meta_payload.setdefault("role", role.value)

        video_grants: dict[str, Any] = {
            "room": room_name,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": True,
            "canPublishData": can_publish_data,
        }

        claims: dict[str, Any] = {
            "iss": self.api_key,
            "sub": identity,
            "name": name,
            "nbf": now - 5,
            "exp": exp,
            "video": video_grants,
            "metadata": json.dumps(meta_payload),
        }

        token: str = jwt.encode(claims, self.api_secret, algorithm="HS256")
        return token

    async def create_room(
        self,
        room_name: str,
        empty_timeout_seconds: int = 300,
        max_participants: int = 100,
    ) -> dict[str, Any]:
        """Provisions a room in the LiveKit SFU."""
        if self._livekit_api:
            try:
                from livekit import api as lk_api

                req = lk_api.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=empty_timeout_seconds,
                    max_participants=max_participants,
                )
                room = await self._livekit_api.room.create_room(req)
                return {
                    "sid": room.sid or f"RM_{uuid.uuid4().hex[:12]}",
                    "name": room.name or room_name,
                    "empty_timeout": room.empty_timeout or empty_timeout_seconds,
                    "max_participants": room.max_participants or max_participants,
                    "creation_time": room.creation_time or int(time.time()),
                    "status": "ACTIVE",
                }
            except Exception as exc:
                logger.warning(
                    "LiveKit API create_room failed: %s", exc
                )
                if settings.app_env.lower() in ("production", "prod"):
                    raise ConnectionError(
                        f"LiveKit SFU room creation failed in production mode: {exc}"
                    ) from exc

        if settings.app_env.lower() in ("production", "prod"):
            raise ConnectionError(
                "LiveKit API client not initialized. Cannot create real SFU room in production environment."
            )

        return {
            "sid": f"RM_{uuid.uuid4().hex[:12]}",
            "name": room_name,
            "empty_timeout": empty_timeout_seconds,
            "max_participants": max_participants,
            "creation_time": int(time.time()),
            "status": "ACTIVE",
        }

    async def delete_room(self, room_name: str) -> bool:
        """Deletes a room from the LiveKit SFU, terminating all active peer connections."""
        if self._livekit_api:
            try:
                from livekit import api as lk_api

                req = lk_api.DeleteRoomRequest(room=room_name)
                await self._livekit_api.room.delete_room(req)
                return True
            except Exception as exc:
                logger.warning("LiveKit API delete_room failed, falling back: %s", exc)

        return bool(room_name)

    async def list_participants(self, room_name: str) -> list[dict[str, Any]]:
        """Lists active participants connected to a LiveKit SFU room."""
        if self._livekit_api:
            try:
                from livekit import api as lk_api

                req = lk_api.ListParticipantsRequest(room=room_name)
                res = await self._livekit_api.room.list_participants(req)
                return [
                    {
                        "sid": p.sid,
                        "identity": p.identity,
                        "name": p.name,
                        "state": str(p.state),
                        "joined_at": p.joined_at,
                    }
                    for p in res.participants
                ]
            except Exception as exc:
                logger.warning("LiveKit API list_participants failed: %s", exc)

        return []

    async def get_room(self, room_name: str) -> dict[str, Any] | None:
        """Retrieves LiveKit room details."""
        if self._livekit_api:
            try:
                from livekit import api as lk_api

                req = lk_api.ListRoomsRequest(names=[room_name])
                res = await self._livekit_api.room.list_rooms(req)
                if res.rooms:
                    r = res.rooms[0]
                    return {
                        "sid": r.sid,
                        "name": r.name,
                        "num_participants": r.num_participants,
                        "creation_time": r.creation_time,
                    }
            except Exception as exc:
                logger.warning("LiveKit API get_room failed: %s", exc)

        return None

    def verify_webhook(self, raw_body: bytes, auth_header: str) -> dict[str, Any]:
        """Validates LiveKit webhook signature and decodes the event payload."""
        if not auth_header:
            raise ValueError("Missing LiveKit webhook Authorization header")

        token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header

        # Decode JWT token sent in auth header
        claims: dict[str, Any] = jwt.decode(
            token,
            self.api_secret,
            algorithms=["HS256"],
            options={"verify_signature": True},
        )

        # Verify body hash if present in claims
        expected_sha = claims.get("sha256")
        if expected_sha:
            computed_sha = base64.b64encode(hashlib.sha256(raw_body).digest()).decode("utf-8")
            if expected_sha != computed_sha:
                raise ValueError("LiveKit webhook payload sha256 mismatch")

        return json.loads(raw_body.decode("utf-8"))

    async def dispatch_webhook_event(
        self,
        event: dict[str, Any],
        db_session: Any = None,
    ) -> dict[str, Any]:
        """Dispatches verified LiveKit webhook events and synchronizes meeting state."""
        event_name = event.get("event", "unknown")
        room_info = event.get("room", {})
        room_name = room_info.get("name", "")
        participant_info = event.get("participant", {})
        participant_identity = participant_info.get("identity", "")
        track_info = event.get("track", {})

        result: dict[str, Any] = {
            "dispatched": True,
            "event": event_name,
            "room_name": room_name,
            "participant_identity": participant_identity,
            "timestamp": int(time.time()),
        }

        # Extract meeting ID if room follows convention room_<uuid>
        meeting_uuid: uuid.UUID | None = None
        if room_name.startswith("room_"):
            try:
                meeting_uuid = uuid.UUID(room_name[5:])
            except (ValueError, TypeError):
                meeting_uuid = None

        if event_name == "participant_joined":
            result["action"] = "participant_joined_recorded"
            logger.info(
                "LiveKit Webhook: Participant %s joined room %s",
                participant_identity,
                room_name,
            )

        elif event_name == "participant_left":
            result["action"] = "participant_left_recorded"
            logger.info(
                "LiveKit Webhook: Participant %s left room %s",
                participant_identity,
                room_name,
            )

        elif event_name == "track_published":
            track_type = track_info.get("type", "UNKNOWN")
            track_sid = track_info.get("sid", "")
            result["action"] = "track_published_registered"
            result["track_type"] = track_type
            result["track_sid"] = track_sid
            logger.info(
                "LiveKit Webhook: Track %s (%s) published by %s in %s",
                track_sid,
                track_type,
                participant_identity,
                room_name,
            )

        elif event_name == "track_unpublished":
            result["action"] = "track_unpublished_registered"
            logger.info(
                "LiveKit Webhook: Track %s unpublished by %s in %s",
                track_info.get("sid"),
                participant_identity,
                room_name,
            )

        elif event_name == "room_started":
            result["action"] = "room_started_synchronized"
            if db_session and meeting_uuid:
                try:
                    stmt = select(Meeting).where(Meeting.id == meeting_uuid)
                    res = await db_session.execute(stmt)
                    meeting = res.scalar_one_or_none()
                    if meeting and meeting.status != "ACTIVE":
                        meeting.status = "ACTIVE"
                        meeting.actual_start = datetime.now(UTC)
                        meeting.state_version += 1
                        await db_session.commit()
                except Exception as exc:
                    logger.warning("DB sync on room_started failed: %s", exc)

        elif event_name == "room_finished":
            result["action"] = "room_finished_synchronized"
            if db_session and meeting_uuid:
                try:
                    stmt = select(Meeting).where(Meeting.id == meeting_uuid)
                    res = await db_session.execute(stmt)
                    meeting = res.scalar_one_or_none()
                    if meeting and meeting.status != "ENDED":
                        meeting.status = "ENDED"
                        meeting.actual_end = datetime.now(UTC)
                        meeting.state_version += 1
                        await db_session.commit()
                except Exception as exc:
                    logger.warning("DB sync on room_finished failed: %s", exc)

        else:
            result["action"] = "unhandled_event"

        return result


livekit_service = LiveKitService()
