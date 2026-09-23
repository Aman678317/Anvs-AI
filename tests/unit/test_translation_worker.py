"""Unit tests for Streaming NMT Worker Service adhering to Document 14."""

import time
from unittest.mock import AsyncMock

import pytest

from packages.event_schema import RedisStreamBus, SourceSegmentEvent
from packages.language_registry import (
    get_language,
    get_optimal_nmt_model,
    is_indic_language,
)
from services.translation_worker import (
    BaseNMTEngine,
    ContextWindowBuffer,
    GlossaryRegistry,
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_poll_and_process() -> None:
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-nmt-poll-ok"
    mock_bus.ack_event.return_value = 1

    engine = MockNMTEngine(simulated_latency_ms=0)
    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        target_languages=["spa", "fra"],
    )

    payload = {
        "event_id": "src_poll_trans",
        "timestamp_ms": 1000,
        "meeting_id": "m_trans_poll",
        "tenant_id": "ten_trans_poll",
        "session_id": "sess_trans_poll",
        "participant_id": "part_trans_poll",
        "source_segment_id": "src_trans_poll_100",
        "language": "eng",
        "text": "Welcome everyone to our multilingual meeting, let's begin the review.",
        "is_final": True,
        "start_ms": 0,
        "end_ms": 1000,
        "confidence": 0.98,
    }

    mock_bus.consume_events.return_value = [("msg-nmt-100", payload)]

    emitted = await consumer.poll_and_process("m_trans_poll")
    assert len(emitted) == 2
    assert {e.target_language for e in emitted} == {"spa", "fra"}
    assert mock_bus.ack_event.called


@pytest.mark.unit
def test_context_window_buffer_meeting_and_participant_clear() -> None:
    buf = ContextWindowBuffer(max_sentences=2)
    buf.add_utterance("m_clear", "p1", "First utterance.")
    buf.add_utterance("m_clear", "p2", "Second utterance.")
    buf.add_utterance("m_keep", "p3", "Other meeting.")

    assert len(buf.get_context("m_clear", "p1")) == 1
    assert len(buf.get_context("m_clear", "p2")) == 1

    # Clear participant
    buf.clear_participant("m_clear", "p1")
    assert buf.get_context("m_clear", "p1") == []
    assert len(buf.get_context("m_clear", "p2")) == 1

    # Clear meeting
    buf.clear_meeting("m_clear")
    assert buf.get_context("m_clear", "p2") == []
    assert len(buf.get_context("m_keep", "p3")) == 1


@pytest.mark.unit
def test_dec01_language_capability_registry() -> None:
    """Verifies DEC-01: Indic pairs route to IndicTrans2 and others to NLLB-200."""
    # 1. Indic detection
    assert is_indic_language("hin") is True
    assert is_indic_language("mar") is True
    assert is_indic_language("tam") is True
    assert is_indic_language("tel") is True
    assert is_indic_language("eng") is False
    assert is_indic_language("spa") is False
    assert is_indic_language("deu") is False

    # 2. Optimal NMT model routing (DEC-01)
    assert get_optimal_nmt_model("eng", "hin") == "ai4bharat/indictrans2-1B"
    assert get_optimal_nmt_model("hin", "mar") == "ai4bharat/indictrans2-1B"
    assert get_optimal_nmt_model("mar", "eng") == "ai4bharat/indictrans2-1B"
    assert get_optimal_nmt_model("eng", "spa") == "facebook/nllb-200-distilled-600M"
    assert get_optimal_nmt_model("fra", "deu") == "facebook/nllb-200-distilled-600M"
    assert get_optimal_nmt_model("zho", "jpn") == "facebook/nllb-200-distilled-600M"

    # 3. Metadata validation for Indic languages
    mar = get_language("mar")
    assert mar is not None
    assert mar.is_indic is True
    assert mar.nmt_model == "ai4bharat/indictrans2-1B"
    assert mar.licensing == "CC-BY-NC-4.0"
    assert mar.bcp47 == "mr-IN"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_listener_resolver_fan_out() -> None:
    """Verifies listener-specific dynamic target language resolution and concurrent fan-out."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-publish-1"
    mock_bus.ack_event.return_value = 1

    engine = MockNMTEngine(simulated_latency_ms=0)

    # Dynamic listener resolver returns preferences of active participants
    async def mock_listener_resolver(meeting_id: str) -> list[str]:
        _ = meeting_id
        return ["spa", "mar", "jpn"]

    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        listener_resolver=mock_listener_resolver,
    )

    source_event = SourceSegmentEvent(
        event_id="src_evt_dynamic_999",
        timestamp_ms=1000,
        meeting_id="meet_fanout_dynamic",
        tenant_id="ten_dynamic",
        session_id="sess_dynamic",
        participant_id="user_alice",
        source_segment_id="src_seg_root_999",
        language="eng",
        text="Welcome everyone to our multilingual meeting, let's begin the review.",
        is_final=True,
        start_ms=0,
        end_ms=2000,
        confidence=0.98,
        correlation_id="corr_root_dynamic_123",
        sequence_number=1,
        hop_count=1,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_fanout_dynamic:transcripts",
        message_id="1-0",
        raw_payload=source_event.model_dump(),
        meeting_id="meet_fanout_dynamic",
    )

    # Must fan out to all 3 listeners concurrently
    assert len(emitted) == 3
    targets_emitted = {e.target_language for e in emitted}
    assert targets_emitted == {"spa", "mar", "jpn"}

    # Invariant #2 check across all fan-out branches
    for evt in emitted:
        assert evt.source_segment_id == "src_seg_root_999"
        assert evt.correlation_id == "corr_root_dynamic_123"
        assert evt.causation_id == "src_evt_dynamic_999"
        assert evt.parent_event_id == "src_evt_dynamic_999"
        assert evt.sequence_number == 2
        assert evt.hop_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nmt_consumer_glossary_injection() -> None:
    """Verifies that GlossaryRegistry protects and restores terminology during translation."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-glossary"
    mock_bus.ack_event.return_value = 1

    glossary = GlossaryRegistry()
    glossary.set_meeting_glossary(
        meeting_id="m_glossary_test",
        terms={"ANVS-AI": "ANVS-AI", "Deep Learning": "Deep Learning"},
    )

    engine = MockNMTEngine(simulated_latency_ms=0)
    consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=engine,
        target_languages=["spa"],
        glossary=glossary,
    )

    source_event = SourceSegmentEvent(
        event_id="src_gloss_1",
        timestamp_ms=1000,
        meeting_id="m_glossary_test",
        tenant_id="ten_gloss",
        session_id="sess_gloss",
        participant_id="user_bob",
        source_segment_id="src_seg_gloss_1",
        language="eng",
        text="ANVS-AI platform uses Deep Learning for speech synthesis.",
        is_final=True,
        start_ms=0,
        end_ms=1500,
        confidence=0.99,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:m_glossary_test:transcripts",
        message_id="2-0",
        raw_payload=source_event.model_dump(),
        meeting_id="m_glossary_test",
    )

    assert len(emitted) == 1
    # Terminology must be preserved in the translated text
    assert "ANVS-AI" in emitted[0].translated_text
    assert "Deep Learning" in emitted[0].translated_text
