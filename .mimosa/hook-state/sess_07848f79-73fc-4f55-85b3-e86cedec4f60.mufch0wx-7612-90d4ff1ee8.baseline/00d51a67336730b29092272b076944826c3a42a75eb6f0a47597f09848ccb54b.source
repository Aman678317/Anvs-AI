"""NMT Worker Data Models and Result Types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationResult:
    """Represents a translated segment result."""

    translated_text: str
    source_language: str
    target_language: str
    latency_ms: int = 0
    model_version: str = "mock-nmt"
