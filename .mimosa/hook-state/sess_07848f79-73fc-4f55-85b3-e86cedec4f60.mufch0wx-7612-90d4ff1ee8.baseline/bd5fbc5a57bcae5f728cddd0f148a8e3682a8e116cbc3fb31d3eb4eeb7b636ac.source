"""Voice Cloning & Speaker Voice Preservation Worker Service (PR-11 Core)."""

from services.voice_worker.consumer import VoiceWorkerConsumer
from services.voice_worker.engine import (
    BaseVoiceEngine,
    ConsentViolationError,
    MockVoiceEngine,
    XTTSv2VoiceEngine,
    create_voice_engine,
)
from services.voice_worker.types import VoiceCloneResult, VoiceConsentRecord, VoiceEmbedding

__all__ = [
    "BaseVoiceEngine",
    "ConsentViolationError",
    "MockVoiceEngine",
    "VoiceCloneResult",
    "VoiceConsentRecord",
    "VoiceEmbedding",
    "VoiceWorkerConsumer",
    "XTTSv2VoiceEngine",
    "create_voice_engine",
]
