"""Voice Worker Data Models and Profiles (PR-01 Scaffolding / PR-11 Core)."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VoiceEmbedding:
    """Speaker voice embedding vector for pitch and timbre preservation."""

    speaker_id: str
    tenant_id: str
    embedding: np.ndarray  # 256 or 512-dimensional speaker embedding vector
    sample_rate: int = 16000
    duration_sec: float = 0.0
    consent_verified: bool = False
    model_version: str = "voice-embed-v1"


@dataclass(frozen=True)
class VoiceCloneResult:
    """Result of voice-cloned speech synthesis."""

    audio_pcm: np.ndarray
    sample_rate: int = 48000
    duration_ms: int = 0
    watermarked: bool = True
    speaker_id: str = ""
    latency_ms: int = 0
    model_version: str = "voice-clone-v1"
