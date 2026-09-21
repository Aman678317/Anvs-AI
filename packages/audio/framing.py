"""Audio framing, sample format conversion, and resampling utilities."""

import math
from collections.abc import Iterator

import numpy as np
from scipy import signal


def pcm_s16le_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """Converts 16-bit signed integer little-endian PCM bytes to float32 array [-1.0, 1.0].

    Args:
        pcm_bytes: Raw 16-bit PCM byte buffer.

    Returns:
        1D numpy array of float32 samples normalized between -1.0 and 1.0.
    """
    if not pcm_bytes:
        return np.empty(0, dtype=np.float32)

    # Convert bytes to int16 array
    samples_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    # Normalize to [-1.0, 1.0]
    return (samples_int16.astype(np.float32) / 32768.0).astype(np.float32)


def float32_to_pcm_s16le(audio: np.ndarray) -> bytes:
    """Converts normalized float32 audio array [-1.0, 1.0] to 16-bit signed PCM bytes.

    Args:
        audio: 1D numpy array of float32 samples.

    Returns:
        Raw 16-bit PCM bytes.
    """
    if len(audio) == 0:
        return b""

    # Clip values to [-1.0, 1.0] to prevent overflow wraps
    clipped = np.clip(audio, -1.0, 1.0)
    int16_samples = (clipped * 32767.0).astype(np.int16)
    return int16_samples.tobytes()


class AudioResampler:
    """High-quality, low-latency polyphase audio resampler."""

    def __init__(self, source_rate: int = 48000, target_rate: int = 16000) -> None:
        self.source_rate = source_rate
        self.target_rate = target_rate

        if source_rate <= 0 or target_rate <= 0:
            raise ValueError("Sample rates must be positive integers")

        gcd = math.gcd(source_rate, target_rate)
        self._up = target_rate // gcd
        self._down = source_rate // gcd

    def resample(self, audio: np.ndarray) -> np.ndarray:
        """Resamples input audio array to the target sample rate.

        Args:
            audio: 1D numpy array of float32 audio samples.

        Returns:
            Resampled 1D numpy array of float32 samples.
        """
        if len(audio) == 0 or self.source_rate == self.target_rate:
            return audio.astype(np.float32)

        # Polyphase FIR filtering for ultra-fast and artifact-free rate conversion
        resampled = signal.resample_poly(audio, self._up, self._down)
        return resampled.astype(np.float32)


class AudioChunker:
    """Accumulates arbitrary-sized audio input and emits fixed-duration PCM frames."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))

        if self.frame_size <= 0:
            raise ValueError("Frame size must be greater than zero")

        self._buffer = np.empty(0, dtype=np.float32)
        self._samples_processed = 0

    def push(self, samples: np.ndarray) -> Iterator[tuple[np.ndarray, int, int]]:
        """Pushes new float32 audio samples and yields complete frames.

        Args:
            samples: 1D numpy array of float32 samples.

        Yields:
            Tuples of (frame_samples, start_ms, end_ms).
        """
        if len(samples) == 0:
            return

        self._buffer = np.concatenate((self._buffer, samples.astype(np.float32)))

        while len(self._buffer) >= self.frame_size:
            frame = self._buffer[: self.frame_size]
            self._buffer = self._buffer[self.frame_size :]

            start_ms = int((self._samples_processed / self.sample_rate) * 1000)
            self._samples_processed += self.frame_size
            end_ms = int((self._samples_processed / self.sample_rate) * 1000)

            yield frame, start_ms, end_ms

    def push_bytes(self, pcm_bytes: bytes) -> Iterator[tuple[np.ndarray, int, int]]:
        """Pushes raw 16-bit PCM bytes and yields complete frames."""
        samples = pcm_s16le_to_float32(pcm_bytes)
        yield from self.push(samples)

    def flush(self) -> tuple[np.ndarray, int, int] | None:
        """Flushes remaining buffered samples (if any) as a final partial frame."""
        if len(self._buffer) == 0:
            return None

        frame = self._buffer
        start_ms = int((self._samples_processed / self.sample_rate) * 1000)
        self._samples_processed += len(frame)
        end_ms = int((self._samples_processed / self.sample_rate) * 1000)
        self._buffer = np.empty(0, dtype=np.float32)

        return frame, start_ms, end_ms

    def reset(self) -> None:
        """Resets the chunker buffer and timestamp tracking."""
        self._buffer = np.empty(0, dtype=np.float32)
        self._samples_processed = 0
