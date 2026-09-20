"""Event schemas package with Pythonic module naming."""

from .events import (
    BaseEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
    AudioSegmentEvent,
    RoomStateEvent,
)

__all__ = [
    "BaseEvent",
    "SourceSegmentEvent",
    "TranslationSegmentEvent",
    "AudioSegmentEvent",
    "RoomStateEvent",
]
