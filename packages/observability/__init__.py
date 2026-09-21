"""Observability package with OpenTelemetry distributed tracing and Prometheus metrics (PR-17)."""

import logging

from .logging import StructuredJsonFormatter, configure_logging
from .metrics import (
    REGISTRY,
    active_meetings_count,
    backpressure_dropped_partials_total,
    degradation_tier_transitions_total,
    diarization_duration_seconds,
    dlq_quarantined_total,
    dlq_retries_total,
    generate_metrics_response,
    meeting_e2e_latency_seconds,
    nmt_inference_duration_seconds,
    pipeline_queue_depth,
    stt_inference_duration_seconds,
    tts_inference_duration_seconds,
    watermark_detections_total,
    worker_heartbeat_liveness,
)
from .tracer import (
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    inject_trace_context,
    trace_async_span,
    trace_span,
)

logger = logging.getLogger("multilingual-meeting-platform")
tracer = get_tracer("multilingual-meeting-platform")

__all__ = [
    "REGISTRY",
    "StructuredJsonFormatter",
    "active_meetings_count",
    "backpressure_dropped_partials_total",
    "configure_logging",
    "degradation_tier_transitions_total",
    "diarization_duration_seconds",
    "dlq_quarantined_total",
    "dlq_retries_total",
    "extract_trace_context",
    "generate_metrics_response",
    "get_current_span_id",
    "get_current_trace_id",
    "get_tracer",
    "inject_trace_context",
    "logger",
    "meeting_e2e_latency_seconds",
    "nmt_inference_duration_seconds",
    "pipeline_queue_depth",
    "stt_inference_duration_seconds",
    "trace_async_span",
    "trace_span",
    "tracer",
    "tts_inference_duration_seconds",
    "watermark_detections_total",
    "worker_heartbeat_liveness",
]
