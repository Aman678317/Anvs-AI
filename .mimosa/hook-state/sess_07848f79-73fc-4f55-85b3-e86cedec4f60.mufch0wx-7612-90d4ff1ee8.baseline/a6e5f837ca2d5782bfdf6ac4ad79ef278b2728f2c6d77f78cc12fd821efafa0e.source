"""Unit tests for Voice Activity Detection and Speech Segmentation."""

import numpy as np
import pytest

from packages.audio.vad import (
    EnergyVAD,
    SileroVADAdapter,
    SpeechSegmenter,
)


@pytest.mark.unit
def test_energy_vad_silence_vs_speech() -> None:
    vad = EnergyVAD(energy_threshold=0.015)

    # 1. Pure silence
    silence = np.zeros(320, dtype=np.float32)
    res_silence = vad.detect(silence, sample_rate=16000)
    assert res_silence.is_speech is False
    assert res_silence.confidence == 0.0

    # 2. Low background noise below threshold
    low_noise = np.random.normal(0, 0.002, 320).astype(np.float32)
    res_noise = vad.detect(low_noise, sample_rate=16000)
    assert res_noise.is_speech is False

    # 3. Active speech-range signal (500 Hz tone with amplitude 0.25)
    t = np.linspace(0, 0.02, 320, endpoint=False, dtype=np.float32)
    voice_frame = 0.25 * np.sin(2 * np.pi * 500 * t)
    res_voice = vad.detect(voice_frame, sample_rate=16000)
    assert res_voice.is_speech is True
    assert res_voice.confidence > 0.5


@pytest.mark.unit
def test_silero_vad_adapter_fallback() -> None:
    adapter = SileroVADAdapter()
    silence = np.zeros(320, dtype=np.float32)
    res = adapter.detect(silence, sample_rate=16000)
    assert res.is_speech is False


@pytest.mark.unit
def test_speech_segmenter_utterance_assembly() -> None:
    vad = EnergyVAD(energy_threshold=0.015)
    segmenter = SpeechSegmenter(
        sample_rate=16000,
        vad=vad,
        speech_pad_ms=60,
        min_speech_duration_ms=200,
        silence_timeout_ms=100,
    )

    t = np.linspace(0, 0.02, 320, endpoint=False, dtype=np.float32)
    voice_frame = 0.3 * np.sin(2 * np.pi * 400 * t)
    silence_frame = np.zeros(320, dtype=np.float32)

    segments = []
    current_ms = 0

    # Phase 1: 5 frames of silence (100ms)
    for _ in range(5):
        emitted = list(segmenter.process_frame(silence_frame, current_ms, current_ms + 20))
        segments.extend(emitted)
        current_ms += 20

    assert len(segments) == 0

    # Phase 2: 15 frames of voice (300ms)
    for _ in range(15):
        emitted = list(segmenter.process_frame(voice_frame, current_ms, current_ms + 20))
        segments.extend(emitted)
        current_ms += 20

    # Utterance is still active (not finished yet)
    assert len(segments) == 0

    # Phase 3: 6 frames of silence (120ms > silence_timeout_ms of 100ms)
    for _ in range(6):
        emitted = list(segmenter.process_frame(silence_frame, current_ms, current_ms + 20))
        segments.extend(emitted)
        current_ms += 20

    # Silence timeout should have triggered segment emission
    assert len(segments) == 1
    seg = segments[0]
    assert seg.sample_rate == 16000
    assert seg.is_final is True
    assert len(seg.audio) > 0


@pytest.mark.unit
def test_speech_segmenter_short_burst_rejection() -> None:
    segmenter = SpeechSegmenter(
        sample_rate=16000,
        min_speech_duration_ms=250,
        silence_timeout_ms=100,
    )

    t = np.linspace(0, 0.02, 320, endpoint=False, dtype=np.float32)
    click_frame = 0.5 * np.sin(2 * np.pi * 400 * t)
    silence_frame = np.zeros(320, dtype=np.float32)

    segments = []
    current_ms = 0

    # Only 2 frames of voice (40ms < 250ms threshold)
    for _ in range(2):
        segments.extend(list(segmenter.process_frame(click_frame, current_ms, current_ms + 20)))
        current_ms += 20

    # 10 frames of silence (200ms)
    for _ in range(10):
        segments.extend(list(segmenter.process_frame(silence_frame, current_ms, current_ms + 20)))
        current_ms += 20

    # Short acoustic pop must be rejected
    assert len(segments) == 0


@pytest.mark.unit
def test_speech_segmenter_max_duration_cutoff() -> None:
    segmenter = SpeechSegmenter(
        sample_rate=16000,
        max_speech_duration_ms=400,  # Cap at 400ms (20 frames)
        min_speech_duration_ms=100,
        silence_timeout_ms=500,
    )

    t = np.linspace(0, 0.02, 320, endpoint=False, dtype=np.float32)
    voice_frame = 0.3 * np.sin(2 * np.pi * 400 * t)

    segments = []
    current_ms = 0

    # Feed 25 consecutive voice frames without silence (500ms total)
    for _ in range(25):
        segments.extend(list(segmenter.process_frame(voice_frame, current_ms, current_ms + 20)))
        current_ms += 20

    # Must emit at least one segment because max_speech_duration_ms (400ms) was reached
    assert len(segments) >= 1
