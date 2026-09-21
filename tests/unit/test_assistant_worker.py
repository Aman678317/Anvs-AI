"""Unit tests for Meeting Assistant Worker Service adhering to Document 14."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.event_schema import (
    AssistantQueryEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.assistant_worker import (
    AssistantAnswer,
    AssistantConsumer,
    BaseAssistantEngine,
    IndexedSegment,
    MeetingSummary,
    MockAssistantEngine,
    OpenAIAssistantEngine,
    TranscriptVectorStore,
    create_assistant_engine,
)


@pytest.mark.unit
def test_mock_assistant_engine_embeds_1536_dim_vector() -> None:
    """Verifies MockAssistantEngine extracts 1536-dim L2 unit-normalized embeddings."""
    engine = MockAssistantEngine(embedding_dim=1536, simulated_latency_ms=0)
    text = "Quarterly financial budget allocation and cloud infrastructure costs."

    embedding = engine.embed_text(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (1536,)
    assert embedding.dtype == np.float32
    norm = float(np.linalg.norm(embedding))
    assert np.isclose(norm, 1.0, atol=1e-5)


@pytest.mark.unit
def test_vector_store_add_and_similarity_search() -> None:
    """Verifies TranscriptVectorStore indexes segments and performs cosine similarity search."""
    store = TranscriptVectorStore()
    engine = MockAssistantEngine(embedding_dim=1536, simulated_latency_ms=0)

    seg_budget = IndexedSegment(
        source_segment_id="src_seg_budget_01",
        text="We must increase the quarterly infrastructure budget.",
        speaker_name="Alice",
        embedding=engine.embed_text("We must increase the quarterly infrastructure budget."),
        meeting_id="meeting_store_test",
        tenant_id="tenant_alpha",
    )
    seg_design = IndexedSegment(
        source_segment_id="src_seg_design_02",
        text="The mobile user interface navigation needs larger buttons.",
        speaker_name="Bob",
        embedding=engine.embed_text(
            "The mobile user interface navigation needs larger buttons."
        ),
        meeting_id="meeting_store_test",
        tenant_id="tenant_alpha",
    )

    store.add_segment(seg_budget)
    store.add_segment(seg_design)

    query_emb = engine.embed_text("infrastructure costs and quarterly budget")
    results = store.similarity_search(query_emb, meeting_id="meeting_store_test", top_k=2)

    assert len(results) >= 1
    top_seg, score = results[0]
    assert top_seg.source_segment_id == "src_seg_budget_01"
    assert score > 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_assistant_engine_answers_query_with_citations() -> None:
    """Verifies Invariant #2: Assistant answers contain citations linking to source_segment_id."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    seg1 = IndexedSegment(
        source_segment_id="lineage_provenance_alpha_01",
        text="The database migration to PostgreSQL 16 is scheduled for Friday.",
        speaker_name="Sarah",
        meeting_id="meet_citations",
    )
    retrieved = [(seg1, 0.95)]

    res = await engine.answer_query(
        query="When is the database migration?",
        retrieved_segments=retrieved,
        query_id="query_cit_100",
    )

    assert isinstance(res, AssistantAnswer)
    assert res.query_id == "query_cit_100"
    # INVARIANT #2 ASSERTION:
    assert "lineage_provenance_alpha_01" in res.citations
    assert len(res.answer) > 0
    assert res.confidence >= 0.90


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_assistant_engine_extracts_action_items() -> None:
    """Verifies action items and commitments are identified from utterance text."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    seg_task = IndexedSegment(
        source_segment_id="src_task_01",
        text="John will deploy the new microservice to production tonight.",
        speaker_name="John",
        meeting_id="meet_action",
    )
    retrieved = [(seg_task, 0.92)]

    res = await engine.answer_query(
        query="What are the next deployment steps?",
        retrieved_segments=retrieved,
        query_id="query_act_200",
    )

    assert len(res.action_items) >= 1
    assert "deploy" in res.action_items[0].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_assistant_engine_generates_meeting_summary() -> None:
    """Verifies executive summary, key decisions, and topic extraction across segments."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    segments = [
        IndexedSegment(
            source_segment_id="seg_01",
            text="Welcome everyone. Today we must review Q3 cloud spending.",
            speaker_name="Host",
            meeting_id="meet_sum",
        ),
        IndexedSegment(
            source_segment_id="seg_02",
            text="The team agreed to reduce unused Kubernetes staging clusters.",
            speaker_name="Lead",
            meeting_id="meet_sum",
        ),
        IndexedSegment(
            source_segment_id="seg_03",
            text="DevOps will schedule the maintenance window for midnight.",
            speaker_name="DevOps",
            meeting_id="meet_sum",
        ),
    ]

    summary = await engine.generate_summary(segments, meeting_id="meet_sum")

    assert isinstance(summary, MeetingSummary)
    assert summary.meeting_id == "meet_sum"
    assert len(summary.summary) > 0
    assert len(summary.key_decisions) >= 1
    assert len(summary.action_items) >= 1
    assert len(summary.topics) >= 1


@pytest.mark.unit
def test_assistant_engine_factory_selection() -> None:
    """Verifies create_assistant_engine factory produces configured engine instances."""
    mock_eng = create_assistant_engine("mock")
    assert isinstance(mock_eng, MockAssistantEngine)
    assert isinstance(mock_eng, BaseAssistantEngine)

    openai_eng = create_assistant_engine("openai", allow_fallback=True)
    assert isinstance(openai_eng, OpenAIAssistantEngine)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_assistant_engine_graceful_fallback() -> None:
    """Verifies OpenAIAssistantEngine falls back gracefully to MockAssistantEngine."""
    engine = OpenAIAssistantEngine(
        model_name="non_existent/fake_llm_model",
        allow_fallback=True,
    )
    assert engine.is_using_fallback is True

    answer = await engine.answer_query(
        query="Explain the meeting status",
        retrieved_segments=[],
        query_id="q_fallback",
    )
    assert answer.query_id == "q_fallback"
    assert len(answer.answer) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assistant_consumer_indexes_transcript_event() -> None:
    """Verifies AssistantConsumer indexes final SourceSegmentEvents into the vector store."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.ack_event.return_value = 1

    vector_store = TranscriptVectorStore()
    consumer = AssistantConsumer(stream_bus=mock_bus, vector_store=vector_store)

    event = SourceSegmentEvent(
        event_id="src_evt_index_1",
        timestamp_ms=1710000000000,
        meeting_id="meet_rag_test",
        tenant_id="tenant_1",
        session_id="sess_1",
        participant_id="user_alice",
        source_segment_id="src_lineage_idx_01",
        language="eng",
        text="We decided to migrate authentication to Supabase JWT.",
        is_final=True,
        start_ms=0,
        end_ms=2500,
        confidence=0.98,
    )

    indexed = await consumer.process_transcript_message(
        stream_name="events:meeting:meet_rag_test:transcripts",
        message_id="90-0",
        raw_payload=event.model_dump(),
        meeting_id="meet_rag_test",
    )

    assert indexed is not None
    assert indexed.source_segment_id == "src_lineage_idx_01"
    assert vector_store.count("meet_rag_test") == 1
    assert consumer.metrics["transcripts_indexed"] == 1
    mock_bus.ack_event.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assistant_consumer_processes_query_and_emits_response() -> None:
    """Verifies AssistantConsumer processes AssistantQueryEvents and emits response."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-asst-101"
    mock_bus.ack_event.return_value = 1

    engine = MockAssistantEngine(simulated_latency_ms=0)
    vector_store = TranscriptVectorStore()
    consumer = AssistantConsumer(
        stream_bus=mock_bus,
        engine=engine,
        vector_store=vector_store,
    )

    # Pre-index an utterance
    canonical_id = "lineage_provenance_jwt_77"
    seg = IndexedSegment(
        source_segment_id=canonical_id,
        text="We decided to adopt Supabase JWT authentication across all services.",
        speaker_name="Lead Architect",
        embedding=engine.embed_text("Supabase JWT authentication"),
        meeting_id="meet_rag_query",
        tenant_id="tenant_sec",
    )
    vector_store.add_segment(seg)

    query_event = AssistantQueryEvent(
        event_id="evt_query_01",
        timestamp_ms=1710000005000,
        meeting_id="meet_rag_query",
        tenant_id="tenant_sec",
        query_id="query_uuid_8888",
        participant_id="user_bob",
        question="Which authentication standard did we decide to use?",
    )

    response = await consumer.process_query_message(
        stream_name="events:meeting:meet_rag_query:assistant",
        message_id="91-0",
        raw_payload=query_event.model_dump(),
        meeting_id="meet_rag_query",
    )

    assert response is not None
    assert response.query_id == "query_uuid_8888"
    assert canonical_id in response.citations
    assert consumer.metrics["queries_processed"] == 1
    assert consumer.metrics["responses_emitted"] == 1
    mock_bus.publish.assert_awaited_once()
    mock_bus.ack_event.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assistant_consumer_dlq_on_malformed_payload() -> None:
    """Verifies that poisoned query payloads route to DLQ without crashing the worker."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.send_to_dlq.return_value = "dlq-asst-err"

    consumer = AssistantConsumer(stream_bus=mock_bus, engine=MockAssistantEngine())

    corrupt_payload = {"malformed_unparseable_field": 99999}

    response = await consumer.process_query_message(
        stream_name="events:meeting:meet_err:assistant",
        message_id="92-0",
        raw_payload=corrupt_payload,
        meeting_id="meet_err",
    )

    assert response is None
    assert consumer.metrics["errors_count"] == 1
    mock_bus.send_to_dlq.assert_awaited_once()
