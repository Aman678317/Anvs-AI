"""Audio ingestion and ultrasonic watermark echo-loop rejection pipeline."""

import base64
import logging
import time
import uuid

import numpy as np

from packages.audio.framing import (
    AudioChunker,
    AudioResampler,
    float32_to_pcm_s16le,
    pcm_s16le_to_float32,
)
from packages.audio.vad import BaseVAD, EnergyVAD, SpeechSegment, SpeechSegmenter
from packages.audio.watermark import detect_watermark
from packages.contracts import AudioStreamType
from packages.event_schema import STREAM_AUDIO, AudioSegmentEvent, RedisStreamBus, get_stream_key

logger = logging.getLogger(__name__)


class AudioIngestionPipeline:
    """Ingests WebRTC participant audio, enforces Invariant #3, and segments speech for STT."""

    def __init__(
        self,
        meeting_id: str,
        participant_id: str,
        source_sample_rate: int = 48000,
        target_sample_rate: int = 16000,
        stream_bus: RedisStreamBus | None = None,
        vad: BaseVAD | None = None,
        watermark_freq: float = 20000.0,
        watermark_threshold: float = 0.001,
    ) -> None:
        self.meeting_id = meeting_id
        self.participant_id = participant_id
        self.source_sample_rate = source_sample_rate
        self.target_sample_rate = target_sample_rate
        self.stream_bus = stream_bus
        self.watermark_freq = watermark_freq
        self.watermark_threshold = watermark_threshold

        # 1. 20ms chunker at native WebRTC source rate (960 samples @ 48kHz)
        self.chunker = AudioChunker(
            sample_rate=source_sample_rate,
            frame_duration_ms=20,
        )

        # 2. Resampler converting 48kHz WebRTC audio to 16kHz STT target
        self.resampler = AudioResampler(
            source_rate=source_sample_rate,
            target_rate=target_sample_rate,
        )

        # 3. Speech Segmenter operating at 16kHz
        self.segmenter = SpeechSegmenter(
            sample_rate=target_sample_rate,
            vad=vad or EnergyVAD(),
        )

        # Telemetry metrics
        self.total_frames_processed = 0
        self.watermarked_frames_dropped = 0
        self.clean_frames_passed = 0
        self.voiced_segments_produced = 0

    async def process_pcm_bytes(self, pcm_bytes: bytes) -> list[SpeechSegment]:
        """Processes raw 16-bit PCM byte buffer through chunking, watermark guard, and VAD.

        Args:
            pcm_bytes: Raw 16-bit PCM bytes.

        Returns:
            List of completed SpeechSegment objects (if any).
        """
        samples = pcm_s16le_to_float32(pcm_bytes)
        return await self.process_samples(samples)

    async def process_samples(self, samples: np.ndarray) -> list[SpeechSegment]:
        """Processes float32 audio samples through the ingestion pipeline.

        Args:
            samples: 1D float32 numpy array.

        Returns:
            List of completed SpeechSegment objects (if any).
        """
        emitted_segments: list[SpeechSegment] = []

        for frame, start_ms, end_ms in self.chunker.push(samples):
            self.total_frames_processed += 1

            # Invariant #3: Ultrasonic synthetic audio watermark detection
            is_watermarked = detect_watermark(
                audio_pcm=frame,
                sample_rate=self.source_sample_rate,
                watermark_freq=self.watermark_freq,
                threshold=self.watermark_threshold,
            )

            if is_watermarked:
                self.watermarked_frames_dropped += 1
                logger.warning(
                    "Invariant #3: Dropped 20 kHz synthetic watermarked audio frame from participant %s in meeting %s",
                    self.participant_id,
                    self.meeting_id,
                )
                continue

            self.clean_frames_passed += 1

            # Resample clean human speech to STT sample rate (e.g. 48kHz -> 16kHz)
            resampled_frame = self.resampler.resample(frame)

            # Route through VAD speech segmenter
            for segment in self.segmenter.process_frame(resampled_frame, start_ms, end_ms):
                self.voiced_segments_produced += 1
                emitted_segments.append(segment)

                # Publish to Redis Streams if stream bus is configured
                if self.stream_bus:
                    await self._publish_audio_segment(segment)

        return emitted_segments

    async def flush(self) -> list[SpeechSegment]:
        """Flushes remaining audio buffers and yields any pending speech segment."""
        emitted: list[SpeechSegment] = []
        pending_chunk = self.chunker.flush()
        if pending_chunk:
            frame, start_ms, end_ms = pending_chunk
            if not detect_watermark(frame, self.source_sample_rate, self.watermark_freq):
                resampled = self.resampler.resample(frame)
                for seg in self.segmenter.process_frame(resampled, start_ms, end_ms):
                    emitted.append(seg)
                    if self.stream_bus:
                        await self._publish_audio_segment(seg)

        final_seg = self.segmenter.flush()
        if final_seg:
            self.voiced_segments_produced += 1
            emitted.append(final_seg)
            if self.stream_bus:
                await self._publish_audio_segment(final_seg)

        return emitted

    async def _publish_audio_segment(self, segment: SpeechSegment) -> None:
        """Publishes voiced speech segment to Redis stream."""
        if not self.stream_bus:
            return

        stream_key = get_stream_key(self.meeting_id, STREAM_AUDIO)
        pcm_bytes = float32_to_pcm_s16le(segment.audio)
        b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")

        event = AudioSegmentEvent(
            event_id=f"aud_{uuid.uuid4()}",
            timestamp_ms=int(time.time() * 1000),
            meeting_id=self.meeting_id,
            participant_id=self.participant_id,
            stream_type=AudioStreamType.ORIGINAL_HUMAN,
            watermarked=False,
            payload=b64_audio,
            duration_ms=segment.end_ms - segment.start_ms,
        )

        await self.stream_bus.publish(stream=stream_key, event=event)
