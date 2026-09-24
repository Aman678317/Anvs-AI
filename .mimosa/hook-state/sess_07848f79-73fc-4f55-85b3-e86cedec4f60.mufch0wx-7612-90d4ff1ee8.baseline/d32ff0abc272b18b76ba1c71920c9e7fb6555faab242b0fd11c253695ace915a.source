"""Prometheus Metrics Exporter and Platform Telemetry Collectors (PR-17).

Provides sub-segment latency profiling (STT, NMT, TTS, Diarization, E2E),
queue depth monitors, backpressure event counters, and Prometheus text exposition.
"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Shared platform registry
REGISTRY = CollectorRegistry(auto_describe=True)

# -----------------------------------------------------------------------------
# 1. Latency Histograms (Sub-segment & End-to-End)
# -----------------------------------------------------------------------------

meeting_e2e_latency_seconds = Histogram(
    "meeting_e2e_latency_seconds",
    "End-to-end glass-to-glass latency from microphone capture to playback in seconds",
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0],
    registry=REGISTRY,
)

stt_inference_duration_seconds = Histogram(
    "stt_inference_duration_seconds",
    "Speech-to-text ASR inference execution latency in seconds",
    ["language", "engine"],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

nmt_inference_duration_seconds = Histogram(
    "nmt_inference_duration_seconds",
    "Neural machine translation model inference latency in seconds",
    ["source_lang", "target_lang"],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

tts_inference_duration_seconds = Histogram(
    "tts_inference_duration_seconds",
    "Text-to-speech audio synthesis execution latency in seconds",
    ["target_lang", "voice_id"],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

diarization_duration_seconds = Histogram(
    "diarization_duration_seconds",
    "Speaker diarization clustering duration in seconds",
    ["engine"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0],
    registry=REGISTRY,
)

# -----------------------------------------------------------------------------
# 2. Flow Control & Resilience Counters
# -----------------------------------------------------------------------------

backpressure_dropped_partials_total = Counter(
    "backpressure_dropped_partials_total",
    "Total non-final partial segments shed under backpressure",
    ["meeting_id"],
    registry=REGISTRY,
)

degradation_tier_transitions_total = Counter(
    "degradation_tier_transitions_total",
    "Pipeline degradation tier state machine transitions",
    ["from_tier", "to_tier"],
    registry=REGISTRY,
)

dlq_retries_total = Counter(
    "dlq_retries_total",
    "Total events successfully retried from Dead Letter Queue",
    ["original_stream"],
    registry=REGISTRY,
)

dlq_quarantined_total = Counter(
    "dlq_quarantined_total",
    "Total poison-pill events permanently quarantined in DLQ",
    ["original_stream"],
    registry=REGISTRY,
)

watermark_detections_total = Counter(
    "watermark_detections_total",
    "Acoustic watermark checks on incoming audio frames",
    ["status"],
    registry=REGISTRY,
)

# -----------------------------------------------------------------------------
# 3. Queue Depth & Liveness Gauges
# -----------------------------------------------------------------------------

active_meetings_count = Gauge(
    "active_meetings_count",
    "Number of currently active meeting rooms in session",
    registry=REGISTRY,
)

pipeline_queue_depth = Gauge(
    "pipeline_queue_depth",
    "Observed message count queued in Redis Stream",
    ["stream_type", "meeting_id"],
    registry=REGISTRY,
)

worker_heartbeat_liveness = Gauge(
    "worker_heartbeat_liveness",
    "Health status of worker instances (1=healthy, 0=dead)",
    ["worker_type", "worker_id"],
    registry=REGISTRY,
)


def generate_metrics_response(
    registry: CollectorRegistry | None = None,
) -> tuple[bytes, str]:
    """Export platform metrics in Prometheus text exposition format."""
    target_registry = registry or REGISTRY
    return generate_latest(target_registry), CONTENT_TYPE_LATEST
