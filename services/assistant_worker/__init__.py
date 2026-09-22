"""Meeting Assistant Worker Service — AI In-Meeting Copilot & RAG (PR-12)."""

from .consumer import AssistantConsumer
from .engine import (
    BaseAssistantEngine,
    MockAssistantEngine,
    OpenAIAssistantEngine,
    create_assistant_engine,
)
from .query_router import QueryIntent, QueryRouter, RouterResult
from .stream_summarizer import MeetingStreamSummarizer, RollingSummaryState
from .types import AssistantAnswer, IndexedSegment, MeetingSummary
from .vector_store import TranscriptVectorStore, cosine_similarity

__all__ = [
    "AssistantAnswer",
    "AssistantConsumer",
    "BaseAssistantEngine",
    "IndexedSegment",
    "MeetingSummary",
    "MeetingStreamSummarizer",
    "MockAssistantEngine",
    "OpenAIAssistantEngine",
    "QueryIntent",
    "QueryRouter",
    "RollingSummaryState",
    "RouterResult",
    "TranscriptVectorStore",
    "cosine_similarity",
    "create_assistant_engine",
]
