"""STT Worker Data Models and Result Types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class STTResult:
    """Represents a streaming or segment transcription hypothesis."""

    text: str
    is_final: bool
    language: str
    start_ms: int
    end_ms: int
    confidence: float
    latency_ms: int = 0
