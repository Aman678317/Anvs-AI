"""Redis Streams Event Schemas adhering to Documents 08, 12, and 14."""

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="forbid",
    )

    event_id: str = Field(..., description="UUIDv4 event identifier")
    timestamp_ms: int = Field(..., description="Epoch millisecond timestamp")
    meeting_id: str = Field(..., description="UUIDv4 meeting identifier")
    tenant_id: str = Field(default="default", description="Organization or tenant identifier")


class SourceSegmentEvent(BaseEvent):
    """Emitted by STT Worker when a speech segment is transcribed."""

    session_id: str = Field(..., description="WebRTC session identifier")
    participant_id: str = Field(..., description="Speaker participant identifier")
    source_segment_id: str = Field(..., description="Immutable lineage source segment identifier")
    language: str = Field(..., min_length=3, max_length=3, description="ISO-639-3 spoken language code")
    text: str = Field(..., description="Transcribed speech text")
    is_final: bool = Field(..., description="Whether this segment is a final commitment")
    start_ms: int = Field(..., ge=0, description="Start offset in milliseconds")
    end_ms: int = Field(..., ge=0, description="End offset in milliseconds")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Transcription confidence score")
    speaker_tag: str | None = Field(default=None, description="Optional diarization speaker tag")


class TranslationSegmentEvent(BaseEvent):
    """Emitted by Translation Worker with source lineage."""

    source_segment_id: str = Field(..., description="Immutable lineage linking to SourceSegmentEvent")
    source_language: str = Field(..., min_length=3, max_length=3, description="ISO-639-3 source language code")
    target_language: str = Field(..., min_length=3, max_length=3, description="ISO-639-3 target language code")
    translated_text: str = Field(..., description="Translated text content")
    is_final: bool = Field(..., description="Whether this translation corresponds to a final transcript")
    latency_ms: int = Field(..., ge=0, description="Translation compute latency in milliseconds")


class AudioSegmentEvent(BaseEvent):
    """Emitted by TTS Worker when synthesized translated audio is ready."""

    source_segment_id: str = Field(..., description="Immutable lineage linking to SourceSegmentEvent")
    target_language: str = Field(..., min_length=3, max_length=3, description="ISO-639-3 target language code")
    audio_uri: str = Field(..., description="URI or storage key of synthesized audio payload")
    duration_ms: int = Field(..., ge=0, description="Audio playback duration in milliseconds")
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz")
    watermarked: bool = Field(default=True, description="Flag verifying 20 kHz acoustic watermark embedding")


class DiarizationSegmentEvent(BaseEvent):
    """Emitted by Diarization Worker identifying speaker profile."""

    source_segment_id: str = Field(..., description="Immutable lineage linking to SourceSegmentEvent")
    speaker_id: str = Field(..., description="Identified speaker identifier or cluster ID")
    speaker_name: str | None = Field(default=None, description="Resolved speaker display name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Speaker recognition confidence")


class AssistantQueryEvent(BaseEvent):
    """Emitted when a meeting participant queries the AI assistant."""

    query_id: str = Field(..., description="UUIDv4 assistant query identifier")
    participant_id: str = Field(..., description="Querying participant identifier")
    question: str = Field(..., min_length=1, max_length=2000, description="Natural language question")


class AssistantResponseEvent(BaseEvent):
    """Emitted by Assistant Worker with grounded response and citations."""

    query_id: str = Field(..., description="Linked assistant query identifier")
    answer: str = Field(..., description="Assistant response text")
    citations: list[str] = Field(default_factory=list, description="Meeting transcript citations")
    action_items: list[str] = Field(default_factory=list, description="Extracted meeting action items")


class RoomStateEvent(BaseEvent):
    """Emitted on room lifecycle transitions."""

    state_version: int = Field(..., ge=1, description="Monotonically increasing state version")
    status: str = Field(..., description="Current meeting status string")
    active_participants_count: int = Field(default=0, ge=0, description="Number of currently connected participants")


class DeadLetterEvent(BaseEvent):
    """Emitted to Dead Letter Queue (DLQ) when an event packet fails processing."""

    failed_event_id: str = Field(..., description="Identifier of the failing event")
    original_stream: str = Field(..., description="Stream name where failure occurred")
    error_reason: str = Field(..., description="Exception or error message description")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts made")
    raw_payload: str = Field(..., description="Raw string payload of the failing message")
