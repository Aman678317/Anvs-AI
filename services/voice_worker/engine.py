"""Base Voice Preservation & Cloning Engine Interface (PR-01 Scaffolding / PR-11 Core)."""

from abc import ABC, abstractmethod

import numpy as np

from services.voice_worker.types import VoiceCloneResult, VoiceEmbedding


class BaseVoiceEngine(ABC):
    """Abstract base class for speaker voice profile extraction and cloned synthesis."""

    @abstractmethod
    async def extract_voice_embedding(
        self,
        audio_pcm: np.ndarray,
        sample_rate: int,
        speaker_id: str,
        tenant_id: str,
        consent_verified: bool = False,
    ) -> VoiceEmbedding:
        """Extracts vocal timbre and pitch embedding from clean speech samples."""
        raise NotImplementedError

    @abstractmethod
    async def synthesize_with_voice(
        self,
        text: str,
        language: str,
        voice_embedding: VoiceEmbedding,
    ) -> VoiceCloneResult:
        """Synthesizes speech in target language preserving speaker vocal characteristics."""
        raise NotImplementedError


class MockVoiceEngine(BaseVoiceEngine):
    """Deterministic mock voice engine for offline test execution."""

    def __init__(self, sample_rate: int = 48000) -> None:
        self.sample_rate = sample_rate

    async def extract_voice_embedding(
        self,
        audio_pcm: np.ndarray,
        sample_rate: int,
        speaker_id: str,
        tenant_id: str,
        consent_verified: bool = False,
    ) -> VoiceEmbedding:
        # Produce deterministic 256-dimensional unit embedding
        rng = np.random.default_rng(seed=hash(speaker_id) % (2**32))
        embed = rng.standard_normal(256).astype(np.float32)
        norm = np.linalg.norm(embed)
        if norm > 0:
            embed /= norm

        return VoiceEmbedding(
            speaker_id=speaker_id,
            tenant_id=tenant_id,
            embedding=embed,
            sample_rate=sample_rate,
            duration_sec=len(audio_pcm) / float(sample_rate) if sample_rate > 0 else 0.0,
            consent_verified=consent_verified,
            model_version="mock-voice-v1",
        )

    async def synthesize_with_voice(
        self,
        text: str,
        language: str,
        voice_embedding: VoiceEmbedding,
    ) -> VoiceCloneResult:
        _ = language  # Unused in deterministic mock engine
        duration_ms = max(500, len(text) * 60)
        num_samples = int((duration_ms / 1000.0) * self.sample_rate)
        # Synthetic sine wave
        t = np.linspace(0, duration_ms / 1000.0, num_samples, endpoint=False, dtype=np.float32)
        samples = 0.2 * np.sin(2 * np.pi * 220.0 * t)

        return VoiceCloneResult(
            audio_pcm=samples,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            watermarked=True,
            speaker_id=voice_embedding.speaker_id,
            latency_ms=25,
            model_version="mock-voice-v1",
        )


def create_voice_engine() -> BaseVoiceEngine:
    """Factory creating configured voice engine."""
    return MockVoiceEngine()
