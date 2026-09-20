"""Redis Streams Event Schemas adhering to Documents 08, 12, and 14."""

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str = Field(..., description="UUIDv4 event identifier")
    timestamp_ms: int = Field(..., description="Epoch millisecond timestamp")
    meeting_id: str = Field(..., description="UUIDv4 meeting identifier")


class SourceSegmentEvent(BaseEvent):
    """Emitted by STT Worker when a speech segment is transcribed."""

    session_id: str
    participant_id: str
    source_segment_id: str
    language: str  # ISO-639-3
    text: str
    is_final: bool
    start_ms: int
    end_ms: int
    confidence: float


class TranslationSegmentEvent(BaseEvent):
    """Emitted by Translation Worker with source lineage."""

    source_segment_id: str
    source_language: str
    target_language: str  # ISO-639-3
    translated_text: str
    is_final: bool
    latency_ms: int


class AudioSegmentEvent(BaseEvent):
    """Emitted by TTS Worker when synthesized translated audio is ready."""

    source_segment_id: str
    target_language: str
    audio_uri: str
    duration_ms: int
    sample_rate: int = 24000
    watermarked: bool = True


class RoomStateEvent(BaseEvent):
    """Emitted on room lifecycle transitions."""

    state_version: int
    status: str
    active_participants_count: int
