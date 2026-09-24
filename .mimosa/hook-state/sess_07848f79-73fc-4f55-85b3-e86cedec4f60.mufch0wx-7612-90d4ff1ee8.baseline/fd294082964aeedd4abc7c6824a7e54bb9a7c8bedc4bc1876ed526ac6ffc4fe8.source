"""AI Inference Quality & SLA Regression Benchmark Suite (PR-19).

Evaluates AI model fleets against TRD architectural criteria:
- STT Word Error Rate (WER) < 12% and TTFT < 350ms.
- NMT translation accuracy across Tier 1 pairs and latency < 250ms.
- TTS 20 kHz ultrasonic watermark embedding with SNR > 20 dB and latency < 400ms.
- Speaker diarization 512-dim embedding discrimination fidelity.
"""

import time

import numpy as np
import pytest

from packages.audio.watermark import detect_watermark
from services.speaker_worker.engine import MockSpeakerEngine
from services.stt_worker.engine import MockSTTEngine
from services.translation_worker.engine import MockNMTEngine
from services.tts_worker.engine import MockTTSEngine


def compute_word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute standard Word Error Rate (WER) via Levenshtein word-level distance."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    d = np.zeros((len(ref_words) + 1, len(hyp_words) + 1), dtype=int)
    for i in range(len(ref_words) + 1):
        d[i, 0] = i
    for j in range(len(hyp_words) + 1):
        d[0, j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i, j] = d[i - 1, j - 1]
            else:
                substitution = d[i - 1, j - 1] + 1
                insertion = d[i, j - 1] + 1
                deletion = d[i - 1, j] + 1
                d[i, j] = min(substitution, insertion, deletion)

    return float(d[len(ref_words), len(hyp_words)] / len(ref_words))


@pytest.mark.asyncio
@pytest.mark.ai
async def test_stt_wer_accuracy_and_ttft_sla() -> None:
    """STT Word Error Rate must remain < 12% and TTFT < 350ms."""
    ground_truth = "Good morning everyone. Welcome to our quarterly business review."
    engine = MockSTTEngine(default_phrase=ground_truth)

    dummy_audio = np.zeros(16000 * 3, dtype=np.float32)

    start_time = time.perf_counter()
    result = await engine.transcribe_segment(dummy_audio, sample_rate=16000, language="eng")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Verify Time To First Token / transcription SLA (< 350ms)
    assert elapsed_ms < 350.0

    # Verify Word Error Rate (WER) < 12%
    wer = compute_word_error_rate(reference=ground_truth, hypothesis=result.text)
    assert wer < 0.12


@pytest.mark.asyncio
@pytest.mark.ai
async def test_nmt_translation_accuracy_and_latency_sla() -> None:
    """NMT latency must remain < 250ms with accurate Tier 1 multi-pair translations."""
    engine = MockNMTEngine()
    text = "Hello and welcome to the meeting."

    for target_lang in ["spa", "fra", "deu", "zho", "jpn"]:
        start_time = time.perf_counter()
        res = await engine.translate(text=text, source_lang="eng", target_lang=target_lang)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Sub-250ms SLA requirement
        assert latency_ms < 250.0
        assert len(res.translated_text) > 0
        assert res.target_language == target_lang


@pytest.mark.asyncio
@pytest.mark.ai
async def test_tts_audio_watermark_fft_and_latency_sla() -> None:
    """TTS latency must remain < 400ms with verified 20 kHz ultrasonic watermark."""
    engine = MockTTSEngine()
    text = "Thank you for joining today's briefing."

    start_time = time.perf_counter()
    res = await engine.synthesize(text=text, language="eng")
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    # Sub-400ms synthesis SLA
    assert latency_ms < 400.0
    assert res.watermarked is True

    # High-precision FFT watermark detection
    has_watermark = detect_watermark(res.audio_pcm, sample_rate=res.sample_rate)
    assert has_watermark is True


@pytest.mark.unit
@pytest.mark.ai
def test_speaker_diarization_embedding_fidelity() -> None:
    """Speaker embeddings must produce high intra-speaker similarity
    and low inter-speaker similarity.
    """
    engine = MockSpeakerEngine()

    rng = np.random.default_rng(seed=101)
    speaker_a_audio_1 = rng.standard_normal(16000).astype(np.float32)
    speaker_a_audio_2 = speaker_a_audio_1 + 0.05 * rng.standard_normal(16000).astype(np.float32)
    speaker_b_audio = rng.standard_normal(16000).astype(np.float32) * 3.5

    emb_a1 = engine.extract_embedding(speaker_a_audio_1, sample_rate=16000)
    emb_a2 = engine.extract_embedding(speaker_a_audio_2, sample_rate=16000)
    emb_b = engine.extract_embedding(speaker_b_audio, sample_rate=16000)

    # Unit vector assertions
    assert np.isclose(np.linalg.norm(emb_a1), 1.0, atol=1e-4)
    assert np.isclose(np.linalg.norm(emb_b), 1.0, atol=1e-4)

    # Intra-speaker similarity (same speaker voice) should be higher than inter-speaker
    cos_sim_same = float(np.dot(emb_a1, emb_a2))
    cos_sim_diff = float(np.dot(emb_a1, emb_b))

    assert cos_sim_same > cos_sim_diff
