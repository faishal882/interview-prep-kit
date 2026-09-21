"""Item editing: typed schemas, server ids, revision enforcement, integrity."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import current_user, get_kit_or_404
from app.api.schemas.items import (
    BriefPatch,
    FlashcardCreate,
    FlashcardPatch,
    QuestionCreate,
    QuestionPatch,
    ReorderBodyStrict,
    RequirementCreate,
    RequirementPatch,
)
from app.coverage.checker import compute_gaps
from app.domain.errors import Codes, KitError
from app.domain.ordering import FIRST_KEY, key_between, needs_rebalance, rebalance
from app.persistence.store import get_store
from app.scheduling.allocator import day_minutes

router = APIRouter()


def _meta_new(origin: str) -> dict:
    return {"origin": origin, "edited": False, "pinned": False, "rev": 1, "order": "a0", "gen_run": None}


def _brief_meta() -> dict:
    return {"origin": "generated", "edited": False, "pinned": False, "rev": 0}


def _recompute(kit_doc: dict, *, schedule_affecting: bool) -> None:
    kit = kit_doc.get("kit") or {}
    reqs = (kit.get("role") or {}).get("requirements", [])
    gaps = compute_gaps([r["id"] for r in reqs], kit.get("questions", []))
    kit.setdefault("coverage", {})["uncovered_requirement_ids"] = gaps
    if schedule_affecting:
        kit_doc["schedule_stale"] = True


def _req_ids(kit: dict) -> set[str]:
    return {r["id"] for r in (kit.get("role") or {}).get("requirements", [])}


def _check_refs(rids: list[str], valid: set[str]) -> None:
    for rid in rids:
        if rid not in valid:
            raise KitError(Codes.INVALID_INPUT, f"unknown requirement reference: {rid}")


def _strip_refs(kit: dict, rid: str) -> list[str]:
    """Remove a deleted requirement everywhere; return questions left uncovered."""
    for q in kit.get("questions", []):
        q["requirement_ids"] = [r for r in q.get("requirement_ids", []) if r != rid]
    for f in kit.get("flashcards", []):
        f["requirement_ids"] = [r for r in (f.get("requirement_ids") or []) if r != rid]
    return [q["id"] for q in kit.get("questions", []) if not q.get("requirement_ids")]


def _fix_minutes(kit: dict) -> None:
    for day in (kit.get("schedule") or {}).get("days", []):
        day["minutes"] = day_minutes(day.get("question_ids", []), kit.get("questions", []))


@router.post("/api/kits/{kit_id}/{collection}")
async def create_item(kit_id: str, collection: str, body: dict, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if collection == "brief":
        raise KitError(Codes.INVALID_INPUT, "use patch for brief")
    if collection == "schedule":
        raise KitError(Codes.INVALID_INPUT, "use schedule endpoints")
    if collection == "questions":
        data = QuestionCreate(**body)
        _check_refs(data.requirement_ids, _req_ids(kit))
        item = {"id": f"q{uuid.uuid4().hex[:6]}", **data.model_dump(), "_meta": _meta_new("user")}
        existing = kit["questions"]
        last = existing[-1].get("_meta", {}).get("order") if existing else None
        item["_meta"]["order"] = key_between(last, None)
        kit["questions"].append(item)
        _recompute(k, schedule_affecting=True)
    elif collection == "flashcards":
        data = FlashcardCreate(**body)
        _check_refs(data.requirement_ids, _req_ids(kit))
        item = {"id": f"f{uuid.uuid4().hex[:6]}", **data.model_dump(), "_meta": _meta_new("user")}
        kit["flashcards"].append(item)
        _recompute(k, schedule_affecting=False)
    elif collection == "requirements":
        data = RequirementCreate(**body)
        item = {"id": f"r{uuid.uuid4().hex[:6]}", **data.model_dump(), "_meta": _meta_new("user")}
        kit["role"]["requirements"].append(item)
        _recompute(k, schedule_affecting=True)
    else:
        raise KitError(Codes.NOT_FOUND, "unknown collection")
    await get_store().kits.save(k)
    return item


@router.patch("/api/kits/{kit_id}/{collection}/{item_id}")
async def patch_item(kit_id: str, collection: str, item_id: str, body: dict, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if collection == "brief":
        data = BriefPatch(**body)
        meta = kit.setdefault("_brief_meta", _brief_meta())
        if data.rev != meta.get("rev", 0):
            raise KitError(Codes.CONFLICT, "stale revision; refetch")
        brief = kit.get("company_brief", {})
        changed = False
        for field in ("summary", "what_they_do", "hiring_process"):
            value = getattr(data, field)
            if value is not None:
                brief[field] = value
                changed = True
        if data.pinned is not None:
            meta["pinned"] = data.pinned
        if changed:
            meta["edited"] = True
        meta["rev"] = meta.get("rev", 0) + 1
        await get_store().kits.save(k)
        return {**brief, "_rev": meta["rev"]}
    if collection == "questions":
        data = QuestionPatch(**body)
    elif collection == "flashcards":
        data = FlashcardPatch(**body)
    elif collection == "requirements":
        data = RequirementPatch(**body)
    else:
        raise KitError(Codes.NOT_FOUND, "unknown collection")
    target_list = kit[collection] if collection != "requirements" else kit["role"]["requirements"]
    item = next((i for i in target_list if i.get("id") == item_id), None)
    if not item:
        raise KitError(Codes.NOT_FOUND, "item not found")
    meta = item.setdefault("_meta", _meta_new("generated"))
    if data.rev != meta.get("rev"):
        raise KitError(Codes.CONFLICT, "stale revision; refetch")
    values = data.model_dump(exclude_unset=True, exclude={"rev", "pinned", "category_moved"})
    if collection == "questions" and values.get("requirement_ids") is not None:
        _check_refs(values["requirement_ids"], _req_ids(kit))
    if collection == "flashcards" and values.get("requirement_ids") is not None:
        _check_refs(values["requirement_ids"], _req_ids(kit))
    material = False
    for field, value in values.items():
        if value is not None and item.get(field) != value:
            item[field] = value
            material = True
    moved = bool(getattr(data, "category_moved", None)) or (
        collection == "questions" and "category" in values and values["category"] is not None)
    if data.pinned is not None:
        meta["pinned"] = data.pinned
    if material or moved:
        meta["edited"] = True
        meta["rev"] = meta.get("rev", 1) + 1
    affecting = collection in ("questions", "requirements") and (material or moved)
    _recompute(k, schedule_affecting=affecting)
    await get_store().kits.save(k)
    return item


@router.delete("/api/kits/{kit_id}/{collection}/{item_id}")
async def delete_item(kit_id: str, collection: str, item_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if collection == "questions":
        kit["questions"] = [i for i in kit["questions"] if i.get("id") != item_id]
        # strip from schedule immediately and repair minutes
        for day in kit.get("schedule", {}).get("days", []):
            day["question_ids"] = [q for q in day.get("question_ids", []) if q != item_id]
        _fix_minutes(kit)
        _recompute(k, schedule_affecting=True)
        await get_store().kits.save(k)
        return {"ok": True}
    if collection == "flashcards":
        kit["flashcards"] = [i for i in kit["flashcards"] if i.get("id") != item_id]
        _recompute(k, schedule_affecting=False)
        await get_store().kits.save(k)
        return {"ok": True}
    if collection == "requirements":
        before = len(kit["role"]["requirements"])
        kit["role"]["requirements"] = [i for i in kit["role"]["requirements"] if i.get("id") != item_id]
        if len(kit["role"]["requirements"]) == before:
            raise KitError(Codes.NOT_FOUND, "item not found")
        flagged = _strip_refs(kit, item_id)
        _recompute(k, schedule_affecting=True)
        await get_store().kits.save(k)
        return {"ok": True, "flagged": flagged}
    raise KitError(Codes.NOT_FOUND, "unknown collection")


@router.post("/api/kits/{kit_id}/questions/reorder")
async def reorder(kit_id: str, body: dict, user: dict = Depends(current_user)) -> dict:
    data = ReorderBodyStrict(**body)
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    item = next((i for i in kit["questions"] if i.get("id") == data.id), None)
    if not item:
        raise KitError(Codes.NOT_FOUND, "question not found")
    meta = item.setdefault("_meta", _meta_new("generated"))
    if data.category and data.category != item.get("category"):
        item["category"] = data.category
        # cross-category move counts as an edit (rev bumped once below)
    # fractional order within target category
    siblings = sorted(
        [q for q in kit["questions"] if q.get("category") == item.get("category") and q.get("id") != item.get("id")],
        key=lambda q: q.get("_meta", {}).get("order", ""),
    )
    if not siblings:
        meta["order"] = FIRST_KEY
    elif data.after_id is None:
        meta["order"] = key_between(None, siblings[0].get("_meta", {}).get("order"))
    else:
        idx = next((i for i, q in enumerate(siblings) if q.get("id") == data.after_id), None)
        if idx is None:
            raise KitError(Codes.INVALID_INPUT, "unknown after_id")
        prev_k = siblings[idx].get("_meta", {}).get("order")
        next_k = siblings[idx + 1].get("_meta", {}).get("order") if idx + 1 < len(siblings) else None
        meta["order"] = key_between(prev_k, next_k)
    scope = sorted(
        [q for q in kit["questions"] if q.get("category") == item.get("category")],
        key=lambda q: q.get("_meta", {}).get("order", ""),
    )
    if any(needs_rebalance(q.get("_meta", {}).get("order", "")) for q in scope):
        # reassign short keys across the category, preserving rev/edited flags
        for q, fresh in zip(scope, rebalance(len(scope))):
            q.setdefault("_meta", _meta_new("generated"))["order"] = fresh
    # reordering alone never affects the schedule
    _recompute(k, schedule_affecting=False)
    await get_store().kits.save(k)
    return item
