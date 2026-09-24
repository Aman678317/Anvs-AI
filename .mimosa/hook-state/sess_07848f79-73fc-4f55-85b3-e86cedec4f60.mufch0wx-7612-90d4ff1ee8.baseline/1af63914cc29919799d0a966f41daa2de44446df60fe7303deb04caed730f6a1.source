"""Structured JSON Logging Formatter with Tracing Correlation (PR-17).

Injects ISO-8601 timestamps, log level, logger name, active OpenTelemetry
`trace_id` and `span_id`, plus optional `correlation_id` and `tenant_id`.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from packages.observability.tracer import get_current_span_id, get_current_trace_id

getLogger = logging.getLogger


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with distributed tracing metadata."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize log record into a single-line JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject OpenTelemetry distributed trace identifiers if present
        trace_id = get_current_trace_id()
        if trace_id:
            log_entry["trace_id"] = trace_id

        span_id = get_current_span_id()
        if span_id:
            log_entry["span_id"] = span_id

        # Inject tenant and correlation metadata if present on record
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id

        # Include exception trace if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger to output structured JSON format."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    root_logger.handlers = [handler]
