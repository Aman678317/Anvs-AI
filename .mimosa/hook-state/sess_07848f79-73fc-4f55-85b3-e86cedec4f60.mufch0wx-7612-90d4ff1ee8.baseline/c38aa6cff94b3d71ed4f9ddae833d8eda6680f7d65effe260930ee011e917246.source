"""Contract tests for TTS worker schemas and downstream audio pipeline compatibility."""

import base64
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from packages.audio.framing import pcm_s16le_to_float32
from packages.audio.watermark import detect_watermark
from packages.event_schema import (
    AudioSegmentEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.translation_worker import MockNMTEngine, NMTConsumer
from services.tts_worker import MockTTSEngine, TTSConsumer


@pytest.mark.contract
def test_audio_segment_event_strict_contract() -> None:
    """Verifies that AudioSegmentEvent schema forbids extra attributes and validates bounds."""
    valid_data = {
        "event_id": "evt_aud_contract_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_contract_001",
        "tenant_id": "tenant_123",
        "source_segment_id": "src_lineage_001",
        "target_language": "spa",
        "audio_uri": "base64://dGVzdF9hdWRpb19kYXRh",
        "duration_ms": 1250,
        "sample_rate": 48000,
        "watermarked": True,
    }

    event = AudioSegmentEvent.model_validate(valid_data)
    assert event.target_language == "spa"
    assert event.duration_ms == 1250
    assert event.watermarked is True

    # 1. Extra attributes forbidden
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "unauthorized_extra_field": "illegal"})

    # 2. Duration must be non-negative
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "duration_ms": -100})

    # 3. Target language must be 3-character ISO-639-3 code
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "target_language": "es"})


@pytest.mark.contract
@pytest.mark.asyncio
async def test_full_stt_nmt_tts_lineage_pipeline_contract() -> None:
    """Verifies complete lineage chain from SourceSegmentEvent -> Translation -> Audio."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-pipeline-id"
    mock_bus.ack_event.return_value = 1

    # Initialize NMT and TTS workers
    nmt_consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=MockNMTEngine(simulated_latency_ms=0),
        target_languages=["fra"],
    )
    tts_consumer = TTSConsumer(
        stream_bus=mock_bus,
        engine=MockTTSEngine(sample_rate=48000, simulated_latency_ms=0),
    )

    # 1. STT emits SourceSegmentEvent with original lineage ID
    canonical_lineage_id = "src_immutable_pipeline_supreme_007"
    stt_event = SourceSegmentEvent(
        event_id="src_evt_start",
        timestamp_ms=1710000000000,
        meeting_id="meet_e2e_pipeline",
        session_id="sess_livekit_01",
        participant_id="user_speaker_01",
        source_segment_id=canonical_lineage_id,
        language="eng",
        text="Hello world contract verification",
        is_final=True,
        start_ms=0,
        end_ms=1500,
        confidence=0.98,
        speaker_tag="Speaker_1",
    )

    # 2. NMT consumes SourceSegmentEvent -> emits TranslationSegmentEvent
    emitted_translations = await nmt_consumer.process_message(
        stream_name="events:meeting:meet_e2e_pipeline:transcripts",
        message_id="100-0",
        raw_payload=stt_event.model_dump(),
        meeting_id="meet_e2e_pipeline",
    )
    assert len(emitted_translations) == 1
    trans_evt = emitted_translations[0]

    # INVARIANT #2 Check at NMT Stage
    assert trans_evt.source_segment_id == canonical_lineage_id
    assert trans_evt.target_language == "fra"

    # 3. TTS consumes TranslationSegmentEvent -> emits AudioSegmentEvent
    emitted_audios = await tts_consumer.process_message(
        stream_name="events:meeting:meet_e2e_pipeline:translations",
        message_id="101-0",
        raw_payload=trans_evt.model_dump(),
        meeting_id="meet_e2e_pipeline",
    )
    assert len(emitted_audios) == 1
    audio_evt = emitted_audios[0]

    # INVARIANT #2 Check at TTS Stage: Unbroken Lineage Chain!
    assert audio_evt.source_segment_id == canonical_lineage_id
    assert audio_evt.target_language == "fra"
    assert audio_evt.watermarked is True
    assert audio_evt.duration_ms > 0
    assert audio_evt.audio_uri.startswith("base64://")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_tts_to_audio_ingestion_watermark_rejection_contract() -> None:
    """Verifies Invariant #3 end-to-end: synthesized TTS audio is detected as watermarked."""
    engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
    result = await engine.synthesize("Bonjour le monde", language="fra")

    # Verify directly on PCM array
    assert detect_watermark(result.audio_pcm, sample_rate=48000, watermark_freq=20000.0) is True

    # Verify on decoded base64 payload (as transmitted over Redis Streams)
    uri = result.to_base64_uri()
    assert uri.startswith("base64://")
    b64_str = uri.replace("base64://", "")
    pcm_bytes = base64.b64decode(b64_str)
    decoded_pcm = pcm_s16le_to_float32(pcm_bytes)

    # Ingestion pipeline watermark detection on decoded audio buffer
    assert detect_watermark(decoded_pcm, sample_rate=48000, watermark_freq=20000.0) is True
