"""Unit tests for Enterprise Admin Console & Organization Portal Router (PR-15)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.auth import AuthenticatedUser
from packages.contracts import ParticipantRole
from packages.database.models import Meeting, Organization, TranscriptSegment, User
from services.api.middleware.tenant import (
    TenantContextMiddleware,
    get_authenticated_tenant_session,
    get_current_user,
)
from services.api.routers import admin_router, get_admin_user

TEST_TENANT_ID = str(uuid.uuid4())
TEST_ADMIN_USER_ID = str(uuid.uuid4())
TEST_MEMBER_USER_ID = str(uuid.uuid4())


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


HOST_USER = AuthenticatedUser(
    user_id=TEST_ADMIN_USER_ID,
    tenant_id=TEST_TENANT_ID,
    email="admin@enterprise.org",
    role=ParticipantRole.HOST,
    display_name="Enterprise Admin",
)

PARTICIPANT_USER = AuthenticatedUser(
    user_id=TEST_MEMBER_USER_ID,
    tenant_id=TEST_TENANT_ID,
    email="member@enterprise.org",
    role=ParticipantRole.PARTICIPANT,
    display_name="Regular Member",
)


@pytest.fixture
def admin_app(mock_session: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.include_router(admin_router)

    # Override both auth dependencies: skip JWT entirely, inject HOST user directly
    app.dependency_overrides[get_authenticated_tenant_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: HOST_USER
    app.dependency_overrides[get_admin_user] = lambda: HOST_USER
    return app


@pytest.fixture
def participant_app(mock_session: AsyncMock) -> FastAPI:
    """App fixture with a PARTICIPANT user — should receive 403 on admin routes."""
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.include_router(admin_router)

    app.dependency_overrides[get_authenticated_tenant_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: PARTICIPANT_USER
    # Do NOT override get_admin_user — let it run so the role check fires
    return app


# -----------------------------------------------------------------------------
# Unit Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
def test_admin_rbac_guard_blocks_non_host(participant_app: FastAPI) -> None:
    """Non-host users must receive 403 Forbidden on all admin routes."""
    client = TestClient(participant_app)
    response = client.get("/api/v1/admin/organization")
    assert response.status_code == 403
    assert "requires minimum role 'host'" in response.json()["detail"].lower()


@pytest.mark.unit
def test_get_organization_details(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Fetch organization profile with member and meeting count aggregates."""
    org_id = uuid.UUID(TEST_TENANT_ID)
    now = datetime.now(UTC)
    mock_org = Organization(
        id=org_id,
        name="Acme Enterprise",
        slug="acme-enterprise",
        created_at=now,
        updated_at=now,
    )

    # Sequence of mock executions: org, user_count, meeting_count
    mock_res_org = MagicMock()
    mock_res_org.scalar_one_or_none.return_value = mock_org

    mock_res_users = MagicMock()
    mock_res_users.scalar.return_value = 12

    mock_res_meetings = MagicMock()
    mock_res_meetings.scalar.return_value = 45

    mock_session.execute.side_effect = [mock_res_org, mock_res_users, mock_res_meetings]

    client = TestClient(admin_app)
    response = client.get("/api/v1/admin/organization")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_TENANT_ID
    assert data["name"] == "Acme Enterprise"
    assert data["slug"] == "acme-enterprise"
    assert data["member_count"] == 12
    assert data["meeting_count"] == 45


@pytest.mark.unit
def test_update_organization(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Update organization name and slug."""
    org_id = uuid.UUID(TEST_TENANT_ID)
    now = datetime.now(UTC)
    mock_org = Organization(
        id=org_id,
        name="Acme Enterprise",
        slug="acme-enterprise",
        created_at=now,
        updated_at=now,
    )

    mock_res_org = MagicMock()
    mock_res_org.scalar_one_or_none.return_value = mock_org

    mock_res_slug = MagicMock()
    mock_res_slug.scalar_one_or_none.return_value = None  # Slug available

    mock_res_users = MagicMock()
    mock_res_users.scalar.return_value = 12

    mock_res_meetings = MagicMock()
    mock_res_meetings.scalar.return_value = 45

    mock_session.execute.side_effect = [
        mock_res_org,
        mock_res_slug,
        mock_res_users,
        mock_res_meetings,
    ]

    client = TestClient(admin_app)
    response = client.patch(
        "/api/v1/admin/organization",
        json={"name": "Acme Global", "slug": "acme-global"},
    )
    assert response.status_code == 200
    assert mock_org.name == "Acme Global"
    assert mock_org.slug == "acme-global"


@pytest.mark.unit
def test_list_organization_members(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """List team members belonging to tenant."""
    now = datetime.now(UTC)
    user1 = User(
        id=uuid.UUID(TEST_ADMIN_USER_ID),
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        email="admin@enterprise.org",
        full_name="Enterprise Admin",
        role="HOST",
        is_active=True,
        created_at=now,
    )
    user2 = User(
        id=uuid.UUID(TEST_MEMBER_USER_ID),
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        email="member@enterprise.org",
        full_name="Regular Member",
        role="PARTICIPANT",
        is_active=True,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [user1, user2]
    mock_session.execute.return_value = mock_res

    client = TestClient(admin_app)
    response = client.get("/api/v1/admin/members")
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2
    assert members[0]["email"] == "admin@enterprise.org"
    assert members[0]["role"] == "HOST"
    assert members[1]["email"] == "member@enterprise.org"
    assert members[1]["role"] == "PARTICIPANT"


@pytest.mark.unit
def test_invite_member(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Invite and provision a new member in the organization."""
    # Existing check returns None
    mock_res_existing = MagicMock()
    mock_res_existing.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res_existing

    client = TestClient(admin_app)
    response = client.post(
        "/api/v1/admin/members/invite",
        json={
            "email": "new.hire@enterprise.org",
            "role": "MODERATOR",
            "display_name": "New Hire",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new.hire@enterprise.org"
    assert data["role"] == "MODERATOR"
    assert data["display_name"] == "New Hire"
    assert mock_session.add.called
    assert mock_session.commit.awaited


@pytest.mark.unit
def test_update_member_role(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Promote or update member role and status."""
    now = datetime.now(UTC)
    target_user = User(
        id=uuid.UUID(TEST_MEMBER_USER_ID),
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        email="member@enterprise.org",
        full_name="Regular Member",
        role="PARTICIPANT",
        is_active=True,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = target_user
    mock_session.execute.return_value = mock_res

    client = TestClient(admin_app)
    response = client.patch(
        f"/api/v1/admin/members/{TEST_MEMBER_USER_ID}",
        json={"role": "MODERATOR", "is_active": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "MODERATOR"
    assert target_user.role == "MODERATOR"


@pytest.mark.unit
def test_remove_member(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Remove a non-self member from the organization."""
    now = datetime.now(UTC)
    target_user = User(
        id=uuid.UUID(TEST_MEMBER_USER_ID),
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        email="member@enterprise.org",
        full_name="Regular Member",
        role="PARTICIPANT",
        is_active=True,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = target_user
    mock_session.execute.return_value = mock_res

    client = TestClient(admin_app)
    response = client.delete(f"/api/v1/admin/members/{TEST_MEMBER_USER_ID}")
    assert response.status_code == 204
    assert mock_session.delete.awaited


@pytest.mark.unit
def test_meeting_history_and_transcripts(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Fetch meeting compliance summaries and lineaged transcript segments."""
    meeting_id = uuid.uuid4()
    now = datetime.now(UTC)
    mock_meeting = Meeting(
        id=meeting_id,
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        title="Q3 Strategy Review",
        status="ACTIVE",
        created_at=now,
    )

    # 1. Test /meetings
    mock_res_meetings = MagicMock()
    mock_res_meetings.scalars.return_value.all.return_value = [mock_meeting]

    mock_res_parts = MagicMock()
    mock_res_parts.scalar.return_value = 8

    mock_res_segs = MagicMock()
    mock_res_segs.scalar.return_value = 34

    mock_session.execute.side_effect = [mock_res_meetings, mock_res_parts, mock_res_segs]

    client = TestClient(admin_app)
    res_meetings = client.get("/api/v1/admin/meetings")
    assert res_meetings.status_code == 200
    summaries = res_meetings.json()
    assert len(summaries) == 1
    assert summaries[0]["title"] == "Q3 Strategy Review"
    assert summaries[0]["participant_count"] == 8
    assert summaries[0]["transcript_segment_count"] == 34

    # 2. Test /meetings/{id}/transcripts (with Invariant #2 Lineage)
    mock_seg = TranscriptSegment(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TEST_TENANT_ID),
        meeting_id=meeting_id,
        source_segment_id="src_seg_1001",
        speaker_id="user_host",
        speaker_name="Dr. Aris Thorne",
        source_language="eng",
        target_language="spa",
        original_text="Welcome everyone to our executive summit.",
        translated_text="Bienvenidos a todos a nuestra cumbre ejecutiva.",
        start_ms=0,
        end_ms=2500,
        is_final=True,
    )

    mock_res_meet_verify = MagicMock()
    mock_res_meet_verify.scalar_one_or_none.return_value = mock_meeting

    mock_res_trans = MagicMock()
    mock_res_trans.scalars.return_value.all.return_value = [mock_seg]

    mock_session.execute.side_effect = [mock_res_meet_verify, mock_res_trans]

    res_transcripts = client.get(f"/api/v1/admin/meetings/{meeting_id}/transcripts")
    assert res_transcripts.status_code == 200
    segments = res_transcripts.json()
    assert len(segments) == 1
    assert segments[0]["source_segment_id"] == "src_seg_1001"
    assert segments[0]["original_text"] == "Welcome everyone to our executive summit."
    assert segments[0]["translated_text"] == "Bienvenidos a todos a nuestra cumbre ejecutiva."


@pytest.mark.unit
def test_analytics_and_audit_logs(admin_app: FastAPI, mock_session: AsyncMock) -> None:
    """Verify live analytics metrics and compliance audit trail."""
    # Mock analytics aggregations
    mock_active = MagicMock()
    mock_active.scalar.return_value = 3

    mock_total_m = MagicMock()
    mock_total_m.scalar.return_value = 24

    mock_total_p = MagicMock()
    mock_total_p.scalar.return_value = 98

    mock_duration = MagicMock()
    mock_duration.scalar.return_value = 720000  # 12 minutes in ms

    mock_langs = MagicMock()
    mock_langs.all.return_value = [("eng", 50), ("spa", 30), ("fra", 15)]

    mock_session.execute.side_effect = [
        mock_active,
        mock_total_m,
        mock_total_p,
        mock_duration,
        mock_langs,
    ]

    client = TestClient(admin_app)
    res_analytics = client.get("/api/v1/admin/analytics/overview")
    assert res_analytics.status_code == 200
    analytics = res_analytics.json()
    assert analytics["active_meetings_count"] == 3
    assert analytics["total_meetings_count"] == 24
    assert analytics["total_participants_count"] == 98
    assert analytics["total_transcribed_minutes"] == 12.0
    assert analytics["language_breakdown"]["eng"] == 50

    # Audit logs
    res_audit = client.get("/api/v1/admin/audit-logs")
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["total"] >= 1
    assert audit_data["logs"][0]["event_type"] == "AUTH_CONSOLE_ACCESS"
