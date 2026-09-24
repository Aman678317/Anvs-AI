"""JWT Token and Session Ticket Generation and Validation."""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from packages.config import settings
from packages.contracts import ParticipantRole

from .models import AuthenticatedUser, SessionTicket


class AuthenticationError(Exception):
    """Base exception for authentication failures."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when an access token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a token signature, format, or claims are invalid."""

    pass


def create_access_token(
    user: AuthenticatedUser,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Generate a signed JWT for the given user identity."""
    key = secret_key or settings.supabase_jwt_secret
    algo = algorithm or settings.supabase_jwt_algorithm
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(hours=1)
    exp = now + delta

    payload: dict[str, Any] = {
        "sub": user.user_id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role.value,
        "name": user.display_name or "",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "app_metadata": {
            "tenant_id": user.tenant_id,
            "role": user.role.value,
        },
        "user_metadata": user.metadata,
    }
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience

    token: str = jwt.encode(payload, key, algorithm=algo)
    return token


def verify_token(
    token: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> AuthenticatedUser:
    """Verify and decode a Supabase or control plane JWT into an AuthenticatedUser."""
    key = secret_key or settings.supabase_jwt_secret
    algo = algorithm or settings.supabase_jwt_algorithm

    decode_options: dict[str, Any] = {
        "verify_signature": True,
        "verify_exp": True,
    }
    if settings.jwt_issuer:
        decode_options["verify_iss"] = True
    if settings.jwt_audience:
        decode_options["verify_aud"] = True

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[algo],
            options=decode_options,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except ExpiredSignatureError as e:
        raise TokenExpiredError("Access token has expired.") from e
    except JWTError as e:
        raise InvalidTokenError(f"Invalid access token: {e}") from e

    # Extract user ID (sub)
    user_id = claims.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing 'sub' (subject) claim.")

    # Extract tenant ID (supporting top-level or app_metadata)
    tenant_id = claims.get("tenant_id")
    if not tenant_id and isinstance(claims.get("app_metadata"), dict):
        tenant_id = claims["app_metadata"].get("tenant_id")

    if not tenant_id:
        raise InvalidTokenError("Token missing required 'tenant_id' claim.")

    # Extract email
    email = claims.get("email", "")

    # Extract role (map to ParticipantRole)
    raw_role = claims.get("role")
    if not raw_role and isinstance(claims.get("app_metadata"), dict):
        raw_role = claims["app_metadata"].get("role")

    try:
        role = ParticipantRole(str(raw_role).upper()) if raw_role else ParticipantRole.PARTICIPANT
    except ValueError:
        role = ParticipantRole.PARTICIPANT

    display_name = claims.get("name") or claims.get("user_metadata", {}).get("full_name")
    metadata = claims.get("user_metadata") if isinstance(claims.get("user_metadata"), dict) else {}

    return AuthenticatedUser(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        email=str(email),
        role=role,
        display_name=display_name,
        metadata=metadata,
    )


def create_session_ticket(
    user: AuthenticatedUser,
    meeting_id: str,
    ttl_seconds: int | None = None,
    secret_key: str | None = None,
) -> str:
    """Issue a signed, short-lived session ticket for WebSocket and LiveKit handshakes."""
    ttl = ttl_seconds or settings.session_ticket_ttl_seconds
    now = int(time.time())
    expires_at = now + ttl
    key = secret_key or settings.api_secret_key

    ticket = SessionTicket(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        meeting_id=meeting_id,
        role=user.role,
        issued_at=now,
        expires_at=expires_at,
    )
    payload = ticket.model_dump()
    token: str = jwt.encode(payload, key, algorithm="HS256")
    return token


def verify_session_ticket(
    ticket_token: str,
    secret_key: str | None = None,
) -> SessionTicket:
    """Validate a WebSocket or LiveKit session ticket."""
    key = secret_key or settings.api_secret_key

    try:
        claims: dict[str, Any] = jwt.decode(
            ticket_token,
            key,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": False},
        )
    except JWTError as e:
        raise InvalidTokenError(f"Invalid session ticket: {e}") from e

    ticket = SessionTicket(**claims)
    now = int(time.time())
    if ticket.expires_at < now:
        raise TokenExpiredError("Session ticket has expired.")

    return ticket
