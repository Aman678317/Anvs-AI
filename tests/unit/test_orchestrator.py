"""Unit tests for Pipeline Orchestration, Backpressure & DLQ Recovery (PR-16)."""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.contracts import (
    DegradationTier,
    WorkerHealthStatus,
    WorkerHeartbeatPayload,
)
from packages.event_schema import DeadLetterEvent, RedisStreamBus
from services.orchestrator import (
    BackpressureController,
    DLQRetryManager,
    DLQRetryOutcome,
    PipelineOrchestrator,
    WorkerHealthMonitor,
)


@pytest.fixture
def mock_stream_bus() -> MagicMock:
    """Mock RedisStreamBus for testing orchestrator interactions."""
    bus = MagicMock(spec=RedisStreamBus)
    bus.client = AsyncMock()
    bus.client.xlen = AsyncMock(return_value=0)
    bus.client.xadd = AsyncMock(return_value="1710000000000-0")
    bus.create_consumer_group = AsyncMock(return_value=True)
    bus.ack_event = AsyncMock(return_value=1)
    bus.consume_events = AsyncMock(return_value=[])
    bus.claim_pending_events = AsyncMock(return_value=[])
    bus.get_stream_length = AsyncMock(return_value=0)
    return bus


# -----------------------------------------------------------------------------
# Unit Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
def test_backpressure_shedding_drops_partials_preserves_finals() -> None:
    """Invariant DoD: Finals must NEVER be shed; partials are dropped under high load."""
    controller = BackpressureController(high_threshold=50, critical_threshold=100)

    # 1. In NORMAL tier: all segments admitted
    assert controller.current_tier == DegradationTier.NORMAL
    assert controller.should_process_segment(is_final=True) is True
    assert controller.should_process_segment(is_final=False) is True
    assert controller.dropped_partials_count == 0

    # 2. In HIGH_LOAD tier: partials dropped, finals preserved
    controller.evaluate_queue_depths({"audio": 60})
    assert controller.current_tier == DegradationTier.HIGH_LOAD

    assert controller.should_process_segment(is_final=True) is True
    assert controller.should_process_segment(is_final=False) is False
    assert controller.dropped_partials_count == 1

    # 3. In CRITICAL_LOAD tier: partials dropped, finals still preserved
    controller.evaluate_queue_depths({"audio": 120})
    assert controller.current_tier == DegradationTier.CRITICAL_LOAD

    assert controller.should_process_segment(is_final=True) is True
    assert controller.should_process_segment(is_final=False) is False
    assert controller.dropped_partials_count == 2


@pytest.mark.unit
def test_degradation_tier_transitions_with_cooldown() -> None:
    """Immediate upward escalation, but downward recovery requires cooldown hysteresis."""
    controller = BackpressureController(
        high_threshold=50,
        critical_threshold=100,
        cooldown_sec=5.0,
    )

    # Immediate escalation to HIGH_LOAD
    tier = controller.evaluate_queue_depths({"transcripts": 55})
    assert tier == DegradationTier.HIGH_LOAD

    # Immediate escalation to CRITICAL_LOAD
    tier = controller.evaluate_queue_depths({"transcripts": 110})
    assert tier == DegradationTier.CRITICAL_LOAD

    # Queue drops to normal, but cooldown not elapsed -> remains CRITICAL_LOAD
    tier = controller.evaluate_queue_depths({"transcripts": 10})
    assert tier == DegradationTier.CRITICAL_LOAD

    # Simulate time advancing past cooldown
    controller._last_transition_time -= 6.0
    tier = controller.evaluate_queue_depths({"transcripts": 10})
    assert tier == DegradationTier.NORMAL


@pytest.mark.unit
def test_worker_heartbeat_and_failure_detection() -> None:
    """Worker liveness evaluates to HEALTHY, DEGRADED, and DEAD (<3.0s SLA)."""
    monitor = WorkerHealthMonitor(timeout_sec=3.0)
    t0 = time.time()

    # Record heartbeats
    monitor.record_heartbeat(
        WorkerHeartbeatPayload(
            worker_type="stt",
            worker_id="stt-node-1",
            timestamp_ms=int(t0 * 1000),
            queue_depth=5,
        )
    )
    monitor.record_heartbeat(
        WorkerHeartbeatPayload(
            worker_type="tts",
            worker_id="tts-node-1",
            timestamp_ms=int(t0 * 1000),
            queue_depth=2,
        )
    )

    # At t0: both healthy
    liveness_t0 = monitor.evaluate_liveness(now=t0)
    assert liveness_t0["stt:stt-node-1"] == WorkerHealthStatus.HEALTHY
    assert liveness_t0["tts:tts-node-1"] == WorkerHealthStatus.HEALTHY

    # At t0 + 4.0s (past 3.0s timeout): DEGRADED
    liveness_t4 = monitor.evaluate_liveness(now=t0 + 4.0)
    assert liveness_t4["stt:stt-node-1"] == WorkerHealthStatus.DEGRADED

    # At t0 + 7.0s (past 2 * 3.0s timeout): DEAD
    liveness_t7 = monitor.evaluate_liveness(now=t0 + 7.0)
    assert liveness_t7["stt:stt-node-1"] == WorkerHealthStatus.DEAD
    assert liveness_t7["tts:tts-node-1"] == WorkerHealthStatus.DEAD

    # Aggregate status
    aggr = monitor.get_aggregate_health_by_type(liveness_t7)
    assert aggr["stt"] == WorkerHealthStatus.DEAD
    assert aggr["tts"] == WorkerHealthStatus.DEAD


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dlq_retry_loop_with_exponential_backoff(mock_stream_bus: MagicMock) -> None:
    """Dead letter queue retries transient failures with backoff and quarantines poison pills."""
    manager = DLQRetryManager(
        stream_bus=mock_stream_bus,
        max_retries=3,
        base_backoff_sec=0.5,
    )

    # 1. Transient failure (retry_count=0): should RETRY
    event_retry = DeadLetterEvent(
        event_id=f"dlq-{uuid.uuid4()}",
        timestamp_ms=int(time.time() * 1000),
        meeting_id="meet_101",
        failed_event_id="evt_err_001",
        original_stream="events:meeting:meet_101:translations",
        error_reason="ConnectionResetError to model service",
        retry_count=0,
        raw_payload='{"event_id": "evt_err_001", "retry_count": 0}',
    )

    outcome1 = await manager.process_dlq_event(
        dlq_event=event_retry,
        dlq_message_id="msg_dlq_1",
        dlq_stream="events:meeting:meet_101:dlq",
    )
    assert outcome1 == DLQRetryOutcome.RETRIED
    assert manager.retried_count == 1
    assert mock_stream_bus.client.xadd.awaited
    assert mock_stream_bus.ack_event.awaited

    # Verify backoff calculation: 0.5 * 2^0 = 0.5s, 0.5 * 2^1 = 1.0s, 0.5 * 2^2 = 2.0s
    assert manager.calculate_backoff(0) == 0.5
    assert manager.calculate_backoff(1) == 1.0
    assert manager.calculate_backoff(2) == 2.0

    # 2. Poison Pill failure (retry_count=3 >= max_retries): should QUARANTINE
    event_poison = DeadLetterEvent(
        event_id=f"dlq-{uuid.uuid4()}",
        timestamp_ms=int(time.time() * 1000),
        meeting_id="meet_101",
        failed_event_id="evt_poison_002",
        original_stream="events:meeting:meet_101:transcripts",
        error_reason="UnicodeDecodeError / corrupt packet",
        retry_count=3,
        raw_payload='{"corrupt": true}',
    )

    outcome2 = await manager.process_dlq_event(
        dlq_event=event_poison,
        dlq_message_id="msg_dlq_2",
        dlq_stream="events:meeting:meet_101:dlq",
    )
    assert outcome2 == DLQRetryOutcome.QUARANTINED
    assert manager.quarantined_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_recovery_and_failover_within_three_seconds(
    mock_stream_bus: MagicMock,
) -> None:
    """When TTS crashes, orchestrator degrades to Captions Only and re-claims pending messages."""
    orchestrator = PipelineOrchestrator(stream_bus=mock_stream_bus)
    meeting_id = str(uuid.uuid4())
    t0 = time.time()

    # Worker heartbeats: STT and NMT are alive, TTS last seen 7 seconds ago (DEAD)
    orchestrator.record_worker_heartbeat(
        WorkerHeartbeatPayload(
            worker_type="stt",
            worker_id="stt-1",
            timestamp_ms=int(t0 * 1000),
        )
    )
    orchestrator.record_worker_heartbeat(
        WorkerHeartbeatPayload(
            worker_type="nmt",
            worker_id="nmt-1",
            timestamp_ms=int(t0 * 1000),
        )
    )
    orchestrator.record_worker_heartbeat(
        WorkerHeartbeatPayload(
            worker_type="tts",
            worker_id="tts-crashed",
            timestamp_ms=int((t0 - 7.0) * 1000),
        )
    )
    # Fast-forward monitor's internal clock for tts-crashed
    orchestrator.health_monitor._workers["tts:tts-crashed"]["last_seen"] = t0 - 7.0

    # Pipeline update
    active_tier = await orchestrator.update_pipeline_state(meeting_id, now=t0)
    assert active_tier == DegradationTier.CRITICAL_LOAD

    # Should bypass TTS and route to captions only
    assert orchestrator.should_synthesize_speech() is False

    # Simulate reclaiming abandoned messages from dead TTS worker within 3s SLA
    mock_stream_bus.claim_pending_events.return_value = [("msg-101", {"payload": "{}"})]
    recovered = await orchestrator.recover_stuck_messages(
        meeting_id=meeting_id,
        stream_type="translations",
        group_name="tts-workers-group",
        consumer_name="tts-recovery-worker",
        min_idle_ms=3000,
    )
    assert len(recovered) == 1
    assert recovered[0][0] == "msg-101"

    # Status response check
    status = await orchestrator.get_pipeline_status(meeting_id)
    assert status.meeting_id == meeting_id
    assert status.current_tier == DegradationTier.CRITICAL_LOAD
    assert status.active_workers["tts:tts-crashed"] == WorkerHealthStatus.DEAD
