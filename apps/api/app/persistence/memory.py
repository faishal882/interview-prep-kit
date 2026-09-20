"""In-memory stores (used by CLI/tests; Mongo repos mirror the interface)."""
from __future__ import annotations

import hashlib
import time
import uuid

SESSION_TTL = 7 * 24 * 3600


class MemoryDB:
    def __init__(self):
        self.users: dict[str, dict] = {}  # id -> user
        self.users_by_email: dict[str, str] = {}
        self.sessions: dict[str, dict] = {}  # digest -> session
        self.kits: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.practice: dict[str, list[dict]] = {}  # card_key -> reviews
        self.failed_logins: dict[str, list[float]] = {}

    # users
    def create_user(self, email: str, pw_hash: str) -> dict:
        uid = uuid.uuid4().hex[:12]
        u = {"id": uid, "email": email.lower(), "pw_hash": pw_hash, "created_at": time.time()}
        self.users[uid] = u
        self.users_by_email[u["email"]] = uid
        return u

    # dedupe
    @staticmethod
    def dedupe_key(user_id: str, jd: str, url: str, days: int) -> str:
        norm = lambda s: " ".join(str(s or "").lower().split())
        return hashlib.sha256(f"{user_id}|{norm(jd)}|{norm(url)}|{days}".encode()).hexdigest()


DB = MemoryDB()
