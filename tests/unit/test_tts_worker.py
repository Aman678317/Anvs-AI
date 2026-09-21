"""Unit tests for Streaming TTS Worker Service adhering to Document 14."""

import time
from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.watermark import detect_watermark
from packages.event_schema import RedisStreamBus, TranslationSegmentEvent
from services.tts_worker import (
    BaseTTSEngine,
    MockTTSEngine,
    TTSConsumer,
    XTTSv2Engine,
    create_tts_engine,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_tts_engine_synthesizes_audio() -> None:
    """Verifies that MockTTSEngine produces normalized float32 audio samples."""
    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
    result = await engine.synthesize(
        "Welcome everyone to our multilingual meeting.",
        language="eng",
    )

    assert isinstance(result.audio_pcm, np.ndarray)
    assert result.audio_pcm.dtype == np.float32
    assert len(result.audio_pcm) > 0
    assert result.sample_rate == 48000
    assert result.duration_ms > 0
    assert np.max(result.audio_pcm) <= 1.0
    assert np.min(result.audio_pcm) >= -1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_tts_engine_embeds_watermark() -> None:
    """Verifies Architecture Invariant #3: Compulsory 20 kHz ultrasonic watermarking."""
    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0, watermark_freq_hz=20000.0)
    result = await engine.synthesize("Contract verification audio payload", language="spa")

    assert result.watermarked is True
    # INVARIANT #3 ASSERTION: 20 kHz pilot tone detected via FFT
    is_detected = detect_watermark(
        audio_pcm=result.audio_pcm,
        sample_rate=48000,
        watermark_freq=20000.0,
        threshold=0.001,
    )
    assert is_detected is True, "Ultrasonic 20 kHz watermark tone was not detected in output audio"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_tts_engine_latency_sla() -> None:
    """Verifies that TTS speech synthesis satisfies <400ms SLA."""
    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=10)

    t0 = time.perf_counter()
    result = await engine.synthesize(
        "Can everyone hear me clearly?",
        language="fra",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert result.latency_ms >= 10
    assert elapsed_ms < 400.0, f"Synthesis latency {elapsed_ms}ms exceeded 400ms SLA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_tts_engine_language_cadence() -> None:
    """Verifies synthesis across multiple supported language profiles."""
    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
    languages = ["eng", "spa", "fra", "deu", "zho", "jpn", "hin"]

    for lang in languages:
        res = await engine.synthesize("Standard test phrase.", language=lang)
        assert len(res.audio_pcm) > 0
        assert res.duration_ms >= 400
        assert res.watermarked is True


@pytest.mark.unit
def test_tts_engine_factory() -> None:
    """Verifies engine factory creates mock and neural TTS instances."""
    mock_eng = create_tts_engine("mock")
    assert isinstance(mock_eng, MockTTSEngine)
    assert isinstance(mock_eng, BaseTTSEngine)

    xtts_eng = create_tts_engine("xtts", allow_fallback=True)
    assert isinstance(xtts_eng, XTTSv2Engine)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_xtts_engine_graceful_fallback() -> None:
    """Verifies that XTTSv2Engine gracefully falls back to MockTTSEngine when weights are absent."""
    engine = XTTSv2Engine(
        model_name="non_existent/fake_tts_model",
        allow_fallback=True,
    )
    assert engine.is_using_fallback is True

    result = await engine.synthesize(
        "Thank you for joining today's session.",
        language="fra",
    )
    assert len(result.audio_pcm) > 0
    assert result.watermarked is True
    assert detect_watermark(result.audio_pcm, sample_rate=48000) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tts_consumer_preserves_source_segment_id_invariant() -> None:
    """Verifies Invariant #2: Immutable source lineage preservation from Translation to Audio."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-tts-123"
    mock_bus.ack_event.return_value = 1

    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
    consumer = TTSConsumer(stream_bus=mock_bus, engine=engine)

    custom_lineage_id = "lineage_strict_translation_uuid_8888"
    translation_event = TranslationSegmentEvent(
        event_id="trans_001",
        timestamp_ms=1710000000000,
        meeting_id="meeting_tts_lineage",
        tenant_id="tenant_alpha",
        source_segment_id=custom_lineage_id,
        source_language="eng",
        target_language="spa",
        translated_text="Bienvenidos a todos a nuestra reunión multilingüe.",
        is_final=True,
        latency_ms=25,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_tts_lineage:translations",
        message_id="60-0",
        raw_payload=translation_event.model_dump(),
        meeting_id="meeting_tts_lineage",
    )

    assert len(emitted) == 1
    audio_event = emitted[0]

    # INVARIANT #2 CRITICAL ASSERTION:
    assert audio_event.source_segment_id == custom_lineage_id
    assert audio_event.target_language == "spa"
    assert audio_event.tenant_id == "tenant_alpha"
    assert audio_event.meeting_id == "meeting_tts_lineage"
    assert audio_event.duration_ms > 0

    mock_bus.publish.assert_awaited_once()
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meeting_tts_lineage:translations",
        consumer.group_name,
        "60-0",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tts_consumer_emits_watermarked_audio_segment_event() -> None:
    """Verifies Invariant #3: Published AudioSegmentEvent has watermarked=True and base64 URI."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-synth-01"
    mock_bus.ack_event.return_value = 1

    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
    consumer = TTSConsumer(stream_bus=mock_bus, engine=engine)

    payload = {
        "event_id": "trans_wm_01",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_wm",
        "tenant_id": "tenant_1",
        "source_segment_id": "src_wm_123",
        "source_language": "eng",
        "target_language": "fra",
        "translated_text": "Merci d'avoir rejoint la session d'aujourd'hui.",
        "is_final": True,
        "latency_ms": 20,
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_wm:translations",
        message_id="61-0",
        raw_payload=payload,
        meeting_id="meet_wm",
    )

    assert len(emitted) == 1
    evt = emitted[0]

    # INVARIANT #3 ASSERTIONS:
    assert evt.watermarked is True
    assert evt.sample_rate == 48000
    assert evt.audio_uri.startswith("base64://")
    assert consumer.metrics["audio_segments_emitted"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tts_consumer_skips_non_final_translations() -> None:
    """Verifies that non-final (partial) translations are skipped to prevent audio jitter."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.ack_event.return_value = 1

    engine = MockTTSEngine(simulated_latency_ms=0)
    consumer = TTSConsumer(stream_bus=mock_bus, engine=engine)

    payload = {
        "event_id": "trans_partial",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_skip",
        "tenant_id": "tenant_1",
        "source_segment_id": "src_skip_01",
        "source_language": "eng",
        "target_language": "deu",
        "translated_text": "Willkommen alle",
        "is_final": False,  # Non-final!
        "latency_ms": 15,
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_skip:translations",
        message_id="62-0",
        raw_payload=payload,
        meeting_id="meet_skip",
    )

    assert len(emitted) == 0
    mock_bus.publish.assert_not_called()
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meet_skip:translations",
        consumer.group_name,
        "62-0",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tts_consumer_dlq_on_malformed_payload() -> None:
    """Verifies that malformed translation payloads route to DLQ without crashing."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-msg-tts"

    consumer = TTSConsumer(stream_bus=mock_bus, engine=MockTTSEngine())

    # Corrupted payload
    corrupted = {"corrupted_key": 99999}

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_err:translations",
        message_id="63-0",
        raw_payload=corrupted,
        meeting_id="meet_err",
    )

    assert emitted == []
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()
