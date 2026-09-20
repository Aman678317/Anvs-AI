"""REST API Request and Response Contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import MeetingStatus, ParticipantRole, TranscriptFormat


class BaseContract(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="forbid",
    )


class AuthTokenRequest(BaseContract):
    user_id: str = Field(..., description="Unique user identifier")
    tenant_id: str = Field(..., description="Organization or tenant identifier")
    email: str = Field(..., description="User primary email address")
    role: ParticipantRole = Field(default=ParticipantRole.PARTICIPANT)


class AuthTokenResponse(BaseContract):
    access_token: str
    token_type: str = "Bearer"
    expires_in_sec: int
    tenant_id: str
    user_id: str


class CreateMeetingRequest(BaseContract):
    title: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    host_spoken_language: str = Field(
        default="eng", min_length=3, max_length=3, description="ISO-639-3 spoken language"
    )
    host_listening_language: str = Field(
        default="eng", min_length=3, max_length=3, description="ISO-639-3 listening language"
    )
    scheduled_start: datetime | None = None
    passcode: str | None = Field(default=None, max_length=32)


class CreateMeetingResponse(BaseContract):
    meeting_id: str
    tenant_id: str
    title: str
    status: MeetingStatus = MeetingStatus.SCHEDULED
    state_version: int = 1
    created_at: datetime


class GetMeetingResponse(BaseContract):
    meeting_id: str
    tenant_id: str
    title: str
    status: MeetingStatus
    state_version: int
    created_at: datetime
    active_participants_count: int = 0


class EndMeetingRequest(BaseContract):
    reason: str = Field(default="HOST_TERMINATED", max_length=200)


class JoinMeetingRequest(BaseContract):
    display_name: str = Field(..., min_length=1, max_length=100)
    spoken_language: str = Field(
        default="eng", min_length=3, max_length=3, description="ISO-639-3 code"
    )
    listening_language: str = Field(
        default="eng", min_length=3, max_length=3, description="ISO-639-3 code"
    )
    passcode: str | None = None


class JoinMeetingResponse(BaseContract):
    meeting_id: str
    participant_id: str
    display_name: str
    role: ParticipantRole
    livekit_token: str
    ws_ticket: str
    state_version: int


class UpdateParticipantRequest(BaseContract):
    display_name: str | None = Field(default=None, max_length=100)
    spoken_language: str | None = Field(default=None, min_length=3, max_length=3)
    listening_language: str | None = Field(default=None, min_length=3, max_length=3)
    is_muted: bool | None = None
    is_video_enabled: bool | None = None


class ParticipantContract(BaseContract):
    participant_id: str
    user_id: str | None = None
    display_name: str
    role: ParticipantRole
    spoken_language: str = Field(..., description="ISO-639-3 spoken language code")
    listening_language: str = Field(..., description="ISO-639-3 personalized listening language")
    is_muted: bool = False
    is_video_enabled: bool = True
    joined_at: datetime


class MeetingContract(BaseContract):
    meeting_id: str
    tenant_id: str
    title: str
    status: MeetingStatus
    state_version: int = 1
    created_at: datetime
    updated_at: datetime


class TranscriptSegmentResponse(BaseContract):
    source_segment_id: str
    speaker_id: str
    speaker_name: str
    source_language: str
    target_language: str
    original_text: str
    translated_text: str
    start_ms: int
    end_ms: int
    is_final: bool


class GetTranscriptResponse(BaseContract):
    meeting_id: str
    total_segments: int
    format: TranscriptFormat
    segments: list[TranscriptSegmentResponse]
