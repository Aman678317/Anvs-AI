"""Unit tests for Streaming NMT Worker Service adhering to Document 14."""

import time
from unittest.mock import AsyncMock

import pytest

from packages.event_schema import RedisStreamBus, SourceSegmentEvent
from services.translation_worker import (
    BaseNMTEngine,
    ContextWindowBuffer,
    MockNMTEngine,
    NLLBTranslationEngine,
    NMTConsumer,
    create_nmt_engine,
    iso639_3_to_nllb,
    nllb_to_iso639_3,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_nmt_engine_translation() -> None:
    """Verifies deterministic multi-pair translation accuracy in MockNMTEngine."""
    engine = MockNMTEngine(simulated_latency_ms=0)

    # 1. Known dictionary phrase
    phrase = "Welcome everyone to our multilingual meeting, let's begin the review."
    target_languages = ["spa", "fra", "deu", "zho", "jpn", "hin"]

    for tgt in target_languages:
        result = await engine.translate(phrase, source_lang="eng", target_lang=tgt)
        assert result.source_language == "eng"
        assert result.target_language == tgt
        assert len(result.translated_text) > 0
        assert result.latency_ms >= 0

    # 2. Word-by-word fallback for novel text
    novel_text = "Good morning everyone"
    res_spa = await engine.translate(novel_text, source_lang="eng", target_lang="spa")
    assert "buenos" in res_spa.translated_text.lower()
    assert "dias" in res_spa.translated_text.lower() or "días" in res_spa.translated_text.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_nmt_engine_latency_sla() -> None:
    """Verifies that NMT translation latency satisfies <250ms SLA."""
    engine = MockNMTEngine(simulated_latency_ms=10)

    t0 = time.perf_counter()
    result = await engine.translate(
        "Can everyone hear me clearly?",
        source_lang="eng",
        target_lang="fra",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert result.latency_ms >= 10
    assert elapsed_ms < 250.0, f"Translation latency {elapsed_ms}ms exceeded 250ms SLA"


@pytest.mark.unit
def test_flores200_language_mapping() -> None:
    """Verifies bidirectional mapping between ISO-639-3 and FLORES-200 tags."""
    assert iso639_3_to_nllb("eng") == "eng_Latn"
    assert iso639_3_to_nllb("spa") == "spa_Latn"
    assert iso639_3_to_nllb("fra") == "fra_Latn"
    assert iso639_3_to_nllb("deu") == "deu_Latn"
    assert iso639_3_to_nllb("zho") == "zho_Hans"
    assert iso639_3_to_nllb("jpn") == "jpn_Jpan"
    assert iso639_3_to_nllb("hin") == "hin_Deva"
    assert iso639_3_to_nllb("unknown_code") == "eng_Latn"

    assert nllb_to_iso639_3("eng_Latn") == "eng"
    assert nllb_to_iso639_3("spa_Latn") == "spa"
    assert nllb_to_iso639_3("fra_Latn") == "fra"
    assert nllb_to_iso639_3("deu_Latn") == "deu"
    assert nllb_to_iso639_3("unknown_tag") == "eng"


@pytest.mark.unit
def test_context_window_buffer() -> None:
    """Verifies FIFO sliding queue of preceding 2 sentences per participant."""
    buf = ContextWindowBuffer(max_sentences=2)
    meeting_id = "meet_001"
    speaker_id = "part_alpha"

    # Initially empty
    assert buf.get_context(meeting_id, speaker_id) == []

    # 1. Add first sentence
    buf.add_utterance(meeting_id, speaker_id, "Hello everyone.")
    assert buf.get_context(meeting_id, speaker_id) == ["Hello everyone."]

    # 2. Add second sentence
    buf.add_utterance(meeting_id, speaker_id, "Welcome to the presentation.")
    assert buf.get_context(meeting_id, speaker_id) == [
        "Hello everyone.",
        "Welcome to the presentation.",
    ]

    # 3. Add third sentence -> sliding FIFO drops first
    buf.add_utterance(meeting_id, speaker_id, "Let's review the architectural invariants.")
    assert buf.get_context(meeting_id, speaker_id) == [
        "Welcome to the presentation.",
        "Let's review the architectural invariants.",
    ]

    # Format context prefix
    formatted = buf.format_context_prefix(meeting_id, speaker_id, "Next slide please.")
    assert "Welcome to the presentation." in formatted
    assert formatted.endswith("Next slide please.")

    # Clear participant
    buf.clear_participant(meeting_id, speaker_id)
    assert buf.get_context(meeting_id, speaker_id) == []


@pytest.mark.unit
def test_create_nmt_engine_factory() -> None:
    """Verifies NMT engine factory creates mock and NLLB engine instances."""
    mock_eng = create_nmt_engine("mock")
    assert isinstance(mock_eng, MockNMTEngine)
    assert isinstance(mock_eng, BaseNMTEngine)

    nllb_eng = create_nmt_engine("nllb", allow_fallback=True)
    assert isinstance(nllb_eng, NLLBTranslationEngine)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_preserves_source_segment_id() -> None:
    """Verifies Invariant #2: Immutable source lineage preservation in NMT worker."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-nmt-123"
    mock_bus.ack_event.return_value = 1

    engine = MockNMTEngine(simulated_latency_ms=0)
    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        target_languages=["spa"],
    )

    custom_lineage_id = "lineage_strict_transcript_uuid_7777"
    source_event = SourceSegmentEvent(
        event_id="trans_001",
        timestamp_ms=1710000000000,
        meeting_id="meeting_lineage_test",
        session_id="sess_001",
        participant_id="user_host",
        source_segment_id=custom_lineage_id,
        language="eng",
        text="Welcome everyone to our multilingual meeting, let's begin the review.",
        is_final=True,
        start_ms=0,
        end_ms=2500,
        confidence=0.98,
        speaker_tag="Host",
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_lineage_test:transcripts",
        message_id="50-0",
        raw_payload=source_event.model_dump(),
        meeting_id="meeting_lineage_test",
    )

    assert len(emitted) == 1
    # INVARIANT #2 CRITICAL ASSERTION:
    assert emitted[0].source_segment_id == custom_lineage_id
    assert emitted[0].source_language == "eng"
    assert emitted[0].target_language == "spa"
    assert emitted[0].is_final is True
    assert len(emitted[0].translated_text) > 0

    mock_bus.publish.assert_awaited_once()
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meeting_lineage_test:transcripts",
        consumer.group_name,
        "50-0",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_dynamic_target_routing() -> None:
    """Verifies concurrent multi-target translation emission for room participants."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-publish"
    mock_bus.ack_event.return_value = 1

    engine = MockNMTEngine(simulated_latency_ms=0)
    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        target_languages=["spa", "fra", "deu"],
    )

    payload = {
        "event_id": "trans_multi",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_multi",
        "tenant_id": "tenant_1",
        "session_id": "sess_1",
        "participant_id": "user_speaker",
        "source_segment_id": "src_seg_multi_001",
        "language": "eng",
        "text": "Hello world contract verification",
        "is_final": True,
        "start_ms": 0,
        "end_ms": 1000,
        "confidence": 0.95,
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_multi:transcripts",
        message_id="51-0",
        raw_payload=payload,
        meeting_id="meet_multi",
    )

    assert len(emitted) == 3
    targets_emitted = {evt.target_language for evt in emitted}
    assert targets_emitted == {"spa", "fra", "deu"}
    assert mock_bus.publish.call_count == 3
    assert consumer.metrics["translations_emitted"] == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_skips_identical_source_target() -> None:
    """Verifies that translation is skipped when target language equals source language."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.ack_event.return_value = 1

    engine = MockNMTEngine(simulated_latency_ms=0)
    # Only target is 'spa', and source speech is also 'spa'
    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        target_languages=["spa"],
    )

    payload = {
        "event_id": "trans_same_lang",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_same",
        "tenant_id": "tenant_1",
        "session_id": "sess_1",
        "participant_id": "user_speaker",
        "source_segment_id": "src_seg_spa_001",
        "language": "spa",
        "text": "Buenas tardes",
        "is_final": True,
        "start_ms": 0,
        "end_ms": 1000,
        "confidence": 0.95,
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_same:transcripts",
        message_id="52-0",
        raw_payload=payload,
        meeting_id="meet_same",
    )

    assert len(emitted) == 0
    mock_bus.publish.assert_not_called()
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meet_same:transcripts",
        consumer.group_name,
        "52-0",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_dlq_on_malformed_payload() -> None:
    """Verifies that malformed transcript payloads route to DLQ without crashing."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-msg-nmt"

    consumer = NMTConsumer(stream_bus=mock_bus, engine=MockNMTEngine())

    # Corrupt payload missing text, source_segment_id, etc.
    corrupted = {"invalid": 12345}

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_err:transcripts",
        message_id="53-0",
        raw_payload=corrupted,
        meeting_id="meet_err",
    )

    assert emitted == []
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nllb_engine_fallback_behavior() -> None:
    """Verifies that NLLBTranslationEngine gracefully falls back to MockNMTEngine."""
    # When initialized with allow_fallback=True on non-existent model
    engine = NLLBTranslationEngine(
        model_name="non_existent/fake_nllb_model",
        allow_fallback=True,
    )
    assert engine.is_using_fallback is True

    result = await engine.translate(
        "Thank you for joining today's session.",
        source_lang="eng",
        target_lang="fra",
    )
    assert result.source_language == "eng"
    assert result.target_language == "fra"
    assert len(result.translated_text) > 0
