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
from app.jobs.worker import drain_pending_jobs, server_deps
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


# Generation execution lives in app.jobs.worker (execute_generation); this
# router only enqueues pending jobs and kicks a dispatch burst. The lifespan
# worker loop performs recovery and steady-state dispatch.


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
    # one active job per kit; the worker loop enforces concurrency + per-user limits
    existing = await store.jobs.active_for_kit(kit_id)
    if existing:
        return {"kit_id": kit_id, "job_id": existing["id"], "duplicate": False}
    settings = get_settings()
    job = new_job(kit_id, user_id=user["id"], kind="generation",
                  deadline=time.time() + settings.OVERALL_TIMEOUT_S + 60)
    try:
        await store.jobs.create_active(job)
    except ConflictError:
        existing = await store.jobs.active_for_kit(kit_id)
        return {"kit_id": kit_id, "job_id": existing["id"] if existing else None, "duplicate": False}
    background.add_task(drain_pending_jobs)
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
    # strip all internal metadata — export exact Appendix A shape
    import copy
    out = copy.deepcopy(kit)
    out.pop("research_log", None)
    out.pop("warnings", None)
    out.pop("_brief_meta", None)
    for q in out.get("questions", []):
        q.pop("_meta", None)
        q.pop("outline_points", None) if False else None  # outline_points is allowed extension; keep? strip to be safe? keep.
    for f in out.get("flashcards", []):
        f.pop("_meta", None)
    for r in out.get("role", {}).get("requirements", []):
        r.pop("_meta", None)
        r.pop("evidence", None)
    errs = validate_kit({**out, "research_log": {}, "warnings": []} if "research_log" not in out else out)
    if errs:
        raise KitError(Codes.KIT_INVALID, f"kit does not validate for export: {errs[0]}")
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
        settings = get_settings()
        job = new_job(kit_id, user_id=user["id"], kind="generation",
                      deadline=time.time() + settings.OVERALL_TIMEOUT_S + 60)
        try:
            await store.jobs.create_active(job)
        except ConflictError:
            existing = await store.jobs.active_for_kit(kit_id)
            accepted.append({"id": eid, "kit_id": kit_id, "job_id": existing["id"] if existing else None})
            continue
        background.add_task(drain_pending_jobs)
        accepted.append({"id": eid, "kit_id": kit_id, "job_id": job["id"]})
    return {"accepted": accepted, "rejected": rejected}


@router.get("/api/health")
async def health() -> dict:
    return {"ok": True}
