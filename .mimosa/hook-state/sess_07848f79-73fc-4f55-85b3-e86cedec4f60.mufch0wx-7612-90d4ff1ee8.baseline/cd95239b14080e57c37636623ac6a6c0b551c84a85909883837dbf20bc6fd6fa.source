"""Unit tests for Audio Framing, PCM conversion, and Resampling."""

import numpy as np
import pytest

from packages.audio.framing import (
    AudioChunker,
    AudioResampler,
    float32_to_pcm_s16le,
    pcm_s16le_to_float32,
)


@pytest.mark.unit
def test_pcm_conversions_fidelity() -> None:
    # Generate 1000 float32 samples in [-1.0, 1.0]
    t = np.linspace(0, 1, 1000, endpoint=False, dtype=np.float32)
    original_audio = np.sin(2 * np.pi * 440 * t)

    pcm_bytes = float32_to_pcm_s16le(original_audio)
    assert len(pcm_bytes) == 1000 * 2  # 16-bit = 2 bytes per sample

    recovered_audio = pcm_s16le_to_float32(pcm_bytes)
    assert len(recovered_audio) == 1000

    # Max quantization error for 16-bit PCM should be < 1/32768 ~= 0.000031
    diff = np.abs(original_audio - recovered_audio)
    assert np.max(diff) < 0.0001


@pytest.mark.unit
def test_pcm_edge_cases() -> None:
    # Empty conversions
    assert len(pcm_s16le_to_float32(b"")) == 0
    assert float32_to_pcm_s16le(np.empty(0, dtype=np.float32)) == b""

    # Extreme value clipping (prevent int16 overflow wraps)
    overshoot_audio = np.array([-2.5, 0.0, 3.8], dtype=np.float32)
    clipped_bytes = float32_to_pcm_s16le(overshoot_audio)
    clipped_recovered = pcm_s16le_to_float32(clipped_bytes)

    assert clipped_recovered[0] <= -0.999
    assert abs(clipped_recovered[1]) < 0.001
    assert clipped_recovered[2] >= 0.999


@pytest.mark.unit
def test_audio_chunker_20ms_framing_16khz() -> None:
    # At 16,000 Hz, 20ms frame = 320 samples
    chunker = AudioChunker(sample_rate=16000, frame_duration_ms=20)
    assert chunker.frame_size == 320

    # Push 800 samples (should yield exactly 2 frames of 320, leaving 160 remainder)
    samples = np.ones(800, dtype=np.float32) * 0.5
    frames = list(chunker.push(samples))

    assert len(frames) == 2

    # Frame 1: 0ms to 20ms
    f1, s1, e1 = frames[0]
    assert len(f1) == 320
    assert s1 == 0
    assert e1 == 20

    # Frame 2: 20ms to 40ms
    f2, s2, e2 = frames[1]
    assert len(f2) == 320
    assert s2 == 20
    assert e2 == 40

    # Push another 200 samples (160 + 200 = 360 -> yields 1 frame of 320, leaves 40 remainder)
    frames_2 = list(chunker.push(np.ones(200, dtype=np.float32)))
    assert len(frames_2) == 1
    f3, s3, e3 = frames_2[0]
    assert len(f3) == 320
    assert s3 == 40
    assert e3 == 60

    # Flush remainder (40 samples)
    flushed = chunker.flush()
    assert flushed is not None
    rem_frame, rem_s, rem_e = flushed
    assert len(rem_frame) == 40
    assert rem_s == 60
    assert rem_e == 62


@pytest.mark.unit
def test_audio_chunker_48khz_push_bytes() -> None:
    # At 48,000 Hz, 20ms frame = 960 samples
    chunker = AudioChunker(sample_rate=48000, frame_duration_ms=20)
    assert chunker.frame_size == 960

    # 1920 samples = 2 exact frames of 20ms each (40ms total)
    raw_samples = np.zeros(1920, dtype=np.float32)
    raw_bytes = float32_to_pcm_s16le(raw_samples)

    frames = list(chunker.push_bytes(raw_bytes))
    assert len(frames) == 2
    assert len(frames[0][0]) == 960
    assert len(frames[1][0]) == 960
    assert frames[0][1] == 0
    assert frames[0][2] == 20
    assert frames[1][1] == 20
    assert frames[1][2] == 40


@pytest.mark.unit
def test_audio_resampler_48khz_to_16khz() -> None:
    resampler = AudioResampler(source_rate=48000, target_rate=16000)

    # 1 second of 48000 samples containing 1000 Hz sine wave
    t_48k = np.linspace(0, 1.0, 48000, endpoint=False, dtype=np.float32)
    sine_48k = np.sin(2 * np.pi * 1000 * t_48k)

    resampled_16k = resampler.resample(sine_48k)

    # 48000 samples resampled by 16/48 = 1/3 should be exactly 16000 samples
    assert len(resampled_16k) == 16000

    # Verify frequency preservation (FFT peak at 1000 Hz in 16kHz signal)
    fft_vals = np.abs(np.fft.rfft(resampled_16k))
    freqs = np.fft.rfftfreq(len(resampled_16k), 1.0 / 16000)
    dominant_freq = freqs[np.argmax(fft_vals)]
    assert abs(dominant_freq - 1000.0) < 5.0
