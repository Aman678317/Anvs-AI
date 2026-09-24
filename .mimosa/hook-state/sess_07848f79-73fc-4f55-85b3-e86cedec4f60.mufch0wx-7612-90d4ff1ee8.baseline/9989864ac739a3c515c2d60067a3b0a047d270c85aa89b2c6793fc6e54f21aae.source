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
from packages.contracts import WorkerHealthStatus, WorkerHeartbeatPayload
from packages.event_schema.events import DeadLetterEvent
from services.orchestrator.dlq_retry import DLQRetryManager, DLQRetryOutcome
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
    payload = WorkerHeartbeatPayload(
        worker_id=worker_id,
        worker_type=worker_type,
        timestamp_ms=100000,
    )
    monitor.record_heartbeat(payload)
    key = monitor.get_worker_key(worker_type, worker_id)
    monitor._workers[key]["last_seen"] = 100.0

    st_1 = monitor.evaluate_liveness(now=101.5)
    assert st_1[key] == WorkerHealthStatus.HEALTHY

    # At t=103.5 (> 3.0s without heartbeat), worker must be classified DEAD or DEGRADED
    st_2 = monitor.evaluate_liveness(now=103.5)
    assert st_2[key] in (WorkerHealthStatus.DEGRADED, WorkerHealthStatus.DEAD)

    # At t=107.0 (> 2x timeout), worker is strictly DEAD
    st_3 = monitor.evaluate_liveness(now=107.0)
    assert st_3[key] == WorkerHealthStatus.DEAD


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_pel_recovery_after_worker_crash() -> None:
    """Orchestrator re-claims abandoned pending messages (PEL) from crashed workers."""
    mock_bus = AsyncMock()
    # Mock claim_pending_events returning 2 abandoned messages
    mock_bus.claim_pending_events.return_value = [
        ("1700000000000-0", {"source_segment_id": "seg_001", "is_final": "true"}),
        ("1700000000001-0", {"source_segment_id": "seg_002", "is_final": "true"}),
    ]

    orchestrator = PipelineOrchestrator(stream_bus=mock_bus)
    reclaimed = await orchestrator.recover_stuck_messages(
        meeting_id="test_meeting",
        stream_type="transcripts",
        group_name="nmt-workers-group",
        consumer_name="orchestrator_reclaim_worker",
        min_idle_ms=3000,
    )

    assert len(reclaimed) == 2
    mock_bus.claim_pending_events.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_acoustic_watermark_feedback_storm_rejected() -> None:
    """High-volume continuous 20 kHz acoustic watermark injection must be 100% dropped."""
    mock_bus = AsyncMock()
    pipeline = AudioIngestionPipeline(
        meeting_id="meet_chaos_feedback",
        participant_id="part_loop_attacker",
        stream_bus=mock_bus,
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
        await pipeline.process_pcm_bytes(watermarked_bytes)

    # Every single watermarked frame must be dropped
    assert pipeline.watermarked_frames_dropped == 250
    # Zero audio segments should have been produced
    assert pipeline.voiced_segments_produced == 0


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_poison_pill_flooding_quarantined_after_retries() -> None:
    """Poison-pill payloads retried with backoff and permanently quarantined after 3 attempts."""
    mock_bus = AsyncMock()
    mock_bus.client = AsyncMock()
    retry_manager = DLQRetryManager(stream_bus=mock_bus, max_retries=3, base_backoff_sec=0.01)

    corrupt_event = DeadLetterEvent(
        event_id="dlq_evt_001",
        timestamp_ms=1710000000000,
        meeting_id="meet_chaos_poison",
        failed_event_id="evt_poison_001",
        original_stream="events:meeting:test:audio",
        error_reason="Corrupted unparsable Opus bitstream",
        retry_count=0,
        raw_payload='{"corrupted": true, "magic_byte": "0xFF"}',
    )

    # First attempt: Retry count incremented and re-enqueued
    outcome = await retry_manager.process_dlq_event(
        dlq_event=corrupt_event,
        dlq_message_id="1700000000000-0",
        dlq_stream="events:meeting:test:dlq",
    )
    assert outcome == DLQRetryOutcome.RETRIED
    assert retry_manager.retried_count == 1
    mock_bus.client.xadd.assert_awaited()

    # Advance retry count to maximum limit (3)
    corrupt_event_final = DeadLetterEvent(
        event_id="dlq_evt_002",
        timestamp_ms=1710000000100,
        meeting_id="meet_chaos_poison",
        failed_event_id="evt_poison_001",
        original_stream="events:meeting:test:audio",
        error_reason="Corrupted unparsable Opus bitstream",
        retry_count=3,
        raw_payload='{"corrupted": true, "magic_byte": "0xFF"}',
    )
    outcome_final = await retry_manager.process_dlq_event(
        dlq_event=corrupt_event_final,
        dlq_message_id="1700000000001-0",
        dlq_stream="events:meeting:test:dlq",
    )
    # Exceeded max retries: must be permanently quarantined
    assert outcome_final == DLQRetryOutcome.QUARANTINED
    assert retry_manager.quarantined_count == 1


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_redis_stream_trimming_chaos_under_memory_pressure() -> None:
    """Simulates high-velocity stream message flood with active XTRIM memory capping (P1-06)."""
    mock_bus = AsyncMock()
    mock_bus.trim_stream.return_value = 250

    orchestrator = PipelineOrchestrator(
        stream_bus=mock_bus,
        stream_maxlen=1000,
    )
    meeting_id = "meet_chaos_flood_99"

    # Simulate 5 consecutive bursts of stream trimming
    total_trimmed = 0
    for _ in range(5):
        trim_res = await orchestrator.trim_meeting_streams(meeting_id)
        total_trimmed += sum(trim_res.values())

    # 7 streams * 250 trimmed per call * 5 bursts
    assert total_trimmed == 7 * 250 * 5
    assert mock_bus.trim_stream.await_count == 35
