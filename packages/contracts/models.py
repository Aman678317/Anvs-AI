"""Shared Domain Contracts and REST/WebSocket API Models."""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ParticipantRole(str, Enum):
    HOST = "HOST"
    MODERATOR = "MODERATOR"
    PARTICIPANT = "PARTICIPANT"
    GUEST = "GUEST"


class MeetingStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    ARCHIVED = "ARCHIVED"


class ParticipantContract(BaseModel):
    participant_id: str
    user_id: Optional[str] = None
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
