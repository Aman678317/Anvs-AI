"""Unit tests for Voice Cloning & Preservation Worker Service adhering to Document 14."""

import time
from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.watermark import detect_watermark
from packages.event_schema import RedisStreamBus
from services.voice_worker import (
    BaseVoiceEngine,
    ConsentViolationError,
    MockVoiceEngine,
    VoiceCloneResult,
    VoiceConsentRecord,
    VoiceEmbedding,
    VoiceWorkerConsumer,
    XTTSv2VoiceEngine,
    create_voice_engine,
)

# ---------------------------------------------------------------------------
# Engine Factory Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_voice_engine_factory_returns_mock() -> None:
    """Verifies factory creates MockVoiceEngine by default."""
    engine = create_voice_engine("mock")
    assert isinstance(engine, MockVoiceEngine)
    assert isinstance(engine, BaseVoiceEngine)


@pytest.mark.unit
def test_voice_engine_factory_xtts_fallback() -> None:
    """Verifies XTTSv2VoiceEngine activates fallback when model weights absent."""
    engine = XTTSv2VoiceEngine(model_name="non_existent/fake_xtts", allow_fallback=True)
    assert engine.is_using_fallback is True


# ---------------------------------------------------------------------------
# Consent Gate Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_engine_consent_gate_enforced() -> None:
    """Verifies ConsentViolationError is raised when consent_verified=False."""
    engine = MockVoiceEngine(sample_rate=16000, simulated_latency_ms=0)
    audio = np.zeros(16000, dtype=np.float32)

    with pytest.raises(ConsentViolationError):
        await engine.extract_voice_embedding(
            audio_pcm=audio,
            sample_rate=16000,
            speaker_id="speaker_alice",
            tenant_id="tenant_acme",
            consent_verified=False,  # Should raise
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_engine_consent_gate_passes() -> None:
    """Verifies voice embedding extraction proceeds when consent_verified=True."""
    engine = MockVoiceEngine(sample_rate=16000, simulated_latency_ms=0)
    audio = np.zeros(16000, dtype=np.float32)

    embed = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="speaker_alice",
        tenant_id="tenant_acme",
        consent_verified=True,
    )

    assert isinstance(embed, VoiceEmbedding)
    assert embed.consent_verified is True
    assert embed.speaker_id == "speaker_alice"
    assert embed.tenant_id == "tenant_acme"


# ---------------------------------------------------------------------------
# Voice Embedding Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_embedding_unit_normalized() -> None:
    """Verifies that extracted voice embeddings are unit-normalized (L2 norm ≈ 1.0)."""
    engine = MockVoiceEngine(sample_rate=16000, simulated_latency_ms=0)
    audio = np.random.default_rng(42).standard_normal(16000).astype(np.float32)

    embed = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="speaker_bob",
        tenant_id="tenant_xyz",
        consent_verified=True,
    )

    assert embed.embedding.shape == (256,)
    norm = float(np.linalg.norm(embed.embedding))
    assert np.isclose(norm, 1.0, atol=1e-5), f"Embedding norm {norm} is not ~1.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_embedding_deterministic_per_speaker() -> None:
    """Verifies the same speaker_id always produces an identical embedding vector."""
    engine = MockVoiceEngine(simulated_latency_ms=0)
    audio = np.zeros(8000, dtype=np.float32)

    embed_a = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="speaker_carol",
        tenant_id="t1",
        consent_verified=True,
    )
    embed_b = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="speaker_carol",
        tenant_id="t1",
        consent_verified=True,
    )

    assert np.allclose(embed_a.embedding, embed_b.embedding, atol=1e-7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_embedding_differs_across_speakers() -> None:
    """Verifies different speakers produce distinct embeddings (no collision)."""
    engine = MockVoiceEngine(simulated_latency_ms=0)
    audio = np.zeros(8000, dtype=np.float32)

    embed_alice = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="alice",
        tenant_id="t1",
        consent_verified=True,
    )
    embed_bob = await engine.extract_voice_embedding(
        audio_pcm=audio, sample_rate=16000, speaker_id="bob", tenant_id="t1", consent_verified=True
    )

    similarity = float(np.dot(embed_alice.embedding, embed_bob.embedding))
    assert similarity < 0.99, "Embeddings for distinct speakers must not be identical"


# ---------------------------------------------------------------------------
# Voice Cloning / Synthesis Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_synthesis_produces_audio() -> None:
    """Verifies synthesize_with_voice returns valid float32 audio."""
    engine = MockVoiceEngine(sample_rate=48000, simulated_latency_ms=0)

    embed = VoiceEmbedding(
        speaker_id="speaker_dan",
        tenant_id="tenant_acme",
        embedding=np.ones(256, dtype=np.float32) / 16.0,
        sample_rate=16000,
        consent_verified=True,
    )

    result = await engine.synthesize_with_voice(
        text="Buenos días a todos los participantes.",
        language="spa",
        voice_embedding=embed,
    )

    assert isinstance(result, VoiceCloneResult)
    assert isinstance(result.audio_pcm, np.ndarray)
    assert result.audio_pcm.dtype == np.float32
    assert len(result.audio_pcm) > 0
    assert result.duration_ms >= 400
    assert result.speaker_id == "speaker_dan"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_synthesis_embeds_watermark() -> None:
    """Verifies Invariant #3: synthesized voice-cloned audio contains 20 kHz watermark."""
    engine = MockVoiceEngine(sample_rate=48000, simulated_latency_ms=0, watermark_freq_hz=20000.0)

    embed = VoiceEmbedding(
        speaker_id="speaker_eve",
        tenant_id="tenant_beta",
        embedding=np.random.default_rng(99).standard_normal(256).astype(np.float32),
        sample_rate=16000,
        consent_verified=True,
    )

    result = await engine.synthesize_with_voice(
        text="Voice cloning watermark invariant test.",
        language="eng",
        voice_embedding=embed,
    )

    assert result.watermarked is True
    is_detected = detect_watermark(
        audio_pcm=result.audio_pcm,
        sample_rate=48000,
        watermark_freq=20000.0,
        threshold=0.001,
    )
    assert is_detected is True, "20 kHz ultrasonic pilot tone not detected in cloned voice output"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_voice_clone_result_base64_uri_roundtrip() -> None:
    """Verifies VoiceCloneResult.to_base64_uri() produces a valid decodable base64 URI."""
    engine = MockVoiceEngine(sample_rate=48000, simulated_latency_ms=0)

    embed = VoiceEmbedding(
        speaker_id="speaker_frank",
        tenant_id="tenant_corp",
        embedding=np.ones(256, dtype=np.float32) / 16.0,
        sample_rate=16000,
        consent_verified=True,
    )
    result = await engine.synthesize_with_voice("Test base64 encode.", "fra", embed)

    uri = result.to_base64_uri()
    assert uri.startswith("base64://")
    assert len(uri) > 9


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_voice_synthesis_latency_sla() -> None:
    """Verifies voice cloned synthesis completes within <400ms SLA."""
    engine = MockVoiceEngine(sample_rate=48000, simulated_latency_ms=10)
    embed = VoiceEmbedding(
        speaker_id="speaker_grace",
        tenant_id="t1",
        embedding=np.ones(256, dtype=np.float32) / 16.0,
        sample_rate=16000,
        consent_verified=True,
    )

    t0 = time.perf_counter()
    await engine.synthesize_with_voice("Quick latency SLA test.", "deu", embed)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 400.0, f"Voice synthesis latency {elapsed_ms:.1f}ms exceeded 400ms SLA"


# ---------------------------------------------------------------------------
# VoiceWorkerConsumer Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_enroll_speaker_consent_gate() -> None:
    """Verifies consumer refuses profile enrollment without consent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    audio = np.zeros(8000, dtype=np.float32)
    result = await consumer.enroll_speaker_from_audio(
        meeting_id="meet_1",
        speaker_id="spk_001",
        tenant_id="tenant_acme",
        audio_pcm=audio,
        sample_rate=16000,
        consent_verified=False,
    )

    assert result is None
    assert consumer.metrics["consent_violations"] == 1
    assert consumer.metrics["profiles_enrolled"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_enroll_speaker_with_consent() -> None:
    """Verifies consumer successfully enrolls a speaker profile with consent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    audio = np.zeros(16000, dtype=np.float32)
    embed = await consumer.enroll_speaker_from_audio(
        meeting_id="meet_enroll",
        speaker_id="spk_alice",
        tenant_id="tenant_acme",
        audio_pcm=audio,
        sample_rate=16000,
        consent_verified=True,
    )

    assert embed is not None
    assert embed.speaker_id == "spk_alice"
    assert consumer.metrics["profiles_enrolled"] == 1
    cached = consumer.get_enrolled_profile("meet_enroll", "spk_alice")
    assert cached is not None
    assert np.allclose(cached.embedding, embed.embedding)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_synthesize_voice_cloned_translation() -> None:
    """Verifies voice-cloned synthesis preserves Invariant #2 source_segment_id."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-vc-001"
    mock_bus.ack_event.return_value = 1

    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    # Pre-enroll speaker
    audio = np.zeros(16000, dtype=np.float32)
    await consumer.enroll_speaker_from_audio(
        meeting_id="meet_vc",
        speaker_id="spk_henry",
        tenant_id="tenant_corp",
        audio_pcm=audio,
        sample_rate=16000,
        consent_verified=True,
    )

    canonical_lineage_id = "src_vc_lineage_immutable_001"
    payload = {
        "event_id": "trans_vc_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_vc",
        "tenant_id": "tenant_corp",
        "source_segment_id": canonical_lineage_id,
        "source_language": "eng",
        "target_language": "jpn",
        "translated_text": "皆様、ようこそ。今日の会議を始めましょう。",
        "is_final": True,
        "latency_ms": 22,
        "speaker_tag": "spk_henry",
    }

    result = await consumer.synthesize_for_translation(
        stream_name="events:meeting:meet_vc:translations",
        message_id="50-0",
        raw_payload=payload,
        meeting_id="meet_vc",
    )

    assert result is not None
    # INVARIANT #2 CRITICAL ASSERTION
    assert result.source_segment_id == canonical_lineage_id
    assert result.target_language == "jpn"
    assert result.watermarked is True
    assert result.audio_uri.startswith("base64://")
    assert consumer.metrics["voice_cloned_segments"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_synthesize_fallback_without_profile() -> None:
    """Verifies consumer falls back to standard synthesis when no voice profile enrolled."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-fallback-002"
    mock_bus.ack_event.return_value = 1

    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    lineage_id = "src_fallback_no_profile_007"
    payload = {
        "event_id": "trans_fallback_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_fallback",
        "tenant_id": "tenant_acme",
        "source_segment_id": lineage_id,
        "source_language": "eng",
        "target_language": "fra",
        "translated_text": "Bonjour à tous les participants.",
        "is_final": True,
        "latency_ms": 18,
        # No speaker_tag → no profile found
    }

    result = await consumer.synthesize_for_translation(
        stream_name="events:meeting:meet_fallback:translations",
        message_id="51-0",
        raw_payload=payload,
        meeting_id="meet_fallback",
    )

    assert result is not None
    assert result.source_segment_id == lineage_id
    assert result.watermarked is True
    # No profile enrolled → voice_cloned_segments stays 0
    assert consumer.metrics["voice_cloned_segments"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_skips_non_final_translation() -> None:
    """Verifies non-final translations are acknowledged and skipped."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.ack_event.return_value = 1

    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    payload = {
        "event_id": "trans_partial_vc",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meet_skip_vc",
        "tenant_id": "tenant_1",
        "source_segment_id": "src_partial",
        "source_language": "eng",
        "target_language": "deu",
        "translated_text": "Guten",
        "is_final": False,  # Non-final, must be skipped
        "latency_ms": 10,
    }

    result = await consumer.synthesize_for_translation(
        stream_name="events:meeting:meet_skip_vc:translations",
        message_id="52-0",
        raw_payload=payload,
        meeting_id="meet_skip_vc",
    )

    assert result is None
    mock_bus.publish.assert_not_called()
    mock_bus.ack_event.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_dlq_on_malformed_payload() -> None:
    """Verifies malformed payloads route to DLQ without crashing."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-vc-msg"

    consumer = VoiceWorkerConsumer(stream_bus=mock_bus, engine=MockVoiceEngine())

    result = await consumer.synthesize_for_translation(
        stream_name="events:meeting:meet_err_vc:translations",
        message_id="53-0",
        raw_payload={"bad_field": "corrupt"},
        meeting_id="meet_err_vc",
    )

    assert result is None
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_meeting_profile_eviction() -> None:
    """Verifies all speaker profiles are cleared on meeting termination."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    consumer = VoiceWorkerConsumer(
        stream_bus=mock_bus, engine=MockVoiceEngine(simulated_latency_ms=0)
    )

    audio = np.zeros(8000, dtype=np.float32)
    for spk in ["spk_a", "spk_b", "spk_c"]:
        await consumer.enroll_speaker_from_audio(
            meeting_id="meet_evict",
            speaker_id=spk,
            tenant_id="t1",
            audio_pcm=audio,
            sample_rate=16000,
            consent_verified=True,
        )

    assert consumer.metrics["profiles_enrolled"] == 3

    evicted = consumer.clear_meeting_profiles("meet_evict")
    assert evicted == 3
    assert consumer.get_enrolled_profile("meet_evict", "spk_a") is None


@pytest.mark.unit
def test_voice_consent_record_structure() -> None:
    """Verifies VoiceConsentRecord captures all required consent fields."""
    record = VoiceConsentRecord(
        speaker_id="speaker_ivan",
        tenant_id="tenant_acme",
        consent_granted=True,
        consent_timestamp_ms=1710000000000,
        consent_version="v1",
    )

    assert record.speaker_id == "speaker_ivan"
    assert record.consent_granted is True
    assert record.consent_version == "v1"
