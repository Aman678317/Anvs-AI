"""Contract tests for Pipeline Orchestrator, Backpressure & DLQ Resilience (PR-13)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from packages.contracts import (
    DegradationTier,
    PipelineStatusResponse,
    WorkerHealthStatus,
    WorkerHeartbeatPayload,
)
from packages.event_schema import RedisStreamBus
from services.orchestrator.pipeline import PipelineOrchestrator


@pytest.mark.contract
def test_worker_heartbeat_payload_strict_contract() -> None:
    """Verifies WorkerHeartbeatPayload schema integrity, field bounds, and forbidden extra fields."""
    valid_payload_data = {
        "worker_type": "stt",
        "worker_id": "stt_node_01",
        "timestamp_ms": 1710000000000,
        "queue_depth": 5,
        "gpu_utilization_pct": 45.5,
    }

    payload = WorkerHeartbeatPayload.model_validate(valid_payload_data)
    assert payload.worker_type == "stt"
    assert payload.worker_id == "stt_node_01"
    assert payload.queue_depth == 5
    assert payload.gpu_utilization_pct == 45.5

    # 1. Extra attributes strictly forbidden
    with pytest.raises(ValidationError):
        WorkerHeartbeatPayload.model_validate(
            {**valid_payload_data, "unauthorized_extra_field": "illegal"}
        )

    # 2. Negative queue depth forbidden (ge=0)
    with pytest.raises(ValidationError):
        WorkerHeartbeatPayload.model_validate({**valid_payload_data, "queue_depth": -1})

    # 3. GPU utilization boundary violation (>100.0 or <0.0)
    with pytest.raises(ValidationError):
        WorkerHeartbeatPayload.model_validate({**valid_payload_data, "gpu_utilization_pct": 105.0})
    with pytest.raises(ValidationError):
        WorkerHeartbeatPayload.model_validate({**valid_payload_data, "gpu_utilization_pct": -5.0})

    # 4. JSON serialization and deserialization roundtrip
    serialized = payload.model_dump_json()
    reloaded = WorkerHeartbeatPayload.model_validate_json(serialized)
    assert reloaded.worker_id == payload.worker_id
    assert reloaded.timestamp_ms == payload.timestamp_ms


@pytest.mark.contract
def test_pipeline_status_response_strict_contract() -> None:
    """Verifies PipelineStatusResponse contract conformity, types, and forbidden extra fields."""
    status_data = {
        "meeting_id": "meet_contract_101",
        "current_tier": DegradationTier.HIGH_LOAD.value,
        "active_workers": {
            "stt:stt_1": WorkerHealthStatus.HEALTHY.value,
            "tts:tts_1": WorkerHealthStatus.DEGRADED.value,
        },
        "queue_depths": {"transcripts": 65, "audio": 12},
        "dropped_partials_count": 4,
        "uptime_seconds": 120.5,
    }

    response = PipelineStatusResponse.model_validate(status_data)
    assert response.meeting_id == "meet_contract_101"
    assert response.current_tier == DegradationTier.HIGH_LOAD
    assert response.active_workers["stt:stt_1"] == WorkerHealthStatus.HEALTHY
    assert response.dropped_partials_count == 4

    # Extra attributes strictly forbidden
    with pytest.raises(ValidationError):
        PipelineStatusResponse.model_validate({**status_data, "rogue_extra_metric": 9999})

    # JSON roundtrip
    json_bytes = response.model_dump_json()
    reloaded = PipelineStatusResponse.model_validate_json(json_bytes)
    assert reloaded.meeting_id == response.meeting_id
    assert reloaded.current_tier == response.current_tier


@pytest.mark.contract
def test_degradation_tier_contract_enum_values() -> None:
    """Verifies all 4 degradation tier variants required by Document 14."""
    expected_tiers = {"NORMAL", "HIGH_LOAD", "CRITICAL_LOAD", "EMERGENCY"}
    actual_tiers = {tier.value for tier in DegradationTier}
    assert actual_tiers == expected_tiers


@pytest.mark.contract
def test_worker_health_status_contract_enum_values() -> None:
    """Verifies worker health status values match carrier-grade lifecycle states."""
    expected_statuses = {"HEALTHY", "DEGRADED", "DEAD"}
    actual_statuses = {st.value for st in WorkerHealthStatus}
    assert actual_statuses == expected_statuses


@pytest.mark.contract
@pytest.mark.asyncio
async def test_orchestrator_status_generation_conforms_to_contract() -> None:
    """Verifies PipelineOrchestrator.get_pipeline_status produces a certified contract response."""
    mock_bus = MagicMock(spec=RedisStreamBus)
    mock_bus.get_stream_length = AsyncMock(return_value=15)
    mock_bus.trim_stream = AsyncMock(return_value=0)

    orchestrator = PipelineOrchestrator(stream_bus=mock_bus)
    status = await orchestrator.get_pipeline_status("meeting_contract_verify")

    assert isinstance(status, PipelineStatusResponse)
    assert status.meeting_id == "meeting_contract_verify"
    assert status.current_tier == DegradationTier.NORMAL
    assert isinstance(status.queue_depths, dict)
    assert isinstance(status.active_workers, dict)

    # Strict contract validation via re-serialization
    json_str = status.model_dump_json()
    revalidated = PipelineStatusResponse.model_validate_json(json_str)
    assert revalidated.meeting_id == status.meeting_id
