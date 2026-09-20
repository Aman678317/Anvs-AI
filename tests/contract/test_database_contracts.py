"""Contract tests verifying 1:1 mapping between Database Models and Domain Contracts."""

import uuid
from datetime import UTC, datetime

import pytest

from packages.contracts import (
    MeetingContract,
    MeetingStatus,
    ParticipantContract,
    ParticipantRole,
    TranscriptSegmentResponse,
)
from packages.database.models import (
    Meeting,
    Participant,
    TranscriptSegment,
)
from packages.event_schema import SourceSegmentEvent


@pytest.mark.contract
def test_meeting_model_to_domain_contract_mapping() -> None:
    now = datetime.now(UTC)
    meeting_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    db_meeting = Meeting(
        id=meeting_id,
        tenant_id=tenant_id,
        title="Q3 Strategy Meeting",
        status=MeetingStatus.ACTIVE,
        state_version=2,
        created_at=now,
        updated_at=now,
    )

    domain_contract = MeetingContract(
        meeting_id=str(db_meeting.id),
        tenant_id=str(db_meeting.tenant_id),
        title=db_meeting.title,
        status=MeetingStatus(db_meeting.status),
        state_version=db_meeting.state_version,
        created_at=db_meeting.created_at,
        updated_at=db_meeting.updated_at,
    )

    assert domain_contract.meeting_id == str(meeting_id)
    assert domain_contract.status == MeetingStatus.ACTIVE
    assert domain_contract.state_version == 2


@pytest.mark.contract
def test_participant_model_to_domain_contract_mapping() -> None:
    now = datetime.now(UTC)
    part_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    db_part = Participant(
        id=part_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        user_id=user_id,
        display_name="Dr. Elena Rostova",
        role=ParticipantRole.HOST,
        spoken_language="rus",
        listening_language="eng",
        is_muted=False,
        is_video_enabled=True,
        joined_at=now,
    )

    part_contract = ParticipantContract(
        participant_id=str(db_part.id),
        user_id=str(db_part.user_id),
        display_name=db_part.display_name,
        role=ParticipantRole(db_part.role),
        spoken_language=db_part.spoken_language,
        listening_language=db_part.listening_language,
        is_muted=db_part.is_muted,
        is_video_enabled=db_part.is_video_enabled,
        joined_at=db_part.joined_at,
    )

    assert part_contract.participant_id == str(part_id)
    assert part_contract.role == ParticipantRole.HOST
    assert part_contract.spoken_language == "rus"


@pytest.mark.contract
def test_transcript_model_to_contract_and_event_mapping() -> None:
    seg_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    db_segment = TranscriptSegment(
        id=seg_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        source_segment_id="src-lineage-999",
        speaker_id="user-123",
        speaker_name="Sarah Connor",
        source_language="eng",
        target_language="spa",
        original_text="Initiating system sync.",
        translated_text="Iniciando sincronización del sistema.",
        start_ms=1000,
        end_ms=3500,
        confidence=0.98,
        is_final=True,
    )

    # 1. Map to REST response contract
    rest_response = TranscriptSegmentResponse(
        source_segment_id=db_segment.source_segment_id,
        speaker_id=db_segment.speaker_id,
        speaker_name=db_segment.speaker_name,
        source_language=db_segment.source_language,
        target_language=db_segment.target_language,
        original_text=db_segment.original_text,
        translated_text=db_segment.translated_text,
        start_ms=db_segment.start_ms,
        end_ms=db_segment.end_ms,
        is_final=db_segment.is_final,
    )
    assert rest_response.source_segment_id == "src-lineage-999"
    assert rest_response.is_final is True

    # 2. Map to Event Schema (PR-03)
    stt_event = SourceSegmentEvent(
        event_id="evt-sync-1",
        timestamp_ms=1710000000000,
        meeting_id=str(meeting_id),
        session_id="sess-alpha",
        participant_id=db_segment.speaker_id,
        source_segment_id=db_segment.source_segment_id,
        language=db_segment.source_language,
        text=db_segment.original_text,
        is_final=db_segment.is_final,
        start_ms=db_segment.start_ms,
        end_ms=db_segment.end_ms,
        confidence=db_segment.confidence,
    )
    assert stt_event.source_segment_id == db_segment.source_segment_id
    assert stt_event.confidence == 0.98
