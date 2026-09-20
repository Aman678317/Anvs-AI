"""Authentication and Token Management Router."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from packages.auth import (
    AuthenticatedUser,
    create_access_token,
    create_session_ticket,
)
from packages.contracts import AuthTokenRequest, AuthTokenResponse
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
    "/token",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue access token for tenant user",
)
async def issue_token(payload: AuthTokenRequest) -> AuthTokenResponse:
    """Generate a signed JWT access token for control plane API calls."""
    user = AuthenticatedUser(
        user_id=payload.user_id,
        tenant_id=payload.tenant_id,
        email=payload.email,
        role=payload.role,
    )
    expires_in_sec = 3600
    token = create_access_token(user)

    return AuthTokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_sec=expires_in_sec,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
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
