"""Repository behavioural contract suite — runs against every store backend.

The MongoDB run uses the composition's database (localhost:27017, override
with MONGODB_TEST_URI) and is skipped when unreachable.
"""
import os
import time
import uuid

import pytest
import pytest_asyncio

from app.persistence.errors import ConflictError
from app.persistence.repos_memory import MemoryStore


def _mongo_uri() -> str | None:
    uri = os.environ.get("MONGODB_TEST_URI", "mongodb://127.0.0.1:27017")
    try:
        import socket
        from urllib.parse import urlparse
        host = urlparse(uri).hostname or "127.0.0.1"
        port = urlparse(uri).port or 27017
        socket.create_connection((host, port), timeout=2).close()
        return uri
    except OSError:
        return None


@pytest_asyncio.fixture(params=["memory", "mongo"])
async def store(request):
    if request.param == "memory":
        yield MemoryStore()
        return
    uri = _mongo_uri()
    if uri is None:
        pytest.skip("mongodb not reachable")
    from app.persistence.repos_mongo import MongoStore

    mongo_store = MongoStore(uri, f"trao_contract_{uuid.uuid4().hex[:8]}")
    await mongo_store.startup()
    yield mongo_store
    for col in ("users", "sessions", "kits", "jobs", "practice", "page_cache", "throttles"):
        await mongo_store._db[col].delete_many({})
    await mongo_store.shutdown()


def _kit(uid, kid="k1", status="ready"):
    return {"id": kid, "user_id": uid, "dedupe_key": "d1", "status": status,
            "input": {}, "kit": None, "created_at": time.time()}


def _job(jid, kid, status="pending"):
    return {"id": jid, "kit_id": kid, "status": status, "steps": [],
            "attempts": 0, "heartbeat": time.time(), "error": None, "retryable": False}


async def test_users_create_and_lookup(store):
    u = await store.users.create("A@x.co", "hash")
    assert (await store.users.by_id(u["id"]))["email"] == "a@x.co"
    assert (await store.users.by_email("A@X.CO"))["id"] == u["id"]
    assert await store.users.by_email("nobody@x.co") is None
    with pytest.raises(ConflictError):
        await store.users.create("a@x.co", "other")


async def test_sessions_expiry_and_purge(store):
    now = time.time()
    await store.sessions.create("live", "u1", now + 3600)
    await store.sessions.create("dead", "u1", now - 1)
    assert (await store.sessions.get("live"))["user_id"] == "u1"
    assert await store.sessions.get("dead") is None
    assert await store.sessions.get("missing") is None
    await store.sessions.delete("live")
    assert await store.sessions.get("live") is None
    await store.sessions.create("dead2", "u1", now - 5)
    assert await store.sessions.purge_expired(now) >= 1


async def test_kits_ownership_and_dedupe(store):
    await store.kits.create(_kit("u1", "k1", "ready"))
    await store.kits.create(_kit("u1", "k2", "generating"))
    await store.kits.create(_kit("u2", "k3", "ready"))
    mine = await store.kits.list_for_user("u1")
    assert {k["id"] for k in mine} == {"k1", "k2"}
    assert await store.kits.get("k9") is None
    found = await store.kits.find_by_dedupe("u1", "d1", ("ready", "generating"))
    assert found is not None and found["user_id"] == "u1"
    assert await store.kits.find_by_dedupe("u2", "d1", ("generating",)) is None
    assert await store.kits.count_for_user("u1") == 2
    assert await store.kits.created_since("u1", time.time() - 60) == 2
    assert await store.kits.created_since("u1", time.time() + 60) == 0
    doc = await store.kits.get("k1")
    doc["status"] = "failed"
    await store.kits.save(doc)
    assert (await store.kits.get("k1"))["status"] == "failed"
    await store.kits.delete("k1")
    assert await store.kits.get("k1") is None


async def test_jobs_single_active_per_kit(store):
    await store.jobs.create_active(_job("j1", "k1", "pending"))
    with pytest.raises(ConflictError):
        await store.jobs.create_active(_job("j2", "k1", "running"))
    assert (await store.jobs.active_for_kit("k1"))["id"] == "j1"
    assert await store.jobs.running_count() == 0
    j = await store.jobs.get("j1")
    j["status"] = "running"
    await store.jobs.save(j)
    assert await store.jobs.running_count() == 1
    j["status"] = "done"
    await store.jobs.save(j)
    assert await store.jobs.active_for_kit("k1") is None
    await store.jobs.create_active(_job("j3", "k1", "pending"))
    assert (await store.jobs.active_for_kit("k1"))["id"] == "j3"
    assert len(await store.jobs.list_for_kit("k1")) == 2
    await store.jobs.delete_for_kit("k1")
    assert await store.jobs.list_for_kit("k1") == []


async def test_practice_reviews_and_kit_delete(store):
    assert await store.practice.reviews("k1:f1") == []
    await store.practice.append_review("k1:f1", {"confidence": 2, "at": 1.0})
    await store.practice.append_review("k1:f1", {"confidence": 3, "at": 2.0})
    reviews = await store.practice.reviews("k1:f1")
    assert [r["confidence"] for r in reviews] == [2, 3]
    await store.practice.delete_for_kit("k1")
    assert await store.practice.reviews("k1:f1") == []


async def test_page_cache_expiry(store):
    await store.page_cache.put("http://x.test/", {"text": "hi"})
    assert (await store.page_cache.get("http://x.test/"))["text"] == "hi"
    assert await store.page_cache.get("http://y.test/") is None
    assert await store.page_cache.purge_expired(time.time() + 10**6) >= 1
    assert await store.page_cache.get("http://x.test/") is None


async def test_page_cache_bound_memory_only():
    from app.persistence.repos_memory import MemoryPageCache
    cache = MemoryPageCache(maxsize=3, ttl_s=3600)
    for i in range(5):
        await cache.put(f"http://x.test/{i}", {"text": str(i)})
    assert await cache.get("http://x.test/0") is None
    assert await cache.get("http://x.test/4") is not None


async def test_throttle_times_roundtrip(store):
    assert await store.throttles.get_times("a@x") == []
    await store.throttles.set_times("a@x", [1.0, 2.0])
    assert await store.throttles.get_times("a@x") == [1.0, 2.0]
