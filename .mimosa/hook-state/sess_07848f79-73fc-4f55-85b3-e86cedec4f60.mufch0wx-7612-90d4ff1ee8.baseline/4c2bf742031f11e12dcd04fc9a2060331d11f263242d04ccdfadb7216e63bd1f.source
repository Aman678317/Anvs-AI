"""Contract tests for Enterprise Admin Console & Organization Portal REST Contracts (PR-15)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.contracts import (
    AdminAnalyticsResponse,
    AdminAuditLogsResponse,
    AdminMeetingSummaryResponse,
    AuditLogEntry,
    InviteMemberRequest,
    MeetingStatus,
    OrganizationMemberResponse,
    OrganizationResponse,
    ParticipantRole,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)


@pytest.mark.contract
def test_organization_contract_roundtrip() -> None:
    now = datetime.now(UTC)
    res = OrganizationResponse(
        id="org-1234",
        name="Global Solutions Inc",
        slug="global-solutions",
        created_at=now,
        member_count=25,
        meeting_count=140,
    )
    assert res.id == "org-1234"
    assert res.name == "Global Solutions Inc"
    assert res.slug == "global-solutions"
    assert res.member_count == 25
    assert res.meeting_count == 140

    update_req = UpdateOrganizationRequest(name="New Global Corp")
    assert update_req.name == "New Global Corp"
    assert update_req.slug is None


@pytest.mark.contract
def test_member_and_invite_contracts() -> None:
    now = datetime.now(UTC)
    member = OrganizationMemberResponse(
        user_id="user-5678",
        email="operator@enterprise.org",
        role=ParticipantRole.MODERATOR,
        display_name="DevOps Lead",
        is_active=True,
        created_at=now,
    )
    assert member.user_id == "user-5678"
    assert member.role == ParticipantRole.MODERATOR
    assert member.is_active is True

    invite = InviteMemberRequest(
        email="architect@enterprise.org",
        role=ParticipantRole.HOST,
        display_name="Chief Architect",
    )
    assert invite.email == "architect@enterprise.org"
    assert invite.role == ParticipantRole.HOST

    update_role = UpdateMemberRoleRequest(role=ParticipantRole.PARTICIPANT, is_active=False)
    assert update_role.role == ParticipantRole.PARTICIPANT
    assert update_role.is_active is False


@pytest.mark.contract
def test_analytics_and_audit_contracts() -> None:
    now = datetime.now(UTC)
    summary = AdminMeetingSummaryResponse(
        meeting_id="meet-uuid-9999",
        title="Architecture Review",
        status=MeetingStatus.ENDED,
        duration_seconds=3600,
        participant_count=15,
        transcript_segment_count=420,
        created_at=now,
    )
    assert summary.meeting_id == "meet-uuid-9999"
    assert summary.status == MeetingStatus.ENDED
    assert summary.duration_seconds == 3600

    analytics = AdminAnalyticsResponse(
        tenant_id="tenant-1111",
        active_meetings_count=2,
        total_meetings_count=85,
        total_transcribed_minutes=1450.5,
        total_participants_count=320,
        language_breakdown={"eng": 50, "spa": 25, "jpn": 10},
        average_translation_latency_ms=380.0,
    )
    assert analytics.total_transcribed_minutes == 1450.5
    assert analytics.language_breakdown["eng"] == 50

    log_entry = AuditLogEntry(
        id="audit-1",
        event_type="ROLE_UPDATE",
        actor_email="admin@corp.com",
        target="user-2",
        timestamp=now,
        details={"old_role": "PARTICIPANT", "new_role": "MODERATOR"},
    )
    audit_resp = AdminAuditLogsResponse(logs=[log_entry], total=1)
    assert audit_resp.total == 1
    assert audit_resp.logs[0].event_type == "ROLE_UPDATE"


@pytest.mark.contract
def test_strict_extra_fields_forbidden_in_admin_contracts() -> None:
    """Extra unexpected fields must be rejected (security baseline)."""
    with pytest.raises(ValidationError):
        InviteMemberRequest(
            email="test@corp.com",
            unexpected_field="injection",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        UpdateOrganizationRequest(
            name="Valid Name",
            malicious_payload={"drop": "database"},  # type: ignore[call-arg]
        )
