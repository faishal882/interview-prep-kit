"""Uniform error envelope: {error: {code, message, details, trace_id}}.

`trace_id` equals the request id that appears in structured logs (or the OTel
trace id when telemetry is on). Unexpected errors return a generic message
with no exception type and are logged with a stack trace.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors import KitError
from app.observability import get_logger, log_exception, request_id, trace_id

_log = get_logger("trao.errors")


def envelope(code: str, message: str, details: dict | None = None, trace_id_value: str | None = None) -> dict:
    tid = trace_id_value or trace_id() or request_id()
    if not tid:
        from app.observability.context import new_id
        tid = new_id()
    return {"error": {"code": code, "message": message, "details": details or {}, "trace_id": tid}}


async def kit_error_handler(request: Request, exc: KitError) -> JSONResponse:
    status = {"UNAUTHORIZED": 401, "SESSION_EXPIRED": 401, "FORBIDDEN": 403, "NOT_FOUND": 404,
              "CONFLICT": 409, "RATE_LIMITED": 429, "PAYLOAD_TOO_LARGE": 413}.get(exc.code, 400)
    tid = getattr(request.state, "request_id", None) or trace_id() or request_id()
    return JSONResponse(status_code=status, content=envelope(exc.code, exc.message, exc.details, tid))


async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
    details: dict = {}
    try:
        errors = getattr(exc, "errors", lambda: [])()
        details = {"fields": [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in errors][:10]}
    except Exception:
        pass
    tid = getattr(request.state, "request_id", None) or trace_id() or request_id()
    return JSONResponse(status_code=422, content=envelope("INVALID_INPUT", "invalid request", details, tid))


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    tid = getattr(request.state, "request_id", None) or trace_id() or request_id()
    log_exception(_log, f"unhandled error request_id={tid}", exc)
    return JSONResponse(status_code=500, content=envelope("INTERNAL", "unexpected error", None, tid))
