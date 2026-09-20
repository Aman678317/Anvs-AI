/**
 * Redis Streams Event Contracts adhering to Documents 08, 12, and 14.
 */

export interface BaseEvent {
  event_id: string;
  timestamp_ms: number;
  meeting_id: string;
  tenant_id: string;
}

export interface SourceSegmentEvent extends BaseEvent {
  session_id: string;
  participant_id: string;
  source_segment_id: string;
  language: string;
  text: string;
  is_final: boolean;
  start_ms: number;
  end_ms: number;
  confidence: number;
  speaker_tag?: string | null;
}

export interface TranslationSegmentEvent extends BaseEvent {
  source_segment_id: string;
  source_language: string;
  target_language: string;
  translated_text: string;
  is_final: boolean;
  latency_ms: number;
}

export interface AudioSegmentEvent extends BaseEvent {
  source_segment_id: string;
  target_language: string;
  audio_uri: string;
  duration_ms: number;
  sample_rate: number;
  watermarked: boolean;
}

export interface DiarizationSegmentEvent extends BaseEvent {
  source_segment_id: string;
  speaker_id: string;
  speaker_name?: string | null;
  confidence: number;
}

export interface AssistantQueryEvent extends BaseEvent {
  query_id: string;
  participant_id: string;
  question: string;
}

export interface AssistantResponseEvent extends BaseEvent {
  query_id: string;
  answer: string;
  citations: string[];
  action_items: string[];
}

export interface RoomStateEvent extends BaseEvent {
  state_version: number;
  status: string;
  active_participants_count: number;
}

export interface DeadLetterEvent extends BaseEvent {
  failed_event_id: string;
  original_stream: string;
  error_reason: string;
  retry_count: number;
  raw_payload: string;
}

export type MeetingEvent =
  | SourceSegmentEvent
  | TranslationSegmentEvent
  | AudioSegmentEvent
  | DiarizationSegmentEvent
  | AssistantQueryEvent
  | AssistantResponseEvent
  | RoomStateEvent
  | DeadLetterEvent;
