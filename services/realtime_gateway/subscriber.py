"""Redis Stream Subscriber and Event-to-WebSocket Frame Converter."""

import logging
from typing import Any

from packages.contracts import (
    BaseWSFrame,
    MeetingStatus,
    ParticipantContract,
    WSServerAssistantFrame,
    WSServerCaptionFrame,
    WSServerRoomStateFrame,
)
from packages.event_schema import (
    STREAM_ASSISTANT,
    STREAM_ROOM_STATE,
    STREAM_TRANSCRIPTS,
    STREAM_TRANSLATIONS,
    AssistantResponseEvent,
    RedisStreamBus,
    RoomStateEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from services.realtime_gateway.manager import ConnectionManager

logger = logging.getLogger(__name__)


def source_segment_to_caption_frame(event: SourceSegmentEvent) -> WSServerCaptionFrame:
    """Converts a SourceSegmentEvent into a WSServerCaptionFrame for original speech listeners."""
    return WSServerCaptionFrame(
        source_segment_id=event.source_segment_id,
        speaker_id=event.participant_id,
        source_language=event.language,
        target_language=event.language,
        text=event.text,
        is_final=event.is_final,
        start_ms=event.start_ms,
        end_ms=event.end_ms,
    )


def translation_segment_to_caption_frame(
    event: TranslationSegmentEvent,
    speaker_id: str = "",
    start_ms: int = 0,
    end_ms: int = 0,
) -> WSServerCaptionFrame:
    """Converts a TranslationSegmentEvent into a WSServerCaptionFrame with lineage preservation."""
    return WSServerCaptionFrame(
        source_segment_id=event.source_segment_id,
        speaker_id=speaker_id,
        source_language=event.source_language,
        target_language=event.target_language,
        text=event.translated_text,
        is_final=event.is_final,
        start_ms=start_ms,
        end_ms=end_ms,
    )


def room_state_to_frame(
    event: RoomStateEvent,
    participants: list[ParticipantContract] | None = None,
) -> WSServerRoomStateFrame:
    """Converts a RoomStateEvent into a WSServerRoomStateFrame."""
    try:
        status = MeetingStatus(event.status.upper())
    except (ValueError, AttributeError):
        status = MeetingStatus.ACTIVE

    return WSServerRoomStateFrame(
        state_version=event.state_version,
        status=status,
        participants=participants or [],
    )


def assistant_response_to_frame(event: AssistantResponseEvent) -> WSServerAssistantFrame:
    """Converts an AssistantResponseEvent into a WSServerAssistantFrame."""
    return WSServerAssistantFrame(
        query_id=event.query_id,
        answer=event.answer,
        citations=event.citations,
        action_items=event.action_items,
    )


class RedisStreamSubscriber:
    """Subscribes to Redis Stream channels and dispatches WebSocket frames to ConnectionManager."""

    def __init__(
        self,
        stream_bus: RedisStreamBus | None = None,
        manager: ConnectionManager | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.manager = manager

    async def handle_source_segment(self, event: SourceSegmentEvent) -> WSServerCaptionFrame:
        """Processes a SourceSegmentEvent and routes to source language listeners."""
        frame = source_segment_to_caption_frame(event)
        if self.manager:
            await self.manager.deliver_caption_event(event.meeting_id, frame)
        return frame

    async def handle_translation_segment(
        self,
        event: TranslationSegmentEvent,
        speaker_id: str = "",
        start_ms: int = 0,
        end_ms: int = 0,
    ) -> WSServerCaptionFrame:
        """Processes a TranslationSegmentEvent and routes to target language listeners."""
        frame = translation_segment_to_caption_frame(
            event=event,
            speaker_id=speaker_id,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        if self.manager:
            await self.manager.deliver_caption_event(event.meeting_id, frame)
        return frame

    async def handle_room_state(
        self,
        event: RoomStateEvent,
        participants: list[ParticipantContract] | None = None,
    ) -> WSServerRoomStateFrame:
        """Processes a RoomStateEvent and broadcasts to all room participants."""
        frame = room_state_to_frame(event, participants)
        if self.manager:
            await self.manager.broadcast_to_meeting(event.meeting_id, frame)
        return frame

    async def handle_assistant_response(
        self,
        event: AssistantResponseEvent,
    ) -> WSServerAssistantFrame:
        """Processes an AssistantResponseEvent and broadcasts to the meeting."""
        frame = assistant_response_to_frame(event)
        if self.manager:
            await self.manager.broadcast_to_meeting(event.meeting_id, frame)
        return frame

    async def process_raw_event(
        self,
        stream_name_or_type: str,
        payload: dict[str, Any],
    ) -> BaseWSFrame | None:
        """Parses a raw Redis message dict according to the stream type and dispatches frame."""
        stream_type = stream_name_or_type.lower()

        if STREAM_TRANSCRIPTS in stream_type:
            source_event = SourceSegmentEvent.model_validate(payload)
            return await self.handle_source_segment(source_event)

        if STREAM_TRANSLATIONS in stream_type:
            trans_event = TranslationSegmentEvent.model_validate(payload)
            return await self.handle_translation_segment(trans_event)

        if STREAM_ROOM_STATE in stream_type:
            state_event = RoomStateEvent.model_validate(payload)
            return await self.handle_room_state(state_event)

        if STREAM_ASSISTANT in stream_type:
            asst_event = AssistantResponseEvent.model_validate(payload)
            return await self.handle_assistant_response(asst_event)

        logger.debug("Unrecognized or unhandled stream type: %s", stream_name_or_type)
        return None
