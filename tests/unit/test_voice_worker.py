"""Unit tests for services/voice_worker (PR-01 Scaffolding / PR-11 Core)."""

import numpy as np
import pytest

from services.voice_worker import (
    BaseVoiceEngine,
    MockVoiceEngine,
    VoiceCloneResult,
    VoiceEmbedding,
    create_voice_engine,
)


@pytest.mark.unit
def test_voice_engine_factory() -> None:
    engine = create_voice_engine()
    assert isinstance(engine, BaseVoiceEngine)
    assert isinstance(engine, MockVoiceEngine)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mock_voice_embedding_extraction() -> None:
    engine = MockVoiceEngine(sample_rate=16000)
    audio = np.zeros(16000, dtype=np.float32)

    embed = await engine.extract_voice_embedding(
        audio_pcm=audio,
        sample_rate=16000,
        speaker_id="speaker_alice",
        tenant_id="tenant_acme",
        consent_verified=True,
    )

    assert isinstance(embed, VoiceEmbedding)
    assert embed.speaker_id == "speaker_alice"
    assert embed.tenant_id == "tenant_acme"
    assert embed.consent_verified is True
    assert embed.embedding.shape == (256,)
    # Verify unit normalized vector
    norm = np.linalg.norm(embed.embedding)
    assert np.isclose(norm, 1.0, atol=1e-5)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mock_voice_synthesis() -> None:
    engine = MockVoiceEngine(sample_rate=48000)
    embed = VoiceEmbedding(
        speaker_id="speaker_bob",
        tenant_id="tenant_acme",
        embedding=np.ones(256, dtype=np.float32) / 16.0,
        sample_rate=16000,
        consent_verified=True,
    )

    result = await engine.synthesize_with_voice(
        text="Hello world, testing voice cloning preservation",
        language="spa",
        voice_embedding=embed,
    )

    assert isinstance(result, VoiceCloneResult)
    assert result.watermarked is True
    assert result.speaker_id == "speaker_bob"
    assert result.sample_rate == 48000
    assert len(result.audio_pcm) > 0
