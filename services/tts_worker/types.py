"""TTS Worker Data Models and Result Types."""

import base64
from dataclasses import dataclass

import numpy as np

from packages.audio.framing import float32_to_pcm_s16le


@dataclass(frozen=True)
class TTSResult:
    """Represents a synthesized audio segment result."""

    audio_pcm: np.ndarray
    sample_rate: int = 48000
    duration_ms: int = 0
    watermarked: bool = True
    latency_ms: int = 0
    model_version: str = "mock-tts-v1"

    def to_pcm_bytes(self) -> bytes:
        """Converts float32 audio samples to 16-bit PCM byte buffer."""
        return float32_to_pcm_s16le(self.audio_pcm)

    def to_base64_uri(self) -> str:
        """Encodes audio buffer into base64 URI format."""
        pcm_bytes = self.to_pcm_bytes()
        encoded = base64.b64encode(pcm_bytes).decode("utf-8")
        return f"base64://{encoded}"
