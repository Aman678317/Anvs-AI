"""Query Router: Intent classification and routing for the AI Copilot (PR-12).

Classifies incoming natural language questions into intent categories before
dispatching to the most appropriate retrieval or generation strategy.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Classification of participant copilot query intent."""

    FACTUAL = "factual"
    """Participant is asking a factual question about what was discussed."""

    ACTION_ITEM = "action_item"
    """Participant is asking about tasks, commitments, or next steps."""

    SUMMARY = "summary"
    """Participant is asking for an overview, recap, or executive summary."""

    DECISION = "decision"
    """Participant is asking about agreements, approvals, or resolutions."""

    CLARIFICATION = "clarification"
    """Participant is asking for elaboration or re-explanation of a point."""


@dataclass(frozen=True)
class RouterResult:
    """Result of the intent classification phase."""

    intent: QueryIntent
    confidence: float
    top_k_override: int | None = None
    similarity_threshold_override: float | None = None


# Keyword-trigger pattern registry, ordered by priority (most specific first)
_INTENT_PATTERNS: list[tuple[QueryIntent, re.Pattern[str], int | None, float | None]] = [
    # ACTION_ITEM: assignment / commitment / follow-up language
    (
        QueryIntent.ACTION_ITEM,
        re.compile(
            r"\b(action items?|tasks?|todos?|follow.?ups?|assign(ed|ment|ments|s|ing)?|"
            r"responsibilit(y|ies)|who.+will|next steps?|deliverables?|deadlines?|"
            r"due dates?|commit(s|ted|ting|ment|ments)?)\b",
            re.IGNORECASE,
        ),
        10,  # Retrieve more context for action items
        0.45,
    ),
    # DECISION: consensus / approval language
    (
        QueryIntent.DECISION,
        re.compile(
            r"\b(decid(ed|es|ing|e)?|decisions?|agree(d|ment|ments|s|ing)?|"
            r"approv(ed|al|als|e|es|ing)?|consensus|resolv(ed|es|ing|e)?|"
            r"resolutions?|vot(ed|e|es|ing)?|outcomes?)\b",
            re.IGNORECASE,
        ),
        8,
        0.50,
    ),
    # SUMMARY: overview / recap language
    (
        QueryIntent.SUMMARY,
        re.compile(
            r"\b(summar(y|ies|ize|ise|ized|ised|izing|ising)?|recaps?|overviews?|gists?|"
            r"tldr|tl;?dr|highlights?|key points?|main topics?|what.+covered|what.+discussed|overall)\b",
            re.IGNORECASE,
        ),
        15,
        0.35,
    ),
    # CLARIFICATION: elaboration / explain language
    (
        QueryIntent.CLARIFICATION,
        re.compile(
            r"\b(clarif(y|ied|ies|ication|ying)?|elaborat(e|ed|es|ing)?|explain(ed|s|ing)?|"
            r"what.+mean|what did.+say|repeat(ed|s|ing)?|rephrase(d|s)?|more detail|expand on)\b",
            re.IGNORECASE,
        ),
        5,
        0.60,
    ),
    # FACTUAL: default catch-all
    (
        QueryIntent.FACTUAL,
        re.compile(r".*"),  # matches everything
        5,
        0.55,
    ),
]


class QueryRouter:
    """Lightweight intent classifier for AI copilot queries.

    Uses ordered keyword pattern matching with confidence scoring.
    Provides `top_k` and `similarity_threshold` overrides per intent class
    to tune RAG retrieval quality for each query type.
    """

    def classify(self, question: str) -> RouterResult:
        """Classifies a natural-language question into a QueryIntent.

        Args:
            question: Raw natural language query from meeting participant.

        Returns:
            RouterResult with classified intent, confidence, and retrieval overrides.
        """
        if not question or not question.strip():
            return RouterResult(
                intent=QueryIntent.FACTUAL,
                confidence=0.5,
                top_k_override=5,
                similarity_threshold_override=0.55,
            )

        clean = question.strip()

        for intent, pattern, top_k, threshold in _INTENT_PATTERNS:
            match = pattern.search(clean)
            if match:
                # Confidence scales with match specificity vs. question length
                match_len = len(match.group(0))
                question_len = max(1, len(clean))
                base_confidence = 0.70 if intent != QueryIntent.FACTUAL else 0.60
                length_factor = min(1.0, match_len / question_len * 3)
                confidence = round(min(0.98, base_confidence + length_factor * 0.25), 3)

                logger.debug(
                    "Classified query intent=%s confidence=%.2f question='%s...'",
                    intent.value,
                    confidence,
                    clean[:60],
                )
                return RouterResult(
                    intent=intent,
                    confidence=confidence,
                    top_k_override=top_k,
                    similarity_threshold_override=threshold,
                )

        # Unreachable — FACTUAL regex matches everything, but defensive fallback
        return RouterResult(
            intent=QueryIntent.FACTUAL,
            confidence=0.60,
            top_k_override=5,
            similarity_threshold_override=0.55,
        )

    def get_retrieval_params(
        self,
        question: str,
        default_top_k: int = 5,
        default_threshold: float = 0.55,
    ) -> tuple[int, float, QueryIntent]:
        """Classifies and returns retrieval parameters for the question.

        Returns:
            (top_k, similarity_threshold, intent) tuple ready for vector store call.
        """
        result = self.classify(question)
        top_k = result.top_k_override if result.top_k_override is not None else default_top_k
        threshold = (
            result.similarity_threshold_override
            if result.similarity_threshold_override is not None
            else default_threshold
        )
        return top_k, threshold, result.intent
