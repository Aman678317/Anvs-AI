"""Unit tests for Speaker Diarization Worker Service adhering to Document 14."""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from packages.event_schema import RedisStreamBus, SourceSegmentEvent
from services.speaker_worker import (
    BaseSpeakerEngine,
    DiarizationResult,
    MockSpeakerEngine,
    PyAnnoteSpeakerEngine,
    SpeakerConsumer,
    VoiceProfileRegistry,
    cosine_similarity,
    create_speaker_engine,
    normalize_embedding,
)


@pytest.mark.unit
def test_mock_speaker_engine_extracts_512_dim_embedding() -> None:
    """Verifies MockSpeakerEngine extracts 512-dim unit-normalized d-vectors."""
    engine = MockSpeakerEngine(embedding_dim=512, simulated_latency_ms=0)
    audio = np.sin(np.linspace(0, 50, 16000, dtype=np.float32))

    embedding = engine.extract_embedding(audio, sample_rate=16000)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (512,)
    assert embedding.dtype == np.float32
    norm = float(np.linalg.norm(embedding))
    assert np.isclose(norm, 1.0, atol=1e-5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_speaker_engine_diarizes_audio_utterance() -> None:
    """Verifies diarization inference produces valid DiarizationResult and speaker cluster."""
    engine = MockSpeakerEngine(simulated_latency_ms=0)
    audio = 0.4 * np.sin(np.linspace(0, 100, 3200, dtype=np.float32))

    res = await engine.diarize(audio, sample_rate=16000)

    assert isinstance(res, DiarizationResult)
    assert res.speaker_id.startswith("SPEAKER_")
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.embedding) == 512
    assert res.turn_type in {"turn_start", "continued"}


@pytest.mark.unit
def test_voice_profile_registry_enrollment_and_matching() -> None:
    """Verifies that enrolled voice profiles match with high cosine similarity."""
    registry = VoiceProfileRegistry(default_similarity_threshold=0.75)
    rng = np.random.default_rng(42)
    sample_vec = rng.normal(size=512).astype(np.float32)
    enrolled_emb = normalize_embedding(sample_vec)

    registry.register_profile(
        speaker_id="speaker_alice",
        name="Alice Walker",
        embedding=enrolled_emb,
    )

    # Match identical vector
    spk_id, spk_name, confidence = registry.match_speaker(enrolled_emb)
    assert spk_id == "speaker_alice"
    assert spk_name == "Alice Walker"
    assert confidence >= 0.95

    # Match noisy variant (similarity > 0.75)
    noisy_emb = normalize_embedding(enrolled_emb + 0.01 * rng.normal(size=512).astype(np.float32))
    spk_id_noisy, spk_name_noisy, _ = registry.match_speaker(noisy_emb)
    assert spk_id_noisy == "speaker_alice"
    assert spk_name_noisy == "Alice Walker"


@pytest.mark.unit
def test_voice_profile_registry_unregistered_cluster_generation() -> None:
    """Verifies that unseen embeddings spawn sequential dynamic clusters (SPEAKER_00, 01)."""
    registry = VoiceProfileRegistry(default_similarity_threshold=0.85)

    vec_a = np.zeros(512, dtype=np.float32)
    vec_a[0] = 1.0
    vec_b = np.zeros(512, dtype=np.float32)
    vec_b[100] = 1.0

    cluster_a, name_a, _ = registry.match_speaker(vec_a)
    cluster_b, name_b, _ = registry.match_speaker(vec_b)

    assert cluster_a == "SPEAKER_00"
    assert name_a is None
    assert cluster_b == "SPEAKER_01"
    assert name_b is None

    # Recurring vec_a should match existing cluster SPEAKER_00
    recurring_a, _, conf_rec = registry.match_speaker(vec_a)
    assert recurring_a == "SPEAKER_00"
    assert conf_rec >= 0.90


@pytest.mark.unit
def test_voice_profile_registry_cosine_similarity_math() -> None:
    """Verifies mathematical correctness of cosine similarity calculation."""
    vec_x = np.zeros(512, dtype=np.float32)
    vec_x[0] = 1.0
    vec_y = np.zeros(512, dtype=np.float32)
    vec_y[1] = 1.0

    # Orthogonal vectors -> 0.0
    assert np.isclose(cosine_similarity(vec_x, vec_y), 0.0, atol=1e-5)
    # Collinear identical vectors -> 1.0
    assert np.isclose(cosine_similarity(vec_x, vec_x), 1.0, atol=1e-5)
    # Opposite vectors -> -1.0
    assert np.isclose(cosine_similarity(vec_x, -vec_x), -1.0, atol=1e-5)


@pytest.mark.unit
def test_speaker_engine_factory_selection() -> None:
    """Verifies create_speaker_engine factory produces configured engine instances."""
    mock_engine = create_speaker_engine("mock")
    assert isinstance(mock_engine, MockSpeakerEngine)
    assert isinstance(mock_engine, BaseSpeakerEngine)

    pyannote_engine = create_speaker_engine("pyannote", allow_fallback=True)
    assert isinstance(pyannote_engine, PyAnnoteSpeakerEngine)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pyannote_engine_graceful_fallback() -> None:
    """Verifies PyAnnoteSpeakerEngine falls back cleanly to MockSpeakerEngine when absent."""
    engine = PyAnnoteSpeakerEngine(
        model_name="non_existent/fake_pyannote_model",
        allow_fallback=True,
    )
    assert engine.is_using_fallback is True

    audio = np.zeros(1600, dtype=np.float32)
    res = await engine.diarize(audio, sample_rate=1600)
    assert len(res.embedding) == 512
    assert res.confidence > 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_speaker_consumer_preserves_source_segment_id_invariant() -> None:
    """Verifies Invariant #2: Source segment lineage preservation into DiarizationSegmentEvent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-diar-100"
    mock_bus.ack_event.return_value = 1

    engine = MockSpeakerEngine(simulated_latency_ms=0)
    consumer = SpeakerConsumer(stream_bus=mock_bus, engine=engine)

    canonical_lineage_id = "lineage_strict_transcript_uuid_7777"
    source_event = SourceSegmentEvent(
        event_id="src_001",
        timestamp_ms=1710000000000,
        meeting_id="meeting_diar_lineage",
        tenant_id="tenant_gamma",
        session_id="session_01",
        participant_id="part_sarah",
        source_segment_id=canonical_lineage_id,
        language="eng",
        text="Let us review the financial metrics.",
        is_final=True,
        start_ms=0,
        end_ms=2500,
        confidence=0.98,
        speaker_tag=None,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_diar_lineage:transcripts",
        message_id="70-0",
        raw_payload=source_event.model_dump(),
        meeting_id="meeting_diar_lineage",
    )

    assert len(emitted) == 1
    diar_event = emitted[0]

    # INVARIANT #2 CRITICAL ASSERTION:
    assert diar_event.source_segment_id == canonical_lineage_id
    assert diar_event.meeting_id == "meeting_diar_lineage"
    assert diar_event.tenant_id == "tenant_gamma"
    assert 0.0 <= diar_event.confidence <= 1.0

    mock_bus.publish.assert_awaited_once()
    mock_bus.ack_event.assert_awaited_once_with(
        "events:meeting:meeting_diar_lineage:transcripts",
        consumer.group_name,
        "70-0",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_speaker_consumer_detects_speaker_transition() -> None:
    """Verifies SpeakerConsumer tracks transitions between speakers across utterances."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-diar-ok"
    mock_bus.ack_event.return_value = 1

    engine = MockSpeakerEngine(simulated_latency_ms=0)
    consumer = SpeakerConsumer(stream_bus=mock_bus, engine=engine)

    # First utterance from Alice
    evt_a = SourceSegmentEvent(
        event_id="src_a",
        timestamp_ms=1710000000000,
        meeting_id="meet_turn",
        tenant_id="tenant_1",
        session_id="sess_1",
        participant_id="part_alice",
        source_segment_id="src_seg_a",
        language="eng",
        text="Hello team.",
        is_final=True,
        start_ms=0,
        end_ms=1000,
        confidence=0.95,
    )
    await consumer.process_message(
        stream_name="events:meeting:meet_turn:transcripts",
        message_id="71-0",
        raw_payload=evt_a.model_dump(),
        meeting_id="meet_turn",
    )

    # Second utterance from Bob
    evt_b = SourceSegmentEvent(
        event_id="src_b",
        timestamp_ms=1710000002000,
        meeting_id="meet_turn",
        tenant_id="tenant_1",
        session_id="sess_1",
        participant_id="part_bob",
        source_segment_id="src_seg_b",
        language="eng",
        text="Hi Alice, good to see you.",
        is_final=True,
        start_ms=2000,
        end_ms=4000,
        confidence=0.96,
    )
    await consumer.process_message(
        stream_name="events:meeting:meet_turn:transcripts",
        message_id="72-0",
        raw_payload=evt_b.model_dump(),
        meeting_id="meet_turn",
    )

    assert consumer.metrics["diarizations_emitted"] == 2
    assert consumer.metrics["speaker_transitions_detected"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_speaker_consumer_dlq_on_malformed_payload() -> None:
    """Verifies that malformed transcript payloads route to DLQ without crashing."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-msg-diar"

    consumer = SpeakerConsumer(stream_bus=mock_bus, engine=MockSpeakerEngine())

    corrupted_payload = {"unexpected_broken_field": 12345}

    emitted = await consumer.process_message(
        stream_name="events:meeting:meet_corrupt:transcripts",
        message_id="73-0",
        raw_payload=corrupted_payload,
        meeting_id="meet_corrupt",
    )

    assert emitted == []
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()


@pytest.mark.unit
def test_voice_profile_registry_load_from_db_models() -> None:
    """Verifies that database VoiceProfile records can be enrolled into the in-memory registry."""
    registry = VoiceProfileRegistry(default_similarity_threshold=0.8)

    db_profile = MagicMock()
    db_profile.id = "vp-12345"
    db_profile.user_id = "user-alice-db"
    db_profile.speaker_name = "Alice DB"
    db_profile.embedding = [0.1] * 256

    count = registry.load_from_db_profiles([db_profile])
    assert count == 1
    profile = registry.get_profile("user-alice-db")
    assert profile is not None
    assert profile.name == "Alice DB"
    assert profile.metadata["source"] == "db_voice_profile"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_speaker_consumer_poll_and_process() -> None:
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-diar-poll"
    mock_bus.ack_event.return_value = 1

    engine = MockSpeakerEngine(simulated_latency_ms=0)
    consumer = SpeakerConsumer(stream_bus=mock_bus, engine=engine)

    payload = {
        "event_id": "src_poll_1",
        "timestamp_ms": 1000,
        "meeting_id": "meet_poll",
        "tenant_id": "ten_poll",
        "session_id": "sess_poll",
        "participant_id": "part_poll",
        "source_segment_id": "src_poll_100",
        "language": "eng",
        "text": "Testing speaker consumer polling.",
        "is_final": True,
        "start_ms": 0,
        "end_ms": 1000,
        "confidence": 0.95,
    }

    mock_bus.consume_events.return_value = [("msg-diar-100", payload)]

    emitted = await consumer.poll_and_process("meet_poll")
    assert len(emitted) == 1
    assert emitted[0].source_segment_id == "src_poll_100"
    mock_bus.ack_event.assert_awaited_once()


@pytest.mark.unit
def test_pyannote_speaker_engine_fallback_property() -> None:
    engine = PyAnnoteSpeakerEngine(allow_fallback=True)
    assert engine.is_using_fallback is True or engine._pipeline is not None
