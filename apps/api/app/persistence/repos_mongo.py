"""MongoDB repository implementations (motor). Used by the server when configured."""
from __future__ import annotations

import datetime
import time

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from .errors import ConflictError

ACTIVE_JOB_STATUSES = ("pending", "running")


def _dt(ts: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def _to_ts(value: object) -> float:
    """BSON datetimes come back naive (UTC); interpret them as UTC, never local."""
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.timestamp()
    return float(value)  # type: ignore[arg-type]


class MongoUsers:
    def __init__(self, db):
        self._col = db["users"]

    async def create(self, email: str, pw_hash: str) -> dict:
        import uuid
        email = email.lower()
        uid = uuid.uuid4().hex[:12]
        doc = {"_id": uid, "id": uid, "email": email, "pw_hash": pw_hash, "created_at": time.time()}
        try:
            await self._col.insert_one(doc)
        except DuplicateKeyError:
            raise ConflictError("email taken")
        return _out(doc)

    async def by_id(self, user_id: str) -> dict | None:
        doc = await self._col.find_one({"_id": user_id})
        return _out(doc) if doc else None

    async def by_email(self, email: str) -> dict | None:
        doc = await self._col.find_one({"email": email.lower()})
        return _out(doc) if doc else None


def _out(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


class MongoSessions:
    def __init__(self, db):
        self._col = db["sessions"]

    async def create(self, digest: str, user_id: str, expires_at: float) -> None:
        await self._col.replace_one(
            {"_id": digest},
            {"_id": digest, "user_id": user_id, "expires_at": _dt(expires_at)},
            upsert=True,
        )

    async def get(self, digest: str) -> dict | None:
        doc = await self._col.find_one({"_id": digest})
        if not doc:
            return None
        ts = _to_ts(doc["expires_at"])
        if ts < time.time():
            await self._col.delete_one({"_id": digest})
            return None
        return {"user_id": doc["user_id"], "expires_at": ts}

    async def delete(self, digest: str) -> None:
        await self._col.delete_one({"_id": digest})

    async def purge_expired(self, now: float) -> int:
        res = await self._col.delete_many({"expires_at": {"$lt": _dt(now)}})
        return res.deleted_count


class MongoKits:
    def __init__(self, db):
        self._col = db["kits"]

    async def create(self, doc: dict) -> None:
        await self._col.insert_one({**doc, "_id": doc["id"]})

    async def get(self, kit_id: str) -> dict | None:
        return _out(await self._col.find_one({"_id": kit_id}))

    async def list_for_user(self, user_id: str) -> list[dict]:
        return [_out(d) for d in await self._col.find({"user_id": user_id}).to_list(length=None)]

    async def save(self, doc: dict) -> None:
        await self._col.replace_one({"_id": doc["id"]}, {**doc, "_id": doc["id"]}, upsert=True)

    async def delete(self, kit_id: str) -> None:
        await self._col.delete_one({"_id": kit_id})

    async def find_by_dedupe(self, user_id: str, dedupe: str, statuses: tuple[str, ...]) -> dict | None:
        return _out(await self._col.find_one(
            {"user_id": user_id, "dedupe_key": dedupe, "status": {"$in": list(statuses)}}))

    async def count_for_user(self, user_id: str) -> int:
        return await self._col.count_documents({"user_id": user_id})

    async def created_since(self, user_id: str, since_ts: float) -> int:
        return await self._col.count_documents({"user_id": user_id, "created_at": {"$gte": since_ts}})


class MongoJobs:
    def __init__(self, db):
        self._col = db["jobs"]

    async def create(self, doc: dict) -> None:
        await self._col.insert_one({**doc, "_id": doc["id"]})

    async def create_active(self, doc: dict) -> None:
        try:
            await self._col.insert_one({**doc, "_id": doc["id"]})
        except DuplicateKeyError:
            raise ConflictError("active job exists for kit")

    async def get(self, job_id: str) -> dict | None:
        return _out(await self._col.find_one({"_id": job_id}))

    async def list_for_kit(self, kit_id: str) -> list[dict]:
        return [_out(d) for d in await self._col.find({"kit_id": kit_id}).to_list(length=None)]

    async def active_for_kit(self, kit_id: str) -> dict | None:
        return _out(await self._col.find_one(
            {"kit_id": kit_id, "status": {"$in": list(ACTIVE_JOB_STATUSES)}}))

    async def running_count(self) -> int:
        return await self._col.count_documents({"status": "running"})

    async def running_for_user(self, user_id: str) -> int:
        return await self._col.count_documents({"status": "running", "user_id": user_id})

    async def claim_next(self, exclude: tuple[str, ...] = ()) -> dict | None:
        import time as _time
        from pymongo import ReturnDocument
        filt: dict = {"status": "pending"}
        if exclude:
            filt["_id"] = {"$nin": list(exclude)}
        doc = await self._col.find_one_and_update(
            filt,
            {"$set": {"status": "running", "heartbeat": _time.time()}},
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        return _out(doc) if doc else None

    async def stale_running(self, before_ts: float) -> list[dict]:
        cur = self._col.find({"status": "running", "heartbeat": {"$lt": before_ts}})
        return [_out(d) for d in await cur.to_list(length=None)]

    async def save(self, doc: dict) -> None:
        await self._col.replace_one({"_id": doc["id"]}, {**doc, "_id": doc["id"]}, upsert=True)

    async def delete(self, job_id: str) -> None:
        await self._col.delete_one({"_id": job_id})

    async def delete_for_kit(self, kit_id: str) -> None:
        await self._col.delete_many({"kit_id": kit_id})


class MongoPractice:
    def __init__(self, db):
        self._col = db["practice"]

    async def reviews(self, key: str) -> list[dict]:
        doc = await self._col.find_one({"_id": key})
        return list((doc or {}).get("reviews", []))

    async def append_review(self, key: str, review: dict) -> None:
        await self._col.update_one({"_id": key}, {"$push": {"reviews": dict(review)}}, upsert=True)

    async def delete_for_kit(self, kit_id: str) -> None:
        await self._col.delete_many({"_id": {"$regex": f"^{kit_id}:"}})


class MongoPageCache:
    def __init__(self, db, maxsize: int = 500, ttl_s: float = 3600):
        self._col = db["page_cache"]
        self._maxsize = maxsize
        self._ttl = ttl_s

    async def get(self, url: str) -> dict | None:
        doc = await self._col.find_one({"_id": url})
        if not doc:
            return None
        exp = doc.get("expires_at")
        if exp is not None and _to_ts(exp) < time.time():
            await self._col.delete_one({"_id": url})
            return None
        return dict(doc.get("page", {}))

    async def put(self, url: str, page: dict) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        await self._col.replace_one(
            {"_id": url},
            {"_id": url, "page": dict(page), "stored_at": now,
             "expires_at": now + datetime.timedelta(seconds=self._ttl)},
            upsert=True,
        )
        count = await self._col.estimated_document_count()
        if count > self._maxsize:
            oldest = self._col.find({}).sort("stored_at", 1).limit(count - self._maxsize)
            async for doc in oldest:
                await self._col.delete_one({"_id": doc["_id"]})

    async def purge_expired(self, now: float) -> int:
        res = await self._col.delete_many({"expires_at": {"$lt": _dt(now)}})
        return res.deleted_count


class MongoThrottles:
    WINDOW_S = 3600.0

    def __init__(self, db):
        self._col = db["throttles"]

    async def get_times(self, key: str) -> list[float]:
        doc = await self._col.find_one({"_id": key})
        return list((doc or {}).get("times", []))

    async def set_times(self, key: str, times: list[float]) -> None:
        import datetime as _dt
        await self._col.replace_one(
            {"_id": key},
            {"_id": key, "times": list(times),
             "expires": _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=self.WINDOW_S)},
            upsert=True,
        )


async def ensure_indexes(db) -> None:
    from pymongo import ASCENDING
    await db["users"].create_index("email", unique=True)
    await db["sessions"].create_index("expires_at", expireAfterSeconds=0)
    await db["kits"].create_index("user_id")
    await db["jobs"].create_index(
        "kit_id", unique=True,
        partialFilterExpression={"status": {"$in": list(ACTIVE_JOB_STATUSES)}},
    )
    await db["jobs"].create_index("status")
    await db["practice"].create_index("reviews")
    await db["page_cache"].create_index("expires_at", expireAfterSeconds=0)
    await db["throttles"].create_index("expires", expireAfterSeconds=0)
    _ = ASCENDING


class MongoStore:
    """Durable store used by the server when MONGODB_URI is configured."""

    def __init__(self, uri: str, db_name: str = "trao", client=None):
        self._client = client or AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        self._own_client = client is None
        self._db = self._client[db_name]
        self.users = MongoUsers(self._db)
        self.sessions = MongoSessions(self._db)
        self.kits = MongoKits(self._db)
        self.jobs = MongoJobs(self._db)
        self.practice = MongoPractice(self._db)
        self.page_cache = MongoPageCache(self._db)
        self.throttles = MongoThrottles(self._db)

    @property
    def durable(self) -> bool:
        return True

    async def startup(self) -> None:
        await self._client.admin.command("ping")
        await ensure_indexes(self._db)

    async def shutdown(self) -> None:
        if self._own_client:
            self._client.close()
