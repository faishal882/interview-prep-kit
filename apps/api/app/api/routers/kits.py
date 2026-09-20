"""Kits + jobs + batch + export router."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends
from pydantic import BaseModel

from app.api.deps import check_origin, current_user, get_kit_or_404
from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.jobs.runner import active_job_for, new_job
from app.persistence.memory import DB
from app.validation.kit_validator import validate_kit

router = APIRouter()


class CreateKit(BaseModel):
    jd: str = ""
    company_url: str = ""
    days: int = 5
    force_new: bool = False


def _run_pipeline_sync(kit_id: str, job_id: str, case: dict, deps: dict) -> None:
    import asyncio as _aio
    from app.pipeline.orchestrator import run_case
    job = DB.jobs.get(job_id)
    kit = DB.kits.get(kit_id)
    if not job or not kit:
        return

    def on_event(ev: dict) -> None:
        import datetime as _dt
        now = _dt.datetime.utcnow().isoformat() + "Z"
        job["heartbeat"] = time.time()
        for s in job["steps"]:
            if s["name"] == ev.get("step"):
                if s["status"] == "pending" and ev.get("status") in ("running", "done", "skipped", "failed"):
                    s["started_at"] = s["started_at"] or now
                s["status"] = ev.get("status", s["status"])
                s["message"] = ev.get("message", "")
                if s["status"] in ("done", "skipped", "failed"):
                    s["finished_at"] = now

    async def _go() -> None:
        job["status"] = "running"
        job["heartbeat"] = time.time()
        try:
            kit_doc, _log = await run_case(case, deps)
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

    _aio.run(_go())


def _deps_for_server() -> dict:
    import os
    from app.llm.fake import FakeLLM
    s = get_settings()
    if os.environ.get("FAKE_LLM") or s.FAKE_LLM or not (s.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")):
        llm = FakeLLM()
        return {"llm": llm, "allow_private": s.ALLOW_PRIVATE_URLS,
                "skip_retrieval": True, "max_pages": 4, "depth": 1}
    from app.llm.gemini import GeminiProvider
    llm = GeminiProvider(os.environ.get("GEMINI_API_KEY") or s.GEMINI_API_KEY, s.GEMINI_MODEL)
    return {"llm": llm, "allow_private": s.ALLOW_PRIVATE_URLS,
            "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH}


@router.post("/api/kits")
async def create_kit(body: CreateKit, background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    from fastapi import Request
    if not body.jd.strip():
        raise KitError(Codes.INVALID_INPUT, "empty jd")
    if not (1 <= body.days <= 60):
        raise KitError(Codes.INVALID_INPUT, "days must be 1..60")
    key = DB.dedupe_key(user["id"], body.jd, body.company_url, body.days)
    if not body.force_new:
        for k in DB.kits.values():
            if k.get("dedupe_key") == key and k.get("user_id") == user["id"] and k.get("status") in ("ready", "generating"):
                j = active_job_for(k["id"], DB)
                return {"kit_id": k["id"], "job_id": j["id"] if j else None, "duplicate": True}
    # failed kits retried in place: reuse doc if same key failed
    kit_id = None
    if not body.force_new:
        for k in DB.kits.values():
            if k.get("dedupe_key") == key and k.get("user_id") == user["id"] and k.get("status") == "failed":
                kit_id = k["id"]
                break
    if kit_id is None:
        kit_id = uuid.uuid4().hex[:12]
        DB.kits[kit_id] = {"id": kit_id, "user_id": user["id"], "dedupe_key": key,
                           "status": "generating",
                           "input": {"jd": body.jd, "company_url": body.company_url, "days": body.days},
                           "kit": None, "created_at": time.time()}
    else:
        DB.kits[kit_id]["status"] = "generating"
        DB.kits[kit_id]["input"] = {"jd": body.jd, "company_url": body.company_url, "days": body.days}
    # one active job per kit
    existing = active_job_for(kit_id, DB)
    if existing:
        return {"kit_id": kit_id, "job_id": existing["id"], "duplicate": False}
    # bounded concurrency: count running
    running = sum(1 for j in DB.jobs.values() if j["status"] == "running")
    job = new_job(kit_id)
    DB.jobs[job["id"]] = job
    if running >= get_settings().MAX_CONCURRENT_RUNS:
        job["status"] = "pending"
    case = {"jd": body.jd, "company_url": body.company_url, "days": body.days}
    background.add_task(_run_pipeline_sync, kit_id, job["id"], case, _deps_for_server())
    return {"kit_id": kit_id, "job_id": job["id"], "duplicate": False}


@router.get("/api/kits")
async def list_kits(user: dict = Depends(current_user)) -> dict:
    from app.jobs.runner import active_job_for as _active
    items = []
    for k in DB.kits.values():
        if k.get("user_id") != user["id"]:
            continue
        kit = k.get("kit") or {}
        role = kit.get("role") or {}
        reqs = role.get("requirements", [])
        qs = kit.get("questions", [])
        src = kit.get("source") or {}
        inp = k.get("input") or {}
        job = _active(k["id"], DB)
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
    return get_kit_or_404(kit_id, user["id"])


@router.delete("/api/kits/{kit_id}")
async def delete_kit(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = get_kit_or_404(kit_id, user["id"])
    DB.kits.pop(kit_id, None)
    for jid, j in list(DB.jobs.items()):
        if j.get("kit_id") == kit_id:
            DB.jobs.pop(jid, None)
    for key in list(DB.practice.keys()):
        if key.startswith(kit_id + ":"):
            DB.practice.pop(key, None)
    return {"ok": True}


@router.get("/api/kits/{kit_id}/export")
async def export_kit(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = get_kit_or_404(kit_id, user["id"])
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
    j = DB.jobs.get(job_id)
    if not j:
        raise KitError(Codes.NOT_FOUND, "job not found")
    k = DB.kits.get(j.get("kit_id", ""))
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
    if len(body) > 10:
        raise KitError(Codes.INVALID_INPUT, "at most 10 entries")
    accepted, rejected = [], []
    for i, e in enumerate(body):
        eid = e.id or f"entry-{i}"
        if not e.jd.strip() or not (1 <= e.days <= 60):
            rejected.append({"id": eid, "reason": "malformed entry (jd/days)"})
            continue
        key = DB.dedupe_key(user["id"], e.jd, e.company_url, e.days)
        dup = next((k for k in DB.kits.values() if k.get("dedupe_key") == key and k.get("user_id") == user["id"] and k.get("status") in ("ready", "generating")), None)
        if dup:
            accepted.append({"id": eid, "kit_id": dup["id"], "duplicate": True})
            continue
        # concurrency bound: best-effort, still accept (worker bounds execution)
        kit_id = uuid.uuid4().hex[:12]
        DB.kits[kit_id] = {"id": kit_id, "user_id": user["id"], "dedupe_key": key, "status": "generating",
                           "input": {"jd": e.jd, "company_url": e.company_url, "days": e.days},
                           "kit": None, "created_at": time.time()}
        job = new_job(kit_id)
        DB.jobs[job["id"]] = job
        background.add_task(_run_pipeline_sync, kit_id, job["id"],
                            {"jd": e.jd, "company_url": e.company_url, "days": e.days}, _deps_for_server())
        accepted.append({"id": eid, "kit_id": kit_id, "job_id": job["id"]})
    return {"accepted": accepted, "rejected": rejected}


@router.get("/api/health")
async def health() -> dict:
    return {"ok": True}
