"""Section regeneration as jobs: brief / one category / schedule."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import current_user, get_kit_or_404
from app.coverage.checker import compute_gaps
from app.domain.errors import Codes, KitError
from app.domain.merge import merge_category
from app.jobs.runner import new_job
from app.persistence.store import get_store

router = APIRouter()


@router.post("/api/kits/{kit_id}/sections/{section}/regenerate")
async def regenerate(kit_id: str, section: str, background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if section == "brief":
        meta = kit.get("_brief_meta", {})
        if meta.get("edited") or meta.get("pinned"):
            # proposal, not overwrite
            proposal = {"summary": (kit.get("company_brief") or {}).get("summary", "") + " (regenerated proposal)",
                        "status": "proposal"}
            k.setdefault("proposals", {})["brief"] = proposal
            await get_store().kits.save(k)
            return {"proposal": proposal}
        kit["company_brief"]["summary"] = (kit["company_brief"].get("summary") or "") + " (refreshed)"
        await get_store().kits.save(k)
        return {"ok": True}
    if section == "schedule":
        from app.scheduling.allocator import allocate
        reqs = kit["role"]["requirements"]
        days, _w = allocate(kit["questions"], reqs, kit["schedule"]["days_available"])
        kit["schedule"]["days"] = days
        k["schedule_stale"] = False
        await get_store().kits.save(k)
        return {"ok": True, "warning": "manual schedule edits were replaced"}
    if section.startswith("questions:"):
        category = section.split(":", 1)[1]
        # snapshot revs; generate replacements (fake: template questions for gaps in this category)
        snapshot = {q["id"]: q.get("_meta", {}).get("rev", 1) for q in kit["questions"]}
        reqs = kit["role"]["requirements"]
        gaps = compute_gaps([r["id"] for r in reqs], kit["questions"])
        fresh = []
        for i, gid in enumerate(gaps):
            fresh.append({"id": f"q-new-{uuid.uuid4().hex[:4]}", "requirement_ids": [gid],
                          "category": category, "prompt": f"Regenerated {category} question for {gid}",
                          "answer_outline": "Outline.", "difficulty": 2, "outline_points": [],
                          "_meta": {"origin": "generated", "edited": False, "pinned": False, "rev": 1, "order": "a9"}})
        current_cat = [q for q in kit["questions"] if q.get("category") == category]
        others = [q for q in kit["questions"] if q.get("category") != category]
        merged = merge_category(current_cat, fresh, snapshot)
        kit["questions"] = others + merged
        reqs_all = [r["id"] for r in reqs]
        kit.setdefault("coverage", {})["uncovered_requirement_ids"] = compute_gaps(reqs_all, kit["questions"])
        await get_store().kits.save(k)
        job = new_job(kit_id)
        job["status"] = "done"
        await get_store().jobs.create(job)
        return {"ok": True, "job_id": job["id"]}
    raise KitError(Codes.NOT_FOUND, "unknown section")


@router.post("/api/kits/{kit_id}/sections/brief/accept")
async def accept_brief(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    proposal = (k.get("proposals") or {}).get("brief")
    if not proposal:
        raise KitError(Codes.NOT_FOUND, "no proposal")
    kit["company_brief"]["summary"] = proposal.get("summary", "")
    kit.setdefault("_brief_meta", {"rev": 0})["rev"] += 1
    k["proposals"].pop("brief", None)
    await get_store().kits.save(k)
    return {"ok": True}


@router.post("/api/kits/{kit_id}/sections/brief/reject")
async def reject_brief(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    if not k.get("kit"):
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    (k.get("proposals") or {}).pop("brief", None)
    await get_store().kits.save(k)
    return {"ok": True}


@router.post("/api/kits/{kit_id}/requirements/{requirement_id}/generate")
async def generate_for_requirement(kit_id: str, requirement_id: str, user: dict = Depends(current_user)) -> dict:
    """Targeted generation: Questions for exactly one Requirement, nothing else touched."""
    from app.domain.item_meta import is_protected as _prot  # noqa: F401 (kept for clarity)
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    req = next((r for r in kit["role"]["requirements"] if r.get("id") == requirement_id), None)
    if not req:
        raise KitError(Codes.NOT_FOUND, "requirement not found")
    kind = req.get("kind", "technical")
    category = {"technical": "technical", "behavioural": "behavioural", "domain": "company-fit"}.get(kind, "technical")
    existing_prompts = {q.get("prompt") for q in kit["questions"]}
    prompt = f"Targeted {category} question for {requirement_id}: {req.get('text', '')[:80]}"
    if prompt in existing_prompts:
        prompt += " (follow-up)"
    item = {"id": f"q-new-{uuid.uuid4().hex[:4]}", "requirement_ids": [requirement_id],
            "category": category, "prompt": prompt,
            "answer_outline": "Outline.", "difficulty": 2, "outline_points": [],
            "_meta": {"origin": "generated", "edited": False, "pinned": False, "rev": 1, "order": "a9"}}
    kit["questions"].append(item)
    reqs_all = [r["id"] for r in kit["role"]["requirements"]]
    kit.setdefault("coverage", {})["uncovered_requirement_ids"] = compute_gaps(reqs_all, kit["questions"])
    await get_store().kits.save(k)
    job = new_job(kit_id)
    job["status"] = "done"
    await get_store().jobs.create(job)
    return {"ok": True, "job_id": job["id"], "question_id": item["id"]}


@router.patch("/api/kits/{kit_id}/schedule/days/{day}")
async def patch_schedule_day(kit_id: str, day: int, body: dict, user: dict = Depends(current_user)) -> dict:
    """Edit a day's focus text (manual Schedule edits preserved until rebuild)."""
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    days = (kit.get("schedule") or {}).get("days", [])
    target = next((d for d in days if d.get("day") == day), None)
    if not target:
        raise KitError(Codes.NOT_FOUND, "day not found")
    if "focus" in body:
        target["focus"] = str(body["focus"])
    if "question_ids" in body:
        valid = {q["id"] for q in kit.get("questions", [])}
        target["question_ids"] = [q for q in body["question_ids"] if q in valid]
    await get_store().kits.save(k)
    return target


@router.post("/api/kits/{kit_id}/schedule/move")
async def move_schedule_question(kit_id: str, body: dict, user: dict = Depends(current_user)) -> dict:
    """Move a Question to another day on the Schedule."""
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    qid, to_day = body.get("question_id"), body.get("to_day")
    days = (kit.get("schedule") or {}).get("days", [])
    if not any(d.get("day") == to_day for d in days):
        raise KitError(Codes.NOT_FOUND, "day not found")
    if not any(q.get("id") == qid for q in kit.get("questions", [])):
        raise KitError(Codes.NOT_FOUND, "question not found")
    for d in days:
        d["question_ids"] = [q for q in d.get("question_ids", []) if q != qid]
    target = next(d for d in days if d.get("day") == to_day)
    if qid not in target["question_ids"]:
        target["question_ids"].append(qid)
    await get_store().kits.save(k)
    return {"ok": True, "day": to_day}
