"""Observability: structured logs always on; optional OpenTelemetry."""
from .context import job_id, request_id, set_job_id, set_request_id, set_trace_id, trace_id
from .logging import configure_logging, get_logger, log_exception
from .setup import enabled, record_metric, setup, shutdown, span, timed_ms

__all__ = [
    "configure_logging",
    "enabled",
    "get_logger",
    "job_id",
    "log_exception",
    "record_metric",
    "request_id",
    "set_job_id",
    "set_request_id",
    "set_trace_id",
    "setup",
    "shutdown",
    "span",
    "timed_ms",
    "trace_id",
]
