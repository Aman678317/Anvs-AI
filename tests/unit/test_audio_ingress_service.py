"""Unit tests for Audio Ingress Service and LiveKit Audio Stream Management."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.framing import float32_to_pcm_s16le
from packages.audio.watermark import embed_watermark
from packages.event_schema import RedisStreamBus
from services.audio_ingress.service import AudioIngressService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_ingress_pipeline_lifecycle() -> None:
    service = AudioIngressService()
    meeting_id = "meeting_life_1"
    participant_id = "part_life_1"

    # Initially 0 pipelines
    assert service.get_active_pipeline_count() == 0

    # 1. Provision pipeline
    pipeline = await service.get_or_create_pipeline(meeting_id, participant_id)
    assert pipeline is not None
    assert service.get_active_pipeline_count() == 1

    # 2. Re-fetching returns identical instance
    cached_pipeline = await service.get_or_create_pipeline(meeting_id, participant_id)
    assert cached_pipeline is pipeline
    assert service.get_active_pipeline_count() == 1

    # 3. Stop track flushes and removes pipeline
    flushed = await service.stop_track(meeting_id, participant_id)
    assert isinstance(flushed, list)
    assert service.get_active_pipeline_count() == 0

    # Stopping non-existent returns empty list
    assert await service.stop_track(meeting_id, "part_non_existent") == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_ingress_pcm_ingestion_and_watermark_dropping() -> None:
    mock_bus = AsyncMock(spec=RedisStreamBus)
    service = AudioIngressService(stream_bus=mock_bus)

    meeting_id = "meeting_audio_ingest"
    participant_id = "part_audio_ingest"

    # 1. Clean human speech: 48kHz, 48000 samples (1 second = 50 frames of 20ms)
    t = np.linspace(0, 1.0, 48000, endpoint=False, dtype=np.float32)
    clean_audio = 0.3 * np.sin(2 * np.pi * 500 * t)
    clean_pcm = float32_to_pcm_s16le(clean_audio)

    # Ingest clean PCM
    await service.ingest_audio_pcm(meeting_id, participant_id, clean_pcm)
    pipeline = await service.get_or_create_pipeline(meeting_id, participant_id)
    assert pipeline.clean_frames_passed == 50
    assert pipeline.watermarked_frames_dropped == 0

    # 2. Watermarked synthetic audio: 48kHz, 48000 samples (1 second = 50 frames)
    watermarked_audio = embed_watermark(clean_audio, sample_rate=48000, watermark_freq=20000.0)
    watermarked_pcm = float32_to_pcm_s16le(watermarked_audio)

    # Ingest watermarked PCM -> Invariant #3: 100% of watermarked frames dropped
    await service.ingest_audio_pcm(meeting_id, participant_id, watermarked_pcm)
    assert pipeline.watermarked_frames_dropped == 50
    assert pipeline.total_frames_processed == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_ingress_multi_participant_isolation() -> None:
    service = AudioIngressService()

    # Participant A in Meeting 1
    pipe_a = await service.get_or_create_pipeline("m1", "p1")
    # Participant B in Meeting 1
    pipe_b = await service.get_or_create_pipeline("m1", "p2")
    # Participant C in Meeting 2
    pipe_c = await service.get_or_create_pipeline("m2", "p3")

    assert service.get_active_pipeline_count() == 3
    assert pipe_a is not pipe_b
    assert pipe_a is not pipe_c


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_ingress_meeting_cleanup() -> None:
    service = AudioIngressService()

    # Create 2 participants in m_cleanup and 1 in m_other
    await service.get_or_create_pipeline("m_cleanup", "p1")
    await service.get_or_create_pipeline("m_cleanup", "p2")
    await service.get_or_create_pipeline("m_other", "p3")
    assert service.get_active_pipeline_count() == 3

    # Cleanup m_cleanup
    await service.cleanup_meeting("m_cleanup")
    assert service.get_active_pipeline_count() == 1

    # Cleanup m_other
    await service.cleanup_meeting("m_other")
    assert service.get_active_pipeline_count() == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_ingress_aggregated_metrics() -> None:
    service = AudioIngressService()

    pipe1 = await service.get_or_create_pipeline("m1", "p1")
    pipe1.total_frames_processed = 100
    pipe1.clean_frames_passed = 80
    pipe1.watermarked_frames_dropped = 20
    pipe1.voiced_segments_produced = 5

    pipe2 = await service.get_or_create_pipeline("m1", "p2")
    pipe2.total_frames_processed = 50
    pipe2.clean_frames_passed = 50
    pipe2.watermarked_frames_dropped = 0
    pipe2.voiced_segments_produced = 2

    metrics = service.get_total_metrics()
    assert metrics["active_pipelines"] == 2
    assert metrics["total_frames_processed"] == 150
    assert metrics["clean_frames_passed"] == 130
    assert metrics["watermarked_frames_dropped"] == 20
    assert metrics["voiced_segments_produced"] == 7
    assert metrics["overall_watermark_drop_ratio"] == pytest.approx(20 / 150)
