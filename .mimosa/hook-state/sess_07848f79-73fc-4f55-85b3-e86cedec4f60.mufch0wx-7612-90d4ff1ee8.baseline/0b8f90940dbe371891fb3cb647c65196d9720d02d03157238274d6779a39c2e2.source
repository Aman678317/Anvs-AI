"""Authentication and Authorization Domain Models."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts import ParticipantRole


class AuthenticatedUser(BaseModel):
    """Normalized authenticated user identity extracted from JWT claims."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_id: str = Field(..., description="Unique User UUID")
    tenant_id: str = Field(..., description="Organization Tenant UUID")
    email: str = Field(..., description="Primary user email address")
    role: ParticipantRole = Field(
        default=ParticipantRole.PARTICIPANT,
        description="Meeting or platform role",
    )
    display_name: str | None = Field(default=None, description="Human-readable display name")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata claims")


class JWTPayload(BaseModel):
    """Structured representation of decoded Supabase JWT claims."""

    model_config = ConfigDict(extra="ignore")

    sub: str = Field(..., description="Subject claim (User ID)")
    tenant_id: str = Field(..., description="Tenant Organization ID")
    email: str = Field(..., description="User email claim")
    role: str = Field(default="PARTICIPANT", description="Assigned user role")
    exp: int = Field(..., description="Expiration timestamp (Unix Epoch seconds)")
    iat: int = Field(..., description="Issued at timestamp (Unix Epoch seconds)")
    iss: str | None = Field(default=None, description="Issuer claim")
    aud: str | None = Field(default=None, description="Audience claim")
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class SessionTicket(BaseModel):
    """Short-lived signed ticket for WebRTC (LiveKit) and WebSocket connections."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    ticket_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID associated with the session")
    tenant_id: str = Field(..., description="Tenant ID enforcing RLS boundary")
    meeting_id: str = Field(..., description="Target Meeting ID")
    role: ParticipantRole = Field(
        default=ParticipantRole.PARTICIPANT,
        description="Assigned role in meeting",
    )
    issued_at: int = Field(..., description="Issued timestamp in seconds")
    expires_at: int = Field(..., description="Expiration timestamp in seconds")
