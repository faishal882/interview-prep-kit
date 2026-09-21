"""Auth router: register/login/logout/me with throttling + secure cookies."""
from __future__ import annotations

import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from app.api.deps import current_user
from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.persistence.errors import ConflictError
from app.persistence.store import get_store
from app.security.passwords import hash_password, new_token, verify_password

router = APIRouter()
LOGIN_WINDOW = 600
LOGIN_MAX = 8


class Creds(BaseModel):
    email: str
    password: str


def _cookie(response: Response, raw: str) -> None:
    ttl = get_settings().SESSION_TTL_S
    response.set_cookie("session", raw, httponly=True, secure=False, samesite="lax", max_age=ttl, path="/")


@router.post("/api/auth/register")
async def register(body: Creds, response: Response) -> dict:
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 8:
        raise KitError(Codes.INVALID_INPUT, "email and 8+ char password required")
    store = get_store()
    if await store.users.by_email(email):
        raise KitError(Codes.CONFLICT, "email taken")
    try:
        u = await store.users.create(email, hash_password(body.password))
    except ConflictError:
        raise KitError(Codes.CONFLICT, "email taken")
    raw, digest = new_token()
    await store.sessions.create(digest, u["id"], time.time() + get_settings().SESSION_TTL_S)
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/login")
async def login(body: Creds, response: Response) -> dict:
    key = body.email.strip().lower()
    now = time.time()
    store = get_store()
    attempts = [t for t in await store.throttles.get_times(f"login:{key}") if now - t < LOGIN_WINDOW]
    if len(attempts) >= LOGIN_MAX:
        raise KitError(Codes.RATE_LIMITED, "too many attempts; slow down")
    u = await store.users.by_email(key)
    if not u or not verify_password(u["pw_hash"], body.password):
        attempts.append(now)
        await store.throttles.set_times(f"login:{key}", attempts)
        raise KitError(Codes.UNAUTHORIZED, "bad credentials")
    await store.throttles.set_times(f"login:{key}", [])
    raw, digest = new_token()
    await store.sessions.create(digest, u["id"], now + get_settings().SESSION_TTL_S)
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/logout")
async def logout(response: Response, session: Annotated[str | None, Cookie()] = None) -> dict:
    if session:
        await get_store().sessions.delete(hashlib.sha256(session.encode()).hexdigest())
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.get("/api/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"id": user["id"], "email": user["email"]}
