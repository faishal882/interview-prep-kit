"""Item editing: create/patch/delete + reorder + coverage recompute + stale schedule."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import current_user, get_kit_or_404
from app.coverage.checker import compute_gaps
from app.domain.errors import Codes, KitError
from app.domain.ordering import FIRST_KEY, key_between, needs_rebalance, rebalance
from app.persistence.store import get_store

router = APIRouter()

COLLECTIONS = {"questions": "questions", "flashcards": "flashcards", "requirements": "requirements"}


def _meta_new(origin: str) -> dict:
    return {"origin": origin, "edited": False, "pinned": False, "rev": 1, "order": "a0", "gen_run": None}


def _recompute(kit_doc: dict) -> None:
    kit = kit_doc.get("kit") or {}
    reqs = (kit.get("role") or {}).get("requirements", [])
    gaps = compute_gaps([r["id"] for r in reqs], kit.get("questions", []))
    kit.setdefault("coverage", {})["uncovered_requirement_ids"] = gaps
    # mark schedule stale when questions/requirements changed
    kit_doc["schedule_stale"] = True


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
    if collection not in ("questions", "flashcards", "requirements"):
        raise KitError(Codes.NOT_FOUND, "unknown collection")
    item = dict(body)
    item["id"] = item.get("id") or f"{collection[0]}{uuid.uuid4().hex[:6]}"
    item["_meta"] = _meta_new("user")
    if collection == "questions":
        # assign order key at end
        existing = kit["questions"]
        last = existing[-1].get("_meta", {}).get("order") if existing else None
        item["_meta"]["order"] = key_between(last, None)
        kit["questions"].append(item)
        # strip deleted refs n/a; strip nothing
    elif collection == "flashcards":
        kit["flashcards"].append(item)
    else:
        kit["role"]["requirements"].append(item)
    _recompute(k)
    await get_store().kits.save(k)
    return item


@router.patch("/api/kits/{kit_id}/{collection}/{item_id}")
async def patch_item(kit_id: str, collection: str, item_id: str, body: dict, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if collection == "brief":
        brief = kit.get("company_brief", {})
        brief.update({kk: vv for kk, vv in body.items() if kk in ("summary", "what_they_do", "hiring_process")})
        kit.setdefault("_brief_meta", {"rev": 0})["rev"] += 1
        kit["_brief_meta"]["edited"] = True
        await get_store().kits.save(k)
        return brief
    if collection not in ("questions", "flashcards", "requirements"):
        raise KitError(Codes.NOT_FOUND, "unknown collection")
    target_list = kit[collection] if collection != "requirements" else kit["role"]["requirements"]
    item = next((i for i in target_list if i.get("id") == item_id), None)
    if not item:
        raise KitError(Codes.NOT_FOUND, "item not found")
    if "rev" in body and body["rev"] != item.get("_meta", {}).get("rev"):
        raise KitError(Codes.CONFLICT, "stale revision; refetch")
    content_keys = [kk for kk in body.keys() if kk not in ("rev", "pinned", "_meta")]
    meta = item.setdefault("_meta", _meta_new("generated"))
    if "pinned" in body:
        meta["pinned"] = bool(body["pinned"])
    # category move counts as edit
    for kk in content_keys:
        item[kk] = body[kk]
    if content_keys or body.get("category_moved"):
        meta["edited"] = True
        meta["rev"] = meta.get("rev", 1) + 1
    # rapid double-edit safe: serialised here (single process); rev increments each patch
    if collection == "questions":
        # schedule keeps refs; nothing to strip on edit
        pass
    _recompute(k)
    await get_store().kits.save(k)
    return item


@router.delete("/api/kits/{kit_id}/{collection}/{item_id}")
async def delete_item(kit_id: str, collection: str, item_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    if collection not in ("questions", "flashcards", "requirements"):
        raise KitError(Codes.NOT_FOUND, "unknown collection")
    if collection == "questions":
        kit["questions"] = [i for i in kit["questions"] if i.get("id") != item_id]
        # strip from schedule immediately
        for day in kit.get("schedule", {}).get("days", []):
            day["question_ids"] = [q for q in day.get("question_ids", []) if q != item_id]
    elif collection == "flashcards":
        kit["flashcards"] = [i for i in kit["flashcards"] if i.get("id") != item_id]
    else:
        kit["role"]["requirements"] = [i for i in kit["role"]["requirements"] if i.get("id") != item_id]
    _recompute(k)
    await get_store().kits.save(k)
    return {"ok": True}


class ReorderBody(BaseModel):
    id: str
    category: str | None = None
    after_id: str | None = None


@router.post("/api/kits/{kit_id}/questions/reorder")
async def reorder(kit_id: str, body: ReorderBody, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    item = next((i for i in kit["questions"] if i.get("id") == body.id), None)
    if not item:
        raise KitError(Codes.NOT_FOUND, "question not found")
    meta = item.setdefault("_meta", _meta_new("generated"))
    if body.category and body.category != item.get("category"):
        item["category"] = body.category
        meta["edited"] = True  # cross-category move counts as edit
        meta["rev"] += 1
    # fractional order within target category
    siblings = sorted(
        [q for q in kit["questions"] if q.get("category") == item.get("category") and q.get("id") != item.get("id")],
        key=lambda q: q.get("_meta", {}).get("order", ""),
    )
    if not siblings:
        meta["order"] = FIRST_KEY
    elif body.after_id is None:
        meta["order"] = key_between(None, siblings[0].get("_meta", {}).get("order"))
    else:
        idx = next((i for i, q in enumerate(siblings) if q.get("id") == body.after_id), len(siblings) - 1)
        prev_k = siblings[idx].get("_meta", {}).get("order") if idx >= 0 else None
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
    _recompute(k)
    await get_store().kits.save(k)
    return item
