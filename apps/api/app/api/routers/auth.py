"""Auth router: login/logout/me with throttling, quotas and secure cookies.

Registration is closed by default (users are provisioned with the operator
command); setting REGISTRATION_OPEN=true reopens it explicitly.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import client_address, current_user
from app.api.schemas.responses import OkOut, UserOut
from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.persistence.errors import ConflictError
from app.persistence.store import get_store
from app.security.passwords import hash_password, new_token, verify_password

router = APIRouter()
LOGIN_WINDOW = 600
LOGIN_MAX = 8


class Creds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=320)
    password: str = Field(max_length=200)


def session_cookie(response: Response, raw: str, *, secure: bool) -> None:
    ttl = get_settings().SESSION_TTL_S
    response.set_cookie("session", raw, httponly=True, secure=secure,
                        samesite="lax", max_age=ttl, path="/")


def _cookie(response: Response, raw: str) -> None:
    session_cookie(response, raw, secure=get_settings().ENV == "production")


def _throttle_key(request: Request | None, account: str) -> str:
    return f"login:{client_address(request)}:{account}"


@router.post("/api/auth/register", response_model=UserOut)
async def register(body: Creds, response: Response) -> dict:
    if not get_settings().REGISTRATION_OPEN:
        raise KitError(Codes.FORBIDDEN, "registration is closed; ask an operator for an account")
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 8:
        raise KitError(Codes.INVALID_INPUT, "email and 8+ char password required")
    store = get_store()
    if await store.users.by_email(email):
        raise KitError(Codes.CONFLICT, "email taken")
    try:
        u = await store.users.create(email, await asyncio.to_thread(hash_password, body.password))
    except ConflictError:
        raise KitError(Codes.CONFLICT, "email taken")
    raw, digest = new_token()
    await store.sessions.create(digest, u["id"], time.time() + get_settings().SESSION_TTL_S)
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/login", response_model=UserOut)
async def login(body: Creds, response: Response, request: Request) -> dict:
    key = body.email.strip().lower()
    now = time.time()
    store = get_store()
    tkey = _throttle_key(request, key)
    attempts = [t for t in await store.throttles.get_times(tkey) if now - t < LOGIN_WINDOW]
    if len(attempts) >= LOGIN_MAX:
        raise KitError(Codes.RATE_LIMITED, "too many attempts; slow down")
    u = await store.users.by_email(key)
    if not u or not await asyncio.to_thread(verify_password, u["pw_hash"], body.password):
        attempts.append(now)
        await store.throttles.set_times(tkey, attempts)
        raise KitError(Codes.UNAUTHORIZED, "bad credentials")
    await store.throttles.set_times(tkey, [])
    raw, digest = new_token()
    await store.sessions.create(digest, u["id"], now + get_settings().SESSION_TTL_S)
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/logout", response_model=OkOut)
async def logout(response: Response, session: Annotated[str | None, Cookie()] = None) -> dict:
    if session:
        await get_store().sessions.delete(hashlib.sha256(session.encode()).hexdigest())
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.get("/api/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)) -> dict:
    return {"id": user["id"], "email": user["email"]}
