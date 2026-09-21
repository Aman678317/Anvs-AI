"""Contract tests for Diarization worker schemas and downstream subscriber compatibility."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from packages.contracts import WSServerCaptionFrame
from packages.event_schema import (
    DiarizationSegmentEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.speaker_worker import MockSpeakerEngine, SpeakerConsumer


@pytest.mark.contract
def test_diarization_segment_event_strict_contract() -> None:
    """Verifies DiarizationSegmentEvent schema strictly forbids extra attributes and bounds."""
    valid_data = {
        "event_id": "evt_diar_contract_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_contract_001",
        "tenant_id": "tenant_123",
        "source_segment_id": "src_lineage_001",
        "speaker_id": "speaker_alice",
        "speaker_name": "Alice Walker",
        "confidence": 0.96,
    }

    event = DiarizationSegmentEvent.model_validate(valid_data)
    assert event.speaker_id == "speaker_alice"
    assert event.speaker_name == "Alice Walker"
    assert event.confidence == 0.96

    # 1. Extra attributes forbidden
    with pytest.raises(ValidationError):
        DiarizationSegmentEvent.model_validate(
            {**valid_data, "unauthorized_extra_field": "illegal"}
        )

    # 2. Confidence must be within [0.0, 1.0]
    with pytest.raises(ValidationError):
        DiarizationSegmentEvent.model_validate({**valid_data, "confidence": 1.5})

    with pytest.raises(ValidationError):
        DiarizationSegmentEvent.model_validate({**valid_data, "confidence": -0.1})


@pytest.mark.contract
@pytest.mark.asyncio
async def test_full_stt_diarization_lineage_pipeline_contract() -> None:
    """Verifies complete lineage contract from SourceSegmentEvent -> DiarizationSegmentEvent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-diar-pipeline"
    mock_bus.ack_event.return_value = 1

    engine = MockSpeakerEngine(simulated_latency_ms=0)
    consumer = SpeakerConsumer(stream_bus=mock_bus, engine=engine)

    canonical_lineage_id = "lineage_strict_chain_uuid_5555"
    stt_event = SourceSegmentEvent(
        event_id="stt_evt_55",
        timestamp_ms=1710000000000,
        meeting_id="meet_chain",
        tenant_id="tenant_chain",
        session_id="sess_chain",
        participant_id="part_lead",
        source_segment_id=canonical_lineage_id,
        language="eng",
        text="The quarterly figures show strong revenue expansion.",
        is_final=True,
        start_ms=0,
        end_ms=3000,
        confidence=0.99,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_chain:transcripts",
        message_id="80-0",
        raw_payload=stt_event.model_dump(),
        meeting_id="meet_chain",
    )

    assert len(emitted) == 1
    diar_event = emitted[0]

    # Invariant #2: Source segment lineage verification
    assert diar_event.source_segment_id == canonical_lineage_id
    assert diar_event.tenant_id == "tenant_chain"
    assert diar_event.meeting_id == "meet_chain"

    # JSON roundtrip lineage test
    serialized = diar_event.model_dump_json()
    reloaded = DiarizationSegmentEvent.model_validate_json(serialized)
    assert reloaded.source_segment_id == canonical_lineage_id


@pytest.mark.contract
def test_diarization_to_caption_frame_speaker_enrichment_contract() -> None:
    """Verifies that DiarizationSegmentEvent fields enrich WSServerCaptionFrame seamlessly."""
    diar_event = DiarizationSegmentEvent(
        event_id="diar_enrich_01",
        timestamp_ms=1710000000000,
        meeting_id="meet_enrich",
        tenant_id="tenant_1",
        source_segment_id="src_enrich_123",
        speaker_id="speaker_bob",
        speaker_name="Bob Martinez",
        confidence=0.94,
    )

    caption_frame = WSServerCaptionFrame(
        source_segment_id=diar_event.source_segment_id,
        speaker_id=diar_event.speaker_id,
        source_language="eng",
        target_language="eng",
        text="Welcome to the meeting.",
        is_final=True,
        start_ms=0,
        end_ms=2000,
    )

    assert caption_frame.speaker_id == "speaker_bob"
    assert caption_frame.source_segment_id == diar_event.source_segment_id
    assert diar_event.speaker_name == "Bob Martinez"
