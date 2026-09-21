"""Password hashing (Argon2id only) + opaque session tokens (sha256 stored).

There is deliberately no fallback scheme: a missing argon2 library fails
loudly at import rather than silently downgrading security. Hashing and
verification run off the request loop (callers use asyncio.to_thread) and
passwords are length-bounded at the API boundary.
"""
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher

_ph = PasswordHasher()


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(h: str, pw: str) -> bool:
    try:
        return _ph.verify(h, pw)
    except Exception:
        return False


def new_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, digest
