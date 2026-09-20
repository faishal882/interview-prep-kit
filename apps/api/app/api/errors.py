"""Uniform error envelope: {error: {code, message, details, trace_id}}."""
from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors import KitError


def envelope(code: str, message: str, details: dict | None = None, trace_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}, "trace_id": trace_id or uuid.uuid4().hex[:12]}}


async def kit_error_handler(request: Request, exc: KitError) -> JSONResponse:
    status = {"UNAUTHORIZED": 401, "SESSION_EXPIRED": 401, "FORBIDDEN": 403, "NOT_FOUND": 404,
              "CONFLICT": 409, "RATE_LIMITED": 429}.get(exc.code, 400)
    return JSONResponse(status_code=status, content=envelope(exc.code, exc.message, exc.details))


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=envelope("INTERNAL", "unexpected error", {"type": type(exc).__name__}))
