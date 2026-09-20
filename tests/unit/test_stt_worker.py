"""Unit tests for Streaming STT Worker Service adhering to Document 14."""

import base64
import time
from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.framing import float32_to_pcm_s16le
from packages.event_schema import RedisStreamBus, SourceSegmentEvent
from services.stt_worker import (
    FasterWhisperEngine,
    MockSTTEngine,
    STTConsumer,
    create_stt_engine,
    to_iso639_1,
    to_iso639_3,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_stt_engine_streaming_partials_and_final() -> None:
    """Verifies that MockSTTEngine yields progressive partials and a final commitment."""
    engine = MockSTTEngine(simulated_ttft_ms=5, default_language="eng")
    audio = np.zeros(16000, dtype=np.float32)

    results = [res async for res in engine.transcribe_stream(audio, sample_rate=16000)]

    assert len(results) >= 2
    # Check partials
    partials = results[:-1]
    for p in partials:
        assert p.is_final is False
        assert p.language == "eng"
        assert p.confidence > 0.5
        assert len(p.text) > 0

    # Check final
    final = results[-1]
    assert final.is_final is True
    assert final.language == "eng"
    assert final.confidence >= 0.95
    assert len(final.text) >= len(partials[-1].text)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_stt_engine_ttft_latency() -> None:
    """Verifies that Time to First Token (TTFT) satisfies <350ms SLA."""
    engine = MockSTTEngine(simulated_ttft_ms=15)
    audio = np.zeros(16000, dtype=np.float32)

    t0 = time.perf_counter()
    first_token_res = None
    async for res in engine.transcribe_stream(audio, sample_rate=16000):
        first_token_res = res
        break
    ttft_ms = (time.perf_counter() - t0) * 1000

    assert first_token_res is not None
    assert first_token_res.is_final is False
    assert ttft_ms < 350.0, f"TTFT {ttft_ms}ms exceeded 350ms SLA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_stt_engine_transcribe_segment() -> None:
    """Verifies segment-level transcription method."""
    engine = MockSTTEngine(simulated_ttft_ms=0)
    audio = np.zeros(8000, dtype=np.float32)

    result = await engine.transcribe_segment(audio, sample_rate=16000, language="spa")

    assert result.is_final is True
    assert result.language == "spa"
    assert result.confidence >= 0.95
    assert len(result.text) > 0


@pytest.mark.unit
def test_language_code_mapping() -> None:
    """Verifies bidirectional mapping between Whisper 2-letter codes and ISO-639-3."""
    assert to_iso639_3("en") == "eng"
    assert to_iso639_3("es") == "spa"
    assert to_iso639_3("fr") == "fra"
    assert to_iso639_3("de") == "deu"
    assert to_iso639_3("zh") == "zho"
    assert to_iso639_3("ja") == "jpn"
    assert to_iso639_3("hi") == "hin"
    assert to_iso639_3("eng") == "eng"
    assert to_iso639_3("spa") == "spa"
    assert to_iso639_3("unknown_code") == "eng"

    assert to_iso639_1("eng") == "en"
    assert to_iso639_1("spa") == "es"
    assert to_iso639_1("fra") == "fr"
    assert to_iso639_1("jpn") == "ja"


@pytest.mark.unit
def test_create_stt_engine_factory() -> None:
    """Verifies engine factory creates mock and faster-whisper instances."""
    mock_eng = create_stt_engine("mock")
    assert isinstance(mock_eng, MockSTTEngine)

    # Whisper with allow_fallback=True will cleanly instantiate
    whisper_eng = create_stt_engine("faster-whisper", allow_fallback=True)
    assert isinstance(whisper_eng, FasterWhisperEngine)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stt_consumer_audio_decoding_and_transcription() -> None:
    """Verifies end-to-end consumer message processing, base64 audio decoding, and publishing."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-123"
    mock_bus.ack_event.return_value = 1

    engine = MockSTTEngine(simulated_ttft_ms=0)
    consumer = STTConsumer(stream_bus=mock_bus, engine=engine)

    # Create dummy 16kHz audio
    audio = np.sin(2 * np.pi * 440 * np.arange(16000) / 16000).astype(np.float32)
    pcm_bytes = float32_to_pcm_s16le(audio)
    b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")

    payload = {
        "event_id": "aud_123",
        "timestamp_ms": 1000,
        "meeting_id": "meeting_001",
        "tenant_id": "tenant_abc",
        "source_segment_id": "src_participant_789_1000",
        "target_language": "eng",
        "audio_uri": f"base64://{b64_audio}",
        "duration_ms": 1000,
        "sample_rate": 16000,
        "watermarked": False,
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_001:audio",
        message_id="100-0",
        raw_payload=payload,
        meeting_id="meeting_001",
    )

    assert len(emitted) >= 2
    assert mock_bus.publish.call_count >= 2
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meeting_001:audio",
        consumer.group_name,
        "100-0",
    )

    # Check metrics
    assert consumer.metrics["messages_consumed"] == 1
    assert consumer.metrics["finals_emitted"] == 1
    assert consumer.metrics["partials_emitted"] >= 1
    assert consumer.metrics["errors_count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stt_consumer_preserves_source_segment_id_invariant() -> None:
    """Verifies Architecture Invariant #2: Immutable source lineage preservation."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-123"
    mock_bus.ack_event.return_value = 1

    engine = MockSTTEngine(simulated_ttft_ms=0)
    consumer = STTConsumer(stream_bus=mock_bus, engine=engine)

    pcm_bytes = float32_to_pcm_s16le(np.zeros(1600, dtype=np.float32))
    b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")

    custom_lineage_id = "lineage_strict_uuid_9999"
    payload = {
        "source_segment_id": custom_lineage_id,
        "audio_uri": f"base64://{b64_audio}",
        "sample_rate": 16000,
        "target_language": "eng",
        "participant_id": "user_42",
        "session_id": "sess_livekit_1",
    }

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_001:audio",
        message_id="101-0",
        raw_payload=payload,
        meeting_id="meeting_001",
    )

    assert len(emitted) > 0
    for evt in emitted:
        assert isinstance(evt, SourceSegmentEvent)
        # INVARIANT #2 ASSERTION:
        assert evt.source_segment_id == custom_lineage_id
        assert evt.participant_id == "user_42"
        assert evt.session_id == "sess_livekit_1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stt_consumer_dlq_on_malformed_payload() -> None:
    """Verifies that corrupted payloads route to DLQ and do not crash the consumer."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-msg-1"

    consumer = STTConsumer(stream_bus=mock_bus, engine=MockSTTEngine())

    # Payload with missing audio_uri and source_segment_id
    malformed_payload = {"invalid_key": "corrupted_data"}

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_001:audio",
        message_id="102-0",
        raw_payload=malformed_payload,
        meeting_id="meeting_001",
    )

    assert emitted == []
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()
