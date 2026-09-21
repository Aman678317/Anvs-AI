"""Unit tests for Observability, OpenTelemetry Tracing & Prometheus Metrics (PR-17)."""

import json
import logging
import re
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from packages.observability import (
    REGISTRY,
    StructuredJsonFormatter,
    active_meetings_count,
    backpressure_dropped_partials_total,
    extract_trace_context,
    generate_metrics_response,
    get_current_span_id,
    get_current_trace_id,
    inject_trace_context,
    stt_inference_duration_seconds,
    trace_span,
)
from services.api.main import app


# -----------------------------------------------------------------------------
# Unit Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
def test_w3c_trace_context_injection_and_extraction() -> None:
    """W3C traceparent is correctly injected, formatted, and extracted across carriers."""
    with trace_span("parent-ingress-span"):
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        assert trace_id is not None
        assert span_id is not None

        # Inject into Redis event envelope / HTTP header dictionary
        carrier: dict[str, str] = {}
        inject_trace_context(carrier)

        assert "traceparent" in carrier
        # Validate W3C traceparent format: 00-{32hex}-{16hex}-{2hex}
        pattern = r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"
        assert re.match(pattern, carrier["traceparent"]) is not None
        assert trace_id in carrier["traceparent"]

        # Extract context on downstream worker
        extracted_ctx = extract_trace_context(carrier)
        assert extracted_ctx is not None

        # Start child span with extracted context and verify trace continuity
        with trace_span("child-worker-span", parent_context=extracted_ctx):
            child_trace_id = get_current_trace_id()
            assert child_trace_id == trace_id


@pytest.mark.unit
def test_span_creation_and_attributes() -> None:
    """Spans accept custom domain attributes for model profiling and meeting lineage."""
    with trace_span(
        name="nmt-translation-span",
        attributes={
            "meeting_id": "meet_xyz",
            "source_lang": "eng",
            "target_lang": "spa",
            "is_final": True,
        },
    ) as span:
        assert span.is_recording()
        # Verify trace identifiers are queryable inside the span scope
        assert get_current_trace_id() is not None
        assert get_current_span_id() is not None


@pytest.mark.unit
def test_prometheus_metrics_generation() -> None:
    """Prometheus collectors track latencies, queue depths, and generate valid exposition."""
    # 1. Update Gauge
    active_meetings_count.set(7)

    # 2. Increment Counter
    backpressure_dropped_partials_total.labels(meeting_id="meet_test").inc(3)

    # 3. Observe Histogram
    stt_inference_duration_seconds.labels(language="eng", engine="mock").observe(0.125)

    # 4. Generate exposition payload
    content, content_type = generate_metrics_response()
    decoded = content.decode("utf-8")

    assert "text/plain" in content_type
    assert "active_meetings_count 7.0" in decoded
    assert 'backpressure_dropped_partials_total{meeting_id="meet_test"} 3.0' in decoded
    assert 'stt_inference_duration_seconds_count{engine="mock",language="eng"} 1.0' in decoded


@pytest.mark.unit
def test_structured_json_logging() -> None:
    """StructuredJsonFormatter produces valid JSON containing trace and span IDs."""
    formatter = StructuredJsonFormatter()

    with trace_span("traced-operation"):
        current_trace = get_current_trace_id()
        current_span = get_current_span_id()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Speech segment successfully transcribed",
            args=(),
            exc_info=None,
        )
        record.tenant_id = "tenant-corp-123"  # type: ignore[attr-defined]
        record.correlation_id = "corr-abc-789"  # type: ignore[attr-defined]

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Speech segment successfully transcribed"
        assert parsed["trace_id"] == current_trace
        assert parsed["span_id"] == current_span
        assert parsed["tenant_id"] == "tenant-corp-123"
        assert parsed["correlation_id"] == "corr-abc-789"
        assert "timestamp" in parsed


@pytest.mark.unit
def test_fastapi_metrics_endpoint_integration() -> None:
    """FastAPI control plane exposes Prometheus metrics at /metrics with HTTP 200."""
    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "active_meetings_count" in response.text
