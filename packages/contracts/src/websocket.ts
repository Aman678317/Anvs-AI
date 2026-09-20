import { AudioStreamType, MeetingStatus, WSClientMessageType, WSServerMessageType } from "./enums";
import { ParticipantContract } from "./rest";

// --- Client to Server Frames ---

export interface WSClientJoinFrame {
  type: WSClientMessageType.JOIN;
  ticket: string;
  participant_id: string;
}

export interface WSClientSetLanguageFrame {
  type: WSClientMessageType.SET_LISTENING_LANGUAGE;
  listening_language: string;
}

export interface WSClientChatMessageFrame {
  type: WSClientMessageType.CHAT_MESSAGE;
  text: string;
}

export interface WSClientQueryAssistantFrame {
  type: WSClientMessageType.QUERY_ASSISTANT;
  query_id: string;
  question: string;
}

export interface WSClientPingFrame {
  type: WSClientMessageType.PING;
  timestamp_ms: number;
}

export type WSClientFrame =
  | WSClientJoinFrame
  | WSClientSetLanguageFrame
  | WSClientChatMessageFrame
  | WSClientQueryAssistantFrame
  | WSClientPingFrame;

// --- Server to Client Frames ---

export interface WSServerRoomStateFrame {
  type: WSServerMessageType.ROOM_STATE;
  state_version: number;
  status: MeetingStatus;
  participants: ParticipantContract[];
}

export interface WSServerParticipantJoinedFrame {
  type: WSServerMessageType.PARTICIPANT_JOINED;
  state_version: number;
  participant: ParticipantContract;
}

export interface WSServerParticipantLeftFrame {
  type: WSServerMessageType.PARTICIPANT_LEFT;
  state_version: number;
  participant_id: string;
}

export interface WSServerCaptionFrame {
  type: WSServerMessageType.CAPTION_UPDATE;
  source_segment_id: string;
  speaker_id: string;
  source_language: string;
  target_language: string;
  text: string;
  is_final: boolean;
  start_ms: number;
  end_ms: number;
}

export interface WSServerAudioTrackFrame {
  type: WSServerMessageType.AUDIO_TRACK_PUBLISHED;
  track_sid: string;
  language: string;
  stream_type: AudioStreamType;
}

export interface WSServerAssistantFrame {
  type: WSServerMessageType.ASSISTANT_RESPONSE;
  query_id: string;
  answer: string;
  citations: string[];
  action_items: string[];
}

export interface WSServerPongFrame {
  type: WSServerMessageType.PONG;
  timestamp_ms: number;
}

export interface WSServerErrorFrame {
  type: WSServerMessageType.ERROR;
  code: string;
  message: string;
}

export type WSServerFrame =
  | WSServerRoomStateFrame
  | WSServerParticipantJoinedFrame
  | WSServerParticipantLeftFrame
  | WSServerCaptionFrame
  | WSServerAudioTrackFrame
  | WSServerAssistantFrame
  | WSServerPongFrame
  | WSServerErrorFrame;
