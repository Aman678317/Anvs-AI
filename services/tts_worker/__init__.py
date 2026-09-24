"""Text-to-Speech (TTS) Worker Service adhering to Document 14."""

from .consumer import TTSConsumer
from .egress import LiveKitAudioEgress, LiveKitAudioPublisher
from .engine import (
    BaseTTSEngine,
    MockTTSEngine,
    PiperTTSEngine,
    XTTSv2Engine,
    create_tts_engine,
)
from .types import TTSResult

__all__ = [
    "BaseTTSEngine",
    "LiveKitAudioEgress",
    "LiveKitAudioPublisher",
    "MockTTSEngine",
    "PiperTTSEngine",
    "TTSConsumer",
    "TTSResult",
    "XTTSv2Engine",
    "create_tts_engine",
]
