"""Contract tests verifying 1:1 mapping between API payloads and Domain Contracts."""

import uuid
from datetime import UTC, datetime

import pytest

from packages.contracts import (
    CreateMeetingRequest,
    CreateMeetingResponse,
    GetMeetingResponse,
    JoinMeetingRequest,
    JoinMeetingResponse,
    MeetingContract,
    MeetingStatus,
    ParticipantContract,
    ParticipantRole,
)


@pytest.mark.contract
def test_create_meeting_contracts_roundtrip() -> None:
    now = datetime.now(UTC)
    req = CreateMeetingRequest(
        title="Global Architecture Summit",
        host_spoken_language="eng",
        host_listening_language="jpn",
        scheduled_start=now,
        passcode="roompass456",
    )
    req_json = req.model_dump()
    assert req_json["title"] == "Global Architecture Summit"
    assert req_json["host_spoken_language"] == "eng"
    assert req_json["host_listening_language"] == "jpn"

    meeting_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    resp = CreateMeetingResponse(
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        title=req.title,
        status=MeetingStatus.SCHEDULED,
        state_version=1,
        created_at=now,
    )
    assert resp.meeting_id == meeting_id
    assert resp.status == MeetingStatus.SCHEDULED
    assert resp.state_version == 1


@pytest.mark.contract
def test_join_meeting_contracts_roundtrip() -> None:
    meeting_id = str(uuid.uuid4())
    part_id = str(uuid.uuid4())

    join_req = JoinMeetingRequest(
        display_name="Dr. Hans Richter",
        spoken_language="deu",
        listening_language="eng",
        passcode="roompass456",
    )
    assert join_req.spoken_language == "deu"
    assert join_req.listening_language == "eng"

    join_resp = JoinMeetingResponse(
        meeting_id=meeting_id,
        participant_id=part_id,
        display_name=join_req.display_name,
        role=ParticipantRole.PARTICIPANT,
        livekit_token="jwt.livekit.mock.token",
        ws_ticket="jwt.ws.ticket.token",
        state_version=2,
    )
    assert join_resp.meeting_id == meeting_id
    assert join_resp.role == ParticipantRole.PARTICIPANT
    assert join_resp.livekit_token.startswith("jwt.")
    assert join_resp.ws_ticket.startswith("jwt.")


@pytest.mark.contract
def test_meeting_and_participant_contracts_mapping() -> None:
    now = datetime.now(UTC)
    meeting_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    part_id = str(uuid.uuid4())

    meeting = MeetingContract(
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        title="Leadership Review",
        status=MeetingStatus.ACTIVE,
        state_version=3,
        created_at=now,
        updated_at=now,
    )
    assert meeting.meeting_id == meeting_id
    assert meeting.status == MeetingStatus.ACTIVE

    participant = ParticipantContract(
        participant_id=part_id,
        user_id=user_id,
        display_name="Alice Host",
        role=ParticipantRole.HOST,
        spoken_language="eng",
        listening_language="fra",
        is_muted=False,
        is_video_enabled=True,
        joined_at=now,
    )
    assert participant.participant_id == part_id
    assert participant.role == ParticipantRole.HOST
    assert participant.is_video_enabled is True


@pytest.mark.contract
def test_get_meeting_contract() -> None:
    now = datetime.now(UTC)
    meeting_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    resp = GetMeetingResponse(
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        title="Weekly Town Hall",
        status=MeetingStatus.ACTIVE,
        state_version=4,
        created_at=now,
        active_participants_count=12,
    )
    assert resp.meeting_id == meeting_id
    assert resp.active_participants_count == 12
