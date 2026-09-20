"""WebSocket Protocol Inbound and Outbound Frame Contracts."""

from pydantic import BaseModel, ConfigDict, Field

from .enums import AudioStreamType, MeetingStatus, WSClientMessageType, WSServerMessageType
from .rest import ParticipantContract


class BaseWSFrame(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="forbid",
    )


# --- Client to Server Frames ---


class WSClientJoinFrame(BaseWSFrame):
    type: WSClientMessageType = WSClientMessageType.JOIN
    ticket: str = Field(..., description="Single-use WebSocket session ticket issued by API")
    participant_id: str


class WSClientSetLanguageFrame(BaseWSFrame):
    type: WSClientMessageType = WSClientMessageType.SET_LISTENING_LANGUAGE
    listening_language: str = Field(
        ..., min_length=3, max_length=3, description="ISO-639-3 target listening language"
    )


class WSClientChatMessageFrame(BaseWSFrame):
    type: WSClientMessageType = WSClientMessageType.CHAT_MESSAGE
    text: str = Field(..., min_length=1, max_length=2000)


class WSClientQueryAssistantFrame(BaseWSFrame):
    type: WSClientMessageType = WSClientMessageType.QUERY_ASSISTANT
    query_id: str
    question: str = Field(..., min_length=1, max_length=1000)


class WSClientPingFrame(BaseWSFrame):
    type: WSClientMessageType = WSClientMessageType.PING
    timestamp_ms: int


# --- Server to Client Frames ---


class WSServerRoomStateFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.ROOM_STATE
    state_version: int
    status: MeetingStatus
    participants: list[ParticipantContract]


class WSServerParticipantJoinedFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.PARTICIPANT_JOINED
    state_version: int
    participant: ParticipantContract


class WSServerParticipantLeftFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.PARTICIPANT_LEFT
    state_version: int
    participant_id: str


class WSServerCaptionFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.CAPTION_UPDATE
    source_segment_id: str = Field(..., description="Immutable lineage source segment ID")
    speaker_id: str
    source_language: str
    target_language: str
    text: str
    is_final: bool
    start_ms: int
    end_ms: int


class WSServerAudioTrackFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.AUDIO_TRACK_PUBLISHED
    track_sid: str
    language: str
    stream_type: AudioStreamType


class WSServerAssistantFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.ASSISTANT_RESPONSE
    query_id: str
    answer: str
    citations: list[str] = []
    action_items: list[str] = []


class WSServerPongFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.PONG
    timestamp_ms: int


class WSServerErrorFrame(BaseWSFrame):
    type: WSServerMessageType = WSServerMessageType.ERROR
    code: str
    message: str
