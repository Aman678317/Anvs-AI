"""Voice Preservation & Cloning Engine adhering to Document 14 (PR-11 Core)."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from packages.audio.watermark import embed_watermark
from packages.config.settings import settings
from packages.language_registry import normalize_code
from services.voice_worker.types import VoiceCloneResult, VoiceEmbedding

logger = logging.getLogger(__name__)


class ConsentViolationError(RuntimeError):
    """Raised when voice profile extraction or cloning is attempted without consent."""


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
        """Extracts vocal timbre and pitch embedding from clean speech samples.

        Args:
            audio_pcm: Float32 audio samples normalized in [-1.0, 1.0].
            sample_rate: Audio sample rate in Hz (nominally 16 kHz from STT).
            speaker_id: Unique speaker identifier (e.g. participant UUID).
            tenant_id: Tenant organization UUID.
            consent_verified: Must be True; raises ConsentViolationError if False.

        Returns:
            Unit-normalized 256-dim VoiceEmbedding.
        """
        raise NotImplementedError

    @abstractmethod
    async def synthesize_with_voice(
        self,
        text: str,
        language: str,
        voice_embedding: VoiceEmbedding,
    ) -> VoiceCloneResult:
        """Synthesizes speech in target language preserving speaker vocal characteristics.

        Args:
            text: Translated text to synthesize.
            language: ISO 639-3 target language code.
            voice_embedding: Source speaker VoiceEmbedding used for timbre conditioning.

        Returns:
            Watermarked VoiceCloneResult with synthesized audio samples.
        """
        raise NotImplementedError


class MockVoiceEngine(BaseVoiceEngine):
    """Deterministic, zero-dependency mock voice engine for offline testing and CI.

    Enforces Invariant #3 by applying 20 kHz ultrasonic watermark on all synthesized audio.
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        simulated_latency_ms: int = 15,
        watermark_freq_hz: float = 20000.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.simulated_latency_ms = simulated_latency_ms
        self.watermark_freq_hz = watermark_freq_hz

        # Language-to-pitch profile mapping (fundamental vocal frequency, Hz)
        self._language_pitches: dict[str, float] = {
            "eng": 160.0,
            "spa": 175.0,
            "fra": 180.0,
            "deu": 140.0,
            "zho": 210.0,
            "jpn": 220.0,
            "hin": 165.0,
            "arb": 150.0,
            "por": 170.0,
            "rus": 145.0,
        }

    async def extract_voice_embedding(
        self,
        audio_pcm: np.ndarray,
        sample_rate: int,
        speaker_id: str,
        tenant_id: str,
        consent_verified: bool = False,
    ) -> VoiceEmbedding:
        """Produces deterministic 256-dimensional unit-normalized speaker embedding."""
        if not consent_verified:
            raise ConsentViolationError(
                f"Voice embedding extraction denied for speaker '{speaker_id}': "
                "consent_verified must be True (biometric consent required)."
            )

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # Produce deterministic 256-dim unit embedding seeded by speaker_id
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
        """Generates voice-cloned speech audio with 20 kHz ultrasonic watermark."""
        t0 = time.perf_counter()

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        norm_lang = normalize_code(language)
        base_pitch = self._language_pitches.get(norm_lang, 160.0)

        # Derive unique speaker pitch offset from embedding centroid
        speaker_offset = float(np.mean(voice_embedding.embedding[:4])) * 25.0
        speaker_pitch = max(80.0, base_pitch + speaker_offset)

        # Duration estimation: ~65ms per character, clamped 400ms–8000ms
        cleaned_text = text.strip()
        char_count = max(1, len(cleaned_text))
        duration_sec = max(0.4, min(8.0, char_count * 0.065))
        duration_ms = int(duration_sec * 1000)

        total_samples = int(duration_sec * self.sample_rate)
        t_vec = np.linspace(0, duration_sec, total_samples, endpoint=False, dtype=np.float32)

        # Multi-harmonic voice synthesis
        fundamental = 0.25 * np.sin(2 * np.pi * speaker_pitch * t_vec)
        h2 = 0.12 * np.sin(2 * np.pi * (speaker_pitch * 2) * t_vec)
        h3 = 0.06 * np.sin(2 * np.pi * (speaker_pitch * 3) * t_vec)
        raw_speech = (fundamental + h2 + h3).astype(np.float32)

        # Smooth envelope (raised cosine fade-in / fade-out)
        fade_samples = min(int(0.05 * self.sample_rate), total_samples // 4)
        if fade_samples > 0:
            window = np.ones(total_samples, dtype=np.float32)
            fade_in = 0.5 * (1 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
            fade_out = 0.5 * (1 + np.cos(np.pi * np.arange(fade_samples) / fade_samples))
            window[:fade_samples] = fade_in
            window[-fade_samples:] = fade_out
            raw_speech = raw_speech * window

        # INVARIANT #3: Compulsory 20 kHz ultrasonic watermark embedding
        watermarked_audio = embed_watermark(
            audio_pcm=raw_speech,
            sample_rate=self.sample_rate,
            watermark_freq=self.watermark_freq_hz,
            amplitude=0.005,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)

        return VoiceCloneResult(
            audio_pcm=watermarked_audio,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            watermarked=True,
            speaker_id=voice_embedding.speaker_id,
            latency_ms=latency_ms,
            model_version="mock-voice-v1",
        )


class XTTSv2VoiceEngine(BaseVoiceEngine):
    """Production neural voice cloning engine using Coqui XTTS-v2 with automatic fallback.

    Uses speaker audio reference for zero-shot voice preservation.
    """

    def __init__(
        self,
        model_name: str = "coqui/XTTS-v2",
        device: str = "cpu",
        sample_rate: int = 48000,
        allow_fallback: bool = True,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.sample_rate = sample_rate
        self.allow_fallback = allow_fallback
        self._model: Any = None
        self._speaker_encoder: Any = None
        self._fallback_engine: MockVoiceEngine | None = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            from TTS.api import TTS

            logger.info(
                "Initializing XTTS-v2 voice cloning model: %s on %s", self.model_name, self.device
            )
            self._model = TTS(model_name=self.model_name)
            if self.device != "cpu" and hasattr(self._model, "to"):
                self._model.to(self.device)
        except (ImportError, Exception) as exc:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Failed to load XTTS-v2 model '{self.model_name}' with fallback disabled: {exc}"
                ) from exc
            logger.warning(
                "XTTS-v2 voice cloning unavailable (%s). Activating MockVoiceEngine fallback.", exc
            )
            self._fallback_engine = MockVoiceEngine(sample_rate=self.sample_rate)

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_engine is not None

    async def extract_voice_embedding(
        self,
        audio_pcm: np.ndarray,
        sample_rate: int,
        speaker_id: str,
        tenant_id: str,
        consent_verified: bool = False,
    ) -> VoiceEmbedding:
        if not consent_verified:
            raise ConsentViolationError(
                f"Voice embedding extraction denied for speaker '{speaker_id}': "
                "biometric consent must be verified prior to enrollment."
            )

        if self._fallback_engine is not None:
            return await self._fallback_engine.extract_voice_embedding(
                audio_pcm, sample_rate, speaker_id, tenant_id, consent_verified
            )

        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()

        def _encode() -> np.ndarray:
            # Use the XTTS speaker encoder to extract 256-dim gst embedding
            enc = self._model.synthesizer.tts_model.get_speaker_embedding(audio_pcm)
            arr = np.array(enc, dtype=np.float32).flatten()
            norm = np.linalg.norm(arr)
            return arr / norm if norm > 0 else arr

        embedding = await loop.run_in_executor(None, _encode)
        duration_sec = len(audio_pcm) / float(sample_rate) if sample_rate > 0 else 0.0

        logger.debug(
            "Extracted voice embedding for speaker '%s' (%.2fs audio, %.0fms)",
            speaker_id,
            duration_sec,
            (time.perf_counter() - t0) * 1000,
        )

        return VoiceEmbedding(
            speaker_id=speaker_id,
            tenant_id=tenant_id,
            embedding=embedding,
            sample_rate=sample_rate,
            duration_sec=duration_sec,
            consent_verified=consent_verified,
            model_version=self.model_name,
        )

    async def synthesize_with_voice(
        self,
        text: str,
        language: str,
        voice_embedding: VoiceEmbedding,
    ) -> VoiceCloneResult:
        if self._fallback_engine is not None:
            return await self._fallback_engine.synthesize_with_voice(
                text, language, voice_embedding
            )

        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()

        def _infer() -> np.ndarray:
            # XTTS-v2 zero-shot synthesis using cached speaker embedding
            wav = self._model.tts(
                text=text,
                language=language,
                speaker_embedding=voice_embedding.embedding,
            )
            return np.array(wav, dtype=np.float32)

        raw_audio = await loop.run_in_executor(None, _infer)

        # INVARIANT #3: Compulsory 20 kHz ultrasonic watermark
        watermarked_audio = embed_watermark(
            audio_pcm=raw_audio,
            sample_rate=self.sample_rate,
            watermark_freq=settings.tts_watermark_freq_hz,
        )

        duration_ms = int((len(watermarked_audio) / self.sample_rate) * 1000)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        return VoiceCloneResult(
            audio_pcm=watermarked_audio,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            watermarked=True,
            speaker_id=voice_embedding.speaker_id,
            latency_ms=latency_ms,
            model_version=self.model_name,
        )


def create_voice_engine(
    engine_type: str | None = None,
    device: str | None = None,
    sample_rate: int | None = None,
    allow_fallback: bool = True,
) -> BaseVoiceEngine:
    """Factory creating a VoiceEngine instance configured from settings or parameters."""
    selected_type = (engine_type or settings.tts_engine_type).strip().lower()

    if selected_type in {"mock", "test"}:
        return MockVoiceEngine(sample_rate=sample_rate or settings.tts_sample_rate)

    if selected_type in {"xtts", "xtts-v2", "neural"}:
        return XTTSv2VoiceEngine(
            device=device or settings.tts_device,
            sample_rate=sample_rate or settings.tts_sample_rate,
            allow_fallback=allow_fallback,
        )

    logger.warning("Unknown voice engine type '%s', defaulting to MockVoiceEngine", selected_type)
    return MockVoiceEngine(sample_rate=sample_rate or settings.tts_sample_rate)
