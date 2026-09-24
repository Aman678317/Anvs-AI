import { AudioStreamType, ParticipantRole } from "@multilingual/contracts";

export type AudioTrackMode = "original" | "translated";

export type DrawerPanel = "none" | "chat" | "assistant" | "participants" | "settings";

export interface CaptionSegment {
  id: string;
  source_segment_id: string;
  speaker_id: string;
  speaker_name: string;
  source_language: string;
  target_language: string;
  original_text: string;
  translated_text: string;
  is_final: boolean;
  start_ms: number;
  end_ms: number;
  timestamp_ms: number;
}

export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  text: string;
  timestamp_ms: number;
  is_self: boolean;
}

export interface AssistantQueryItem {
  query_id: string;
  question: string;
  answer?: string;
  citations?: string[];
  action_items?: string[];
  is_loading: boolean;
  timestamp_ms: number;
}

export interface MeetingParticipant {
  participant_id: string;
  display_name: string;
  role: ParticipantRole;
  spoken_language: string;
  listening_language: string;
  is_muted: boolean;
  is_video_enabled: boolean;
  is_speaking: boolean;
  audio_level: number;
}

export interface AudioTrackMetadata {
  track_sid: string;
  language: string;
  stream_type: AudioStreamType;
}
