"""Contract tests for Voice Cloning Worker schemas and downstream pipeline compatibility."""

from unittest.mock import AsyncMock

import numpy as np
import pytest
from pydantic import ValidationError

from packages.audio.watermark import detect_watermark
from packages.event_schema import (
    AudioSegmentEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.translation_worker import MockNMTEngine, NMTConsumer
from services.voice_worker import MockVoiceEngine, VoiceEmbedding, VoiceWorkerConsumer


@pytest.mark.contract
def test_audio_segment_event_voice_clone_strict_schema() -> None:
    """Verifies AudioSegmentEvent schema enforces strict validation for voice-cloned outputs."""
    valid_data = {
        "event_id": "vc_evt_contract_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_vc_001",
        "tenant_id": "tenant_123",
        "source_segment_id": "src_lineage_vc_001",
        "target_language": "jpn",
        "audio_uri": "base64://dGVzdF9hdWRpb19kYXRh",
        "duration_ms": 2500,
        "sample_rate": 48000,
        "watermarked": True,
    }

    event = AudioSegmentEvent.model_validate(valid_data)
    assert event.watermarked is True
    assert event.target_language == "jpn"

    # Extra fields must be forbidden
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "voice_clone_id": "illegal"})

    # duration_ms must be non-negative
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "duration_ms": -1})

    # target_language must be exactly 3 chars
    with pytest.raises(ValidationError):
        AudioSegmentEvent.model_validate({**valid_data, "target_language": "ja"})


@pytest.mark.contract
@pytest.mark.asyncio
async def test_full_stt_nmt_voice_clone_lineage_pipeline() -> None:
    """Verifies Invariant #2: Unbroken source_segment_id lineage from STT to voice-cloned audio."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-vc-pipeline"
    mock_bus.ack_event.return_value = 1

    nmt_consumer = NMTConsumer(
        stream_bus=mock_bus,
        engine=MockNMTEngine(simulated_latency_ms=0),
        target_languages=["jpn"],
    )
    voice_consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus,
        engine=MockVoiceEngine(sample_rate=48000, simulated_latency_ms=0),
    )

    # Pre-enroll speaker voice profile
    audio = np.zeros(16000, dtype=np.float32)
    await voice_consumer.enroll_speaker_from_audio(
        meeting_id="meet_contract_vc",
        speaker_id="spk_pipeline_001",
        tenant_id="tenant_pipeline",
        audio_pcm=audio,
        sample_rate=16000,
        consent_verified=True,
    )

    # 1. STT emits SourceSegmentEvent with canonical lineage ID
    canonical_lineage_id = "src_immutable_voice_pipeline_001"
    stt_event = SourceSegmentEvent(
        event_id="stt_evt_start",
        timestamp_ms=1710000000000,
        meeting_id="meet_contract_vc",
        session_id="sess_vc_001",
        participant_id="user_speaker_vc",
        source_segment_id=canonical_lineage_id,
        language="eng",
        text="Good morning everyone",
        is_final=True,
        start_ms=0,
        end_ms=1500,
        confidence=0.97,
        speaker_tag="spk_pipeline_001",
    )

    # 2. NMT consumes SourceSegmentEvent → emits TranslationSegmentEvent
    emitted_translations = await nmt_consumer.process_message(
        stream_name="events:meeting:meet_contract_vc:transcripts",
        message_id="200-0",
        raw_payload=stt_event.model_dump(),
        meeting_id="meet_contract_vc",
    )
    assert len(emitted_translations) == 1
    trans_evt = emitted_translations[0]

    # INVARIANT #2 at NMT stage
    assert trans_evt.source_segment_id == canonical_lineage_id
    assert trans_evt.target_language == "jpn"

    # Add speaker_tag to payload for voice consumer lookup
    payload_dict = trans_evt.model_dump()
    payload_dict["speaker_tag"] = "spk_pipeline_001"

    # 3. Voice Consumer synthesizes with enrolled speaker embedding
    audio_event = await voice_consumer.synthesize_for_translation(
        stream_name="events:meeting:meet_contract_vc:translations",
        message_id="201-0",
        raw_payload=payload_dict,
        meeting_id="meet_contract_vc",
    )
    assert audio_event is not None

    # INVARIANT #2 at TTS/Voice stage — unbroken lineage chain
    assert audio_event.source_segment_id == canonical_lineage_id
    assert audio_event.target_language == "jpn"
    assert audio_event.watermarked is True
    assert audio_event.audio_uri.startswith("base64://")
    assert voice_consumer.metrics["voice_cloned_segments"] == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_voice_clone_audio_watermark_invariant_contract() -> None:
    """Verifies Invariant #3: Voice-cloned audio always contains detectable 20 kHz watermark."""
    engine = MockVoiceEngine(sample_rate=48000, simulated_latency_ms=0, watermark_freq_hz=20000.0)

    embed = VoiceEmbedding(
        speaker_id="speaker_contract_wm",
        tenant_id="tenant_contract",
        embedding=np.random.default_rng(77).standard_normal(256).astype(np.float32),
        sample_rate=16000,
        consent_verified=True,
    )

    languages = ["eng", "spa", "fra", "deu", "jpn", "hin"]
    for lang in languages:
        result = await engine.synthesize_with_voice(
            text="Contract watermark invariant test across all languages.",
            language=lang,
            voice_embedding=embed,
        )
        assert result.watermarked is True
        is_detected = detect_watermark(result.audio_pcm, sample_rate=48000, watermark_freq=20000.0)
        assert (
            is_detected is True
        ), f"Invariant #3 violation: 20 kHz watermark not detected in language={lang}"
