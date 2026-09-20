"""Shared Domain Contracts and REST/WebSocket API Models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ParticipantRole(StrEnum):
    HOST = "HOST"
    MODERATOR = "MODERATOR"
    PARTICIPANT = "PARTICIPANT"
    GUEST = "GUEST"


class MeetingStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    ARCHIVED = "ARCHIVED"


class ParticipantContract(BaseModel):
    participant_id: str
    user_id: str | None = None
    display_name: str
    role: ParticipantRole
    spoken_language: str = Field(..., description="ISO-639-3 spoken language code")
    listening_language: str = Field(..., description="ISO-639-3 personalized listening language")
    is_muted: bool = False
    is_video_enabled: bool = True
    joined_at: datetime


class MeetingContract(BaseModel):
    meeting_id: str
    tenant_id: str
    title: str
    status: MeetingStatus
    state_version: int = 1
    created_at: datetime
    updated_at: datetime
