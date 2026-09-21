"""Section regeneration as real jobs; schedule rebuild stays synchronous."""
from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import current_user, get_kit_or_404
from app.api.schemas.items import ScheduleDayPatch, ScheduleMove
from app.config import get_settings
from app.domain.errors import Codes, KitError
from app.persistence.store import get_store
from app.scheduling.allocator import day_minutes

router = APIRouter()


@router.post("/api/kits/{kit_id}/sections/{section}/regenerate")
async def regenerate(kit_id: str, section: str, background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    from app.jobs.runner import new_job
    from app.jobs.worker import drain_pending_jobs
    from app.persistence.errors import ConflictError
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if section == "brief":
        kind, steps = "sections:brief", ["regenerate:brief"]
    elif section == "schedule":
        from app.scheduling.allocator import allocate
        reqs = kit["role"]["requirements"]
        days, _w = allocate(kit["questions"], reqs, kit["schedule"]["days_available"])
        kit["schedule"]["days"] = days
        k["schedule_stale"] = False
        await get_store().kits.save(k)
        return {"ok": True, "warning": "manual schedule edits were replaced"}
    elif section.startswith("questions:"):
        category = section.split(":", 1)[1]
        if category not in ("technical", "behavioural", "system-design", "company-fit"):
            raise KitError(Codes.NOT_FOUND, "unknown section")
        kind, steps = f"sections:questions:{category}", [f"regenerate:{category}"]
    else:
        raise KitError(Codes.NOT_FOUND, "unknown section")
    store = get_store()
    if await store.jobs.active_for_kit(kit_id):
        raise KitError(Codes.CONFLICT, "a job is already running for this kit")
    job = new_job(kit_id, user_id=user["id"], kind=kind,
                  deadline=time.time() + get_settings().OVERALL_TIMEOUT_S + 60, steps=steps)
    try:
        await store.jobs.create_active(job)
    except ConflictError:
        raise KitError(Codes.CONFLICT, "a job is already running for this kit")
    background.add_task(drain_pending_jobs)
    return {"job_id": job["id"]}


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
async def generate_for_requirement(kit_id: str, requirement_id: str, background: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    """Targeted generation: a real job producing Questions for exactly one Requirement."""
    from app.jobs.runner import new_job
    from app.jobs.worker import drain_pending_jobs
    from app.persistence.errors import ConflictError
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    req = next((r for r in kit["role"]["requirements"] if r.get("id") == requirement_id), None)
    if not req:
        raise KitError(Codes.NOT_FOUND, "requirement not found")
    store = get_store()
    if await store.jobs.active_for_kit(kit_id):
        raise KitError(Codes.CONFLICT, "a job is already running for this kit")
    job = new_job(kit_id, user_id=user["id"], kind=f"requirements:{requirement_id}",
                  deadline=time.time() + get_settings().OVERALL_TIMEOUT_S + 60,
                  steps=[f"generate:{requirement_id}"])
    try:
        await store.jobs.create_active(job)
    except ConflictError:
        raise KitError(Codes.CONFLICT, "a job is already running for this kit")
    background.add_task(drain_pending_jobs)
    return {"job_id": job["id"]}


@router.patch("/api/kits/{kit_id}/schedule/days/{day}")
async def patch_schedule_day(kit_id: str, day: int, body: dict, user: dict = Depends(current_user)) -> dict:
    """Edit a day's focus text (manual Schedule edits preserved until rebuild)."""
    data = ScheduleDayPatch(**body)
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    days = (kit.get("schedule") or {}).get("days", [])
    target = next((d for d in days if d.get("day") == day), None)
    if not target:
        raise KitError(Codes.NOT_FOUND, "day not found")
    if data.focus is not None:
        target["focus"] = data.focus
    if data.question_ids is not None:
        valid = {q["id"] for q in kit.get("questions", [])}
        for qid in data.question_ids:
            if qid not in valid:
                raise KitError(Codes.INVALID_INPUT, f"unknown question reference: {qid}")
        target["question_ids"] = list(data.question_ids)
        target["minutes"] = day_minutes(target["question_ids"], kit.get("questions", []))
    await get_store().kits.save(k)
    return target


@router.post("/api/kits/{kit_id}/schedule/move")
async def move_schedule_question(kit_id: str, body: dict, user: dict = Depends(current_user)) -> dict:
    """Move a Question to another day on the Schedule."""
    data = ScheduleMove(**body)
    qid, to_day = data.question_id, data.to_day
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
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
    for d in days:
        d["minutes"] = day_minutes(d.get("question_ids", []), kit.get("questions", []))
    await get_store().kits.save(k)
    return {"ok": True, "day": to_day}
