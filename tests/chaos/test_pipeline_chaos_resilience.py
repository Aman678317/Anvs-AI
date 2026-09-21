"""Chaos Engineering & Fault-Injection Resilience Suite (PR-19).

Tests platform resilience under simulated systemic failure modes:
1. Worker crash & sub-3.0s failure detection SLA.
2. Abandoned Pending Entries List (PEL) message re-claim without data loss.
3. High-volume acoustic watermark feedback loop rejection.
4. Malformed poison-pill payload flooding with terminal quarantine.
"""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.ingestion import AudioIngestionPipeline
from packages.audio.watermark import embed_watermark
from packages.contracts import WorkerHealthStatus
from packages.event_schema.events import DeadLetterEvent
from services.orchestrator.dlq_retry import DLQRetryManager
from services.orchestrator.heartbeat import WorkerHealthMonitor
from services.orchestrator.pipeline import PipelineOrchestrator


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_worker_crash_detected_within_three_seconds() -> None:
    """Worker crash or network partition must be identified within the 3.0s SLA."""
    monitor = WorkerHealthMonitor(timeout_sec=3.0)
    worker_id = "stt_worker_us_east_1"
    worker_type = "stt"

    # Worker reports healthy heartbeat at t=100.0
    monitor.record_heartbeat(worker_id, worker_type, now=100.0)
    assert monitor.get_worker_health(worker_id, now=101.5) == WorkerHealthStatus.HEALTHY

    # At t=103.5 (> 3.0s without heartbeat), worker must be classified DEAD or DEGRADED
    health = monitor.get_worker_health(worker_id, now=103.5)
    assert health in (WorkerHealthStatus.DEGRADED, WorkerHealthStatus.DEAD)

    # At t=107.0 (> 2x timeout), worker is strictly DEAD
    assert monitor.get_worker_health(worker_id, now=107.0) == WorkerHealthStatus.DEAD


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_pel_recovery_after_worker_crash() -> None:
    """Orchestrator re-claims abandoned pending messages (PEL) from crashed workers."""
    mock_bus = AsyncMock()
    # Mock xautoclaim returning 2 abandoned messages
    mock_bus.claim_abandoned_messages.return_value = [
        ("1700000000000-0", {"source_segment_id": "seg_001", "is_final": "true"}),
        ("1700000000001-0", {"source_segment_id": "seg_002", "is_final": "true"}),
    ]

    orchestrator = PipelineOrchestrator(bus=mock_bus)
    reclaimed = await orchestrator.recover_abandoned_messages(
        stream_name="events:meeting:test:transcripts",
        group_name="nmt-workers-group",
        consumer_name="orchestrator_reclaim_worker",
        min_idle_time_ms=3000,
    )

    assert len(reclaimed) == 2
    mock_bus.claim_abandoned_messages.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_acoustic_watermark_feedback_storm_rejected() -> None:
    """High-volume continuous 20 kHz acoustic watermark injection must be 100% dropped."""
    mock_bus = AsyncMock()
    pipeline = AudioIngestionPipeline(
        meeting_id="meet_chaos_feedback",
        bus=mock_bus,
    )

    sample_rate = 48000
    # 20ms frame = 960 samples
    samples_per_frame = 960
    t = np.linspace(0, 0.02, samples_per_frame, endpoint=False, dtype=np.float32)
    clean_audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz standard speech tone
    watermarked_audio = embed_watermark(clean_audio, sample_rate=sample_rate)

    # Ingest 250 consecutive watermarked frames (5 seconds of synthetic audio loop)
    watermarked_bytes = (watermarked_audio * 32767.0).astype(np.int16).tobytes()
    for _ in range(250):
        await pipeline.process_audio_chunk(
            audio_data=watermarked_bytes,
            participant_id="part_loop_attacker",
        )

    # Every single watermarked frame must be dropped
    assert pipeline.watermarked_frames_dropped == 250
    # Zero audio segments should have been published to Redis
    mock_bus.publish.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_poison_pill_flooding_quarantined_after_retries() -> None:
    """Poison-pill payloads are retried with backoff and permanently quarantined after 3 attempts."""
    mock_bus = AsyncMock()
    retry_manager = DLQRetryManager(bus=mock_bus, max_retries=3, base_backoff_sec=0.01)

    corrupt_event = DeadLetterEvent(
        original_stream="events:meeting:test:audio",
        error_message="Corrupted unparsable Opus bitstream",
        retry_count=0,
        payload={"corrupted": True, "magic_byte": "0xFF"},
    )

    # First attempt: Retry count incremented and re-enqueued
    should_retry = await retry_manager.handle_dlq_event(corrupt_event)
    assert should_retry is True
    assert corrupt_event.retry_count == 1
    mock_bus.publish.assert_awaited()

    # Advance retry count to maximum limit (3)
    corrupt_event.retry_count = 3
    should_retry_final = await retry_manager.handle_dlq_event(corrupt_event)
    # Exceeded max retries: must be permanently quarantined
    assert should_retry_final is False
    assert retry_manager.quarantined_count == 1
