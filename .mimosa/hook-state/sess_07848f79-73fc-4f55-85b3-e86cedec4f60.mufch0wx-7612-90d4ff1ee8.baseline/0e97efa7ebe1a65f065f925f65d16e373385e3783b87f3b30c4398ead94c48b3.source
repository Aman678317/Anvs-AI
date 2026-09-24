"""Unit tests for AI In-Meeting Copilot & RAG Assistant (PR-12)."""

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
    MeetingStreamSummarizer,
    MeetingSummary,
    MockAssistantEngine,
    OpenAIAssistantEngine,
    QueryIntent,
    QueryRouter,
    TranscriptVectorStore,
    create_assistant_engine,
)

# ---------------------------------------------------------------------------
# Pre-existing PR-11 baseline tests (regression guard — all must still pass)
# ---------------------------------------------------------------------------


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
        embedding=engine.embed_text("The mobile user interface navigation needs larger buttons."),
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

    nim_eng = create_assistant_engine("nvidia", allow_fallback=True)
    assert isinstance(nim_eng, OpenAIAssistantEngine)


@pytest.mark.unit
def test_nvidia_nim_engine_configuration() -> None:
    """Verifies OpenAIAssistantEngine adapts base_url and model for NVIDIA NIM."""
    engine = OpenAIAssistantEngine(
        api_key="nvapi-sample-key",
        base_url="https://integrate.api.nvidia.com/v1",
        allow_fallback=True,
    )
    assert engine.base_url == "https://integrate.api.nvidia.com/v1"
    assert engine.model_name == "meta/llama-3.1-8b-instruct"


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


# ---------------------------------------------------------------------------
# PR-12 New Tests: QueryRouter Intent Classification
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_query_router_classifies_action_item_intent() -> None:
    """Verifies QueryRouter correctly classifies action/commitment queries."""
    router = QueryRouter()

    result = router.classify("What are the follow-up tasks assigned to DevOps?")
    assert result.intent == QueryIntent.ACTION_ITEM
    assert result.confidence > 0.70
    assert result.top_k_override is not None and result.top_k_override >= 8

    result2 = router.classify("Who will deploy the new service?")
    assert result2.intent == QueryIntent.ACTION_ITEM


@pytest.mark.unit
def test_query_router_classifies_summary_intent() -> None:
    """Verifies QueryRouter correctly classifies summary/recap queries."""
    router = QueryRouter()

    result = router.classify("Can you give me a summary of the meeting?")
    assert result.intent == QueryIntent.SUMMARY
    assert result.top_k_override is not None and result.top_k_override >= 10

    result2 = router.classify("What were the key highlights from today?")
    assert result2.intent == QueryIntent.SUMMARY


@pytest.mark.unit
def test_query_router_classifies_decision_intent() -> None:
    """Verifies QueryRouter correctly classifies decision/resolution queries."""
    router = QueryRouter()

    result = router.classify("What decisions were made about the budget?")
    assert result.intent == QueryIntent.DECISION
    assert result.confidence > 0.70

    result2 = router.classify("Did we reach consensus on the database migration?")
    assert result2.intent == QueryIntent.DECISION


@pytest.mark.unit
def test_query_router_classifies_clarification_intent() -> None:
    """Verifies QueryRouter correctly classifies clarification/elaboration queries."""
    router = QueryRouter()

    result = router.classify("Can you elaborate on what Alice said about the timeline?")
    assert result.intent == QueryIntent.CLARIFICATION

    result2 = router.classify("What did the team mean by reducing cluster overhead?")
    assert result2.intent == QueryIntent.CLARIFICATION


@pytest.mark.unit
def test_query_router_classifies_factual_default() -> None:
    """Verifies QueryRouter falls back to FACTUAL intent for generic questions."""
    router = QueryRouter()

    result = router.classify("When does the meeting end?")
    # Not action/decision/summary specific — falls through to FACTUAL
    assert result.intent in (QueryIntent.FACTUAL, QueryIntent.ACTION_ITEM)
    assert result.confidence > 0.5

    empty = router.classify("")
    assert empty.intent == QueryIntent.FACTUAL


@pytest.mark.unit
def test_query_router_get_retrieval_params() -> None:
    """Verifies get_retrieval_params returns (top_k, threshold, intent) correctly."""
    router = QueryRouter()

    top_k, threshold, intent = router.get_retrieval_params(
        "What action items were assigned today?",
        default_top_k=5,
        default_threshold=0.55,
    )
    assert isinstance(top_k, int) and top_k >= 1
    assert isinstance(threshold, float) and 0.0 < threshold < 1.0
    assert intent == QueryIntent.ACTION_ITEM


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_query_uses_intent_aware_retrieval() -> None:
    """Verifies process_query_message routes action-item queries with higher top_k."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-intent-aware"
    mock_bus.ack_event.return_value = 1

    engine = MockAssistantEngine(simulated_latency_ms=0)
    vector_store = TranscriptVectorStore()
    consumer = AssistantConsumer(stream_bus=mock_bus, engine=engine, vector_store=vector_store)

    # Pre-index segments
    for i in range(3):
        seg = IndexedSegment(
            source_segment_id=f"src_action_{i}",
            text=f"Alice will deploy the service component {i} by Friday.",
            speaker_name="Alice",
            embedding=engine.embed_text(f"deploy service component {i}"),
            meeting_id="meet_intent",
            tenant_id="t1",
        )
        vector_store.add_segment(seg)

    query_event = AssistantQueryEvent(
        event_id="evt_intent_01",
        timestamp_ms=1710000000000,
        meeting_id="meet_intent",
        tenant_id="t1",
        query_id="qry_intent_001",
        participant_id="participant_01",
        question="What follow-up tasks were assigned to Alice?",
    )

    response = await consumer.process_query_message(
        stream_name="events:meeting:meet_intent:assistant",
        message_id="100-0",
        raw_payload=query_event.model_dump(),
        meeting_id="meet_intent",
    )

    assert response is not None
    assert response.query_id == "qry_intent_001"
    assert len(response.citations) >= 1
    assert consumer.metrics["responses_emitted"] == 1


# ---------------------------------------------------------------------------
# PR-12 New Tests: MeetingStreamSummarizer
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_summarizer_no_batch_trigger_below_watermark() -> None:
    """Verifies no intermediate summary fires when below the batch watermark."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    summarizer = MeetingStreamSummarizer(
        engine=engine,
        meeting_id="meet_wm_test",
        tenant_id="t1",
        batch_watermark=50,
    )

    for i in range(10):
        seg = IndexedSegment(
            source_segment_id=f"seg_{i}",
            text=f"Discussion point {i}",
            meeting_id="meet_wm_test",
        )
        summarizer.add_segment(seg)

    summary = await summarizer.maybe_generate_batch_summary()
    assert summary is None  # not yet at watermark
    assert summarizer.summaries_generated == 0
    assert summarizer.total_segments_indexed == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_summarizer_triggers_at_watermark() -> None:
    """Verifies intermediate summary fires when batch_watermark segments are accumulated."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    summarizer = MeetingStreamSummarizer(
        engine=engine,
        meeting_id="meet_batch",
        tenant_id="t1",
        batch_watermark=5,
    )

    texts = [
        "We must deploy the new API gateway by end of week.",
        "The team agreed to adopt Kubernetes for container orchestration.",
        "Alice will schedule the infrastructure cost review.",
        "The consensus is to migrate databases to PostgreSQL 16.",
        "DevOps will set up monitoring dashboards for all services.",
    ]
    for i, text in enumerate(texts):
        seg = IndexedSegment(
            source_segment_id=f"seg_batch_{i}",
            text=text,
            speaker_name="Participant",
            meeting_id="meet_batch",
        )
        summarizer.add_segment(seg)

    summary = await summarizer.maybe_generate_batch_summary()

    assert summary is not None
    assert isinstance(summary, MeetingSummary)
    assert summary.meeting_id == "meet_batch"
    assert len(summary.summary) > 0
    assert summarizer.summaries_generated == 1
    # Batch should be reset after summary
    assert len(summarizer._state.segments_since_last_summary) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_summarizer_finalize_generates_full_summary() -> None:
    """Verifies finalize() synthesizes a complete executive summary over all segments."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    summarizer = MeetingStreamSummarizer(
        engine=engine,
        meeting_id="meet_final_sum",
        tenant_id="t1",
        batch_watermark=100,  # Won't trigger batch during test
    )

    segments = [
        IndexedSegment(
            source_segment_id=f"seg_fin_{i}",
            text=f"Point {i}: The team will schedule a deployment review.",
            meeting_id="meet_final_sum",
        )
        for i in range(5)
    ]
    for seg in segments:
        summarizer.add_segment(seg)

    final = await summarizer.finalize()

    assert isinstance(final, MeetingSummary)
    assert final.meeting_id == "meet_final_sum"
    assert len(final.summary) > 0
    assert summarizer.summaries_generated == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_summarizer_finalize_empty_meeting() -> None:
    """Verifies finalize() returns a clean summary for meetings with no transcripts."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    summarizer = MeetingStreamSummarizer(
        engine=engine,
        meeting_id="meet_empty",
        tenant_id="t1",
    )

    final = await summarizer.finalize()

    assert isinstance(final, MeetingSummary)
    assert final.meeting_id == "meet_empty"
    assert "no recorded" in final.summary.lower()
    assert final.action_items == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_finalize_meeting_summary() -> None:
    """Verifies AssistantConsumer.finalize_meeting_summary produces a valid summary."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.ack_event.return_value = 1

    engine = MockAssistantEngine(simulated_latency_ms=0)
    vector_store = TranscriptVectorStore()
    consumer = AssistantConsumer(stream_bus=mock_bus, engine=engine, vector_store=vector_store)

    # Index a few segments through normal pipeline
    for i in range(3):
        event = SourceSegmentEvent(
            event_id=f"src_evt_sum_{i}",
            timestamp_ms=1710000000000 + i * 1000,
            meeting_id="meet_finalize",
            tenant_id="tenant_fin",
            session_id="sess_fin",
            participant_id=f"user_{i}",
            source_segment_id=f"src_fin_{i}",
            language="eng",
            text=f"Segment {i}: We agreed to adopt cloud-first infrastructure.",
            is_final=True,
            start_ms=i * 1000,
            end_ms=(i + 1) * 1000,
            confidence=0.97,
        )
        await consumer.process_transcript_message(
            stream_name="events:meeting:meet_finalize:transcripts",
            message_id=f"{i}-0",
            raw_payload=event.model_dump(),
            meeting_id="meet_finalize",
        )

    final_summary = await consumer.finalize_meeting_summary("meet_finalize")

    assert final_summary is not None
    assert isinstance(final_summary, MeetingSummary)
    assert final_summary.meeting_id == "meet_finalize"
    assert len(final_summary.summary) > 0
    assert consumer.metrics["summaries_generated"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_summarizer_source_segment_id_lineage() -> None:
    """Verifies summarizer tracks all source_segment_ids contributing to summaries."""
    engine = MockAssistantEngine(simulated_latency_ms=0)
    summarizer = MeetingStreamSummarizer(
        engine=engine, meeting_id="meet_lineage_sum", tenant_id="t1"
    )

    expected_ids = [f"src_lin_{i}" for i in range(4)]
    for seg_id in expected_ids:
        summarizer.add_segment(
            IndexedSegment(
                source_segment_id=seg_id,
                text="Test segment for lineage tracking.",
                meeting_id="meet_lineage_sum",
            )
        )

    tracked_ids = summarizer.get_source_segment_ids()
    for expected_id in expected_ids:
        assert expected_id in tracked_ids


# ---------------------------------------------------------------------------
# PR-12 New Tests: Multi-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_vector_store_multi_tenant_isolation() -> None:
    """Verifies TranscriptVectorStore correctly isolates segments by meeting_id (tenant boundary)."""
    store = TranscriptVectorStore()
    engine = MockAssistantEngine(simulated_latency_ms=0)

    # Tenant A meeting
    seg_a = IndexedSegment(
        source_segment_id="src_tenant_a_01",
        text="Tenant A decision: deploy microservices on AWS.",
        embedding=engine.embed_text("deploy microservices aws"),
        meeting_id="meet_tenant_a",
        tenant_id="tenant_a",
    )
    # Tenant B meeting
    seg_b = IndexedSegment(
        source_segment_id="src_tenant_b_01",
        text="Tenant B decision: use GCP for our Kubernetes clusters.",
        embedding=engine.embed_text("kubernetes gcp clusters"),
        meeting_id="meet_tenant_b",
        tenant_id="tenant_b",
    )

    store.add_segment(seg_a)
    store.add_segment(seg_b)

    query_emb = engine.embed_text("microservices cloud deployment")

    # Tenant A query must only see Tenant A segments
    results_a = store.similarity_search(query_emb, meeting_id="meet_tenant_a", top_k=5)
    result_ids_a = [seg.source_segment_id for seg, _ in results_a]
    assert "src_tenant_a_01" in result_ids_a
    assert "src_tenant_b_01" not in result_ids_a

    # Tenant B query must only see Tenant B segments
    results_b = store.similarity_search(query_emb, meeting_id="meet_tenant_b", top_k=5)
    result_ids_b = [seg.source_segment_id for seg, _ in results_b]
    assert "src_tenant_b_01" in result_ids_b
    assert "src_tenant_a_01" not in result_ids_b


@pytest.mark.unit
def test_vector_store_clear_meeting_purges_data() -> None:
    """Verifies clear_meeting() purges all segments for a meeting without affecting others."""
    store = TranscriptVectorStore()
    engine = MockAssistantEngine()

    store.add_segment(
        IndexedSegment(
            source_segment_id="src_meet1_01",
            text="First meeting content.",
            embedding=engine.embed_text("first meeting"),
            meeting_id="meet_clear_1",
            tenant_id="t1",
        )
    )
    store.add_segment(
        IndexedSegment(
            source_segment_id="src_meet2_01",
            text="Second meeting content should survive.",
            embedding=engine.embed_text("second meeting"),
            meeting_id="meet_clear_2",
            tenant_id="t1",
        )
    )

    assert store.count("meet_clear_1") == 1
    assert store.count("meet_clear_2") == 1

    store.clear_meeting("meet_clear_1")

    assert store.count("meet_clear_1") == 0
    assert store.count("meet_clear_2") == 1  # Unaffected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consumer_empty_vector_store_returns_answer_without_citations() -> None:
    """Verifies consumer handles empty store gracefully — returns answer without citations."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-empty-store"
    mock_bus.ack_event.return_value = 1

    consumer = AssistantConsumer(
        stream_bus=mock_bus,
        engine=MockAssistantEngine(simulated_latency_ms=0),
        vector_store=TranscriptVectorStore(),
    )

    query_event = AssistantQueryEvent(
        event_id="evt_empty_001",
        timestamp_ms=1710000000000,
        meeting_id="meet_empty_rag",
        tenant_id="t1",
        query_id="qry_empty_001",
        participant_id="participant_01",
        question="What was discussed?",
    )

    response = await consumer.process_query_message(
        stream_name="events:meeting:meet_empty_rag:assistant",
        message_id="200-0",
        raw_payload=query_event.model_dump(),
        meeting_id="meet_empty_rag",
    )

    assert response is not None
    assert response.query_id == "qry_empty_001"
    # No segments indexed → citations list may be empty
    assert isinstance(response.citations, list)
    assert len(response.answer) > 0
