"""Unit tests for Redis Stream Subscriber and Event-to-WebSocket conversion."""

import pytest

from packages.contracts import (
    MeetingStatus,
    WSServerAssistantFrame,
    WSServerCaptionFrame,
    WSServerMessageType,
    WSServerRoomStateFrame,
)
from packages.event_schema import (
    AssistantResponseEvent,
    RoomStateEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from services.realtime_gateway.manager import ConnectionManager
from services.realtime_gateway.subscriber import (
    RedisStreamSubscriber,
    assistant_response_to_frame,
    room_state_to_frame,
    source_segment_to_caption_frame,
    translation_segment_to_caption_frame,
)


@pytest.mark.unit
def test_source_segment_to_caption_frame_conversion() -> None:
    event = SourceSegmentEvent(
        event_id="evt-stt-101",
        timestamp_ms=1710000001000,
        meeting_id="meeting-xyz",
        tenant_id="tenant-abc",
        session_id="sess-1",
        participant_id="spk-host",
        source_segment_id="src-lineage-100",
        language="eng",
        text="Welcome to the multilingual conference.",
        is_final=True,
        start_ms=0,
        end_ms=2500,
        confidence=0.98,
    )

    frame = source_segment_to_caption_frame(event)
    assert frame.type == WSServerMessageType.CAPTION_UPDATE
    assert frame.source_segment_id == "src-lineage-100"
    assert frame.speaker_id == "spk-host"
    assert frame.source_language == "eng"
    assert frame.target_language == "eng"
    assert frame.text == "Welcome to the multilingual conference."
    assert frame.is_final is True
    assert frame.start_ms == 0
    assert frame.end_ms == 2500


@pytest.mark.unit
def test_translation_segment_to_caption_frame_lineage_preservation() -> None:
    """Validates Invariant #2: Source segment lineage is strictly preserved."""
    event = TranslationSegmentEvent(
        event_id="evt-nmt-201",
        timestamp_ms=1710000002000,
        meeting_id="meeting-xyz",
        tenant_id="tenant-abc",
        source_segment_id="src-lineage-100",
        source_language="eng",
        target_language="jpn",
        translated_text="多言語会議へようこそ。",
        is_final=True,
        latency_ms=120,
    )

    frame = translation_segment_to_caption_frame(
        event=event,
        speaker_id="spk-host",
        start_ms=0,
        end_ms=2500,
    )
    assert frame.type == WSServerMessageType.CAPTION_UPDATE
    assert frame.source_segment_id == "src-lineage-100"  # Strict lineage preservation
    assert frame.speaker_id == "spk-host"
    assert frame.source_language == "eng"
    assert frame.target_language == "jpn"
    assert frame.text == "多言語会議へようこそ。"
    assert frame.is_final is True


@pytest.mark.unit
def test_room_state_to_frame_conversion() -> None:
    event = RoomStateEvent(
        event_id="evt-room-301",
        timestamp_ms=1710000003000,
        meeting_id="meeting-xyz",
        tenant_id="tenant-abc",
        state_version=5,
        status="ACTIVE",
        active_participants_count=3,
    )

    frame = room_state_to_frame(event)
    assert isinstance(frame, WSServerRoomStateFrame)
    assert frame.type == WSServerMessageType.ROOM_STATE
    assert frame.state_version == 5
    assert frame.status == MeetingStatus.ACTIVE


@pytest.mark.unit
def test_assistant_response_to_frame_conversion() -> None:
    event = AssistantResponseEvent(
        event_id="evt-asst-401",
        timestamp_ms=1710000004000,
        meeting_id="meeting-xyz",
        tenant_id="tenant-abc",
        query_id="query-abc-123",
        answer="The project roadmap was approved in Q1.",
        citations=["segment-src-12", "segment-src-14"],
        action_items=["Alice to publish the sprint backlog by Friday."],
    )

    frame = assistant_response_to_frame(event)
    assert isinstance(frame, WSServerAssistantFrame)
    assert frame.type == WSServerMessageType.ASSISTANT_RESPONSE
    assert frame.query_id == "query-abc-123"
    assert frame.answer == "The project roadmap was approved in Q1."
    assert frame.citations == ["segment-src-12", "segment-src-14"]
    assert frame.action_items == ["Alice to publish the sprint backlog by Friday."]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_raw_event_routing() -> None:
    manager = ConnectionManager()
    subscriber = RedisStreamSubscriber(manager=manager)

    stt_payload = {
        "event_id": "evt-raw-1",
        "timestamp_ms": 1710000005000,
        "meeting_id": "meeting-raw",
        "tenant_id": "tenant-raw",
        "session_id": "sess-raw",
        "participant_id": "part-raw",
        "source_segment_id": "src-seg-raw",
        "language": "spa",
        "text": "Hola a todos.",
        "is_final": True,
        "start_ms": 100,
        "end_ms": 900,
        "confidence": 0.95,
    }

    frame = await subscriber.process_raw_event("events:meeting:transcripts", stt_payload)
    assert isinstance(frame, WSServerCaptionFrame)
    assert frame.source_language == "spa"
    assert frame.text == "Hola a todos."

    nmt_payload = {
        "event_id": "evt-raw-2",
        "timestamp_ms": 1710000006000,
        "meeting_id": "meeting-raw",
        "tenant_id": "tenant-raw",
        "source_segment_id": "src-seg-raw",
        "source_language": "spa",
        "target_language": "eng",
        "translated_text": "Hello everyone.",
        "is_final": True,
        "latency_ms": 45,
    }

    frame2 = await subscriber.process_raw_event("events:meeting:translations", nmt_payload)
    assert isinstance(frame2, WSServerCaptionFrame)
    assert frame2.target_language == "eng"
    assert frame2.text == "Hello everyone."
