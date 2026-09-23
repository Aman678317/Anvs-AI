"""Shared Enums for Domain, REST, and WebSocket Contracts."""

from enum import StrEnum


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


class AudioStreamType(StrEnum):
    ORIGINAL_HUMAN = "ORIGINAL_HUMAN"
    TRANSLATED_SYNTHETIC = "TRANSLATED_SYNTHETIC"


class TranscriptFormat(StrEnum):
    JSON = "JSON"
    SRT = "SRT"
    VTT = "VTT"
    TXT = "TXT"


class WSClientMessageType(StrEnum):
    JOIN = "JOIN"
    SET_LISTENING_LANGUAGE = "SET_LISTENING_LANGUAGE"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    QUERY_ASSISTANT = "QUERY_ASSISTANT"
    PING = "PING"
    RESYNC = "RESYNC"


class WSServerMessageType(StrEnum):
    ROOM_STATE = "ROOM_STATE"
    PARTICIPANT_JOINED = "PARTICIPANT_JOINED"
    PARTICIPANT_LEFT = "PARTICIPANT_LEFT"
    CAPTION_UPDATE = "CAPTION_UPDATE"
    AUDIO_TRACK_PUBLISHED = "AUDIO_TRACK_PUBLISHED"
    ASSISTANT_RESPONSE = "ASSISTANT_RESPONSE"
    PONG = "PONG"
    ERROR = "ERROR"
    RESYNC_RESPONSE = "RESYNC_RESPONSE"


class DegradationTier(StrEnum):
    NORMAL = "NORMAL"
    HIGH_LOAD = "HIGH_LOAD"
    CRITICAL_LOAD = "CRITICAL_LOAD"
    EMERGENCY = "EMERGENCY"


class WorkerHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DEAD = "DEAD"
