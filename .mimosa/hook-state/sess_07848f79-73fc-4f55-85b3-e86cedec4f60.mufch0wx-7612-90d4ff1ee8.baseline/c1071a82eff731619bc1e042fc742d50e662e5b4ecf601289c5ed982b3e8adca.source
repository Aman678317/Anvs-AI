"""Distributed Tracing with OpenTelemetry and W3C TraceContext (PR-17).

Provides context injection/extraction across async Redis streams and HTTP/WebSocket
boundaries using standard W3C `traceparent` (00-{trace_id}-{span_id}-{flags}).
"""

import contextlib
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

# Initialize default TracerProvider if not already configured
_provider: TracerProvider | None = None
_exporter: InMemorySpanExporter | None = None
_propagator = TraceContextTextMapPropagator()


def get_tracer_provider() -> TracerProvider:
    """Return active TracerProvider or configure default in-memory provider."""
    global _provider, _exporter
    if _provider is None:
        _provider = TracerProvider()
        _exporter = InMemorySpanExporter()
        _provider.add_span_processor(SimpleSpanProcessor(_exporter))
        trace.set_tracer_provider(_provider)
    return _provider


def get_tracer(instrumenting_module_name: str = "multilingual-platform") -> Tracer:
    """Obtain a named OpenTelemetry Tracer."""
    provider = get_tracer_provider()
    return provider.get_tracer(instrumenting_module_name)


def inject_trace_context(carrier: dict[str, str] | None = None) -> dict[str, str]:
    """Inject current active span's W3C trace context into carrier dictionary.

    Adds `traceparent` and optionally `tracestate`.
    """
    target_carrier = carrier if carrier is not None else {}
    _propagator.inject(target_carrier)
    return target_carrier


def extract_trace_context(carrier: dict[str, str]) -> Context:
    """Extract W3C trace context from carrier dictionary."""
    return _propagator.extract(carrier)


def get_current_trace_id() -> str | None:
    """Return current active 32-character hexadecimal trace ID if present."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return f"{ctx.trace_id:032x}"
    return None


def get_current_span_id() -> str | None:
    """Return current active 16-character hexadecimal span ID if present."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return f"{ctx.span_id:016x}"
    return None


@contextlib.contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    parent_context: Context | None = None,
) -> Iterator[Span]:
    """Synchronous context manager creating a traced span with optional attributes."""
    tracer = get_tracer()
    with tracer.start_as_current_span(
        name=name,
        context=parent_context,
        attributes=attributes or {},
    ) as span:
        yield span


@contextlib.asynccontextmanager
async def trace_async_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    parent_context: Context | None = None,
) -> AsyncIterator[Span]:
    """Asynchronous context manager creating a traced span with optional attributes."""
    tracer = get_tracer()
    with tracer.start_as_current_span(
        name=name,
        context=parent_context,
        attributes=attributes or {},
    ) as span:
        yield span
