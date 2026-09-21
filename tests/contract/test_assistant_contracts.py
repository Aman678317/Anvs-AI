"""Contract tests for Assistant worker schemas and downstream WebSocket compatibility."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from packages.contracts import WSServerAssistantFrame
from packages.event_schema import (
    AssistantQueryEvent,
    AssistantResponseEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.assistant_worker import (
    AssistantConsumer,
    IndexedSegment,
    MockAssistantEngine,
    TranscriptVectorStore,
)


@pytest.mark.contract
def test_assistant_events_strict_contract() -> None:
    """Verifies AssistantQueryEvent and AssistantResponseEvent schemas forbid extra attributes."""
    query_data = {
        "event_id": "evt_query_contract_01",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_contract_01",
        "tenant_id": "tenant_123",
        "query_id": "query_uuid_contract_01",
        "participant_id": "part_alex",
        "question": "What was the final decision on database schema?",
    }

    query_event = AssistantQueryEvent.model_validate(query_data)
    assert query_event.query_id == "query_uuid_contract_01"
    assert query_event.question == "What was the final decision on database schema?"

    # Extra attributes forbidden
    with pytest.raises(ValidationError):
        AssistantQueryEvent.model_validate({**query_data, "unauthorized_extra_field": "illegal"})

    response_data = {
        "event_id": "evt_resp_contract_01",
        "timestamp_ms": 1710000000100,
        "meeting_id": "meeting_contract_01",
        "tenant_id": "tenant_123",
        "query_id": "query_uuid_contract_01",
        "answer": "The team approved using PostgreSQL 16 with Row-Level Security.",
        "citations": ["src_lineage_contract_01"],
        "action_items": ["DevOps will apply migrations on Friday."],
    }

    response_event = AssistantResponseEvent.model_validate(response_data)
    assert response_event.citations == ["src_lineage_contract_01"]

    with pytest.raises(ValidationError):
        AssistantResponseEvent.model_validate(
            {**response_data, "unauthorized_extra_field": "illegal"}
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_full_stt_assistant_citation_lineage_contract() -> None:
    """Verifies complete lineage contract from SourceSegmentEvent -> AssistantResponse citations."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-asst-pipeline"
    mock_bus.ack_event.return_value = 1

    engine = MockAssistantEngine(simulated_latency_ms=0)
    store = TranscriptVectorStore()
    consumer = AssistantConsumer(stream_bus=mock_bus, engine=engine, vector_store=store)

    canonical_lineage_id = "lineage_strict_asst_uuid_9999"
    stt_event = SourceSegmentEvent(
        event_id="stt_evt_asst_99",
        timestamp_ms=1710000000000,
        meeting_id="meet_lineage_asst",
        tenant_id="tenant_asst",
        session_id="sess_asst",
        participant_id="part_cto",
        source_segment_id=canonical_lineage_id,
        language="eng",
        text="The consensus is to deploy microservices onto Kubernetes clusters.",
        is_final=True,
        start_ms=0,
        end_ms=3500,
        confidence=0.99,
    )

    # 1. Index transcript segment
    await consumer.process_transcript_message(
        stream_name="events:meeting:meet_lineage_asst:transcripts",
        message_id="10-0",
        raw_payload=stt_event.model_dump(),
        meeting_id="meet_lineage_asst",
    )

    # 2. Query assistant
    query_event = AssistantQueryEvent(
        event_id="query_evt_99",
        timestamp_ms=1710000005000,
        meeting_id="meet_lineage_asst",
        tenant_id="tenant_asst",
        query_id="query_lineage_99",
        participant_id="part_eng",
        question="Where will microservices be deployed?",
    )

    response = await consumer.process_query_message(
        stream_name="events:meeting:meet_lineage_asst:assistant",
        message_id="11-0",
        raw_payload=query_event.model_dump(),
        meeting_id="meet_lineage_asst",
    )

    assert response is not None
    # Invariant #2: Source segment citation lineage
    assert canonical_lineage_id in response.citations

    # JSON roundtrip preservation
    serialized = response.model_dump_json()
    reloaded = AssistantResponseEvent.model_validate_json(serialized)
    assert canonical_lineage_id in reloaded.citations


@pytest.mark.contract
def test_assistant_response_to_websocket_frame_compatibility() -> None:
    """Verifies that AssistantResponseEvent cleanly transforms into WSServerAssistantFrame."""
    response_event = AssistantResponseEvent(
        event_id="evt_asst_ws_01",
        timestamp_ms=1710000000000,
        meeting_id="meet_ws",
        tenant_id="tenant_ws",
        query_id="query_ws_555",
        answer="We confirmed that the ultrasonic 20 kHz watermark prevents echo loops.",
        citations=["src_seg_wm_01"],
        action_items=["Maintain watermark detector at 20 kHz threshold."],
    )

    ws_frame = WSServerAssistantFrame(
        query_id=response_event.query_id,
        answer=response_event.answer,
        citations=response_event.citations,
        action_items=response_event.action_items,
    )

    assert ws_frame.query_id == "query_ws_555"
    assert "ultrasonic 20 kHz" in ws_frame.answer
    assert ws_frame.citations == ["src_seg_wm_01"]
    assert len(ws_frame.action_items) == 1
