"""Unit tests for Audio Ingestion Pipeline enforcing Invariant #3 echo loop rejection."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.ingestion import AudioIngestionPipeline
from packages.audio.watermark import embed_watermark
from packages.event_schema import STREAM_AUDIO, AudioSegmentEvent, RedisStreamBus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_drops_watermarked_audio_invariant_3() -> None:
    pipeline = AudioIngestionPipeline(
        meeting_id="meeting_inv3_test",
        participant_id="part_speaker_1",
        source_sample_rate=48000,
        target_sample_rate=16000,
    )

    # 1 second of 48kHz audio (48000 samples)
    t = np.linspace(0, 1.0, 48000, endpoint=False, dtype=np.float32)
    voice_audio = 0.2 * np.sin(2 * np.pi * 440 * t)

    # Embed 20 kHz ultrasonic watermark (simulating synthetic TTS playing over speakers)
    watermarked_audio = embed_watermark(voice_audio, sample_rate=48000, watermark_freq=20000.0)

    # Process through pipeline
    emitted_segments = await pipeline.process_samples(watermarked_audio)

    # Invariant #3 verification:
    # 1. 100% of watermarked frames must be dropped (48000 / 960 = 50 frames)
    assert pipeline.watermarked_frames_dropped == 50
    assert pipeline.clean_frames_passed == 0
    # 2. No segments must be emitted from synthetic echo audio
    assert len(emitted_segments) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_processes_clean_speech() -> None:
    pipeline = AudioIngestionPipeline(
        meeting_id="meeting_clean_test",
        participant_id="part_human_1",
        source_sample_rate=48000,
        target_sample_rate=16000,
    )

    # 1. 500ms of clean human speech (24000 samples at 48kHz)
    t_speech = np.linspace(0, 0.5, 24000, endpoint=False, dtype=np.float32)
    speech_audio = 0.3 * np.sin(2 * np.pi * 500 * t_speech)

    # 2. 500ms of silence
    silence_audio = np.zeros(24000, dtype=np.float32)

    full_audio = np.concatenate((speech_audio, silence_audio))

    # Process samples
    segments = await pipeline.process_samples(full_audio)

    # Verify watermark guard allowed clean speech
    assert pipeline.watermarked_frames_dropped == 0
    assert pipeline.clean_frames_passed == 50  # 48000 / 960 = 50 frames
    assert pipeline.voiced_segments_produced >= 1
    assert len(segments) >= 1

    # Verify resampled rate is 16kHz
    assert segments[0].sample_rate == 16000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_publishes_to_redis_bus() -> None:
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish = AsyncMock(return_value="msg_audio_101")

    pipeline = AudioIngestionPipeline(
        meeting_id="meeting_bus_test",
        participant_id="part_human_2",
        source_sample_rate=48000,
        target_sample_rate=16000,
        stream_bus=mock_bus,
    )

    # Speech + silence in raw 16-bit PCM bytes at 48kHz
    t_speech = np.linspace(0, 0.5, 24000, endpoint=False, dtype=np.float32)
    speech_audio = 0.3 * np.sin(2 * np.pi * 500 * t_speech)
    silence_audio = np.zeros(24000, dtype=np.float32)
    full_audio = np.concatenate((speech_audio, silence_audio))

    int16_bytes = (np.clip(full_audio, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()

    segments = await pipeline.process_pcm_bytes(int16_bytes)
    assert len(segments) >= 1

    # Verify Redis publish call
    assert mock_bus.publish.called
    call_args = mock_bus.publish.call_args
    assert STREAM_AUDIO in call_args.kwargs["stream"]

    event: AudioSegmentEvent = call_args.kwargs["event"]
    assert isinstance(event, AudioSegmentEvent)
    assert event.meeting_id == "meeting_bus_test"
    assert event.source_segment_id.startswith("src_part_human_2_")
    assert event.watermarked is False  # Invariant: human speech is unwatermarked
    assert event.duration_ms > 0
