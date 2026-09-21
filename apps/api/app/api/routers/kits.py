"""Kits + jobs + batch + export router."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.deps import current_user, get_kit_or_404
from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.jobs.runner import new_job
from app.persistence.errors import ConflictError
from app.persistence.repos_base import dedupe_key
from app.persistence.store import get_store
from app.validation.kit_validator import validate_kit

router = APIRouter()


class CreateKit(BaseModel):
    jd: str = ""
    company_url: str = ""
    days: int = 5
    force_new: bool = False


async def _run_pipeline_async(kit_id: str, job_id: str, case: dict, deps: dict) -> None:
    """Background generation on the server loop (shares it with the store)."""
    from app.pipeline.orchestrator import run_case

    store = get_store()
    job = await store.jobs.get(job_id)
    kit = await store.kits.get(kit_id)
    if not job or not kit:
        return

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
                _save_soon(store, job)

    job["status"] = "running"
    job["heartbeat"] = time.time()
    await store.jobs.save(job)
    try:
        kit_doc, _log = await run_case(case, deps, on_event=on_event)
        kit["kit"] = kit_doc
        kit["status"] = "ready"
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


def _save_soon(store, job) -> None:
    import asyncio as _aio

    async def _save() -> None:
        try:
            await store.jobs.save(job)
        except Exception:
            pass

    try:
        loop = _aio.get_running_loop()
    except RuntimeError:
        return
    try:
        loop.create_task(_save())
    except RuntimeError:
        pass  # loop closing; the final save still persists everything


def _deps_for_server() -> dict:
    import os
    s = get_settings()
    explicit_fake = os.environ.get("FAKE_LLM") or s.FAKE_LLM
    if explicit_fake:
        from app.llm.fake import FakeLLM
        llm = FakeLLM()
        return {"llm": llm, "allow_private": s.ALLOW_PRIVATE_URLS,
                "skip_retrieval": True, "max_pages": 4, "depth": 1,
                "step_timeout_s": s.STEP_TIMEOUT_S, "overall_timeout_s": s.OVERALL_TIMEOUT_S}
    key = os.environ.get("GEMINI_API_KEY") or s.GEMINI_API_KEY
    if not key:
        # never silently serve fake kits: fail fast without a model key
        raise KitError(Codes.MISSING_CREDENTIALS, "Missing GEMINI_API_KEY")
    from app.llm.gemini import GeminiProvider
    llm = GeminiProvider(key, s.GEMINI_MODEL)
    return {"llm": llm, "allow_private": s.ALLOW_PRIVATE_URLS,
            "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH,
            "step_timeout_s": s.STEP_TIMEOUT_S, "overall_timeout_s": s.OVERALL_TIMEOUT_S,
            "max_jd_chars": s.MAX_JD_CHARS}


@router.post("/api/kits")
async def create_kit(body: CreateKit, background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    if not body.jd.strip():
        raise KitError(Codes.INVALID_INPUT, "empty jd")
    if not (1 <= body.days <= 60):
        raise KitError(Codes.INVALID_INPUT, "days must be 1..60")
    store = get_store()
    key = dedupe_key(user["id"], body.jd, body.company_url, body.days)
    if not body.force_new:
        dup = await store.kits.find_by_dedupe(user["id"], key, ("ready", "generating"))
        if dup:
            j = await store.jobs.active_for_kit(dup["id"])
            return {"kit_id": dup["id"], "job_id": j["id"] if j else None, "duplicate": True}
    # failed kits retried in place: reuse doc if same key failed
    kit_id = None
    if not body.force_new:
        failed = await store.kits.find_by_dedupe(user["id"], key, ("failed",))
        if failed:
            kit_id = failed["id"]
    if kit_id is None:
        kit_id = uuid.uuid4().hex[:12]
        await store.kits.create({"id": kit_id, "user_id": user["id"], "dedupe_key": key,
                                 "status": "generating",
                                 "input": {"jd": body.jd, "company_url": body.company_url, "days": body.days},
                                 "kit": None, "created_at": time.time()})
    else:
        doc = await store.kits.get(kit_id)
        assert doc is not None
        doc["status"] = "generating"
        doc["input"] = {"jd": body.jd, "company_url": body.company_url, "days": body.days}
        await store.kits.save(doc)
    # one active job per kit
    existing = await store.jobs.active_for_kit(kit_id)
    if existing:
        return {"kit_id": kit_id, "job_id": existing["id"], "duplicate": False}
    # bounded concurrency: count running
    running = await store.jobs.running_count()
    job = new_job(kit_id)
    try:
        await store.jobs.create_active(job)
    except ConflictError:
        existing = await store.jobs.active_for_kit(kit_id)
        return {"kit_id": kit_id, "job_id": existing["id"] if existing else None, "duplicate": False}
    if running >= get_settings().MAX_CONCURRENT_RUNS:
        job["status"] = "pending"
        await store.jobs.save(job)
    case = {"jd": body.jd, "company_url": body.company_url, "days": body.days}
    background.add_task(_run_pipeline_async, kit_id, job["id"], case, _deps_for_server())
    return {"kit_id": kit_id, "job_id": job["id"], "duplicate": False}


@router.get("/api/kits")
async def list_kits(user: dict = Depends(current_user)) -> dict:
    store = get_store()
    items = []
    for k in await store.kits.list_for_user(user["id"]):
        kit = k.get("kit") or {}
        role = kit.get("role") or {}
        reqs = role.get("requirements", [])
        qs = kit.get("questions", [])
        src = kit.get("source") or {}
        inp = k.get("input") or {}
        job = await store.jobs.active_for_kit(k["id"])
        items.append({
            "id": k["id"], "status": k["status"],
            "company": src.get("company") or "",
            "role": role.get("title") or "",
            "days": (kit.get("schedule") or {}).get("days_available") or inp.get("days") or 0,
            "requirement_count": len(reqs), "question_count": len(qs),
            "updated_at": k.get("created_at"),
            "job_id": job["id"] if job else None,
        })
    return {"kits": items}


@router.get("/api/kits/{kit_id}")
async def get_kit(kit_id: str, user: dict = Depends(current_user)) -> dict:
    return await get_kit_or_404(kit_id, user["id"])


@router.delete("/api/kits/{kit_id}")
async def delete_kit(kit_id: str, user: dict = Depends(current_user)) -> dict:
    store = get_store()
    await get_kit_or_404(kit_id, user["id"])
    await store.kits.delete(kit_id)
    await store.jobs.delete_for_kit(kit_id)
    await store.practice.delete_for_kit(kit_id)
    return {"ok": True}


@router.get("/api/kits/{kit_id}/export")
async def export_kit(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    # strip item metadata (_meta) — export exact Appendix A shape
    import copy
    out = copy.deepcopy(kit)
    out.pop("research_log", None)
    out.pop("warnings", None)
    for q in out.get("questions", []):
        q.pop("_meta", None)
        q.pop("outline_points", None) if False else None  # outline_points is allowed extension; keep? strip to be safe? keep.
    for f in out.get("flashcards", []):
        f.pop("_meta", None)
    for r in out.get("role", {}).get("requirements", []):
        r.pop("_meta", None)
        r.pop("evidence", None)
    errs = validate_kit({**out, "research_log": {}, "warnings": []} if "research_log" not in out else out)
    return out


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(current_user)) -> dict:
    store = get_store()
    j = await store.jobs.get(job_id)
    if not j:
        raise KitError(Codes.NOT_FOUND, "job not found")
    k = await store.kits.get(j.get("kit_id", ""))
    if not k or k.get("user_id") != user["id"]:
        raise KitError(Codes.NOT_FOUND, "job not found")
    return j


class BatchEntry(BaseModel):
    jd: str = ""
    company_url: str = ""
    days: int = 5
    id: str = ""


@router.post("/api/kits/batch")
async def batch_upload(body: list[BatchEntry], background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    s = get_settings()
    if len(body) > s.MAX_BATCH_ENTRIES:
        raise KitError(Codes.INVALID_INPUT, f"at most {s.MAX_BATCH_ENTRIES} entries")
    store = get_store()
    accepted, rejected = [], []
    for i, e in enumerate(body):
        eid = e.id or f"entry-{i}"
        if not e.jd.strip() or not (1 <= e.days <= 60):
            rejected.append({"id": eid, "reason": "malformed entry (jd/days)"})
            continue
        key = dedupe_key(user["id"], e.jd, e.company_url, e.days)
        dup = await store.kits.find_by_dedupe(user["id"], key, ("ready", "generating"))
        if dup:
            accepted.append({"id": eid, "kit_id": dup["id"], "duplicate": True})
            continue
        # concurrency bound: best-effort, still accept (worker bounds execution)
        kit_id = uuid.uuid4().hex[:12]
        await store.kits.create({"id": kit_id, "user_id": user["id"], "dedupe_key": key, "status": "generating",
                                 "input": {"jd": e.jd, "company_url": e.company_url, "days": e.days},
                                 "kit": None, "created_at": time.time()})
        job = new_job(kit_id)
        await store.jobs.create(job)
        background.add_task(_run_pipeline_async, kit_id, job["id"],
                            {"jd": e.jd, "company_url": e.company_url, "days": e.days}, _deps_for_server())
        accepted.append({"id": eid, "kit_id": kit_id, "job_id": job["id"]})
    return {"accepted": accepted, "rejected": rejected}


@router.get("/api/health")
async def health() -> dict:
    return {"ok": True}
