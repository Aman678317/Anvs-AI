"""Contract tests verifying the immutable source_segment_id lineage chain (Document 12)."""

import json
from pathlib import Path

import pytest

from packages.event_schema import (
    AudioSegmentEvent,
    DiarizationSegmentEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


@pytest.mark.contract
def test_golden_schema_v12_serialization_parity() -> None:
    """Verifies that Canonical v1.2 Golden Fixtures validate cleanly against Pydantic models."""
    # 1. Source Segment Golden Fixture
    source_file = FIXTURES_DIR / "source_segment_v1_2.json"
    with source_file.open(encoding="utf-8") as f:
        source_raw = json.load(f)

    source_model = SourceSegmentEvent.model_validate(source_raw)
    assert source_model.event_version == "1.2"
    assert source_model.language == "hin"
    assert source_model.source_segment_id == "seg-source-immutable-100"
    assert source_model.hop_count == 0

    # 2. Translation Segment Golden Fixture
    trans_file = FIXTURES_DIR / "translation_segment_v1_2.json"
    with trans_file.open(encoding="utf-8") as f:
        trans_raw = json.load(f)

    trans_model = TranslationSegmentEvent.model_validate(trans_raw)
    assert trans_model.event_version == "1.2"
    assert trans_model.source_language == "hin"
    assert trans_model.target_language == "eng"
    assert trans_model.source_segment_id == source_model.source_segment_id
    assert trans_model.parent_event_id == source_model.event_id
    assert trans_model.hop_count == 1

    # 3. Audio Segment Golden Fixture
    audio_file = FIXTURES_DIR / "audio_segment_v1_2.json"
    with audio_file.open(encoding="utf-8") as f:
        audio_raw = json.load(f)

    audio_model = AudioSegmentEvent.model_validate(audio_raw)
    assert audio_model.event_version == "1.2"
    assert audio_model.source_segment_id == source_model.source_segment_id
    assert audio_model.parent_event_id == trans_model.event_id
    assert audio_model.hop_count == 2
    assert audio_model.watermarked is True


@pytest.mark.contract
def test_canonical_causal_tree_invariants() -> None:
    """Verifies causal tree properties across multi-worker event transformations."""
    source_file = FIXTURES_DIR / "source_segment_v1_2.json"
    trans_file = FIXTURES_DIR / "translation_segment_v1_2.json"
    audio_file = FIXTURES_DIR / "audio_segment_v1_2.json"

    with source_file.open(encoding="utf-8") as f:
        src = SourceSegmentEvent.model_validate(json.load(f))
    with trans_file.open(encoding="utf-8") as f:
        trans = TranslationSegmentEvent.model_validate(json.load(f))
    with audio_file.open(encoding="utf-8") as f:
        audio = AudioSegmentEvent.model_validate(json.load(f))

    # Invariant #2: Source segment ID is strictly conserved across entire pipeline
    assert src.source_segment_id == trans.source_segment_id == audio.source_segment_id

    # Lineage: Direct parent-child pointers form an unbroken DAG
    assert trans.parent_event_id == src.event_id
    assert audio.parent_event_id == trans.event_id

    # Distributed tracing: Identical trace correlation ID across all hops
    assert src.correlation_id == trans.correlation_id == audio.correlation_id

    # Monotonic hop count increments
    assert src.hop_count == 0
    assert trans.hop_count == src.hop_count + 1
    assert audio.hop_count == trans.hop_count + 1
