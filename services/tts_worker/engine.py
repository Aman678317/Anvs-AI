"""Streaming Text-to-Speech (TTS) Inference Engines adhering to Document 14."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod

import numpy as np

from packages.audio.watermark import embed_watermark
from packages.config.settings import settings
from packages.language_registry import normalize_code
from services.tts_worker.types import TTSResult

logger = logging.getLogger(__name__)


class BaseTTSEngine(ABC):
    """Abstract base class for text-to-speech synthesis engines."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "eng",
        voice_id: str | None = None,
    ) -> TTSResult:
        """Synthesizes text into watermarked audio samples."""
        pass


class MockTTSEngine(BaseTTSEngine):
    """Deterministic, zero-dependency mock TTS engine for local testing and CI.

    Enforces Invariant #3: Compulsory 20 kHz ultrasonic watermarking on all output buffers.
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

        # Language pitch profiles for vocal formants (Hz)
        self._language_pitches: dict[str, float] = {
            "eng": 160.0,
            "spa": 175.0,
            "fra": 180.0,
            "deu": 140.0,
            "zho": 210.0,
            "jpn": 220.0,
            "hin": 165.0,
        }

    async def synthesize(
        self,
        text: str,
        language: str = "eng",
        voice_id: str | None = None,
    ) -> TTSResult:
        """Generates synthetic speech audio with 20 kHz ultrasonic watermark."""
        _ = voice_id
        t0 = time.perf_counter()

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        cleaned_text = text.strip()
        norm_lang = normalize_code(language)
        base_pitch = self._language_pitches.get(norm_lang, 160.0)

        # Estimate duration from text: ~65ms per character, clamped between 400ms and 8000ms
        char_count = max(1, len(cleaned_text))
        duration_sec = max(0.4, min(8.0, char_count * 0.065))
        duration_ms = int(duration_sec * 1000)

        total_samples = int(duration_sec * self.sample_rate)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False, dtype=np.float32)

        # Multi-harmonic speech waveform synthesis
        fundamental = 0.25 * np.sin(2 * np.pi * base_pitch * t)
        h2 = 0.12 * np.sin(2 * np.pi * (base_pitch * 2) * t)
        h3 = 0.06 * np.sin(2 * np.pi * (base_pitch * 3) * t)
        synthetic_speech = (fundamental + h2 + h3).astype(np.float32)

        # Smooth envelope window (raised cosine fade-in and fade-out)
        fade_samples = min(int(0.05 * self.sample_rate), total_samples // 4)
        if fade_samples > 0:
            window = np.ones(total_samples, dtype=np.float32)
            fade_in = 0.5 * (1 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
            fade_out = 0.5 * (1 + np.cos(np.pi * np.arange(fade_samples) / fade_samples))
            window[:fade_samples] = fade_in
            window[-fade_samples:] = fade_out
            synthetic_speech = synthetic_speech * window

        # INVARIANT #3: Compulsory 20 kHz ultrasonic watermark embedding
        watermarked_audio = embed_watermark(
            audio_pcm=synthetic_speech,
            sample_rate=self.sample_rate,
            watermark_freq=self.watermark_freq_hz,
            amplitude=0.005,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)

        return TTSResult(
            audio_pcm=watermarked_audio,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            watermarked=True,
            latency_ms=latency_ms,
            model_version="mock-tts-v1",
        )


class XTTSv2Engine(BaseTTSEngine):
    """Production neural TTS engine using Coqui XTTS-v2 with automatic fallback."""

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
        self._model = None
        self._fallback_engine: MockTTSEngine | None = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            # Production import for XTTS
            from TTS.api import TTS

            logger.info("Initializing neural TTS model: %s on %s", self.model_name, self.device)
            self._model = TTS(model_name=self.model_name)
            if self.device != "cpu" and hasattr(self._model, "to"):
                self._model.to(self.device)
        except (ImportError, Exception) as exc:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Failed to load TTS model '{self.model_name}' and fallback is disabled: {exc}"
                ) from exc

            logger.warning("Neural TTS unavailable (%s). Activating MockTTSEngine fallback.", exc)
            self._fallback_engine = MockTTSEngine(
                sample_rate=self.sample_rate,
                simulated_latency_ms=15,
            )

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_engine is not None

    async def synthesize(
        self,
        text: str,
        language: str = "eng",
        voice_id: str | None = None,
    ) -> TTSResult:
        if self._fallback_engine is not None:
            return await self._fallback_engine.synthesize(text, language, voice_id)

        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()

        def _infer() -> np.ndarray:
            wav = self._model.tts(text=text, language=language, speaker=voice_id)
            return np.array(wav, dtype=np.float32)

        raw_audio = await loop.run_in_executor(None, _infer)

        # Invariant #3: Apply 20 kHz ultrasonic watermark
        watermarked_audio = embed_watermark(
            audio_pcm=raw_audio,
            sample_rate=self.sample_rate,
            watermark_freq=settings.tts_watermark_freq_hz,
        )

        duration_ms = int((len(watermarked_audio) / self.sample_rate) * 1000)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        return TTSResult(
            audio_pcm=watermarked_audio,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            watermarked=True,
            latency_ms=latency_ms,
            model_version=self.model_name,
        )


def create_tts_engine(
    engine_type: str | None = None,
    model_name: str | None = None,
    device: str | None = None,
    sample_rate: int | None = None,
    allow_fallback: bool = True,
) -> BaseTTSEngine:
    """Factory creating a TTS engine instance configured from settings or parameters."""
    selected_type = (engine_type or settings.tts_engine_type).strip().lower()

    if selected_type in {"mock", "test"}:
        return MockTTSEngine(sample_rate=sample_rate or settings.tts_sample_rate)

    if selected_type in {"xtts", "xtts-v2", "neural", "melo"}:
        return XTTSv2Engine(
            model_name=model_name or settings.tts_model_name,
            device=device or settings.tts_device,
            sample_rate=sample_rate or settings.tts_sample_rate,
            allow_fallback=allow_fallback,
        )

    logger.warning("Unknown TTS engine type '%s', defaulting to MockTTSEngine", selected_type)
    return MockTTSEngine(sample_rate=sample_rate or settings.tts_sample_rate)
