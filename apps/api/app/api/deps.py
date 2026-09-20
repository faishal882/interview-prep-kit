"""Auth dependencies: current user from session cookie, origin check, ownership."""
from __future__ import annotations

import time

from fastapi import Cookie, Header, Request

from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.persistence.memory import DB, SESSION_TTL


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
    import hashlib
    if not session:
        raise KitError(Codes.UNAUTHORIZED, "not signed in")
    digest = hashlib.sha256(session.encode()).hexdigest()
    s = DB.sessions.get(digest)
    if not s:
        raise KitError(Codes.SESSION_EXPIRED, "sign in again")
    if s["expires_at"] < time.time():
        DB.sessions.pop(digest, None)
        raise KitError(Codes.SESSION_EXPIRED, "sign in again")
    u = DB.users.get(s["user_id"])
    if not u:
        raise KitError(Codes.SESSION_EXPIRED, "sign in again")
    return u


def get_kit_or_404(kit_id: str, user_id: str) -> dict:
    kit = DB.kits.get(kit_id)
    if not kit or kit.get("user_id") != user_id:
        raise KitError(Codes.NOT_FOUND, "kit not found")
    return kit
