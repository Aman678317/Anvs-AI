"""REST API Request and Response Contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    DegradationTier,
    MeetingStatus,
    ParticipantRole,
    TranscriptFormat,
    WorkerHealthStatus,
)


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


class OrganizationResponse(BaseContract):
    id: str
    name: str
    slug: str
    created_at: datetime
    member_count: int = 0
    meeting_count: int = 0


class UpdateOrganizationRequest(BaseContract):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=100)


class OrganizationMemberResponse(BaseContract):
    user_id: str
    email: str
    role: ParticipantRole
    display_name: str | None = None
    is_active: bool = True
    created_at: datetime


class InviteMemberRequest(BaseContract):
    email: str = Field(..., min_length=3, max_length=255)
    role: ParticipantRole = Field(default=ParticipantRole.PARTICIPANT)
    display_name: str | None = Field(default=None, max_length=100)


class UpdateMemberRoleRequest(BaseContract):
    role: ParticipantRole | None = None
    is_active: bool | None = None


class AdminMeetingSummaryResponse(BaseContract):
    meeting_id: str
    title: str
    status: MeetingStatus
    scheduled_start: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    participant_count: int = 0
    transcript_segment_count: int = 0
    created_at: datetime


class AdminAnalyticsResponse(BaseContract):
    tenant_id: str
    active_meetings_count: int
    total_meetings_count: int
    total_transcribed_minutes: float
    total_participants_count: int
    language_breakdown: dict[str, int]
    average_translation_latency_ms: float


class AuditLogEntry(BaseContract):
    id: str
    event_type: str
    actor_email: str
    target: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class AdminAuditLogsResponse(BaseContract):
    logs: list[AuditLogEntry]
    total: int


class WorkerHeartbeatPayload(BaseContract):
    worker_type: str = Field(..., description="Worker service type (stt, nmt, tts, speaker, assistant)")
    worker_id: str = Field(..., description="Unique instance identifier of the worker")
    timestamp_ms: int = Field(..., description="Epoch millisecond timestamp of the heartbeat")
    queue_depth: int = Field(default=0, ge=0, description="Observed queue depth for this worker")
    gpu_utilization_pct: float | None = Field(default=None, ge=0.0, le=100.0, description="Optional GPU load %")


class PipelineStatusResponse(BaseContract):
    meeting_id: str = Field(..., description="Unique meeting room identifier")
    current_tier: DegradationTier = Field(default=DegradationTier.NORMAL)
    active_workers: dict[str, WorkerHealthStatus] = Field(default_factory=dict)
    queue_depths: dict[str, int] = Field(default_factory=dict)
    dropped_partials_count: int = Field(default=0, ge=0)
    uptime_seconds: float = Field(default=0.0, ge=0.0)
