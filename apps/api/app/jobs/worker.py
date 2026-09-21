"""Durable job queue worker: atomic claim, enforced concurrency, deadlines,
per-user limits and continuous stale recovery (single instance).

Regeneration Sections run as jobs of their own kind through the same loop;
each kind has a registered executor (generation is built in, regeneration
Sections register in phase 10).
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from app.config import get_settings
from app.domain.errors import Codes, KitError

STALE_AFTER_S = 30.0

Executor = Callable[[dict], Awaitable[None]]
_EXECUTORS: dict[str, Executor] = {}


def register_executor(kind: str, fn: Executor) -> None:
    _EXECUTORS[kind] = fn


def server_deps() -> dict:
    """Generation dependencies for the server (fail fast, never silent fake)."""
    import os
    s = get_settings()
    explicit_fake = os.environ.get("FAKE_LLM") or s.FAKE_LLM
    base = {"allow_private": s.ALLOW_PRIVATE_URLS,
            "step_timeout_s": s.STEP_TIMEOUT_S, "overall_timeout_s": s.OVERALL_TIMEOUT_S,
            "max_jd_chars": s.MAX_JD_CHARS}
    if explicit_fake:
        from app.llm.fake import FakeLLM
        from app.persistence.store import get_store as _store
        return {"llm": FakeLLM(), "skip_retrieval": True, "max_pages": 4, "depth": 1,
                "page_cache": _store().page_cache, **base}
    key = os.environ.get("GEMINI_API_KEY") or s.GEMINI_API_KEY
    if not key:
        raise KitError(Codes.MISSING_CREDENTIALS, "Missing GEMINI_API_KEY")
    from app.llm.gemini import GeminiProvider
    from app.persistence.store import get_store as _store
    return {"llm": GeminiProvider(key, s.GEMINI_MODEL),
            "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH,
            "page_cache": _store().page_cache, **base}


async def execute_generation(job: dict, store) -> None:
    """Run a generation job to a terminal state, persisting progress."""
    from app.pipeline.orchestrator import run_case

    kit = await store.kits.get(job["kit_id"])
    if kit is None:
        job["status"] = "failed"
        job["error"] = {"code": Codes.NOT_FOUND, "message": "kit gone"}
        job["retryable"] = False
        await store.jobs.save(job)
        return
    case = kit.get("input") or {}

    def on_event(ev: dict) -> None:
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        job["heartbeat"] = time.time()
        for s in job["steps"]:
            if s["name"] == ev.get("step"):
                if s["status"] == "pending" and ev.get("status") in ("running", "done", "skipped", "failed"):
                    s["started_at"] = s["started_at"] or now
                s["status"] = ev.get("status", s["status"])
                s["message"] = ev.get("message", "")
                if s["status"] in ("done", "skipped", "failed"):
                    s["finished_at"] = now
        _schedule_save(store, job)

    deps = server_deps()
    try:
        kit_doc, _log = await run_case(case, deps, on_event=on_event)
        kit["kit"] = kit_doc
        kit["status"] = "ready"
        kit.pop("error", None)
        job["status"] = "done"
        for s in job["steps"]:
            if s["status"] in ("pending", "running"):
                s["status"] = "skipped"
                s["message"] = s["message"] or "skipped"
    except KitError as ke:
        kit["status"] = "failed"
        kit["error"] = {"code": ke.code, "message": ke.message}
        job["status"] = "failed"
        job["error"] = {"code": ke.code, "message": ke.message}
        job["retryable"] = True
    except Exception as exc:
        kit["status"] = "failed"
        kit["error"] = {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}
        job["status"] = "failed"
        job["error"] = {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}
        job["retryable"] = True
    await store.jobs.save(job)
    await store.kits.save(kit)


def _schedule_save(store, job) -> None:
    async def _save() -> None:
        try:
            await store.jobs.save(job)
        except Exception:
            pass

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    try:
        loop.create_task(_save())
    except RuntimeError:
        pass


async def execute_job(job: dict, store) -> None:
    kind = job.get("kind", "generation")
    fn = _EXECUTORS.get(kind)
    if fn is None and kind.startswith("requirements:"):
        fn = _make_regen(kind, kind.split(":", 1)[1])
    if fn is None:
        job["status"] = "failed"
        job["error"] = {"code": Codes.INVALID_INPUT, "message": f"unknown job kind {job.get('kind')}"}
        job["retryable"] = False
        await store.jobs.save(job)
        return
    await fn(job, store)


def _make_regen(kind: str, section: str):
    async def run(job: dict, store) -> None:
        import datetime as _dt

        def on_event(ev: dict) -> None:
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            job["heartbeat"] = time.time()
            for s in job.get("steps", []):
                s["status"] = ev.get("status", s["status"])
                s["message"] = ev.get("message", "")
                if s["status"] in ("done", "failed"):
                    s["finished_at"] = now
                elif s["status"] == "running" and not s.get("started_at"):
                    s["started_at"] = now
            _schedule_save(store, job)

        from app.config import get_settings
        from app.regen import service as regen_service
        settings = get_settings()
        deps = {**server_deps(), "step_timeout_s": settings.STEP_TIMEOUT_S,
                "overall_timeout_s": settings.OVERALL_TIMEOUT_S}
        try:
            if kind == "sections:brief":
                await regen_service.regenerate_brief(store, job["kit_id"], deps, on_event)
            elif kind.startswith("sections:questions:"):
                await regen_service.regenerate_category(store, job["kit_id"], section, deps, on_event)
            elif kind.startswith("requirements:"):
                req_id = kind.split(":", 1)[1]
                await regen_service.generate_for_requirement(store, job["kit_id"], req_id, deps, on_event)
            else:
                raise KitError(Codes.INVALID_INPUT, f"unknown regeneration {kind}")
            job["status"] = "done"
            for s in job.get("steps", []):
                if s.get("status") in ("pending", "running"):
                    s["status"] = "done"
                    s["finished_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        except KitError as ke:
            job["status"] = "failed"
            job["error"] = {"code": ke.code, "message": ke.message}
            job["retryable"] = True
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}
            job["retryable"] = True
        await store.jobs.save(job)

    return run


register_executor("sections:brief", _make_regen("sections:brief", "brief"))
for _cat in ("technical", "behavioural", "system-design", "company-fit"):
    register_executor(f"sections:questions:{_cat}", _make_regen(f"sections:questions:{_cat}", _cat))


register_executor("generation", execute_generation)


class Worker:
    """Single-instance worker: recover stale jobs, dispatch within limits."""

    def __init__(self, store, execute: Executor | None = None, *,
                 concurrency: int = 2, per_user: int = 1,
                 poll_interval: float = 1.0, stale_after: float = STALE_AFTER_S):
        self.store = store
        self.execute = execute or (lambda job: execute_job(job, store))
        self.concurrency = concurrency
        self.per_user = per_user
        self.poll_interval = poll_interval
        self.stale_after = stale_after
        self._tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._stopping = False

    async def run_forever(self) -> None:
        while not self._stopping:
            try:
                await self.recover()
                await self.dispatch_once()
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._stopping = True
        for t in self._tasks:
            t.cancel()

    def running_tasks(self) -> int:
        self._tasks = {t for t in self._tasks if not t.done()}
        return len(self._tasks)

    async def recover(self) -> None:
        """Requeue a stale job once, then fail it retryable. Runs continuously."""
        async with self._lock:
            now = time.time()
            for job in await self.store.jobs.stale_running(now - self.stale_after):
                if job.get("attempts", 0) >= 1:
                    job["status"] = "failed"
                    job["error"] = {"code": "WORKER_LOST", "message": "worker lost; retryable"}
                    job["retryable"] = True
                else:
                    job["attempts"] = job.get("attempts", 0) + 1
                    job["status"] = "pending"
                    for s in job.get("steps", []):
                        if s.get("status") == "running":
                            s["status"] = "pending"
                await self.store.jobs.save(job)

    async def dispatch_once(self) -> None:
        deferred: list[str] = []
        async with self._lock:
            while self.running_tasks() < self.concurrency:
                job = await self.store.jobs.claim_next(tuple(deferred))
                if job is None:
                    return
                user_running = await self.store.jobs.running_for_user(job.get("user_id", ""))
                if job.get("user_id") and user_running > self.per_user:
                    # over the per-user budget: leave queued, try the next job
                    job["status"] = "pending"
                    await self.store.jobs.save(job)
                    deferred.append(job["id"])
                    continue
                task = asyncio.create_task(self._run_guarded(job))
                self._tasks.add(task)

    async def _run_guarded(self, job: dict) -> None:
        remaining = max(1.0, float(job.get("deadline", 0) or 0) - time.time())
        try:
            await asyncio.wait_for(self.execute(job), timeout=remaining)
        except asyncio.TimeoutError:
            job["status"] = "failed"
            job["error"] = {"code": Codes.TIMEOUT, "message": "job deadline exceeded"}
            job["retryable"] = True
            await self.store.jobs.save(job)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}
            job["retryable"] = True
            try:
                await self.store.jobs.save(job)
            except Exception:
                pass


async def drain_pending_jobs(store=None, execute=None, concurrency: int = 2, per_user: int = 1) -> None:
    """One dispatch burst (request path fallback when the loop is not running)."""
    from app.persistence.store import get_store
    s = store or get_store()
    settings = get_settings()
    worker = Worker(s, execute, concurrency=concurrency, per_user=per_user)
    await worker.dispatch_once()
    if worker._tasks:
        await asyncio.gather(*worker._tasks, return_exceptions=True)
