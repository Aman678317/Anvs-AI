"""Contract tests verifying the immutable source_segment_id lineage chain (Document 12)."""

import pytest

from packages.event_schema import (
    AudioSegmentEvent,
    DiarizationSegmentEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)


@pytest.mark.contract
def test_immutable_source_segment_lineage_chain() -> None:
    # 1. STT Worker produces SourceSegmentEvent with canonical root ID
    canonical_source_segment_id = "seg-lineage-alpha-99"

    stt_event = SourceSegmentEvent(
        event_id="evt-stt-lineage-1",
        timestamp_ms=1710000000000,
        meeting_id="meet-lineage-100",
        session_id="session-webrtc-1",
        participant_id="part-speaker-1",
        source_segment_id=canonical_source_segment_id,
        language="eng",
        text="The quarterly architecture freeze is now in effect.",
        is_final=True,
        start_ms=0,
        end_ms=3200,
        confidence=0.99,
        speaker_tag="spk-speaker-1",
    )
    assert stt_event.source_segment_id == canonical_source_segment_id

    # 2. NMT Worker produces TranslationSegmentEvent preserving source lineage
    nmt_event = TranslationSegmentEvent(
        event_id="evt-nmt-lineage-2",
        timestamp_ms=1710000000350,
        meeting_id="meet-lineage-100",
        source_segment_id=stt_event.source_segment_id,
        source_language=stt_event.language,
        target_language="spa",
        translated_text="El congelamiento de arquitectura trimestral está en efecto.",
        is_final=stt_event.is_final,
        latency_ms=350,
    )
    assert nmt_event.source_segment_id == canonical_source_segment_id

    # 3. TTS Worker produces AudioSegmentEvent preserving source lineage and watermark invariant
    tts_event = AudioSegmentEvent(
        event_id="evt-tts-lineage-3",
        timestamp_ms=1710000000750,
        meeting_id="meet-lineage-100",
        source_segment_id=nmt_event.source_segment_id,
        target_language=nmt_event.target_language,
        audio_uri="s3://meeting-audio/meet-lineage-100/seg-lineage-alpha-99-spa.opus",
        duration_ms=3100,
        sample_rate=24000,
        watermarked=True,
    )
    assert tts_event.source_segment_id == canonical_source_segment_id
    assert tts_event.watermarked is True

    # 4. Diarization Worker produces DiarizationSegmentEvent preserving source lineage
    diar_event = DiarizationSegmentEvent(
        event_id="evt-diar-lineage-4",
        timestamp_ms=1710000000150,
        meeting_id="meet-lineage-100",
        source_segment_id=stt_event.source_segment_id,
        speaker_id="prof-sarah-connor",
        speaker_name="Sarah Connor",
        confidence=0.98,
    )
    assert diar_event.source_segment_id == canonical_source_segment_id

    # Verify JSON roundtrip preserves lineage
    stt_json = stt_event.model_dump_json()
    stt_reloaded = SourceSegmentEvent.model_validate_json(stt_json)
    assert stt_reloaded.source_segment_id == canonical_source_segment_id

    tts_json = tts_event.model_dump_json()
    tts_reloaded = AudioSegmentEvent.model_validate_json(tts_json)
    assert tts_reloaded.source_segment_id == canonical_source_segment_id
    assert tts_reloaded.watermarked is True
