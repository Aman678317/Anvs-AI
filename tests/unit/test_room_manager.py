"""Unit tests for Meeting Room Lifecycle & LiveKit SFU endpoints."""

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from packages.auth import AuthenticatedUser
from packages.contracts import ParticipantRole
from packages.database.models import Meeting
from services.api.main import app
from services.api.middleware.tenant import (
    get_authenticated_tenant_session,
    get_current_user,
)


@pytest.fixture
def host_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="host@corp.com",
        role=ParticipantRole.HOST,
        display_name="Meeting Host",
    )


@pytest.fixture
def participant_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="participant@corp.com",
        role=ParticipantRole.PARTICIPANT,
        display_name="Team Member",
    )


@pytest.fixture
def guest_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="guest@corp.com",
        role=ParticipantRole.GUEST,
        display_name="Audience Guest",
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.unit
def test_create_room_endpoint(host_user: AuthenticatedUser, mock_session: AsyncMock) -> None:
    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: host_user
    app.dependency_overrides[get_authenticated_tenant_session] = override_session

    try:
        client = TestClient(app)
        payload = {
            "title": "Quarterly Planning",
            "host_spoken_language": "eng",
            "host_listening_language": "fra",
            "passcode": "secret123",
        }
        response = client.post("/api/v1/rooms", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Quarterly Planning"
        assert data["status"] == "SCHEDULED"
        assert data["state_version"] == 1
        assert "meeting_id" in data
        assert mock_session.add.call_count == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_get_room_endpoint(host_user: AuthenticatedUser, mock_session: AsyncMock) -> None:
    meeting_id = uuid.uuid4()
    now = datetime.now(UTC)
    fake_meeting = Meeting(
        id=meeting_id,
        tenant_id=uuid.UUID(host_user.tenant_id),
        title="Engineering Standup",
        status="ACTIVE",
        state_version=2,
        created_at=now,
    )

    mock_res_meeting = MagicMock()
    mock_res_meeting.scalar_one_or_none.return_value = fake_meeting

    mock_res_count = MagicMock()
    mock_res_count.scalar.return_value = 5

    mock_session.execute.side_effect = [mock_res_meeting, mock_res_count]

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: host_user
    app.dependency_overrides[get_authenticated_tenant_session] = override_session

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/rooms/{meeting_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_id"] == str(meeting_id)
        assert data["title"] == "Engineering Standup"
        assert data["status"] == "ACTIVE"
        assert data["active_participants_count"] == 5
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_join_room_dual_token_issuance(
    participant_user: AuthenticatedUser, mock_session: AsyncMock
) -> None:
    meeting_id = uuid.uuid4()
    now = datetime.now(UTC)
    fake_meeting = Meeting(
        id=meeting_id,
        tenant_id=uuid.UUID(participant_user.tenant_id),
        title="Global Sync",
        status="SCHEDULED",
        state_version=1,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = fake_meeting
    mock_session.execute.return_value = mock_res

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: participant_user
    app.dependency_overrides[get_authenticated_tenant_session] = override_session

    try:
        client = TestClient(app)
        join_payload = {
            "display_name": "Elena Rostova",
            "spoken_language": "rus",
            "listening_language": "eng",
        }
        response = client.post(f"/api/v1/rooms/{meeting_id}/join", json=join_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_id"] == str(meeting_id)
        assert data["display_name"] == "Elena Rostova"
        assert data["role"] == "PARTICIPANT"
        # Verify dual tokens
        assert "livekit_token" in data
        assert len(data["livekit_token"]) > 20
        assert "ws_ticket" in data
        assert len(data["ws_ticket"]) > 20
        # Verify state transition to ACTIVE
        assert fake_meeting.status == "ACTIVE"
        assert fake_meeting.state_version == 2
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_join_room_passcode_validation(
    participant_user: AuthenticatedUser, mock_session: AsyncMock
) -> None:
    meeting_id = uuid.uuid4()
    now = datetime.now(UTC)
    correct_passcode = "securePass123"
    passcode_hash = hashlib.sha256(correct_passcode.encode()).hexdigest()

    fake_meeting = Meeting(
        id=meeting_id,
        tenant_id=uuid.UUID(participant_user.tenant_id),
        title="Confidential Strategy",
        status="ACTIVE",
        state_version=1,
        passcode_hash=passcode_hash,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = fake_meeting
    mock_session.execute.return_value = mock_res

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_current_user] = lambda: participant_user
    app.dependency_overrides[get_authenticated_tenant_session] = override_session

    try:
        client = TestClient(app)

        # 1. Incorrect passcode returns 403
        bad_payload = {
            "display_name": "Hacker",
            "spoken_language": "eng",
            "listening_language": "eng",
            "passcode": "wrongPasscode",
        }
        bad_resp = client.post(f"/api/v1/rooms/{meeting_id}/join", json=bad_payload)
        assert bad_resp.status_code == 403
        assert "Invalid meeting passcode" in bad_resp.json()["detail"]

        # 2. Correct passcode returns 200
        good_payload = {
            "display_name": "Authorized Colleague",
            "spoken_language": "eng",
            "listening_language": "eng",
            "passcode": correct_passcode,
        }
        good_resp = client.post(f"/api/v1/rooms/{meeting_id}/join", json=good_payload)
        assert good_resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_end_room_host_only(
    host_user: AuthenticatedUser,
    participant_user: AuthenticatedUser,
    mock_session: AsyncMock,
) -> None:
    meeting_id = uuid.uuid4()
    now = datetime.now(UTC)
    fake_meeting = Meeting(
        id=meeting_id,
        tenant_id=uuid.UUID(host_user.tenant_id),
        title="All Hands",
        status="ACTIVE",
        state_version=3,
        created_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = fake_meeting
    mock_session.execute.return_value = mock_res

    async def override_session():
        yield mock_session

    # 1. Participant attempting to end meeting returns 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: participant_user
    app.dependency_overrides[get_authenticated_tenant_session] = override_session

    try:
        client = TestClient(app)
        forbidden_resp = client.post(f"/api/v1/rooms/{meeting_id}/end")
        assert forbidden_resp.status_code == 403
        assert "Only the meeting host can end the meeting" in forbidden_resp.json()["detail"]

        # 2. Host ending meeting succeeds
        app.dependency_overrides[get_current_user] = lambda: host_user
        success_resp = client.post(f"/api/v1/rooms/{meeting_id}/end")
        assert success_resp.status_code == 200
        assert success_resp.json()["status"] == "ENDED"
        assert fake_meeting.status == "ENDED"
    finally:
        app.dependency_overrides.clear()
