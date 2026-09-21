"""Auth dependencies: current user from session cookie, origin check, ownership."""
from __future__ import annotations

import hashlib
import time

from fastapi import Cookie, Request

from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.persistence.store import get_store


def check_origin(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = [o.strip() for o in (get_settings().ALLOWED_ORIGINS or "").split(",") if o.strip()]
    if allowed and origin not in allowed:
        raise KitError(Codes.FORBIDDEN, "foreign origin rejected")


async def current_user(session: str | None = Cookie(default=None)) -> dict:
    if not session:
        raise KitError(Codes.UNAUTHORIZED, "not signed in")
    digest = hashlib.sha256(session.encode()).hexdigest()
    store = get_store()
    s = await store.sessions.get(digest)
    if not s:
        raise KitError(Codes.SESSION_EXPIRED, "sign in again")
    u = await store.users.by_id(s["user_id"])
    if not u:
        raise KitError(Codes.SESSION_EXPIRED, "sign in again")
    return u


async def get_kit_or_404(kit_id: str, user_id: str) -> dict:
    kit = await get_store().kits.get(kit_id)
    if not kit or kit.get("user_id") != user_id:
        raise KitError(Codes.NOT_FOUND, "kit not found")
    return kit


async def save_kit(doc: dict) -> None:
    await get_store().kits.save(doc)


def client_address(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
