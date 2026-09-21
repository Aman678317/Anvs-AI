"""Voice Profile Registry and Cosine Similarity Matching adhering to Document 14."""

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """Normalizes an embedding vector to unit length (L2 norm)."""
    flat = embedding.astype(np.float32).flatten()
    norm = float(np.linalg.norm(flat))
    if norm < 1e-12:
        return flat
    return flat / norm


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes the cosine similarity between two embedding vectors in [-1.0, 1.0]."""
    norm_a = normalize_embedding(vec_a)
    norm_b = normalize_embedding(vec_b)
    dot_product = float(np.dot(norm_a, norm_b))
    return max(-1.0, min(1.0, dot_product))


@dataclass
class VoiceProfile:
    """Represents an enrolled speaker voice profile fingerprint."""

    speaker_id: str
    name: str
    embedding: np.ndarray
    metadata: dict[str, str] = field(default_factory=dict)


class VoiceProfileRegistry:
    """In-memory voice profile catalog with cosine matching and dynamic clustering."""

    def __init__(self, default_similarity_threshold: float = 0.75) -> None:
        self.default_similarity_threshold = default_similarity_threshold
        # Enrolled profiles: speaker_id -> VoiceProfile
        self._enrolled_profiles: dict[str, VoiceProfile] = {}
        # Dynamic speaker clusters for unregistered speakers: cluster_id -> centroid embedding
        self._dynamic_clusters: dict[str, np.ndarray] = {}
        self._cluster_counter: int = 0

    def register_profile(
        self,
        speaker_id: str,
        name: str,
        embedding: np.ndarray,
        metadata: dict[str, str] | None = None,
    ) -> VoiceProfile:
        """Registers or updates a known participant voice profile fingerprint."""
        norm_emb = normalize_embedding(embedding)
        profile = VoiceProfile(
            speaker_id=speaker_id,
            name=name,
            embedding=norm_emb,
            metadata=metadata or {},
        )
        self._enrolled_profiles[speaker_id] = profile
        logger.info("Registered voice profile for speaker '%s' (%s)", speaker_id, name)
        return profile

    def get_profile(self, speaker_id: str) -> VoiceProfile | None:
        """Retrieves an enrolled profile by speaker_id."""
        return self._enrolled_profiles.get(speaker_id)

    def match_speaker(
        self,
        embedding: np.ndarray,
        threshold: float | None = None,
    ) -> tuple[str, str | None, float]:
        """Matches a query embedding against enrolled profiles and dynamic clusters.

        Returns:
            Tuple of (speaker_id, speaker_name, confidence).
        """
        thresh = threshold if threshold is not None else self.default_similarity_threshold
        norm_query = normalize_embedding(embedding)

        best_speaker_id: str | None = None
        best_speaker_name: str | None = None
        best_similarity: float = -1.0

        # 1. Search enrolled known profiles first
        for spk_id, profile in self._enrolled_profiles.items():
            sim = cosine_similarity(norm_query, profile.embedding)
            if sim > best_similarity:
                best_similarity = sim
                best_speaker_id = spk_id
                best_speaker_name = profile.name

        if best_speaker_id is not None and best_similarity >= thresh:
            # Normalize confidence to [0.0, 1.0]
            confidence = max(0.0, min(1.0, (best_similarity + 1.0) / 2.0))
            return best_speaker_id, best_speaker_name, confidence

        # 2. Search existing dynamic clusters
        best_cluster_id: str | None = None
        best_cluster_sim: float = -1.0

        for cluster_id, centroid in self._dynamic_clusters.items():
            sim = cosine_similarity(norm_query, centroid)
            if sim > best_cluster_sim:
                best_cluster_sim = sim
                best_cluster_id = cluster_id

        if best_cluster_id is not None and best_cluster_sim >= thresh:
            # Update centroid with rolling average
            old_centroid = self._dynamic_clusters[best_cluster_id]
            updated_centroid = normalize_embedding(0.8 * old_centroid + 0.2 * norm_query)
            self._dynamic_clusters[best_cluster_id] = updated_centroid
            confidence = max(0.0, min(1.0, (best_cluster_sim + 1.0) / 2.0))
            return best_cluster_id, None, confidence

        # 3. Create a new dynamic speaker cluster
        new_cluster_id = f"SPEAKER_{self._cluster_counter:02d}"
        self._cluster_counter += 1
        self._dynamic_clusters[new_cluster_id] = norm_query

        # First appearance has high self-consistency
        return new_cluster_id, None, 0.90

    def clear(self) -> None:
        """Purges all dynamic clusters and enrolled profiles."""
        self._enrolled_profiles.clear()
        self._dynamic_clusters.clear()
        self._cluster_counter = 0
