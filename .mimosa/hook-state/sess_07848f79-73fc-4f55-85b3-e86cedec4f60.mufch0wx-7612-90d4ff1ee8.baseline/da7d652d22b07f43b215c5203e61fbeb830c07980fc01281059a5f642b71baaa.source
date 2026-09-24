"""Transcript Vector Store for Semantic Retrieval adhering to Document 14."""

import logging

import numpy as np

from services.assistant_worker.types import IndexedSegment

logger = logging.getLogger(__name__)


def cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
    """Computes the cosine similarity between two vector embeddings."""
    norm_u = float(np.linalg.norm(u))
    norm_v = float(np.linalg.norm(v))
    if norm_u < 1e-12 or norm_v < 1e-12:
        return 0.0
    return max(-1.0, min(1.0, float(np.dot(u, v) / (norm_u * norm_v))))


class TranscriptVectorStore:
    """In-memory vector store supporting localized top-k semantic search for RAG."""

    def __init__(self) -> None:
        # meeting_id -> list of IndexedSegment
        self._stores: dict[str, list[IndexedSegment]] = {}

    def add_segment(self, segment: IndexedSegment) -> None:
        """Stores a new indexed transcript segment for a meeting."""
        meeting_id = segment.meeting_id
        if meeting_id not in self._stores:
            self._stores[meeting_id] = []
        self._stores[meeting_id].append(segment)
        logger.debug(
            "Indexed segment '%s' in meeting '%s' (%d total)",
            segment.source_segment_id,
            meeting_id,
            len(self._stores[meeting_id]),
        )

    def similarity_search(
        self,
        query_embedding: np.ndarray,
        meeting_id: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> list[tuple[IndexedSegment, float]]:
        """Retrieves top-k segments most similar to the query embedding.

        Returns:
            List of (IndexedSegment, similarity_score) tuples ordered by relevance.
        """
        segments = self._stores.get(meeting_id, [])
        if not segments or len(query_embedding) == 0:
            return []

        scored: list[tuple[IndexedSegment, float]] = []
        for seg in segments:
            if len(seg.embedding) == 0:
                continue
            sim = cosine_similarity(query_embedding, seg.embedding)
            if sim >= threshold:
                scored.append((seg, sim))

        # Sort by similarity score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        if scored:
            return scored[:top_k]

        # Best-effort fallback: if no segments exceeded strict threshold, return top matches
        all_scored = [
            (seg, cosine_similarity(query_embedding, seg.embedding))
            for seg in segments
            if len(seg.embedding) > 0
        ]
        all_scored.sort(key=lambda x: x[1], reverse=True)
        return all_scored[:top_k]

    def get_transcript(self, meeting_id: str) -> list[IndexedSegment]:
        """Returns all indexed segments for a meeting in chronological sequence."""
        return list(self._stores.get(meeting_id, []))

    def count(self, meeting_id: str) -> int:
        """Returns the number of indexed segments for a meeting."""
        return len(self._stores.get(meeting_id, []))

    def clear_meeting(self, meeting_id: str) -> None:
        """Purges all indexed segments associated with a meeting session."""
        self._stores.pop(meeting_id, None)
