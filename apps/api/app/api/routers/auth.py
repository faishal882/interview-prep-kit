"""Auth router: register/login/logout/me with throttling + secure cookies."""
from __future__ import annotations

import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from app.api.deps import current_user
from app.domain.errors import Codes, KitError
from app.persistence.memory import DB, SESSION_TTL
from app.security.passwords import hash_password, new_token, verify_password

router = APIRouter()
LOGIN_WINDOW = 600
LOGIN_MAX = 8


class Creds(BaseModel):
    email: str
    password: str


def _cookie(response: Response, raw: str) -> None:
    response.set_cookie("session", raw, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL, path="/")


@router.post("/api/auth/register")
async def register(body: Creds, response: Response) -> dict:
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 8:
        raise KitError(Codes.INVALID_INPUT, "email and 8+ char password required")
    if email in DB.users_by_email:
        raise KitError(Codes.CONFLICT, "email taken")
    u = DB.create_user(email, hash_password(body.password))
    raw, digest = new_token()
    DB.sessions[digest] = {"user_id": u["id"], "expires_at": time.time() + SESSION_TTL}
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/login")
async def login(body: Creds, response: Response) -> dict:
    key = body.email.strip().lower()
    now = time.time()
    DB.failed_logins.setdefault(key, [])
    DB.failed_logins[key] = [t for t in DB.failed_logins[key] if now - t < LOGIN_WINDOW]
    if len(DB.failed_logins[key]) >= LOGIN_MAX:
        raise KitError(Codes.RATE_LIMITED, "too many attempts; slow down")
    uid = DB.users_by_email.get(key)
    u = DB.users.get(uid or "")
    if not u or not verify_password(u["pw_hash"], body.password):
        DB.failed_logins[key].append(now)
        raise KitError(Codes.UNAUTHORIZED, "bad credentials")
    DB.failed_logins[key] = []
    raw, digest = new_token()
    DB.sessions[digest] = {"user_id": u["id"], "expires_at": now + SESSION_TTL}
    _cookie(response, raw)
    return {"id": u["id"], "email": u["email"]}


@router.post("/api/auth/logout")
async def logout(response: Response, session: Annotated[str | None, Cookie()] = None) -> dict:
    if session:
        DB.sessions.pop(hashlib.sha256(session.encode()).hexdigest(), None)
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.get("/api/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"id": user["id"], "email": user["email"]}
