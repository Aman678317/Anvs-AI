"""Meeting Assistant Worker Service adhering to Document 14."""

from .consumer import AssistantConsumer
from .engine import (
    BaseAssistantEngine,
    MockAssistantEngine,
    OpenAIAssistantEngine,
    create_assistant_engine,
)
from .types import AssistantAnswer, IndexedSegment, MeetingSummary
from .vector_store import TranscriptVectorStore, cosine_similarity

__all__ = [
    "AssistantAnswer",
    "AssistantConsumer",
    "BaseAssistantEngine",
    "IndexedSegment",
    "MeetingSummary",
    "MockAssistantEngine",
    "OpenAIAssistantEngine",
    "TranscriptVectorStore",
    "cosine_similarity",
    "create_assistant_engine",
]
