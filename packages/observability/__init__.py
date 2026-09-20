"""Observability package with OpenTelemetry tracing and Prometheus metrics."""

import logging

from opentelemetry import trace

tracer = trace.get_tracer("multilingual-meeting-platform")
logger = logging.getLogger("multilingual-meeting-platform")

__all__ = ["logger", "tracer"]
