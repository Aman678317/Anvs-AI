"""Unit tests for the 20 kHz Acoustic Watermarking Utility (Invariant #3)."""

import numpy as np
import pytest
from packages.audio.watermark import embed_watermark, detect_watermark


@pytest.mark.unit
def test_watermark_embedding_and_detection() -> None:
    sample_rate = 48000
    duration_sec = 0.5
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False, dtype=np.float32)

    # Generate a pure 1 kHz human voice test tone
    clean_audio = 0.5 * np.sin(2 * np.pi * 1000.0 * t)

    # Initially, clean audio should NOT have the 20 kHz watermark
    assert not detect_watermark(clean_audio, sample_rate=sample_rate, watermark_freq=20000.0)

    # Embed 20 kHz watermark
    watermarked_audio = embed_watermark(
        clean_audio,
        sample_rate=sample_rate,
        watermark_freq=20000.0,
        amplitude=0.005,
    )

    # Detection should now confirm the presence of the 20 kHz tone
    assert detect_watermark(watermarked_audio, sample_rate=sample_rate, watermark_freq=20000.0)


@pytest.mark.unit
def test_low_sample_rate_handling() -> None:
    # 16 kHz sample rate cannot sustain 20 kHz watermark due to Nyquist theorem (16k / 2 = 8kHz)
    sample_rate = 16000
    audio = np.zeros(16000, dtype=np.float32)
    watermarked = embed_watermark(audio, sample_rate=sample_rate, watermark_freq=20000.0)
    assert np.array_equal(audio, watermarked)
    assert not detect_watermark(watermarked, sample_rate=sample_rate, watermark_freq=20000.0)
