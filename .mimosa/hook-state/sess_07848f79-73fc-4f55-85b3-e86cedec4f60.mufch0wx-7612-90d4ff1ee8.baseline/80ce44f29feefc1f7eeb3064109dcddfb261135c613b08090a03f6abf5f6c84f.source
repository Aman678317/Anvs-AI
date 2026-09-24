"""Audio Ingress Daemon & Pipeline Manager for Multilingual LiveKit SFU Audio Streams."""

import asyncio
import logging
from typing import Any

from packages.audio.ingestion import AudioIngestionPipeline
from packages.audio.vad import SpeechSegment
from packages.config import settings
from packages.event_schema import RedisStreamBus

logger = logging.getLogger(__name__)


class AudioIngressService:
    """Manages participant AudioIngestionPipelines, enforcing Invariant #3 and routing to STT."""

    def __init__(
        self,
        stream_bus: RedisStreamBus | None = None,
        source_sample_rate: int | None = None,
        target_sample_rate: int | None = None,
        watermark_freq: float | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.source_sample_rate = source_sample_rate or 48000
        self.target_sample_rate = target_sample_rate or settings.audio_sample_rate
        self.watermark_freq = watermark_freq or settings.audio_watermark_freq_hz

        # Map of (meeting_id, participant_id) -> AudioIngestionPipeline
        self._pipelines: dict[tuple[str, str], AudioIngestionPipeline] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_pipeline(
        self,
        meeting_id: str,
        participant_id: str,
        tenant_id: str = "",
        spoken_language: str = "eng",
    ) -> AudioIngestionPipeline:
        """Retrieves an existing pipeline or initializes a new one for the participant."""
        key = (meeting_id, participant_id)
        async with self._lock:
            if key not in self._pipelines:
                logger.info(
                    "Provisioning audio ingestion pipeline for participant %s in meeting %s",
                    participant_id,
                    meeting_id,
                )
                self._pipelines[key] = AudioIngestionPipeline(
                    meeting_id=meeting_id,
                    participant_id=participant_id,
                    tenant_id=tenant_id,
                    spoken_language=spoken_language,
                    source_sample_rate=self.source_sample_rate,
                    target_sample_rate=self.target_sample_rate,
                    stream_bus=self.stream_bus,
                    watermark_freq=self.watermark_freq,
                )
            return self._pipelines[key]

    async def ingest_audio_pcm(
        self,
        meeting_id: str,
        participant_id: str,
        pcm_bytes: bytes,
        tenant_id: str = "",
        spoken_language: str = "eng",
    ) -> list[SpeechSegment]:
        """Ingests raw 16-bit PCM bytes from a participant WebRTC audio track.

        Performs:
        1. 20ms chunking at 48kHz.
        2. Invariant #3: 20kHz acoustic watermark detection and synthetic loop drop.
        3. Polyphase resampling from 48kHz to 16kHz.
        4. Energy/Silero VAD segmentation and Redis stream dispatch.
        """
        pipeline = await self.get_or_create_pipeline(
            meeting_id=meeting_id,
            participant_id=participant_id,
            tenant_id=tenant_id,
            spoken_language=spoken_language,
        )
        return await pipeline.process_pcm_bytes(pcm_bytes)

    async def stop_track(
        self,
        meeting_id: str,
        participant_id: str,
    ) -> list[SpeechSegment]:
        """Flushes and deregisters the participant's audio ingestion pipeline."""
        key = (meeting_id, participant_id)
        async with self._lock:
            pipeline = self._pipelines.pop(key, None)

        if pipeline:
            logger.info(
                "Stopping audio ingestion pipeline for participant %s in meeting %s",
                participant_id,
                meeting_id,
            )
            return await pipeline.flush()
        return []

    async def cleanup_meeting(self, meeting_id: str) -> None:
        """Tears down all active audio ingestion pipelines for a concluded meeting."""
        async with self._lock:
            keys_to_remove = [k for k in self._pipelines if k[0] == meeting_id]
            for key in keys_to_remove:
                pipeline = self._pipelines.pop(key, None)
                if pipeline:
                    await pipeline.flush()
        logger.info(
            "Cleaned up %d audio ingress pipelines for meeting %s",
            len(keys_to_remove),
            meeting_id,
        )

    def get_active_pipeline_count(self) -> int:
        """Returns the number of currently active participant ingestion pipelines."""
        return len(self._pipelines)

    def get_total_metrics(self) -> dict[str, Any]:
        """Aggregates real-time audio ingress telemetry across all active pipelines."""
        total_processed = sum(p.total_frames_processed for p in self._pipelines.values())
        total_dropped = sum(p.watermarked_frames_dropped for p in self._pipelines.values())
        total_passed = sum(p.clean_frames_passed for p in self._pipelines.values())
        total_voiced = sum(p.voiced_segments_produced for p in self._pipelines.values())

        return {
            "active_pipelines": len(self._pipelines),
            "total_frames_processed": total_processed,
            "watermarked_frames_dropped": total_dropped,
            "clean_frames_passed": total_passed,
            "voiced_segments_produced": total_voiced,
            "overall_watermark_drop_ratio": (
                total_dropped / total_processed if total_processed > 0 else 0.0
            ),
        }


# Default singleton instance
audio_ingress_service = AudioIngressService()
