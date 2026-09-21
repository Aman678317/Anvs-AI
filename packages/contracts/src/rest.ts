import {
  DegradationTier,
  MeetingStatus,
  ParticipantRole,
  TranscriptFormat,
  WorkerHealthStatus,
} from "./enums";

export interface AuthTokenRequest {
  user_id: string;
  tenant_id: string;
  email: string;
  role?: ParticipantRole;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in_sec: number;
  tenant_id: string;
  user_id: string;
}

export interface CreateMeetingRequest {
  title: string;
  host_spoken_language?: string;
  host_listening_language?: string;
  scheduled_start?: string;
  passcode?: string;
}

export interface CreateMeetingResponse {
  meeting_id: string;
  tenant_id: string;
  title: string;
  status: MeetingStatus;
  state_version: number;
  created_at: string;
}

export interface GetMeetingResponse {
  meeting_id: string;
  tenant_id: string;
  title: string;
  status: MeetingStatus;
  state_version: number;
  created_at: string;
  active_participants_count: number;
}

export interface EndMeetingRequest {
  reason?: string;
}

export interface JoinMeetingRequest {
  display_name: string;
  spoken_language?: string;
  listening_language?: string;
  passcode?: string;
}

export interface JoinMeetingResponse {
  meeting_id: string;
  participant_id: string;
  display_name: string;
  role: ParticipantRole;
  livekit_token: string;
  ws_ticket: string;
  state_version: number;
}

export interface UpdateParticipantRequest {
  display_name?: string;
  spoken_language?: string;
  listening_language?: string;
  is_muted?: boolean;
  is_video_enabled?: boolean;
}

export interface ParticipantContract {
  participant_id: string;
  user_id?: string | null;
  display_name: string;
  role: ParticipantRole;
  spoken_language: string;
  listening_language: string;
  is_muted: boolean;
  is_video_enabled: boolean;
  joined_at: string;
}

export interface MeetingContract {
  meeting_id: string;
  tenant_id: string;
  title: string;
  status: MeetingStatus;
  state_version: number;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSegmentResponse {
  source_segment_id: string;
  speaker_id: string;
  speaker_name: string;
  source_language: string;
  target_language: string;
  original_text: string;
  translated_text: string;
  start_ms: number;
  end_ms: number;
  is_final: boolean;
}

export interface GetTranscriptResponse {
  meeting_id: string;
  total_segments: number;
  format: TranscriptFormat;
  segments: TranscriptSegmentResponse[];
}

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  member_count: number;
  meeting_count: number;
}

export interface UpdateOrganizationRequest {
  name?: string;
  slug?: string;
}

export interface OrganizationMemberResponse {
  user_id: string;
  email: string;
  role: ParticipantRole;
  display_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface InviteMemberRequest {
  email: string;
  role?: ParticipantRole;
  display_name?: string | null;
}

export interface UpdateMemberRoleRequest {
  role?: ParticipantRole;
  is_active?: boolean;
}

export interface AdminMeetingSummaryResponse {
  meeting_id: string;
  title: string;
  status: MeetingStatus;
  scheduled_start?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  duration_seconds?: number | null;
  participant_count: number;
  transcript_segment_count: number;
  created_at: string;
}

export interface AdminAnalyticsResponse {
  tenant_id: string;
  active_meetings_count: number;
  total_meetings_count: number;
  total_transcribed_minutes: number;
  total_participants_count: number;
  language_breakdown: Record<string, number>;
  average_translation_latency_ms: number;
}

export interface AuditLogEntry {
  id: string;
  event_type: string;
  actor_email: string;
  target: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface AdminAuditLogsResponse {
  logs: AuditLogEntry[];
  total: number;
}

export interface WorkerHeartbeatPayload {
  worker_type: string;
  worker_id: string;
  timestamp_ms: number;
  queue_depth?: number;
  gpu_utilization_pct?: number | null;
}

export interface PipelineStatusResponse {
  meeting_id: string;
  current_tier: DegradationTier;
  active_workers: Record<string, WorkerHealthStatus>;
  queue_depths: Record<string, number>;
  dropped_partials_count: number;
  uptime_seconds: number;
}
