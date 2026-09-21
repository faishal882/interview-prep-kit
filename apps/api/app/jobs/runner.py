"""Job queue: in-process worker, atomic claim, heartbeat, requeue-once."""
from __future__ import annotations

import asyncio
import time
import uuid

from app.config import get_settings

STEPS = ["ingest", "extract_requirements", "crawl_company", "research_discussion",
         "analyze_hiring_signals", "write_brief", "generate_questions",
         "generate_flashcards", "build_schedule", "assemble_kit"]

STALE_AFTER = 30  # seconds without heartbeat -> stale


def new_job(kit_id: str, *, user_id: str = "", kind: str = "generation",
              deadline: float | None = None) -> dict:
    now = time.time()
    return {
        "id": uuid.uuid4().hex[:12],
        "kit_id": kit_id,
        "user_id": user_id,
        "kind": kind,
        "status": "pending",  # pending|running|done|failed
        "steps": [{"name": s, "status": "pending", "message": "", "started_at": None, "finished_at": None} for s in STEPS],
        "attempts": 0,
        "heartbeat": now,
        "created_at": now,
        "deadline": deadline if deadline is not None else now + 240.0,
        "error": None,
        "retryable": False,
    }


def active_job_for(kit_id: str, db) -> dict | None:
    for j in db.jobs.values():
        if j["kit_id"] == kit_id and j["status"] in ("pending", "running"):
            return j
    return None


def claim_stale(db) -> dict | None:
    """Requeue one stale running job (attempts+1); second stale -> fail retryable."""
    now = time.time()
    for j in db.jobs.values():
        if j["status"] == "running" and now - j.get("heartbeat", now) > STALE_AFTER:
            if j.get("attempts", 0) >= 1:
                j["status"] = "failed"
                j["error"] = {"code": "WORKER_LOST", "message": "worker lost; retryable"}
                j["retryable"] = True
            else:
                j["attempts"] = j.get("attempts", 0) + 1
                j["status"] = "pending"
                for s in j["steps"]:
                    if s["status"] == "running":
                        s["status"] = "pending"
            return j
    return None
