"""In-memory repository implementations (batch, CLI, tests)."""
from __future__ import annotations

import copy
import time
import uuid

from .errors import ConflictError

ACTIVE_JOB_STATUSES = ("pending", "running")


def _clone(doc: dict) -> dict:
    return copy.deepcopy(doc)


class MemoryUsers:
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._by_email: dict[str, str] = {}

    async def create(self, email: str, pw_hash: str) -> dict:
        email = email.lower()
        if email in self._by_email:
            raise ConflictError("email taken")
        uid = uuid.uuid4().hex[:12]
        u = {"id": uid, "email": email, "pw_hash": pw_hash, "created_at": time.time()}
        self._users[uid] = u
        self._by_email[email] = uid
        return _clone(u)

    async def by_id(self, user_id: str) -> dict | None:
        u = self._users.get(user_id)
        return _clone(u) if u else None

    async def by_email(self, email: str) -> dict | None:
        uid = self._by_email.get(email.lower())
        return await self.by_id(uid) if uid else None


class MemorySessions:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    async def create(self, digest: str, user_id: str, expires_at: float) -> None:
        self._sessions[digest] = {"user_id": user_id, "expires_at": expires_at}

    async def get(self, digest: str) -> dict | None:
        s = self._sessions.get(digest)
        if not s:
            return None
        if s["expires_at"] < time.time():
            self._sessions.pop(digest, None)
            return None
        return _clone(s)

    async def delete(self, digest: str) -> None:
        self._sessions.pop(digest, None)

    async def purge_expired(self, now: float) -> int:
        dead = [k for k, s in self._sessions.items() if s["expires_at"] < now]
        for k in dead:
            self._sessions.pop(k, None)
        return len(dead)


class MemoryKits:
    def __init__(self):
        self._kits: dict[str, dict] = {}

    async def create(self, doc: dict) -> None:
        self._kits[doc["id"]] = _clone(doc)

    async def get(self, kit_id: str) -> dict | None:
        k = self._kits.get(kit_id)
        return _clone(k) if k else None

    async def list_for_user(self, user_id: str) -> list[dict]:
        return [_clone(k) for k in self._kits.values() if k.get("user_id") == user_id]

    async def save(self, doc: dict) -> None:
        self._kits[doc["id"]] = _clone(doc)

    async def delete(self, kit_id: str) -> None:
        self._kits.pop(kit_id, None)

    async def find_by_dedupe(self, user_id: str, dedupe: str, statuses: tuple[str, ...]) -> dict | None:
        for k in self._kits.values():
            if k.get("dedupe_key") == dedupe and k.get("user_id") == user_id and k.get("status") in statuses:
                return _clone(k)
        return None

    async def count_for_user(self, user_id: str) -> int:
        return sum(1 for k in self._kits.values() if k.get("user_id") == user_id)

    async def created_since(self, user_id: str, since_ts: float) -> int:
        return sum(1 for k in self._kits.values()
                   if k.get("user_id") == user_id and k.get("created_at", 0) >= since_ts)


class MemoryJobs:
    def __init__(self):
        self._jobs: dict[str, dict] = {}

    async def create(self, doc: dict) -> None:
        self._jobs[doc["id"]] = _clone(doc)

    async def create_active(self, doc: dict) -> None:
        if await self.active_for_kit(doc["kit_id"]) is not None:
            raise ConflictError("active job exists for kit")
        await self.create(doc)

    async def get(self, job_id: str) -> dict | None:
        j = self._jobs.get(job_id)
        return _clone(j) if j else None

    async def list_for_kit(self, kit_id: str) -> list[dict]:
        return [_clone(j) for j in self._jobs.values() if j.get("kit_id") == kit_id]

    async def active_for_kit(self, kit_id: str) -> dict | None:
        for j in self._jobs.values():
            if j.get("kit_id") == kit_id and j.get("status") in ACTIVE_JOB_STATUSES:
                return _clone(j)
        return None

    async def running_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.get("status") == "running")

    async def save(self, doc: dict) -> None:
        self._jobs[doc["id"]] = _clone(doc)

    async def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def delete_for_kit(self, kit_id: str) -> None:
        for jid in [j for j, d in self._jobs.items() if d.get("kit_id") == kit_id]:
            self._jobs.pop(jid, None)


class MemoryPractice:
    def __init__(self):
        self._practice: dict[str, list[dict]] = {}

    async def reviews(self, key: str) -> list[dict]:
        import copy
        return copy.deepcopy(self._practice.get(key, []))

    async def append_review(self, key: str, review: dict) -> None:
        self._practice.setdefault(key, []).append(_clone(review))

    async def delete_for_kit(self, kit_id: str) -> None:
        for key in [k for k in self._practice if k.startswith(kit_id + ":")]:
            self._practice.pop(key, None)


class MemoryPageCache:
    def __init__(self, maxsize: int = 500, ttl_s: float = 3600):
        self._data: dict[str, tuple[dict, float]] = {}
        self._maxsize = maxsize
        self._ttl = ttl_s

    async def get(self, url: str) -> dict | None:
        hit = self._data.get(url)
        if hit is None:
            return None
        page, at = hit
        if time.time() - at > self._ttl:
            self._data.pop(url, None)
            return None
        return _clone(page)

    async def put(self, url: str, page: dict) -> None:
        self._data[url] = (_clone(page), time.time())
        while len(self._data) > self._maxsize:
            self._data.pop(next(iter(self._data)))

    async def purge_expired(self, now: float) -> int:
        dead = [k for k, (_, at) in self._data.items() if now - at > self._ttl]
        for k in dead:
            self._data.pop(k, None)
        return len(dead)


class MemoryThrottles:
    def __init__(self):
        self._times: dict[str, list[float]] = {}

    async def get_times(self, key: str) -> list[float]:
        return list(self._times.get(key, []))

    async def set_times(self, key: str, times: list[float]) -> None:
        self._times[key] = list(times)


class MemoryStore:
    """Full in-memory store (batch, CLI, tests). Not durable."""

    def __init__(self):
        self.users = MemoryUsers()
        self.sessions = MemorySessions()
        self.kits = MemoryKits()
        self.jobs = MemoryJobs()
        self.practice = MemoryPractice()
        self.page_cache = MemoryPageCache()
        self.throttles = MemoryThrottles()

    @property
    def jobs_raw(self) -> dict:
        """Raw job mapping for the legacy runner shim (phase 8 removes it)."""
        return self.jobs._jobs

    @property
    def durable(self) -> bool:
        return False

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None
