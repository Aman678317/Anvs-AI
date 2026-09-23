"""Unit tests for Redis Streams Event Schemas."""

import time
import uuid

import pytest
from pydantic import ValidationError

from packages.event_schema import (
    AssistantQueryEvent,
    AssistantResponseEvent,
    AudioSegmentEvent,
    BaseEvent,
    DeadLetterEvent,
    DiarizationSegmentEvent,
    RoomStateEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)


@pytest.mark.unit
def test_base_event_fields() -> None:
    event_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)
    base = BaseEvent(
        event_id=event_id,
        timestamp_ms=now_ms,
        meeting_id="meet-100",
        tenant_id="tenant-alpha",
    )
    assert base.event_id == event_id
    assert base.timestamp_ms == now_ms
    assert base.meeting_id == "meet-100"
    assert base.tenant_id == "tenant-alpha"


@pytest.mark.unit
def test_source_segment_event_validation() -> None:
    source_evt = SourceSegmentEvent(
        event_id="evt-stt-1",
        timestamp_ms=1710000000100,
        meeting_id="meet-100",
        session_id="sess-xyz",
        participant_id="user-1",
        source_segment_id="src-seg-555",
        language="eng",
        text="Welcome to the quarterly sync.",
        is_final=True,
        start_ms=0,
        end_ms=2500,
        confidence=0.97,
        speaker_tag="spk-1",
    )
    assert source_evt.source_segment_id == "src-seg-555"
    assert source_evt.language == "eng"
    assert source_evt.is_final is True
    assert source_evt.confidence == 0.97
    assert source_evt.speaker_tag == "spk-1"

    # Invalid ISO-639-3 code length
    with pytest.raises(ValidationError):
        SourceSegmentEvent(
            event_id="evt-stt-2",
            timestamp_ms=1710000000200,
            meeting_id="meet-100",
            session_id="sess-xyz",
            participant_id="user-1",
            source_segment_id="src-seg-556",
            language="english",  # Invalid >3 chars
            text="Invalid language",
            is_final=False,
            start_ms=0,
            end_ms=1000,
            confidence=0.9,
        )


@pytest.mark.unit
def test_translation_segment_event_lineage() -> None:
    trans_evt = TranslationSegmentEvent(
        event_id="evt-nmt-1",
        timestamp_ms=1710000000300,
        meeting_id="meet-100",
        source_segment_id="src-seg-555",
        source_language="eng",
        target_language="spa",
        translated_text="Bienvenidos a la sincronización trimestral.",
        is_final=True,
        latency_ms=210,
    )
    assert trans_evt.source_segment_id == "src-seg-555"
    assert trans_evt.target_language == "spa"
    assert trans_evt.latency_ms == 210


@pytest.mark.unit
def test_audio_segment_event_watermark_invariant() -> None:
    audio_evt = AudioSegmentEvent(
        event_id="evt-tts-1",
        timestamp_ms=1710000000500,
        meeting_id="meet-100",
        source_segment_id="src-seg-555",
        target_language="spa",
        audio_uri="s3://bucket/audio/src-seg-555-spa.opus",
        duration_ms=2400,
        sample_rate=24000,
        watermarked=True,
    )
    assert audio_evt.source_segment_id == "src-seg-555"
    assert audio_evt.watermarked is True
    assert audio_evt.sample_rate == 24000


@pytest.mark.unit
def test_diarization_and_assistant_events() -> None:
    diar_evt = DiarizationSegmentEvent(
        event_id="evt-diar-1",
        timestamp_ms=1710000000150,
        meeting_id="meet-100",
        source_segment_id="src-seg-555",
        speaker_id="spk-prof-42",
        speaker_name="Sarah Connor",
        confidence=0.99,
    )
    assert diar_evt.speaker_id == "spk-prof-42"
    assert diar_evt.speaker_name == "Sarah Connor"

    query_evt = AssistantQueryEvent(
        event_id="evt-asst-q1",
        timestamp_ms=1710000001000,
        meeting_id="meet-100",
        query_id="query-abc",
        participant_id="user-2",
        question="What was the timeline agreed upon?",
    )
    assert query_evt.query_id == "query-abc"

    resp_evt = AssistantResponseEvent(
        event_id="evt-asst-r1",
        timestamp_ms=1710000002000,
        meeting_id="meet-100",
        query_id="query-abc",
        answer="The team agreed to deploy next Friday.",
        citations=["src-seg-555"],
        action_items=["Complete QA checklist by Thursday"],
    )
    assert resp_evt.query_id == "query-abc"
    assert "src-seg-555" in resp_evt.citations
    assert len(resp_evt.action_items) == 1


@pytest.mark.unit
def test_room_state_and_dead_letter_events() -> None:
    room_evt = RoomStateEvent(
        event_id="evt-room-1",
        timestamp_ms=1710000000000,
        meeting_id="meet-100",
        state_version=2,
        status="ACTIVE",
        active_participants_count=8,
    )
    assert room_evt.state_version == 2
    assert room_evt.active_participants_count == 8

    dlq_evt = DeadLetterEvent(
        event_id="evt-dlq-1",
        timestamp_ms=1710000005000,
        meeting_id="meet-100",
        failed_event_id="msg-100-999",
        original_stream="events:meeting:meet-100:transcripts",
        error_reason="JSONDecodeError: invalid character",
        retry_count=3,
        raw_payload="{bad json...}",
    )
    assert dlq_evt.failed_event_id == "msg-100-999"
    assert dlq_evt.retry_count == 3


@pytest.mark.unit
def test_strict_forbidden_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SourceSegmentEvent(
            event_id="evt-stt-3",
            timestamp_ms=1710000000300,
            meeting_id="meet-100",
            session_id="sess-xyz",
            participant_id="user-1",
            source_segment_id="src-seg-557",
            language="eng",
            text="Testing extra fields",
            is_final=True,
            start_ms=0,
            end_ms=1000,
            confidence=0.9,
            unexpected_malicious_key="exploit",  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_base_event_canonical_v12_lineage() -> None:
    """Verifies that BaseEvent satisfies Canonical v1.2 lineage requirements."""
    evt = BaseEvent(
        event_id="evt-base-100",
        timestamp_ms=1710000000000,
        meeting_id="meet-100",
        tenant_id="tenant-alpha",
        correlation_id="corr-trace-999",
        causation_id="cause-evt-001",
        parent_event_id="parent-evt-001",
        sequence_number=5,
        hop_count=2,
        max_hops=10,
        ttl_seconds=300,
        occurred_at="2026-09-24T00:00:00Z",
    )
    assert evt.event_version == "1.2"
    assert evt.correlation_id == "corr-trace-999"
    assert evt.causation_id == "cause-evt-001"
    assert evt.parent_event_id == "parent-evt-001"
    assert evt.sequence_number == 5
    assert evt.hop_count == 2
    assert evt.is_loop_detected() is False


@pytest.mark.unit
def test_lineage_chain_from_source_to_translation() -> None:
    """Verifies end-to-end causal lineage tracing from SourceSegment to TranslationSegment."""
    source_evt = SourceSegmentEvent(
        event_id="evt-stt-100",
        timestamp_ms=1710000000100,
        meeting_id="meet-100",
        tenant_id="tenant-alpha",
        session_id="sess-xyz",
        participant_id="user-1",
        source_segment_id="src-seg-555",
        language="eng",
        text="Hello world",
        is_final=True,
        start_ms=0,
        end_ms=1500,
        confidence=0.98,
        correlation_id="trace-meet-100",
        hop_count=0,
    )

    # Downstream translation preserves lineage and links directly to parent
    translation_evt = TranslationSegmentEvent(
        event_id="evt-nmt-200",
        timestamp_ms=1710000000250,
        meeting_id=source_evt.meeting_id,
        tenant_id=source_evt.tenant_id,
        source_segment_id=source_evt.source_segment_id,
        source_language="eng",
        target_language="spa",
        translated_text="Hola mundo",
        is_final=True,
        latency_ms=150,
        parent_event_id=source_evt.event_id,
        causation_id=source_evt.event_id,
        correlation_id=source_evt.correlation_id,
        hop_count=source_evt.hop_count + 1,
    )

    assert translation_evt.source_segment_id == source_evt.source_segment_id
    assert translation_evt.parent_event_id == source_evt.event_id
    assert translation_evt.causation_id == source_evt.event_id
    assert translation_evt.correlation_id == source_evt.correlation_id
    assert translation_evt.hop_count == 1
    assert translation_evt.is_loop_detected() is False


@pytest.mark.unit
def test_loop_detection_exceeds_max_hops() -> None:
    """Verifies that events exceeding max_hops are flagged for dead-letter routing."""
    loop_evt = BaseEvent(
        event_id="evt-loop-1",
        timestamp_ms=1710000000000,
        meeting_id="meet-100",
        hop_count=10,
        max_hops=10,
    )
    assert loop_evt.is_loop_detected() is True

