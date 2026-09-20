"""Unit tests for JWT Token and Session Ticket Generation and Validation."""

import time
import uuid
from datetime import timedelta

import pytest
from jose import jwt

from packages.auth import (
    AuthenticatedUser,
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    create_session_ticket,
    verify_session_ticket,
    verify_token,
)
from packages.contracts import ParticipantRole


@pytest.fixture
def sample_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="developer@enterprise.com",
        role=ParticipantRole.HOST,
        display_name="Dev Lead",
        metadata={"department": "Engineering"},
    )


@pytest.mark.unit
def test_create_and_verify_valid_token(sample_user: AuthenticatedUser) -> None:
    token = create_access_token(sample_user, expires_delta=timedelta(minutes=30))
    assert isinstance(token, str)
    assert len(token) > 20

    verified_user = verify_token(token)
    assert verified_user.user_id == sample_user.user_id
    assert verified_user.tenant_id == sample_user.tenant_id
    assert verified_user.email == sample_user.email
    assert verified_user.role == ParticipantRole.HOST
    assert verified_user.display_name == "Dev Lead"
    assert verified_user.metadata.get("department") == "Engineering"


@pytest.mark.unit
def test_expired_token_raises_token_expired_error(sample_user: AuthenticatedUser) -> None:
    # Create an already-expired token (-5 seconds)
    expired_token = create_access_token(sample_user, expires_delta=timedelta(seconds=-5))

    with pytest.raises(TokenExpiredError, match="Access token has expired"):
        verify_token(expired_token)


@pytest.mark.unit
def test_invalid_signature_raises_invalid_token_error(sample_user: AuthenticatedUser) -> None:
    valid_token = create_access_token(sample_user)
    # Tamper with the token string
    tampered_token = valid_token[:-6] + "xxxxxx"

    with pytest.raises(InvalidTokenError):
        verify_token(tampered_token)


@pytest.mark.unit
def test_token_missing_tenant_id_raises_invalid_token_error() -> None:
    # Token with sub and email but no tenant_id
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "orphan@domain.com",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    secret = "dev-supabase-jwt-secret-key-32-chars-min-change-in-prod"
    token = jwt.encode(payload, secret, algorithm="HS256")

    with pytest.raises(InvalidTokenError, match="missing required 'tenant_id'"):
        verify_token(token, secret_key=secret)


@pytest.mark.unit
def test_session_ticket_lifecycle(sample_user: AuthenticatedUser) -> None:
    meeting_id = str(uuid.uuid4())
    ticket_token = create_session_ticket(sample_user, meeting_id=meeting_id, ttl_seconds=60)
    assert isinstance(ticket_token, str)

    ticket = verify_session_ticket(ticket_token)
    assert ticket.user_id == sample_user.user_id
    assert ticket.tenant_id == sample_user.tenant_id
    assert ticket.meeting_id == meeting_id
    assert ticket.role == sample_user.role
    assert ticket.expires_at > int(time.time())


@pytest.mark.unit
def test_expired_session_ticket_raises_error(sample_user: AuthenticatedUser) -> None:
    meeting_id = str(uuid.uuid4())
    expired_ticket = create_session_ticket(sample_user, meeting_id=meeting_id, ttl_seconds=-10)

    with pytest.raises(TokenExpiredError, match="Session ticket has expired"):
        verify_session_ticket(expired_ticket)
