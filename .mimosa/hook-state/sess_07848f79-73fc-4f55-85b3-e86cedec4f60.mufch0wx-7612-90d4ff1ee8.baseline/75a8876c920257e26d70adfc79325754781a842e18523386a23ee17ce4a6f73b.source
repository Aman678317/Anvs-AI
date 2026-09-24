"""Speaker Diarization Data Models and Result Types."""

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class DiarizationResult:
    """Represents a speaker diarization inference result."""

    speaker_id: str
    confidence: float
    embedding: np.ndarray
    speaker_name: str | None = None
    turn_type: str = "continued"
    start_ms: int = 0
    end_ms: int = 0
    metadata: dict[str, str] = field(default_factory=dict)
