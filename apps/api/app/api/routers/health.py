"""Liveness and readiness probes.

Liveness always succeeds while the process is up. Readiness verifies the
database (when configured) and that a model key or explicit fake setting is
present — so a load balancer and a deploy script can trust them.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.responses import HealthOut
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut)
@router.get("/api/health/live", response_model=HealthOut)
async def liveness() -> dict:
    """Process is up — does not check dependencies."""
    return {"ok": True}


@router.get("/api/health/ready", response_model=HealthOut)
async def readiness():
    """Database reachable (when configured) and model credentials present."""
    import os

    from app.persistence.store import get_store

    problems: list[str] = []
    s = get_settings()
    store = get_store()
    if store.durable:
        try:
            await store.ping()
        except Exception as exc:
            problems.append(f"database unreachable: {exc}")
    elif (s.MONGODB_URI or "").strip():
        problems.append("database configured but store is not durable")

    has_key = bool((s.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or "").strip())
    has_fake = bool(s.FAKE_LLM or os.environ.get("FAKE_LLM"))
    if not has_key and not has_fake:
        problems.append("model key missing")

    if problems:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "problems": problems},
        )
    return {"ok": True}
