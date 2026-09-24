"""Unit tests for the Seven-Type Memory Architecture (DEC-05, PR-14 STEP-14-3).

Validates:
1. Working Memory: Sliding window bounding (drops oldest when window size exceeded).
2. Semantic Memory: Tenant-isolated domain concepts and technical terminology.
3. Episodic Memory: Consent-gated durable summaries with retention and expiration rules.
4. Procedural Memory: Operational response templates for meetings.
5. Retrieval Memory: Dense semantic vector search integration.
6. Parametric Memory: System grounding rules and non-hallucination directives.
7. Prospective Memory: Action item and commitment tracking.
8. End-to-end integration with AssistantConsumer.
"""

from unittest.mock import AsyncMock

import pytest

from packages.event_schema import (
    AssistantQueryEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.assistant_worker import (
    AssistantConsumer,
    EpisodicRecord,
    IndexedSegment,
    MemoryType,
    MockAssistantEngine,
    ProceduralTemplate,
    SevenTypeMemoryManager,
    TranscriptVectorStore,
)


@pytest.mark.unit
def test_memory_types_enum() -> None:
    """Verifies that all 7 cognitive memory types are defined in MemoryType enum."""
    assert len(MemoryType) == 7
    expected = {
        "WORKING",
        "SEMANTIC",
        "EPISODIC",
        "PROCEDURAL",
        "RETRIEVAL",
        "PARAMETRIC",
        "PROSPECTIVE",
    }
    assert {m.value for m in MemoryType} == expected


@pytest.mark.unit
def test_working_memory_sliding_window_bounding() -> None:
    """Verifies that Working Memory enforces the sliding window limit (DEC-05)."""
    mem = SevenTypeMemoryManager(max_working_window=3)
    meeting_id = "meet_working_test"

    for i in range(5):
        seg = IndexedSegment(
            source_segment_id=f"src_seg_{i}",
            text=f"Utterance number {i}",
            speaker_name=f"Speaker_{i}",
            meeting_id=meeting_id,
            tenant_id="tenant_alpha",
        )
        mem.add_working_segment(seg)

    window = mem.get_working_memory(meeting_id)
    # Must be bounded strictly to 3 segments
    assert len(window) == 3
    # Oldest segments (0, 1) dropped; only 2, 3, 4 retained
    assert [s.source_segment_id for s in window] == ["src_seg_2", "src_seg_3", "src_seg_4"]


@pytest.mark.unit
def test_semantic_concepts_tenant_isolation() -> None:
    """Verifies that Semantic Memory catalogs domain concepts under strict tenant isolation."""
    mem = SevenTypeMemoryManager()

    seg_a = IndexedSegment(
        source_segment_id="src_a",
        text="We are implementing Kubernetes and PostgreSQL RLS.",
        meeting_id="meet_a",
        tenant_id="tenant_a",
    )
    seg_b = IndexedSegment(
        source_segment_id="src_b",
        text="Our stack uses DynamoDB and Serverless Lambda.",
        meeting_id="meet_b",
        tenant_id="tenant_b",
    )

    mem.add_working_segment(seg_a)
    mem.add_working_segment(seg_b)

    concepts_a = mem.get_semantic_concepts("tenant_a")
    concepts_b = mem.get_semantic_concepts("tenant_b")

    assert "Kubernetes" in concepts_a or "PostgreSQL" in concepts_a
    assert "DynamoDB" not in concepts_a  # Tenant isolation!

    assert "DynamoDB" in concepts_b or "Serverless" in concepts_b
    assert "PostgreSQL" not in concepts_b


@pytest.mark.unit
def test_episodic_memory_consent_gating_and_expiration() -> None:
    """Verifies that Episodic Memory strictly enforces user consent and expiration (DEC-05)."""
    mem = SevenTypeMemoryManager()
    tenant_id = "tenant_consent_test"

    # 1. Storing without consent must be rejected
    no_consent_record = EpisodicRecord(
        meeting_id="meet_no_consent",
        tenant_id=tenant_id,
        summary="Confidential meeting recap without consent",
        consent_granted=False,
    )
    stored_1 = mem.store_episodic_summary(no_consent_record)
    assert stored_1 is False
    assert len(mem.get_episodic_history(tenant_id)) == 0

    # 2. Storing with consent must succeed
    consent_record = EpisodicRecord(
        meeting_id="meet_with_consent",
        tenant_id=tenant_id,
        summary="Approved executive recap",
        consent_granted=True,
        expires_at_ms=None,
    )
    stored_2 = mem.store_episodic_summary(consent_record)
    assert stored_2 is True

    history = mem.get_episodic_history(tenant_id)
    assert len(history) == 1
    assert history[0].meeting_id == "meet_with_consent"

    # 3. Expired record filtering
    expired_record = EpisodicRecord(
        meeting_id="meet_expired",
        tenant_id=tenant_id,
        summary="Old expired meeting recap",
        consent_granted=True,
        expires_at_ms=1000,  # Far in the past
    )
    mem.store_episodic_summary(expired_record)

    # Active records only
    active_history = mem.get_episodic_history(tenant_id, include_expired=False)
    assert len(active_history) == 1
    assert active_history[0].meeting_id == "meet_with_consent"

    # All records including expired
    all_history = mem.get_episodic_history(tenant_id, include_expired=True)
    assert len(all_history) == 2


@pytest.mark.unit
def test_procedural_memory_templates() -> None:
    """Verifies Procedural Memory provides structured operational templates."""
    mem = SevenTypeMemoryManager()

    recap_tmpl = mem.get_procedural_template("EXECUTIVE_RECAP")
    assert recap_tmpl is not None
    assert "Executive Summary" in recap_tmpl.template

    action_tmpl = mem.get_procedural_template("ACTION_ITEM_EXTRACTION")
    assert action_tmpl is not None
    assert "source_segment_id" in action_tmpl.template

    # Custom procedure registration
    custom = ProceduralTemplate(
        name="VOTING_CONSENSUS",
        description="Consensus vote tallying procedure",
        template="Record in-favor, against, and abstaining participants.",
    )
    mem.register_procedural_template(custom)
    retrieved = mem.get_procedural_template("VOTING_CONSENSUS")
    assert retrieved is not None
    assert retrieved.name == "VOTING_CONSENSUS"


@pytest.mark.unit
def test_parametric_memory_rules() -> None:
    """Verifies Parametric Memory enforces non-hallucination and Invariant rules."""
    mem = SevenTypeMemoryManager()

    rules = mem.get_parametric_rules()
    assert len(rules) >= 4
    prompt = mem.get_parametric_grounding_prompt()
    assert "CRITICAL SYSTEM DIRECTIVES" in prompt
    assert "source_segment_id" in prompt


@pytest.mark.unit
def test_prospective_memory_commitments() -> None:
    """Verifies Prospective Memory tracks action items, assignees, and source segment IDs."""
    mem = SevenTypeMemoryManager()
    meeting_id = "meet_prospective_test"

    item = mem.add_action_item(
        meeting_id=meeting_id,
        tenant_id="tenant_p",
        task="Deploy translation worker update to staging",
        source_segment_id="src_commit_42",
        assignee="Sarah",
    )

    assert item.task == "Deploy translation worker update to staging"
    assert item.assignee == "Sarah"
    assert item.source_segment_id == "src_commit_42"
    assert item.status == "PENDING"

    items = mem.get_prospective_items(meeting_id)
    assert len(items) == 1
    assert items[0].source_segment_id == "src_commit_42"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assistant_consumer_seven_type_memory_integration() -> None:
    """End-to-end test verifying AssistantConsumer seamlessly integrates all memory layers."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-mem-test"
    mock_bus.ack_event.return_value = 1

    engine = MockAssistantEngine(simulated_latency_ms=0)
    vector_store = TranscriptVectorStore()
    memory = SevenTypeMemoryManager(vector_store=vector_store, max_working_window=5)

    consumer = AssistantConsumer(
        stream_bus=mock_bus,
        engine=engine,
        vector_store=vector_store,
        memory=memory,
    )

    meeting_id = "meet_integrated_mem"
    tenant_id = "tenant_corp"

    # 1. Ingest transcript utterance: indexes in vector store AND working memory
    stt_event = SourceSegmentEvent(
        event_id="stt_mem_001",
        timestamp_ms=1710000000000,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        session_id="sess_mem",
        participant_id="user_architect",
        source_segment_id="src_lineage_mem_001",
        language="eng",
        text="Alice will complete the database migration on Friday.",
        is_final=True,
        start_ms=0,
        end_ms=2000,
        confidence=0.99,
        speaker_tag="Lead Architect",
    )

    await consumer.process_transcript_message(
        stream_name=f"events:meeting:{meeting_id}:transcripts",
        message_id="1-0",
        raw_payload=stt_event.model_dump(),
        meeting_id=meeting_id,
    )

    # Working memory assertion
    working = memory.get_working_memory(meeting_id)
    assert len(working) == 1
    assert working[0].source_segment_id == "src_lineage_mem_001"

    # Retrieval memory assertion
    assert vector_store.count(meeting_id) == 1

    # 2. Query processing: formulate grounded answer and record prospective action item
    query_event = AssistantQueryEvent(
        event_id="qry_mem_001",
        timestamp_ms=1710000005000,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        query_id="query_mem_123",
        participant_id="user_pm",
        question="What tasks are scheduled for Friday?",
    )

    response = await consumer.process_query_message(
        stream_name=f"events:meeting:{meeting_id}:assistant",
        message_id="2-0",
        raw_payload=query_event.model_dump(),
        meeting_id=meeting_id,
    )

    assert response is not None
    assert response.query_id == "query_mem_123"
    assert "src_lineage_mem_001" in response.citations

    # Prospective memory check: action items captured
    prospective = memory.get_prospective_items(meeting_id)
    assert len(prospective) >= 1
    assert "migration" in prospective[0].task.lower() or "complete" in prospective[0].task.lower()

    # 3. Finalize summary with consent: stored into episodic memory
    summary = await consumer.finalize_meeting_summary(meeting_id, consent_granted=True)
    assert summary is not None

    episodic = memory.get_episodic_history(tenant_id)
    assert len(episodic) == 1
    assert episodic[0].meeting_id == meeting_id

    # 4. Clear meeting: ephemeral working and prospective wiped, episodic preserved
    consumer.clear_meeting(meeting_id)
    assert len(memory.get_working_memory(meeting_id)) == 0
    assert len(memory.get_prospective_items(meeting_id)) == 0
    assert vector_store.count(meeting_id) == 0
    # Durable episodic memory survives meeting teardown!
    assert len(memory.get_episodic_history(tenant_id)) == 1
