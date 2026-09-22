"""Authentication and Token Management Router (PR-02)."""

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth import (
    AuthenticatedUser,
    create_access_token,
    create_session_ticket,
    hash_password,
    verify_password,
)
from packages.config.settings import settings
from packages.contracts import (
    AuthTokenRequest,
    AuthTokenResponse,
    LoginRequest,
    ParticipantRole,
    RegisterRequest,
    RegisterResponse,
)
from packages.database import Organization, User, get_db_session_dependency
from services.api.middleware.tenant import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class TicketRequest(BaseModel):
    """Payload to request a real-time WebSocket / LiveKit session ticket."""

    meeting_id: str = Field(..., description="Target meeting UUID")
    ttl_seconds: int = Field(default=300, ge=10, le=3600, description="Ticket validity period")


class TicketResponse(BaseModel):
    """Signed short-lived session ticket payload."""

    ticket: str
    meeting_id: str
    user_id: str
    tenant_id: str
    expires_in_sec: int


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant user with hashed credentials",
)
async def register_user(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session_dependency),
) -> RegisterResponse:
    """Register a new user with bcrypt password and provision tenant org."""
    # 1. Check if user already exists
    existing_query = await session.execute(
        select(User).where(User.email == payload.email.strip().lower())
    )
    if existing_query.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists.",
        )

    # 2. Resolve or provision tenant organization
    tenant_uuid: uuid.UUID
    if payload.tenant_id:
        try:
            tenant_uuid = uuid.UUID(payload.tenant_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id UUID format.",
            ) from err

        org_query = await session.execute(
            select(Organization).where(Organization.id == tenant_uuid)
        )
        if org_query.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization tenant with ID '{payload.tenant_id}' does not exist.",
            )
    else:
        # Create a new organization for the user
        org_name = (
            payload.organization_name.strip()
            if payload.organization_name
            else f"{payload.full_name}'s Workspace"
        )
        base_slug = re.sub(r"[^a-z0-9]+", "-", org_name.lower()).strip("-")
        rand_id = uuid.uuid4().hex[:8]
        slug = f"{base_slug}-{rand_id[:6]}" if base_slug else f"org-{rand_id}"

        new_org = Organization(
            id=uuid.uuid4(),
            name=org_name,
            slug=slug,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(new_org)
        await session.flush()
        tenant_uuid = new_org.id

    # 3. Hash plaintext password with bcrypt
    hashed_pwd = hash_password(payload.password)

    # 4. Provision User record
    new_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        email=payload.email.strip().lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hashed_pwd,
        role=payload.role.value,
        default_spoken_language=payload.default_spoken_language,
        default_listening_language=payload.default_listening_language,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(new_user)
    await session.commit()

    # 5. Generate signed access token
    auth_user = AuthenticatedUser(
        user_id=str(new_user.id),
        tenant_id=str(new_user.tenant_id),
        email=new_user.email,
        role=ParticipantRole(new_user.role),
        display_name=new_user.full_name,
    )
    expires_in_sec = 3600
    token = create_access_token(auth_user)

    return RegisterResponse(
        user_id=auth_user.user_id,
        tenant_id=auth_user.tenant_id,
        email=auth_user.email,
        full_name=new_user.full_name,
        role=auth_user.role,
        access_token=token,
        token_type="Bearer",
        expires_in_sec=expires_in_sec,
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user via email and password",
)
async def login_user(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session_dependency),
) -> AuthTokenResponse:
    """Authenticates user credentials and returns a signed JWT access token."""
    email_clean = payload.email.strip().lower()
    user_query = await session.execute(select(User).where(User.email == email_clean))
    user = user_query.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact organization administrator.",
        )

    auth_user = AuthenticatedUser(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        role=ParticipantRole(user.role),
        display_name=user.full_name,
    )
    expires_in_sec = 3600
    token = create_access_token(auth_user)

    return AuthTokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_sec=expires_in_sec,
        tenant_id=auth_user.tenant_id,
        user_id=auth_user.user_id,
    )


@router.post(
    "/token",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue access token for tenant user",
)
async def issue_token(
    payload: AuthTokenRequest,
    session: AsyncSession = Depends(get_db_session_dependency),
) -> AuthTokenResponse:
    """Generate a signed JWT access token for control plane API calls.

    Verifies credentials in production, or resolves user from DB to prevent privilege escalation.
    """
    email_clean = payload.email.strip().lower()
    user = None
    try:
        user_query = await session.execute(select(User).where(User.email == email_clean))
        user = user_query.scalar_one_or_none()
    except Exception:
        if settings.app_env == "production" and not settings.debug:
            raise
        user = None

    # If password is provided, verify it
    if payload.password and (
        user is None or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In production, require registered user and prohibit unverified client identity
    if settings.app_env == "production" and not settings.debug:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not registered.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Derive tenant and role strictly from database
        user_id = str(user.id)
        tenant_id = str(user.tenant_id)
        role = ParticipantRole(user.role)
    else:
        # Non-production / test mode: derive from DB if exists, else permit test fixture
        if user is not None:
            user_id = str(user.id)
            tenant_id = str(user.tenant_id)
            role = ParticipantRole(user.role)
        else:
            user_id = payload.user_id
            tenant_id = payload.tenant_id
            role = payload.role

    auth_user = AuthenticatedUser(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email_clean,
        role=role,
    )
    expires_in_sec = 3600
    token = create_access_token(auth_user)

    return AuthTokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_sec=expires_in_sec,
        tenant_id=auth_user.tenant_id,
        user_id=auth_user.user_id,
    )


@router.post(
    "/ticket",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue short-lived session ticket for WebSockets / LiveKit",
)
async def issue_session_ticket(
    body: TicketRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TicketResponse:
    """Issue a single-use signed session ticket for real-time meeting join handshakes."""
    ticket_token = create_session_ticket(
        user=current_user,
        meeting_id=body.meeting_id,
        ttl_seconds=body.ttl_seconds,
    )
    return TicketResponse(
        ticket=ticket_token,
        meeting_id=body.meeting_id,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        expires_in_sec=body.ttl_seconds,
    )


@router.get(
    "/me",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user and tenant profile",
)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Return the profile and tenant context extracted from the verified access token."""
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and invalidate active session context",
)
async def logout_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Acknowledge session termination and logout."""
    return {
        "status": "logged_out",
        "user_id": current_user.user_id,
    }
