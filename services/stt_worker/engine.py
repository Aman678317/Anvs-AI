"""Streaming Speech-to-Text Inference Engines adhering to Document 14."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import numpy as np

from packages.config.settings import settings
from services.stt_worker.language import to_iso639_1, to_iso639_3
from services.stt_worker.types import STTResult

logger = logging.getLogger(__name__)


class BaseSTTEngine(ABC):
    """Abstract base class for streaming speech-to-text inference engines."""

    @abstractmethod
    async def transcribe_stream(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> AsyncIterator[STTResult]:
        """Streams partial and final transcription results from an audio buffer."""
        pass

    @abstractmethod
    async def transcribe_segment(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> STTResult:
        """Transcribes an audio segment and returns the final committed result."""
        pass


class MockSTTEngine(BaseSTTEngine):
    """Deterministic, zero-dependency mock STT engine for fast local development and CI."""

    def __init__(
        self,
        simulated_ttft_ms: int = 20,
        default_language: str = "eng",
        custom_text: str | None = None,
    ) -> None:
        self.simulated_ttft_ms = simulated_ttft_ms
        self.default_language = to_iso639_3(default_language)
        self.custom_text = custom_text
        self._default_phrases: dict[str, str] = {
            "eng": "Welcome everyone to our multilingual meeting, let's begin the review.",
            "spa": "Bienvenidos a todos a nuestra reunión multilingüe, comencemos la revisión.",
            "fra": "Bienvenue à tous à notre réunion multilingue, commençons la révision.",
            "deu": (
                "Willkommen alle zu unserem mehrsprachigen Treffen, "
                "beginnen wir die Überprüfung."
            ),
            "zho": "欢迎大家参加我们的多语言会议，让我们开始审查。",
            "jpn": "多言語ミーティングへようこそ、レビューを開始しましょう。",
        }

    def _get_target_text(self, language: str) -> str:
        if self.custom_text:
            return self.custom_text
        lang_3 = to_iso639_3(language)
        return self._default_phrases.get(lang_3, self._default_phrases["eng"])

    async def transcribe_stream(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> AsyncIterator[STTResult]:
        target_lang = to_iso639_3(language or self.default_language)
        full_text = self._get_target_text(target_lang)
        words = full_text.split()
        duration_ms = int((len(audio) / max(1, sample_rate)) * 1000)
        end_ms = start_offset_ms + max(duration_ms, 500)

        t0 = time.perf_counter()

        # Emit progressive partial hypotheses
        num_partials = min(3, len(words))
        step = max(1, len(words) // (num_partials + 1))

        for i in range(1, num_partials + 1):
            if self.simulated_ttft_ms > 0:
                await asyncio.sleep(self.simulated_ttft_ms / 1000.0)

            partial_words = words[: i * step]
            partial_text = " ".join(partial_words)
            latency = int((time.perf_counter() - t0) * 1000)
            partial_end = start_offset_ms + int(duration_ms * (i / (num_partials + 1)))

            yield STTResult(
                text=partial_text,
                is_final=False,
                language=target_lang,
                start_ms=start_offset_ms,
                end_ms=partial_end,
                confidence=0.85,
                latency_ms=latency,
            )

        # Final commitment
        if self.simulated_ttft_ms > 0:
            await asyncio.sleep(self.simulated_ttft_ms / 1000.0)

        total_latency = int((time.perf_counter() - t0) * 1000)
        yield STTResult(
            text=full_text,
            is_final=True,
            language=target_lang,
            start_ms=start_offset_ms,
            end_ms=end_ms,
            confidence=0.98,
            latency_ms=total_latency,
        )

    async def transcribe_segment(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> STTResult:
        target_lang = to_iso639_3(language or self.default_language)
        full_text = self._get_target_text(target_lang)
        duration_ms = int((len(audio) / max(1, sample_rate)) * 1000)
        end_ms = start_offset_ms + max(duration_ms, 500)

        t0 = time.perf_counter()
        if self.simulated_ttft_ms > 0:
            await asyncio.sleep(self.simulated_ttft_ms / 1000.0)
        total_latency = int((time.perf_counter() - t0) * 1000)

        return STTResult(
            text=full_text,
            is_final=True,
            language=target_lang,
            start_ms=start_offset_ms,
            end_ms=end_ms,
            confidence=0.98,
            latency_ms=total_latency,
        )


class FasterWhisperEngine(BaseSTTEngine):
    """Production streaming STT engine using faster-whisper CTranslate2."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "default",
        cpu_threads: int = 4,
        default_language: str = "eng",
        allow_fallback: bool = True,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.default_language = to_iso639_3(default_language)
        self.allow_fallback = allow_fallback
        self._model = None
        self._fallback_engine: MockSTTEngine | None = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Initializing FasterWhisper model: %s on %s (%s)",
                self.model_size,
                self.device,
                self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
        except (ImportError, Exception) as exc:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Failed to initialize FasterWhisperModel and fallback is disabled: {exc}"
                ) from exc

            logger.warning(
                "FasterWhisper not available (%s). Activating MockSTTEngine fallback.", exc
            )
            self._fallback_engine = MockSTTEngine(
                simulated_ttft_ms=20,
                default_language=self.default_language,
            )

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_engine is not None

    async def transcribe_stream(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> AsyncIterator[STTResult]:
        if self._fallback_engine is not None:
            async for res in self._fallback_engine.transcribe_stream(
                audio, sample_rate, language, start_offset_ms
            ):
                yield res
            return

        # Real Faster-Whisper transcription in threadpool to avoid blocking event loop
        target_lang_3 = to_iso639_3(language or self.default_language)
        whisper_lang = to_iso639_1(target_lang_3)
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()

        def _infer() -> list[tuple[str, float, float, float]]:
            segments, _info = self._model.transcribe(
                audio,
                language=whisper_lang,
                vad_filter=True,
                beam_size=1,
            )
            return [(s.text.strip(), s.start, s.end, s.avg_logprob) for s in segments]

        raw_segments = await loop.run_in_executor(None, _infer)
        latency = int((time.perf_counter() - t0) * 1000)

        accumulated_text = []
        for i, (text, start_sec, end_sec, logprob) in enumerate(raw_segments):
            if not text:
                continue
            accumulated_text.append(text)
            is_last = i == len(raw_segments) - 1
            confidence = min(1.0, max(0.0, float(np.exp(logprob))))

            yield STTResult(
                text=" ".join(accumulated_text),
                is_final=is_last,
                language=target_lang_3,
                start_ms=start_offset_ms + int(start_sec * 1000),
                end_ms=start_offset_ms + int(end_sec * 1000),
                confidence=confidence,
                latency_ms=latency,
            )

    async def transcribe_segment(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
        start_offset_ms: int = 0,
    ) -> STTResult:
        if self._fallback_engine is not None:
            return await self._fallback_engine.transcribe_segment(
                audio, sample_rate, language, start_offset_ms
            )

        target_lang_3 = to_iso639_3(language or self.default_language)
        whisper_lang = to_iso639_1(target_lang_3)
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()

        def _infer() -> list[tuple[str, float, float, float]]:
            segments, _info = self._model.transcribe(
                audio,
                language=whisper_lang,
                vad_filter=True,
                beam_size=1,
            )
            return [(s.text.strip(), s.start, s.end, s.avg_logprob) for s in segments]

        raw_segments = await loop.run_in_executor(None, _infer)
        latency = int((time.perf_counter() - t0) * 1000)

        all_text = " ".join([s[0] for s in raw_segments if s[0]])
        duration_ms = int((len(audio) / max(1, sample_rate)) * 1000)
        end_ms = start_offset_ms + duration_ms

        avg_conf = 0.95
        if raw_segments:
            confs = [min(1.0, max(0.0, float(np.exp(s[3])))) for s in raw_segments]
            avg_conf = sum(confs) / len(confs)

        return STTResult(
            text=all_text,
            is_final=True,
            language=target_lang_3,
            start_ms=start_offset_ms,
            end_ms=end_ms,
            confidence=avg_conf,
            latency_ms=latency,
        )


def create_stt_engine(
    engine_type: str | None = None,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    default_language: str | None = None,
    allow_fallback: bool = True,
) -> BaseSTTEngine:
    """Factory creating an STT engine instance configured from settings or arguments."""
    selected_type = (engine_type or settings.stt_engine_type).strip().lower()

    if selected_type in {"mock", "test"}:
        return MockSTTEngine(
            default_language=default_language or settings.stt_default_language,
        )

    if selected_type in {"faster-whisper", "whisper"}:
        return FasterWhisperEngine(
            model_size=model_size or settings.stt_model_size,
            device=device or settings.stt_device,
            compute_type=compute_type or settings.stt_compute_type,
            default_language=default_language or settings.stt_default_language,
            allow_fallback=allow_fallback,
        )

    logger.warning("Unknown STT engine type '%s', defaulting to MockSTTEngine", selected_type)
    return MockSTTEngine(default_language=default_language or settings.stt_default_language)
