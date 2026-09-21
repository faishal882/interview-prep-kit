"""Request / job correlation ids carried on every log line and error envelope."""
from __future__ import annotations

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_job_id: ContextVar[str] = ContextVar("job_id", default="")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def set_request_id(value: str | None = None) -> str:
    rid = value or new_id()
    _request_id.set(rid)
    # When telemetry is off, the request id is the trace id that appears in errors.
    if not _trace_id.get():
        _trace_id.set(rid)
    return rid


def set_job_id(value: str | None) -> None:
    _job_id.set(value or "")


def set_trace_id(value: str | None) -> None:
    if value:
        _trace_id.set(value)


def request_id() -> str:
    return _request_id.get() or ""


def job_id() -> str:
    return _job_id.get() or ""


def trace_id() -> str:
    return _trace_id.get() or _request_id.get() or ""


def clear() -> None:
    _request_id.set("")
    _job_id.set("")
    _trace_id.set("")
