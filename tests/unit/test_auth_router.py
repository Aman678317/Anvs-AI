"""Unit tests for Authentication Router, Registration, Login & Token Derivation (PR-02)."""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.auth import AuthenticatedUser, hash_password, verify_session_ticket
from packages.contracts import ParticipantRole
from packages.database.models import User
from packages.database.session import get_db_session_dependency
from services.api.middleware.tenant import get_current_user
from services.api.routers.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)
client = TestClient(app)


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.unit
def test_register_new_user_and_org(mock_db: AsyncMock) -> None:
    # Simulate email not found in DB
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "new.user@enterprise.org",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "organization_name": "Acme Innovations",
            "role": "HOST",
            "default_spoken_language": "eng",
            "default_listening_language": "eng",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new.user@enterprise.org"
        assert data["full_name"] == "New User"
        assert data["role"] == "HOST"
        assert "access_token" in data
        assert len(data["access_token"]) > 20
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_register_duplicate_email(mock_db: AsyncMock) -> None:
    # Simulate email already exists in DB
    existing_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="existing@enterprise.org",
        full_name="Existing User",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "existing@enterprise.org",
            "password": "SecurePassword123!",
            "full_name": "Duplicate Attempt",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_login_success(mock_db: AsyncMock) -> None:
    raw_password = "CorrectHorseBatteryStaple!"
    hashed_pwd = hash_password(raw_password)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    db_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="verified@corp.com",
        full_name="Verified Admin",
        hashed_password=hashed_pwd,
        role="HOST",
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "verified@corp.com",
            "password": raw_password,
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user_id)
        assert data["tenant_id"] == str(tenant_id)
        assert data["token_type"] == "Bearer"
        assert len(data["access_token"]) > 20
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_login_invalid_password(mock_db: AsyncMock) -> None:
    hashed_pwd = hash_password("CorrectPassword123!")

    db_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="target@corp.com",
        full_name="Target User",
        hashed_password=hashed_pwd,
        role="PARTICIPANT",
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "target@corp.com",
            "password": "WrongPasswordGuessed!",
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_login_nonexistent_user(mock_db: AsyncMock) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "ghost@corp.com",
            "password": "SomePassword123!",
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_login_deactivated_user(mock_db: AsyncMock) -> None:
    raw_pwd = "ValidPassword123!"
    hashed_pwd = hash_password(raw_pwd)

    db_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="inactive@corp.com",
        full_name="Inactive User",
        hashed_password=hashed_pwd,
        role="PARTICIPANT",
        is_active=False,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session_dependency] = lambda: mock_db

    try:
        payload = {
            "email": "inactive@corp.com",
            "password": raw_pwd,
        }
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_get_my_profile_and_ticket() -> None:
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    meeting_id = str(uuid.uuid4())

    test_user = AuthenticatedUser(
        user_id=user_id,
        tenant_id=tenant_id,
        email="user@enterprise.org",
        role=ParticipantRole.PARTICIPANT,
        display_name="Profile Tester",
    )

    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        # 1. GET /api/v1/auth/me
        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["user_id"] == user_id
        assert me_data["tenant_id"] == tenant_id
        assert me_data["email"] == "user@enterprise.org"

        # 2. POST /api/v1/auth/ticket
        ticket_resp = client.post(
            "/api/v1/auth/ticket",
            json={"meeting_id": meeting_id, "ttl_seconds": 120},
        )
        assert ticket_resp.status_code == 200
        ticket_data = ticket_resp.json()
        assert ticket_data["meeting_id"] == meeting_id
        assert ticket_data["user_id"] == user_id
        assert ticket_data["expires_in_sec"] == 120
        assert "ticket" in ticket_data

        # Strengthened validation: decode & verify token cryptographically
        token_str = ticket_data["ticket"]
        decoded_ticket = verify_session_ticket(token_str)
        assert decoded_ticket.user_id == user_id
        assert decoded_ticket.tenant_id == tenant_id
        assert decoded_ticket.meeting_id == meeting_id
        assert decoded_ticket.role == ParticipantRole.PARTICIPANT
        now = int(time.time())
        assert decoded_ticket.issued_at <= now
        assert decoded_ticket.expires_at == decoded_ticket.issued_at + 120
        assert decoded_ticket.expires_at > now

        # 3. POST /api/v1/auth/logout
        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["status"] == "logged_out"
    finally:
        app.dependency_overrides.clear()
