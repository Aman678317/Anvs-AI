"""Voice Activity Detection (VAD) and speech utterance segmentation."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np


@dataclass
class VADResult:
    """Outcome of VAD evaluation on an audio frame."""

    is_speech: bool
    confidence: float
    energy: float


@dataclass
class SpeechSegment:
    """Voiced speech utterance aggregated across consecutive frames."""

    audio: np.ndarray
    sample_rate: int
    start_ms: int
    end_ms: int
    is_final: bool = True


class BaseVAD(ABC):
    """Abstract Voice Activity Detector."""

    @abstractmethod
    def detect(self, frame: np.ndarray, sample_rate: int = 16000) -> VADResult:
        """Evaluates whether an audio frame contains human speech.

        Args:
            frame: 1D numpy array of float32 samples.
            sample_rate: Sampling frequency in Hz.

        Returns:
            VADResult with speech decision and confidence.
        """
        pass


class EnergyVAD(BaseVAD):
    """Fast, zero-dependency Energy and Zero-Crossing Rate (ZCR) VAD."""

    def __init__(
        self,
        energy_threshold: float = 0.015,
        zcr_min: float = 0.02,
        zcr_max: float = 0.55,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.zcr_min = zcr_min
        self.zcr_max = zcr_max

    def detect(self, frame: np.ndarray, _sample_rate: int = 16000) -> VADResult:
        """Determines speech presence using RMS energy and Zero-Crossing Rate."""
        if len(frame) == 0:
            return VADResult(is_speech=False, confidence=0.0, energy=0.0)

        # Root Mean Square energy
        rms = float(np.sqrt(np.mean(frame**2)))

        # Zero-Crossing Rate
        zcr = float(np.mean(np.abs(np.diff(np.signbit(frame)))))

        # Human vocal energy and formant spectral distribution check
        has_energy = rms >= self.energy_threshold
        in_vocal_zcr = self.zcr_min <= zcr <= self.zcr_max

        is_speech = has_energy and in_vocal_zcr
        confidence = min(1.0, rms / max(self.energy_threshold * 2.0, 1e-6)) if is_speech else 0.0

        return VADResult(
            is_speech=is_speech,
            confidence=float(confidence),
            energy=rms,
        )


class SileroVADAdapter(BaseVAD):
    """Adapter for Silero VAD with fallback to EnergyVAD when ML dependencies are absent."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._fallback = EnergyVAD()
        self._model = None
        self._initialized = False

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            import torch

            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=True,
            )
            self._model = model
        except Exception:
            self._model = None

    def detect(self, frame: np.ndarray, sample_rate: int = 16000) -> VADResult:
        self._lazy_init()
        if self._model is None:
            return self._fallback.detect(frame, sample_rate)

        try:
            import torch

            tensor_frame = torch.from_numpy(frame)
            prob = float(self._model(tensor_frame, sample_rate).item())
            is_speech = prob >= self.threshold
            rms = float(np.sqrt(np.mean(frame**2)))
            return VADResult(is_speech=is_speech, confidence=prob, energy=rms)
        except Exception:
            return self._fallback.detect(frame, sample_rate)


class SpeechSegmenter:
    """Stateful aggregator collecting 20ms frames into bounded speech utterances."""

    def __init__(
        self,
        sample_rate: int = 16000,
        vad: BaseVAD | None = None,
        speech_pad_ms: int = 200,
        min_speech_duration_ms: int = 250,
        max_speech_duration_ms: int = 15000,
        silence_timeout_ms: int = 400,
    ) -> None:
        self.sample_rate = sample_rate
        self.vad = vad or EnergyVAD()
        self.speech_pad_ms = speech_pad_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.max_speech_duration_ms = max_speech_duration_ms
        self.silence_timeout_ms = silence_timeout_ms

        self._pad_samples = int(sample_rate * (speech_pad_ms / 1000.0))
        self._min_speech_samples = int(sample_rate * (min_speech_duration_ms / 1000.0))
        self._max_speech_samples = int(sample_rate * (max_speech_duration_ms / 1000.0))

        # Internal state
        self._in_speech = False
        self._current_segment: list[np.ndarray] = []
        self._pre_speech_ring: list[np.ndarray] = []
        self._silence_ms = 0
        self._speech_start_ms = 0
        self._current_end_ms = 0

    def process_frame(
        self,
        frame: np.ndarray,
        start_ms: int,
        end_ms: int,
    ) -> Iterator[SpeechSegment]:
        """Processes a single 20ms frame and emits completed SpeechSegment items.

        Args:
            frame: 1D float32 numpy array.
            start_ms: Start timestamp of frame in milliseconds.
            end_ms: End timestamp of frame in milliseconds.

        Yields:
            SpeechSegment when speech boundaries conclude or max length is reached.
        """
        frame_duration_ms = max(1, end_ms - start_ms)
        vad_res = self.vad.detect(frame, self.sample_rate)

        if not self._in_speech:
            if vad_res.is_speech:
                # Speech onset detected
                self._in_speech = True
                self._silence_ms = 0
                self._speech_start_ms = start_ms

                # Prepend audio padding from ring buffer
                if self._pre_speech_ring:
                    self._current_segment.extend(self._pre_speech_ring)
                    self._pre_speech_ring.clear()

                self._current_segment.append(frame)
                self._current_end_ms = end_ms
            else:
                # Keep audio in pre-speech ring buffer
                self._pre_speech_ring.append(frame)
                # Cap ring buffer to pad samples
                total_pad = sum(len(f) for f in self._pre_speech_ring)
                while total_pad > self._pad_samples and len(self._pre_speech_ring) > 1:
                    total_pad -= len(self._pre_speech_ring.pop(0))
        else:
            self._current_segment.append(frame)
            self._current_end_ms = end_ms

            if vad_res.is_speech:
                self._silence_ms = 0
            else:
                self._silence_ms += frame_duration_ms

            # Check if segment reached maximum duration or silence timeout
            total_samples = sum(len(f) for f in self._current_segment)
            if (
                total_samples >= self._max_speech_samples
                or self._silence_ms >= self.silence_timeout_ms
            ):
                seg = self._flush_segment()
                if seg:
                    yield seg

    def _flush_segment(self) -> SpeechSegment | None:
        if not self._current_segment:
            self._in_speech = False
            self._silence_ms = 0
            return None

        audio = np.concatenate(self._current_segment)
        start_ms = self._speech_start_ms
        end_ms = self._current_end_ms

        self._current_segment.clear()
        self._in_speech = False
        self._silence_ms = 0

        # Filter out transient bursts shorter than min_speech_samples
        if len(audio) < self._min_speech_samples:
            return None

        return SpeechSegment(
            audio=audio,
            sample_rate=self.sample_rate,
            start_ms=start_ms,
            end_ms=end_ms,
            is_final=True,
        )

    def flush(self) -> SpeechSegment | None:
        """Forces completion and emission of any currently active speech segment."""
        return self._flush_segment()

    def reset(self) -> None:
        """Resets all segmenter state."""
        self._in_speech = False
        self._current_segment.clear()
        self._pre_speech_ring.clear()
        self._silence_ms = 0
