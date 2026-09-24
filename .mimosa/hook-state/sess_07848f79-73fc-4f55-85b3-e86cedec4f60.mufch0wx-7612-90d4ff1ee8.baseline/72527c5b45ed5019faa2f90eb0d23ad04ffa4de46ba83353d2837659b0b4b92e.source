"""Speaker Diarization Worker Service adhering to Document 14."""

from .consumer import SpeakerConsumer
from .engine import (
    BaseSpeakerEngine,
    MockSpeakerEngine,
    PyAnnoteSpeakerEngine,
    create_speaker_engine,
)
from .profiles import (
    VoiceProfile,
    VoiceProfileRegistry,
    cosine_similarity,
    normalize_embedding,
)
from .types import DiarizationResult

__all__ = [
    "BaseSpeakerEngine",
    "DiarizationResult",
    "MockSpeakerEngine",
    "PyAnnoteSpeakerEngine",
    "SpeakerConsumer",
    "VoiceProfile",
    "VoiceProfileRegistry",
    "cosine_similarity",
    "create_speaker_engine",
    "normalize_embedding",
]
