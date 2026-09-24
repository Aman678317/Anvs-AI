"""Contract and schema validation tests."""

from datetime import UTC, datetime

import pytest

from packages.contracts import (
    MeetingContract,
    MeetingStatus,
    ParticipantContract,
    ParticipantRole,
)
from packages.event_schema import (
    AudioSegmentEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)


@pytest.mark.contract
def test_participant_contract_validation() -> None:
    participant = ParticipantContract(
        participant_id="part-12345",
        user_id="user-9999",
        display_name="Dr. Elena Rostova",
        role=ParticipantRole.HOST,
        spoken_language="rus",
        listening_language="eng",
        joined_at=datetime.now(UTC),
    )
    assert participant.participant_id == "part-12345"
    assert participant.role == ParticipantRole.HOST
    assert participant.spoken_language == "rus"
    assert participant.listening_language == "eng"


@pytest.mark.contract
def test_meeting_contract_validation() -> None:
    now = datetime.now(UTC)
    meeting = MeetingContract(
        meeting_id="meet-abc",
        tenant_id="tenant-123",
        title="Global Sync",
        status=MeetingStatus.ACTIVE,
        state_version=1,
        created_at=now,
        updated_at=now,
    )
    assert meeting.meeting_id == "meet-abc"
    assert meeting.status == MeetingStatus.ACTIVE


@pytest.mark.contract
def test_immutable_source_lineage_contract() -> None:
    # Emits source segment
    src_event = SourceSegmentEvent(
        event_id="evt-001",
        timestamp_ms=1710000000000,
        meeting_id="meet-abc",
        session_id="sess-xyz",
        participant_id="part-12345",
        source_segment_id="src-seg-987",
        language="spa",
        text="Buenos días a todos.",
        is_final=True,
        start_ms=0,
        end_ms=1800,
        confidence=0.98,
    )
    assert src_event.source_segment_id == "src-seg-987"

    # Emits translation segment linked to source_segment_id
    trans_event = TranslationSegmentEvent(
        event_id="evt-002",
        timestamp_ms=1710000000450,
        meeting_id="meet-abc",
        source_segment_id=src_event.source_segment_id,
        source_language="spa",
        target_language="eng",
        translated_text="Good morning everyone.",
        is_final=True,
        latency_ms=450,
    )
    assert trans_event.source_segment_id == src_event.source_segment_id

    # Emits audio segment linked to source_segment_id
    audio_event = AudioSegmentEvent(
        event_id="evt-003",
        timestamp_ms=1710000000850,
        meeting_id="meet-abc",
        source_segment_id=src_event.source_segment_id,
        target_language="eng",
        audio_uri="s3://meeting-audio/meet-abc/src-seg-987-eng.opus",
        duration_ms=1600,
        watermarked=True,
    )
    assert audio_event.source_segment_id == src_event.source_segment_id
    assert audio_event.watermarked is True
