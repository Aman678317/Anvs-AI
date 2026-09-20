"""Contract tests for NMT worker schemas and downstream subscriber compatibility."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from packages.contracts import WSServerCaptionFrame
from packages.event_schema import (
    RedisStreamBus,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from services.realtime_gateway.subscriber import translation_segment_to_caption_frame
from services.translation_worker import MockNMTEngine, NMTConsumer


@pytest.mark.contract
def test_translation_segment_event_strict_contract() -> None:
    """Verifies that TranslationSegmentEvent schema forbids extra attributes and validates bounds."""
    valid_data = {
        "event_id": "evt_nmt_contract_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_contract_001",
        "tenant_id": "tenant_123",
        "source_segment_id": "src_lineage_001",
        "source_language": "eng",
        "target_language": "spa",
        "translated_text": "Hola mundo verificación de contrato",
        "is_final": True,
        "latency_ms": 25,
    }

    event = TranslationSegmentEvent.model_validate(valid_data)
    assert event.source_language == "eng"
    assert event.target_language == "spa"
    assert event.latency_ms == 25

    # 1. Extra attributes forbidden
    with pytest.raises(ValidationError):
        TranslationSegmentEvent.model_validate(
            {**valid_data, "unauthorized_extra_field": "illegal"}
        )

    # 2. Latency must be non-negative
    with pytest.raises(ValidationError):
        TranslationSegmentEvent.model_validate({**valid_data, "latency_ms": -5})

    # 3. Languages must be 3-character ISO-639-3 codes
    with pytest.raises(ValidationError):
        TranslationSegmentEvent.model_validate({**valid_data, "source_language": "en"})

    with pytest.raises(ValidationError):
        TranslationSegmentEvent.model_validate({**valid_data, "target_language": "es"})


@pytest.mark.contract
def test_translation_to_gateway_caption_frame_compatibility() -> None:
    """Verifies that TranslationSegmentEvent seamlessly maps to WSServerCaptionFrame."""
    event = TranslationSegmentEvent(
        event_id="evt_trans_001",
        timestamp_ms=1710000000000,
        meeting_id="meeting_cap_001",
        tenant_id="tenant_cap_001",
        source_segment_id="src_speaker_123_400",
        source_language="eng",
        target_language="spa",
        translated_text="Buenas tardes a todos",
        is_final=True,
        latency_ms=18,
    )

    caption_frame = translation_segment_to_caption_frame(
        event,
        speaker_id="user_speaker_123",
        start_ms=400,
        end_ms=2100,
    )

    assert isinstance(caption_frame, WSServerCaptionFrame)
    # INVARIANT #2 ASSERTION
    assert caption_frame.source_segment_id == "src_speaker_123_400"
    assert caption_frame.speaker_id == "user_speaker_123"
    assert caption_frame.source_language == "eng"
    assert caption_frame.target_language == "spa"
    assert caption_frame.text == "Buenas tardes a todos"
    assert caption_frame.is_final is True
    assert caption_frame.start_ms == 400
    assert caption_frame.end_ms == 2100


@pytest.mark.contract
@pytest.mark.asyncio
async def test_end_to_end_stt_to_nmt_lineage_pipeline() -> None:
    """Verifies complete contract pipeline from SourceSegmentEvent to TranslationSegmentEvent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-pipeline-id"
    mock_bus.ack_event.return_value = 1

    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=MockNMTEngine(simulated_latency_ms=0),
        target_languages=["fra"],
    )

    source_segment_id = "src_lineage_strict_pipeline_9999"
    source_event = SourceSegmentEvent(
        event_id="src_evt_100",
        timestamp_ms=1710000000000,
        meeting_id="meet_pipeline",
        session_id="sess_livekit_99",
        participant_id="user_presenter",
        source_segment_id=source_segment_id,
        language="eng",
        text="Hello world contract verification",
        is_final=True,
        start_ms=1000,
        end_ms=2500,
        confidence=0.97,
        speaker_tag="Presenter",
    )

    emitted_translations = await consumer.process_message(
        stream_name="events:meeting:meet_pipeline:transcripts",
        message_id="300-0",
        raw_payload=source_event.model_dump(),
        meeting_id="meet_pipeline",
    )

    assert len(emitted_translations) == 1
    trans_evt = emitted_translations[0]

    # Invariant #2: SourceSegmentEvent -> TranslationSegmentEvent
    assert trans_evt.source_segment_id == source_segment_id
    assert trans_evt.source_language == "eng"
    assert trans_evt.target_language == "fra"
    assert trans_evt.is_final is True

    # TranslationSegmentEvent -> WSServerCaptionFrame
    caption = translation_segment_to_caption_frame(
        trans_evt,
        speaker_id=source_event.participant_id,
        start_ms=source_event.start_ms,
        end_ms=source_event.end_ms,
    )
    assert caption.source_segment_id == source_segment_id
    assert caption.speaker_id == "user_presenter"
    assert caption.source_language == "eng"
    assert caption.target_language == "fra"
    assert caption.start_ms == 1000
    assert caption.end_ms == 2500
