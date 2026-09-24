"""Acoustic Watermarking Utility (Invariant #3: Synthetic Audio Loop Rejection).

Encodes and detects an imperceptible 20 kHz acoustic pilot tone in synthesized
speech frames to prevent synthetic audio from re-entering the STT pipeline.
"""

import numpy as np


def embed_watermark(
    audio_pcm: np.ndarray,
    sample_rate: int = 48000,
    watermark_freq: float = 20000.0,
    amplitude: float = 0.005,
) -> np.ndarray:
    """Embeds an imperceptible continuous sinusoidal pilot tone at watermark_freq.

    Args:
        audio_pcm: Audio samples normalized in range [-1.0, 1.0] (float32).
        sample_rate: Audio sample rate in Hz (must be > 2 * watermark_freq, i.e. >= 44100 Hz).
        watermark_freq: Frequency of the pilot tone in Hz (default: 20000 Hz).
        amplitude: Relative amplitude of the watermark tone (default: -46 dB / 0.005).

    Returns:
        Watermarked audio buffer.
    """
    if sample_rate < 2 * watermark_freq:
        # Sample rate too low for ultrasonic watermark without aliasing (e.g. 16kHz STT target)
        return audio_pcm

    n_samples = len(audio_pcm)
    t = np.arange(n_samples) / sample_rate
    watermark = amplitude * np.sin(2 * np.pi * watermark_freq * t).astype(audio_pcm.dtype)

    # Soft clip to prevent digital clipping
    watermarked = np.clip(audio_pcm + watermark, -1.0, 1.0)
    return watermarked


def detect_watermark(
    audio_pcm: np.ndarray,
    sample_rate: int = 48000,
    watermark_freq: float = 20000.0,
    threshold: float = 0.001,
) -> bool:
    """Detects whether incoming audio contains the 20 kHz synthetic pilot tone.

    Uses Goertzel or FFT magnitude evaluation at the target watermark bin.
    """
    if sample_rate < 2 * watermark_freq or len(audio_pcm) < 512:
        return False

    # Compute FFT magnitude around watermark frequency bin
    fft_vals = np.abs(np.fft.rfft(audio_pcm))
    freqs = np.fft.rfftfreq(len(audio_pcm), 1.0 / sample_rate)

    bin_idx = np.argmin(np.abs(freqs - watermark_freq))
    band_energy = float(fft_vals[bin_idx] / len(audio_pcm))

    return band_energy >= threshold
