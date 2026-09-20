"""Tests for REST API Request and Response Contracts."""

import pytest
from pydantic import ValidationError

from packages.contracts import (
    CreateMeetingRequest,
    GetTranscriptResponse,
    JoinMeetingResponse,
    ParticipantRole,
    TranscriptFormat,
    TranscriptSegmentResponse,
)


@pytest.mark.contract
def test_create_meeting_request_validation() -> None:
    # Valid creation request
    req = CreateMeetingRequest(
        title="Q3 Strategic Alignment",
        host_spoken_language="eng",
        host_listening_language="jpn",
    )
    assert req.title == "Q3 Strategic Alignment"
    assert req.host_spoken_language == "eng"
    assert req.host_listening_language == "jpn"

    # Invalid empty title
    with pytest.raises(ValidationError):
        CreateMeetingRequest(title="")

    # Invalid language code length
    with pytest.raises(ValidationError):
        CreateMeetingRequest(title="Valid Title", host_spoken_language="english")


@pytest.mark.contract
def test_strict_extra_fields_forbidden() -> None:
    # Extra unexpected fields must be rejected (security baseline)
    with pytest.raises(ValidationError):
        CreateMeetingRequest(
            title="Valid Title",
            unexpected_malicious_payload="attack",  # type: ignore[call-arg]
        )


@pytest.mark.contract
def test_join_meeting_contract_roundtrip() -> None:
    join_res = JoinMeetingResponse(
        meeting_id="meet-uuid-1234",
        participant_id="part-uuid-5678",
        display_name="Kenji Sato",
        role=ParticipantRole.PARTICIPANT,
        livekit_token="eyJhbGciOi...",
        ws_ticket="ticket-abcd-9999",
        state_version=1,
    )
    assert join_res.meeting_id == "meet-uuid-1234"
    assert join_res.role == ParticipantRole.PARTICIPANT
    assert join_res.state_version == 1

    # Verify JSON roundtrip
    json_data = join_res.model_dump_json()
    reparsed = JoinMeetingResponse.model_validate_json(json_data)
    assert reparsed == join_res


@pytest.mark.contract
def test_transcript_lineage_contract() -> None:
    segment = TranscriptSegmentResponse(
        source_segment_id="seg-src-777",
        speaker_id="spk-1",
        speaker_name="Sarah Connor",
        source_language="eng",
        target_language="spa",
        original_text="We need to finalize the deployment checklist.",
        translated_text="Necesitamos finalizar la lista de verificación del despliegue.",
        start_ms=1200,
        end_ms=4500,
        is_final=True,
    )
    assert segment.source_segment_id == "seg-src-777"
    assert segment.is_final is True

    transcript_res = GetTranscriptResponse(
        meeting_id="meet-uuid-1234",
        total_segments=1,
        format=TranscriptFormat.JSON,
        segments=[segment],
    )
    assert transcript_res.total_segments == 1
    assert transcript_res.format == TranscriptFormat.JSON
