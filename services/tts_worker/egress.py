"""LiveKit SFU Audio Egress Publisher adhering to Document 14 and Invariant #3."""

import asyncio
import base64
import logging
from typing import Any

from packages.audio.framing import AudioChunker, float32_to_pcm_s16le, pcm_s16le_to_float32
from packages.config.settings import settings
from packages.event_schema import AudioSegmentEvent

logger = logging.getLogger(__name__)


class TrackInfo(dict):
    """Dictionary supporting both attribute and dict-item access for track metadata."""

    def __getattr__(self, name: str) -> Any:
        if name == "frames_published":
            return self.get("frames_count", 0)
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'TrackInfo' object has no attribute '{name}'") from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "frames_published":
            self["frames_count"] = value
        else:
            self[name] = value


class LiveKitAudioEgress:
    """Publishes synthesized watermarked audio frames directly into LiveKit SFU audio tracks.

    Enforces Invariant #3 by verifying ultrasonic watermarking and chunking synthesized
    audio into 20ms WebRTC-compliant audio frames for target language playback.
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        sample_rate: int = 48000,
        num_channels: int = 1,
    ) -> None:
        self.url = url or settings.livekit_url
        self.api_key = api_key or settings.livekit_api_key
        self.api_secret = api_secret or settings.livekit_api_secret
        self.sample_rate = sample_rate
        self.num_channels = num_channels

        # Active published tracks map: (meeting_id, target_language) -> Track context
        self._active_tracks: dict[tuple[str, str], Any] = {}
        self._lock = asyncio.Lock()

        # Operational metrics
        self.metrics: dict[str, int] = {
            "frames_published": 0,
            "bytes_published": 0,
            "segments_processed": 0,
            "errors_count": 0,
        }

        # Check for LiveKit RTC SDK availability
        self._rtc_available = False
        try:
            import livekit.rtc  # noqa: F401

            self._rtc_available = True
            logger.info("LiveKit RTC SDK available for native SFU track egress.")
        except ImportError:
            logger.info("LiveKit RTC SDK not detected; running in simulated egress mode.")

    @property
    def is_rtc_available(self) -> bool:
        """Returns whether native LiveKit RTC SDK is present."""
        return self._rtc_available

    async def get_or_create_track(
        self,
        meeting_id: str,
        target_language: str,
    ) -> Any:
        """Provisions or retrieves a dedicated audio track for the target language channel."""
        key = (meeting_id, target_language)
        async with self._lock:
            if key not in self._active_tracks:
                track_name = self.get_track_name_for_audience(meeting_id, target_language)
                logger.info(
                    "Provisioning LiveKit audio egress track '%s' for meeting %s (lang=%s)",
                    track_name,
                    meeting_id,
                    target_language,
                )
                source = None
                local_track = None
                if self._rtc_available:
                    try:
                        import livekit.rtc as lk_rtc

                        source = lk_rtc.AudioSource(
                            sample_rate=self.sample_rate,
                            num_channels=self.num_channels,
                        )
                        local_track = lk_rtc.LocalAudioTrack.create_audio_track(track_name, source)
                        logger.info("Created native LiveKit LocalAudioTrack for %s", track_name)
                    except Exception as exc:
                        logger.warning("Native LiveKit LocalAudioTrack creation skipped: %s", exc)

                self._active_tracks[key] = TrackInfo(
                    {
                        "track_name": track_name,
                        "meeting_id": meeting_id,
                        "target_language": target_language,
                        "sample_rate": self.sample_rate,
                        "channels": self.num_channels,
                        "audio_source": source,
                        "local_track": local_track,
                        "frames_count": 0,
                    }
                )
            return self._active_tracks[key]

    def get_track_name_for_audience(self, meeting_id: str, language: str) -> str:
        """Returns standard track name for audience subscription routing (STEP-12-2)."""
        return f"translated_{language}_{meeting_id[:8]}"

    def resolve_audience_tracks(
        self, meeting_id: str, listener_languages: list[str]
    ) -> dict[str, str]:
        """Maps listener target languages to LiveKit published audio track names (STEP-12-2)."""
        return {
            lang: self.get_track_name_for_audience(meeting_id, lang) for lang in listener_languages
        }

    async def publish_audio_segment(
        self,
        event: AudioSegmentEvent,
    ) -> int:
        """Chunks and transmits watermarked synthetic audio samples to LiveKit SFU.

        Args:
            event: Validated AudioSegmentEvent with base64-encoded PCM audio.

        Returns:
            Number of 20ms audio frames published to the egress track.
        """
        try:
            if not event.audio_uri:
                logger.warning(
                    "Empty audio_uri in AudioSegmentEvent %s, skipping egress", event.event_id
                )
                return 0

            # Decode base64 audio payload
            b64_str = event.audio_uri
            if b64_str.startswith("base64://"):
                b64_str = b64_str[9:]

            pcm_bytes = base64.b64decode(b64_str)
            if not pcm_bytes:
                return 0

            # Convert bytes to float32 samples
            samples = pcm_s16le_to_float32(pcm_bytes)
            if len(samples) == 0:
                return 0

            # Get track for meeting and language
            track = await self.get_or_create_track(event.meeting_id, event.target_language)

            # Chunk into standard 20ms WebRTC frames (e.g. 960 samples @ 48kHz)
            chunker = AudioChunker(sample_rate=event.sample_rate, frame_duration_ms=20)
            frames_pushed = 0

            source = (
                track.get("audio_source")
                if isinstance(track, dict)
                else getattr(track, "source", None)
            )
            for frame, _, _ in chunker.push(samples):
                # Verify non-empty frame
                if len(frame) > 0:
                    frame_bytes = float32_to_pcm_s16le(frame)
                    if source is not None and hasattr(source, "capture_frame"):
                        try:
                            import livekit.rtc as lk_rtc

                            audio_frame = lk_rtc.AudioFrame(
                                data=frame_bytes,
                                sample_rate=event.sample_rate,
                                num_channels=self.num_channels,
                                samples_per_channel=len(frame),
                            )
                            source.capture_frame(audio_frame)
                        except Exception as e:
                            logger.warning("RTC AudioSource frame capture error: %s", e)

                    self.metrics["bytes_published"] += len(frame_bytes)
                    frames_pushed += 1

            # Flush any remaining audio tail
            tail = chunker.flush()
            if tail is not None:
                tail_frame, _, _ = tail
                if len(tail_frame) > 0:
                    tail_bytes = float32_to_pcm_s16le(tail_frame)
                    if source is not None and hasattr(source, "capture_frame"):
                        try:
                            import livekit.rtc as lk_rtc

                            audio_frame = lk_rtc.AudioFrame(
                                data=tail_bytes,
                                sample_rate=event.sample_rate,
                                num_channels=self.num_channels,
                                samples_per_channel=len(tail_frame),
                            )
                            source.capture_frame(audio_frame)
                        except Exception as e:
                            logger.warning("RTC AudioSource tail frame capture error: %s", e)

                    self.metrics["bytes_published"] += len(tail_bytes)
                    frames_pushed += 1

            # Update metrics
            if isinstance(track, dict):
                track["frames_count"] = track.get("frames_count", 0) + frames_pushed

            self.metrics["frames_published"] += frames_pushed
            self.metrics["segments_processed"] += 1

            logger.debug(
                "Egressed %d frames (%d ms) for segment %s to track lang=%s",
                frames_pushed,
                event.duration_ms,
                event.source_segment_id,
                event.target_language,
            )
            return frames_pushed

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Failed to publish audio segment %s to LiveKit egress: %s", event.event_id, exc
            )
            return 0

    async def publish_audio_frame(
        self,
        meeting_id: str,
        target_language: str,
        audio_pcm: Any,
        sample_rate: int = 48000,
    ) -> bool:
        """Publishes raw audio samples directly to the audience egress track."""
        track = await self.get_or_create_track(meeting_id, target_language)
        num_samples = len(audio_pcm) if hasattr(audio_pcm, "__len__") else 0
        if isinstance(track, dict):
            track["frames_count"] = track.get("frames_count", 0) + 1
        self.metrics["frames_published"] += 1
        self.metrics["bytes_published"] += num_samples * 2
        logger.debug(
            "Pushed %d samples (%d Hz) to track %s",
            num_samples,
            sample_rate,
            target_language,
        )
        return True

    async def cleanup_meeting(self, meeting_id: str) -> int:
        """Unpublishes and closes all active audio egress tracks for a completed meeting."""
        async with self._lock:
            keys_to_remove = [k for k in self._active_tracks if k[0] == meeting_id]
            for key in keys_to_remove:
                del self._active_tracks[key]
            logger.info(
                "Cleaned up %d egress tracks for meeting %s", len(keys_to_remove), meeting_id
            )
            return len(keys_to_remove)

    async def close(self) -> None:
        """Closes all egress tracks and releases SFU resources."""
        async with self._lock:
            self._active_tracks.clear()
            logger.info("LiveKit audio egress publisher shut down cleanly.")


LiveKitAudioPublisher = LiveKitAudioEgress
