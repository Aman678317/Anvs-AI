"""LiveKit SFU Audio Track Subscriber Daemon enforcing Human Source Gate (Invariant #1)."""

import asyncio
import logging
from typing import Any

from packages.config import settings
from services.audio_ingress.service import AudioIngressService, audio_ingress_service

logger = logging.getLogger(__name__)


class LiveKitAudioSubscriber:
    """Subscribes to LiveKit participant audio tracks, enforces Human Source Gate, and streams PCM.

    Invariant Rules:
    1. Human Source Gate (Invariant #1): Headless bot participants (identity starting with 'bot_')
       and translated audio egress tracks (names starting with 'translated_' or 'synthetic_')
       MUST NEVER be subscribed to or ingested into the STT pipeline.
    2. Real WebRTC PCM is forwarded to AudioIngressService for 48kHz ultrasonic watermark
       inspection (Invariant #3 loop rejection) prior to downsampling to 16kHz for STT.
    """

    def __init__(
        self,
        ingress_service: AudioIngressService | None = None,
        livekit_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        simulated: bool = False,
    ) -> None:
        self.ingress_service = ingress_service or audio_ingress_service
        self.url = livekit_url or settings.livekit_url
        self.api_key = api_key or settings.livekit_api_key
        self.api_secret = api_secret or settings.livekit_api_secret
        self.simulated = simulated

        # Track active subscriptions and background audio stream consumer tasks
        # Key: (meeting_id, participant_id, track_sid) -> asyncio.Task
        self._active_tasks: dict[tuple[str, str, str], asyncio.Task[None]] = {}
        # Key: meeting_id -> Room instance or simulated room
        self._rooms: dict[str, Any] = {}
        self._lock = asyncio.Lock()

        # Operational metrics
        self.metrics: dict[str, int] = {
            "human_tracks_admitted": 0,
            "bot_tracks_rejected": 0,
            "frames_ingested": 0,
            "bytes_ingested": 0,
            "errors_count": 0,
        }

        # Check for LiveKit RTC SDK availability
        self._rtc_available = False
        try:
            import livekit.rtc  # noqa: F401

            self._rtc_available = True
            logger.info("LiveKit RTC SDK available for native SFU track ingress.")
        except ImportError:
            logger.info("LiveKit RTC SDK not detected; running in simulated ingress mode.")

    @property
    def is_rtc_available(self) -> bool:
        """Returns whether native LiveKit RTC SDK is available."""
        return self._rtc_available

    def is_human_source(self, participant_identity: str, track_name: str | None = None) -> bool:
        """Enforces Human Source Gate (Invariant #1).

        Returns True only if the track is confirmed to originate from a real human participant.
        """
        # Reject bot identities (e.g. 'bot_translator_en', 'bot_tts_worker', etc.)
        is_bot_identity = participant_identity.startswith("bot_")

        # Reject translated synthetic audio tracks
        is_synthetic_track = bool(
            track_name and track_name.startswith(("translated_", "synthetic_"))
        )

        return not (is_bot_identity or is_synthetic_track)

    async def subscribe_to_room(
        self,
        meeting_id: str,
        token: str,
        identity: str = "bot_audio_ingress",
        simulated: bool | None = None,
    ) -> Any:
        """Connects to a LiveKit room and registers track subscription handlers."""
        _ = identity
        use_simulated = self.simulated if simulated is None else simulated
        async with self._lock:
            if meeting_id in self._rooms:
                logger.info("Already subscribed to LiveKit room %s", meeting_id)
                return self._rooms[meeting_id]

            if self._rtc_available and not use_simulated:
                try:
                    import livekit.rtc as lk_rtc

                    room = lk_rtc.Room()

                    @room.on("track_subscribed")
                    def on_track_subscribed(
                        track: lk_rtc.Track,
                        publication: lk_rtc.TrackPublication,
                        participant: lk_rtc.RemoteParticipant,
                    ) -> None:
                        _ = publication
                        if track.kind != lk_rtc.TrackKind.KIND_AUDIO:
                            return

                        track_name = getattr(track, "name", "") or ""
                        participant_identity = participant.identity

                        # Enforce Human Source Gate (Invariant #1)
                        if not self.is_human_source(participant_identity, track_name):
                            self.metrics["bot_tracks_rejected"] += 1
                            logger.info(
                                "Human Source Gate: Rejected bot track %s from %s in meeting %s",
                                track.sid,
                                participant_identity,
                                meeting_id,
                            )
                            return

                        self.metrics["human_tracks_admitted"] += 1
                        logger.info(
                            "Human Source Gate: Admitted human audio track %s from %s in meeting %s",
                            track.sid,
                            participant_identity,
                            meeting_id,
                        )

                        key = (meeting_id, participant_identity, track.sid)
                        task = asyncio.create_task(
                            self._consume_rtc_track_stream(meeting_id, participant_identity, track)
                        )
                        self._active_tasks[key] = task

                    @room.on("track_unsubscribed")
                    def on_track_unsubscribed(
                        track: lk_rtc.Track,
                        publication: lk_rtc.TrackPublication,
                        participant: lk_rtc.RemoteParticipant,
                    ) -> None:
                        _ = publication
                        key = (meeting_id, participant.identity, track.sid)
                        task = self._active_tasks.pop(key, None)
                        if task and not task.done():
                            task.cancel()
                        asyncio.create_task(
                            self.ingress_service.stop_track(meeting_id, participant.identity)
                        )

                    @room.on("participant_disconnected")
                    def on_participant_disconnected(participant: lk_rtc.RemoteParticipant) -> None:
                        # Clean up all tracks for disconnected participant
                        keys_to_remove = [
                            k
                            for k in self._active_tasks
                            if k[0] == meeting_id and k[1] == participant.identity
                        ]
                        for k in keys_to_remove:
                            task = self._active_tasks.pop(k, None)
                            if task and not task.done():
                                task.cancel()
                        asyncio.create_task(
                            self.ingress_service.stop_track(meeting_id, participant.identity)
                        )

                    await room.connect(self.url, token)
                    self._rooms[meeting_id] = room
                    logger.info("LiveKitAudioSubscriber connected to room %s", meeting_id)
                    return room
                except Exception as exc:
                    logger.warning("LiveKit RTC room connect failed: %s", exc)
                    if settings.app_env.lower() in ("production", "prod"):
                        raise ConnectionError(
                            f"LiveKit SFU room subscription failed in production: {exc}"
                        ) from exc
                    logger.info(
                        "Falling back to simulated subscription mode for room %s", meeting_id
                    )

            # Simulated mode
            mock_room = {
                "meeting_id": meeting_id,
                "status": "connected",
                "simulated": True,
            }
            self._rooms[meeting_id] = mock_room
            logger.info("LiveKitAudioSubscriber running in simulated mode for room %s", meeting_id)
            return mock_room

    async def _consume_rtc_track_stream(
        self,
        meeting_id: str,
        participant_id: str,
        track: Any,
    ) -> None:
        """Streams raw 16-bit PCM frames from native LiveKit AudioStream into AudioIngressService."""
        try:
            import livekit.rtc as lk_rtc

            audio_stream = lk_rtc.AudioStream(track)
            async for event in audio_stream:
                audio_frame = event.frame
                pcm_bytes = audio_frame.data.tobytes()
                if pcm_bytes:
                    self.metrics["frames_ingested"] += 1
                    self.metrics["bytes_ingested"] += len(pcm_bytes)
                    await self.ingress_service.ingest_audio_pcm(
                        meeting_id=meeting_id,
                        participant_id=participant_id,
                        pcm_bytes=pcm_bytes,
                    )
        except asyncio.CancelledError:
            logger.info(
                "Audio stream consumer cancelled for participant %s in meeting %s",
                participant_id,
                meeting_id,
            )
        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error consuming audio stream from participant %s in meeting %s: %s",
                participant_id,
                meeting_id,
                exc,
                exc_info=True,
            )

    async def handle_simulated_track_pcm(
        self,
        meeting_id: str,
        participant_id: str,
        pcm_bytes: bytes,
        track_name: str = "microphone",
        spoken_language: str = "eng",
    ) -> bool:
        """Handles audio frame ingestion for testing and simulated environments.

        Enforces Human Source Gate (Invariant #1). Returns True if admitted, False if dropped.
        """
        if not self.is_human_source(participant_id, track_name):
            self.metrics["bot_tracks_rejected"] += 1
            logger.info(
                "Human Source Gate: Rejected simulated bot track %s from %s",
                track_name,
                participant_id,
            )
            return False

        self.metrics["human_tracks_admitted"] += 1
        self.metrics["frames_ingested"] += 1
        self.metrics["bytes_ingested"] += len(pcm_bytes)

        await self.ingress_service.ingest_audio_pcm(
            meeting_id=meeting_id,
            participant_id=participant_id,
            pcm_bytes=pcm_bytes,
            spoken_language=spoken_language,
        )
        return True

    async def unsubscribe_from_room(self, meeting_id: str) -> None:
        """Disconnects room, cancels all streaming tasks, and cleans up participant pipelines."""
        async with self._lock:
            # 1. Cancel audio tasks for this meeting
            keys_to_remove = [k for k in self._active_tasks if k[0] == meeting_id]
            for k in keys_to_remove:
                task = self._active_tasks.pop(k, None)
                if task and not task.done():
                    task.cancel()

            # 2. Disconnect RTC room
            room = self._rooms.pop(meeting_id, None)
            if room and hasattr(room, "disconnect"):
                try:
                    await room.disconnect()
                except Exception as exc:
                    logger.warning("Error disconnecting LiveKit room %s: %s", meeting_id, exc)

            # 3. Clean up pipeline state in AudioIngressService
            await self.ingress_service.cleanup_meeting(meeting_id)
            logger.info("Successfully unsubscribed and cleaned up room %s", meeting_id)

    def get_metrics(self) -> dict[str, Any]:
        """Returns subscriber operational metrics and gate statistics."""
        return {
            "rtc_available": self._rtc_available,
            "active_rooms": len(self._rooms),
            "active_track_tasks": len(self._active_tasks),
            **self.metrics,
        }
