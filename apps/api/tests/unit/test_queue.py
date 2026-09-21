"""Phase 8: durable queue — concurrency, stale recovery, deadlines, per-user limits."""
import asyncio
import time
import uuid

import pytest
import pytest_asyncio

from app.jobs import worker as worker_mod
from app.jobs.runner import new_job
from app.jobs.worker import Worker
from app.persistence.repos_memory import MemoryStore

pytestmark = pytest.mark.asyncio


def _mongo_uri():
    import os
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
    mongo_store = MongoStore(uri, f"trao_queue_{uuid.uuid4().hex[:8]}")
    await mongo_store.startup()
    yield mongo_store
    for col in ("users", "sessions", "kits", "jobs", "practice", "page_cache", "throttles"):
        await mongo_store._db[col].delete_many({})
    await mongo_store.shutdown()


def _job(kit, user="u1", status="pending"):
    return {**new_job(kit, user_id=user), "status": status}


async def test_concurrency_limit_enforced(store):
    seen = []
    active = 0
    peak = 0

    async def execute(job):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        seen.append(job["id"])
        await asyncio.sleep(0.05)
        active -= 1
        job["status"] = "done"
        await store.jobs.save(job)

    for i in range(3):
        await store.jobs.create_active(_job(f"k{i}"))
    worker = Worker(store, execute, concurrency=2, per_user=10, poll_interval=0.01)
    task = asyncio.create_task(worker.run_forever())
    for _ in range(100):
        await asyncio.sleep(0.02)
        done = 0
        for i in range(3):
            jobs = await store.jobs.list_for_kit(f"k{i}")
            if jobs and jobs[0]["status"] == "done":
                done += 1
        if done == 3:
            break
    worker.stop()
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    assert len(seen) == 3
    assert peak == 2


async def test_stale_requeued_once_then_retryable(store):
    old = time.time() - 100
    job = _job("k9")
    job["status"] = "running"
    job["heartbeat"] = old
    job["steps"] = [{"name": "ingest", "status": "running", "message": ""}]
    await store.jobs.create(job)
    worker = Worker(store, None, stale_after=30)
    await worker.recover()
    j = await store.jobs.get(job["id"])
    assert j["status"] == "pending" and j["attempts"] == 1
    assert j["steps"][0]["status"] == "pending"
    j["status"] = "running"
    j["heartbeat"] = old
    await store.jobs.save(j)
    await worker.recover()
    j = await store.jobs.get(job["id"])
    assert j["status"] == "failed" and j["retryable"] is True
    assert j["error"]["code"] == "WORKER_LOST"


async def test_hung_job_stopped_by_deadline(store):
    async def hang(job):
        await asyncio.sleep(30)

    job = _job("kd")
    job["deadline"] = time.time() + 0.2
    await store.jobs.create_active(job)
    worker = Worker(store, hang, concurrency=1, per_user=10, poll_interval=0.01)
    await worker.dispatch_once()
    if worker._tasks:
        await asyncio.gather(*worker._tasks, return_exceptions=True)
    j = await store.jobs.get(job["id"])
    assert j["status"] == "failed" and j["error"]["code"] == "TIMEOUT" and j["retryable"] is True


async def test_double_trigger_yields_one_active_job(store):
    from app.persistence.errors import ConflictError
    await store.jobs.create_active(_job("kq"))
    with pytest.raises(ConflictError):
        await store.jobs.create_active(_job("kq"))
    assert await store.jobs.active_for_kit("kq") is not None


async def test_per_user_limit_queues_second_generation(store):
    ran = []

    async def execute(job):
        ran.append(job["kit_id"])
        job["status"] = "done"
        await store.jobs.save(job)

    running = _job("ka", user="alice", status="running")
    await store.jobs.create(running)
    await store.jobs.create_active(_job("kb", user="alice"))
    await store.jobs.create_active(_job("kc", user="bob"))
    worker = Worker(store, execute, concurrency=2, per_user=1, poll_interval=0.01)
    await worker.dispatch_once()
    if worker._tasks:
        await asyncio.gather(*worker._tasks, return_exceptions=True)
    assert "kc" in ran and "kb" not in ran
    pending = await store.jobs.get((await store.jobs.list_for_kit("kb"))[0]["id"])
    assert pending["status"] == "pending"


async def test_retry_reuses_cached_pages():
    from app.persistence.repos_memory import MemoryPageCache
    from app.retrieval.crawler import crawl

    cache = MemoryPageCache()
    page = {"url": "http://site.test/", "final_url": "http://site.test/",
            "text": "hello", "links": [], "title": "Site", "site_name": "Site"}
    await cache.put("http://site.test/", page)

    def explode(request):
        raise AssertionError("network must not be hit on a cache retry")

    import httpx
    transport = httpx.MockTransport(explode)
    async with httpx.AsyncClient(transport=transport) as client:
        pages, _ = await crawl("http://site.test/", budget=2, depth=0,
                               allow_private=True, client=client, cache=cache)
    assert len(pages) == 1 and pages[0]["text"] == "hello"


async def test_generation_kinds_registered():
    assert "generation" in worker_mod._EXECUTORS
