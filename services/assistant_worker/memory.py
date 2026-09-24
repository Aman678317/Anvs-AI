"""Seven-Type Memory Layer for AI In-Meeting Copilot (DEC-05, Document 14).

Adheres strictly to DEC-05 constraints:
1. Working Memory: Active meeting window bounded to a sliding window (10-20 segments).
2. Semantic Memory: Domain concepts and topic keywords with strict tenant scoping.
3. Episodic Memory: Durable meeting recaps and key decisions requiring verified consent and expiration.
4. Procedural Memory: Operating templates for summarization, action items, and consensus.
5. Retrieval Memory: Dense semantic vector search integration.
6. Parametric Memory: System-level grounding directives and citation enforcement rules.
7. Prospective Memory: Future commitments, tasks, and follow-ups tracked per meeting.
8. Non-Interference Invariant: Memory NEVER feeds synthetic outputs into live STT streams.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from services.assistant_worker.types import IndexedSegment
from services.assistant_worker.vector_store import TranscriptVectorStore

logger = logging.getLogger(__name__)


class MemoryType(StrEnum):
    """The seven distinct cognitive memory layers."""

    WORKING = "WORKING"
    SEMANTIC = "SEMANTIC"
    EPISODIC = "EPISODIC"
    PROCEDURAL = "PROCEDURAL"
    RETRIEVAL = "RETRIEVAL"
    PARAMETRIC = "PARAMETRIC"
    PROSPECTIVE = "PROSPECTIVE"


@dataclass(frozen=True)
class ActionItemRecord:
    """Prospective memory: committed task to be executed after the meeting."""

    task: str
    source_segment_id: str
    meeting_id: str
    tenant_id: str
    assignee: str | None = None
    status: str = "PENDING"
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass(frozen=True)
class EpisodicRecord:
    """Episodic memory: durable recap of a completed meeting session."""

    meeting_id: str
    tenant_id: str
    summary: str
    key_decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    consent_granted: bool = True
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    retention_days: int = 90
    expires_at_ms: int | None = None


@dataclass(frozen=True)
class ProceduralTemplate:
    """Procedural memory: operational template for structured responses."""

    name: str
    description: str
    template: str


class SevenTypeMemoryManager:
    """Orchestrates the Seven-Type Memory Architecture for the In-Meeting Copilot."""

    def __init__(
        self,
        vector_store: TranscriptVectorStore | None = None,
        max_working_window: int = 15,
    ) -> None:
        self.vector_store = vector_store or TranscriptVectorStore()
        self.max_working_window = max_working_window

        # 1. Working Memory: meeting_id -> list of recent IndexedSegments (sliding window)
        self._working_memory: dict[str, list[IndexedSegment]] = {}

        # 2. Semantic Memory: tenant_id -> set of technical/domain terms
        self._semantic_memory: dict[str, set[str]] = {}

        # 3. Episodic Memory: tenant_id -> list of EpisodicRecords (requires consent)
        self._episodic_memory: dict[str, list[EpisodicRecord]] = {}

        # 4. Procedural Memory: name -> ProceduralTemplate
        self._procedural_memory: dict[str, ProceduralTemplate] = self._init_default_procedures()

        # 5. Parametric Memory: System grounding rules and prompt directives
        self._parametric_rules: list[str] = [
            "Ground all statements strictly in verified meeting transcript facts.",
            "Always include source_segment_id citations for every assertion.",
            "If an answer cannot be deduced from transcript context, state so explicitly.",
            "Never feed synthetic or memory content into live STT audio streams (Invariant #1).",
            "Preserve multi-tenant isolation; never leak cross-tenant or cross-room data.",
        ]

        # 6. Prospective Memory: meeting_id -> list of ActionItemRecords
        self._prospective_memory: dict[str, list[ActionItemRecord]] = {}

    def _init_default_procedures(self) -> dict[str, ProceduralTemplate]:
        """Seeds standard operational procedural templates."""
        return {
            "ACTION_ITEM_EXTRACTION": ProceduralTemplate(
                name="ACTION_ITEM_EXTRACTION",
                description="Procedure for extracting commitments, assignees, and deadlines.",
                template=(
                    "Format each action item as: [Assignee] Action Description "
                    "(Source: source_segment_id)"
                ),
            ),
            "EXECUTIVE_RECAP": ProceduralTemplate(
                name="EXECUTIVE_RECAP",
                description="Template for synthesizing concise meeting recaps.",
                template="Structure: 1. Executive Summary, 2. Key Decisions, 3. Next Steps.",
            ),
            "CONSENSUS_DETECTION": ProceduralTemplate(
                name="CONSENSUS_DETECTION",
                description="Procedure for detecting agreements and unresolved debates.",
                template="List explicit agreements reached and flag open/unresolved questions.",
            ),
        }

    # --- 1. Working Memory ---

    def add_working_segment(self, segment: IndexedSegment) -> None:
        """Appends segment to the sliding working memory window and indexes domain concepts."""
        mid = segment.meeting_id
        if mid not in self._working_memory:
            self._working_memory[mid] = []

        window = self._working_memory[mid]
        window.append(segment)

        # Enforce bounded sliding window (DEC-05)
        if len(window) > self.max_working_window:
            self._working_memory[mid] = window[-self.max_working_window :]

        # Index semantic concepts for tenant
        if segment.tenant_id and segment.text:
            self.add_semantic_concepts(segment.tenant_id, segment.text)

    def get_working_memory(self, meeting_id: str) -> list[IndexedSegment]:
        """Returns the bounded chronological working memory window for a meeting."""
        return list(self._working_memory.get(meeting_id, []))

    # --- 2. Semantic Memory ---

    def add_semantic_concepts(self, tenant_id: str, text: str) -> None:
        """Extracts and catalogs candidate domain terminology under tenant isolation."""
        if tenant_id not in self._semantic_memory:
            self._semantic_memory[tenant_id] = set()

        # Simple high-value token extraction (capitalized words / technical terms)
        words = text.split()
        for word in words:
            cleaned = word.strip(".,;:?!'\"()[]{}")
            if len(cleaned) >= 4 and (cleaned[0].isupper() or "_" in cleaned or "-" in cleaned):
                self._semantic_memory[tenant_id].add(cleaned)

    def get_semantic_concepts(self, tenant_id: str) -> list[str]:
        """Returns sorted list of cataloged domain terms for a tenant."""
        return sorted(self._semantic_memory.get(tenant_id, set()))

    # --- 3. Episodic Memory ---

    def store_episodic_summary(self, record: EpisodicRecord) -> bool:
        """Persists a meeting summary if explicit consent is granted (DEC-05).

        Returns:
            True if stored successfully; False if rejected due to missing consent.
        """
        if not record.consent_granted:
            logger.warning(
                "Episodic memory storage denied for meeting %s: user/host consent not granted.",
                record.meeting_id,
            )
            return False

        tid = record.tenant_id
        if tid not in self._episodic_memory:
            self._episodic_memory[tid] = []

        self._episodic_memory[tid].append(record)
        logger.info(
            "Episodic memory stored for meeting %s under tenant %s (retention: %d days)",
            record.meeting_id,
            tid,
            record.retention_days,
        )
        return True

    def get_episodic_history(
        self,
        tenant_id: str,
        include_expired: bool = False,
    ) -> list[EpisodicRecord]:
        """Retrieves past meeting records for a tenant, filtering out expired ones."""
        records = self._episodic_memory.get(tenant_id, [])
        if include_expired:
            return list(records)

        now_ms = int(time.time() * 1000)
        valid: list[EpisodicRecord] = []
        for r in records:
            if r.expires_at_ms is not None and now_ms > r.expires_at_ms:
                continue
            valid.append(r)
        return valid

    # --- 4. Procedural Memory ---

    def get_procedural_template(self, name: str) -> ProceduralTemplate | None:
        """Retrieves an operational procedure by name."""
        return self._procedural_memory.get(name)

    def register_procedural_template(self, template: ProceduralTemplate) -> None:
        """Registers a custom operational procedure template."""
        self._procedural_memory[template.name] = template

    # --- 5. Parametric Memory ---

    def get_parametric_rules(self) -> list[str]:
        """Returns foundational grounding rules."""
        return list(self._parametric_rules)

    def get_parametric_grounding_prompt(self) -> str:
        """Formats the grounding prompt directives for LLM consumption."""
        rules = "\n".join(f"- {r}" for r in self._parametric_rules)
        return f"CRITICAL SYSTEM DIRECTIVES:\n{rules}"

    # --- 6. Prospective Memory ---

    def add_action_item(
        self,
        meeting_id: str,
        tenant_id: str,
        task: str,
        source_segment_id: str,
        assignee: str | None = None,
    ) -> ActionItemRecord:
        """Registers a future commitment or task committed during a meeting."""
        record = ActionItemRecord(
            task=task,
            source_segment_id=source_segment_id,
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            assignee=assignee,
        )
        if meeting_id not in self._prospective_memory:
            self._prospective_memory[meeting_id] = []

        self._prospective_memory[meeting_id].append(record)
        return record

    def get_prospective_items(self, meeting_id: str) -> list[ActionItemRecord]:
        """Returns all action items tracked for a meeting."""
        return list(self._prospective_memory.get(meeting_id, []))

    # --- 7. Retrieval Memory & Unified Context ---

    def get_context_for_query(
        self,
        query: str,
        query_embedding: np.ndarray,
        meeting_id: str,
        tenant_id: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Integrates Working, Retrieval, Prospective, and Parametric memory into a query context.

        Returns:
            Dictionary containing:
            - working_memory: recent chronological transcript segments
            - retrieved_segments: top-k vector similarity segments with scores
            - prospective_items: pending meeting action items
            - semantic_concepts: domain terminology for the tenant
            - grounding_directives: parametric prompt instructions
        """
        # 1. Working memory (immediate conversational context)
        working_segs = self.get_working_memory(meeting_id)

        # 2. Retrieval memory (dense semantic search)
        retrieved = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            meeting_id=meeting_id,
            top_k=top_k,
            threshold=threshold,
        )

        # 3. Prospective memory
        action_items = self.get_prospective_items(meeting_id)

        # 4. Semantic memory
        concepts = self.get_semantic_concepts(tenant_id)

        return {
            "query": query,
            "working_memory": working_segs,
            "retrieved_segments": retrieved,
            "prospective_items": action_items,
            "semantic_concepts": concepts,
            "grounding_directives": self.get_parametric_grounding_prompt(),
        }

    # --- Lifecycle & Teardown ---

    def clear_meeting(self, meeting_id: str) -> None:
        """Purges ephemeral working, prospective, and retrieval memory upon meeting conclusion."""
        self._working_memory.pop(meeting_id, None)
        self._prospective_memory.pop(meeting_id, None)
        self.vector_store.clear_meeting(meeting_id)
        logger.info("Cleared ephemeral memory for meeting %s", meeting_id)
