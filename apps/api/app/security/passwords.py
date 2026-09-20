"""Password hashing (argon2id) + opaque session tokens (sha256 stored)."""
from __future__ import annotations

import hashlib
import secrets

try:
    from argon2 import PasswordHasher
    _ph = PasswordHasher()

    def hash_password(pw: str) -> str:
        return _ph.hash(pw)

    def verify_password(h: str, pw: str) -> bool:
        try:
            return _ph.verify(h, pw)
        except Exception:
            return False
except ImportError:  # fallback for minimal envs
    def hash_password(pw: str) -> str:
        import os
        salt = os.urandom(16).hex()
        return "pbkdf2$" + salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 100000).hex()

    def verify_password(h: str, pw: str) -> bool:
        try:
            _, salt, digest = h.split("$")
            return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 100000).hex() == digest
        except Exception:
            return False


def new_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, digest
