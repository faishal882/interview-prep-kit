"""Practice: queue, reviews, summary, answer check (Jev with fallback)."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import current_user, get_kit_or_404
from app.domain.errors import Codes, KitError
from app.persistence.memory import DB
from app.practice.prioritizer import order_queue

router = APIRouter()


@router.get("/api/kits/{kit_id}/practice/queue")
async def queue(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    cards = kit.get("flashcards", [])
    must_ids = {r["id"] for r in kit.get("role", {}).get("requirements", []) if r.get("priority") == "must"}
    enriched = [{**c, "priority": "must" if set(c.get("requirement_ids", [])) & must_ids else "nice"} for c in cards]
    hist = {c["id"]: DB.practice.get(f"{kit_id}:{c['id']}", []) for c in cards}
    ordered = order_queue(enriched, hist)
    return {"queue": [c["id"] for c in ordered]}


class Review(BaseModel):
    flashcard_id: str
    confidence: int


@router.post("/api/kits/{kit_id}/practice/reviews")
async def review(kit_id: str, body: Review, user: dict = Depends(current_user)) -> dict:
    if body.confidence not in (1, 2, 3):
        raise KitError(Codes.INVALID_INPUT, "confidence 1..3")
    get_kit_or_404(kit_id, user["id"])
    key = f"{kit_id}:{body.flashcard_id}"
    DB.practice.setdefault(key, []).append({"confidence": body.confidence, "at": time.time()})
    return {"ok": True}


@router.get("/api/kits/{kit_id}/practice/summary")
async def summary(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    cards = kit.get("flashcards", [])
    covered = sum(1 for c in cards if DB.practice.get(f"{kit_id}:{c['id']}"))
    return {"total": len(cards), "covered": covered, "uncovered": len(cards) - covered}


class CheckBody(BaseModel):
    question_id: str
    answer: str


@router.post("/api/kits/{kit_id}/practice/check")
async def check(kit_id: str, body: CheckBody, user: dict = Depends(current_user)) -> dict:
    k = get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    q = next((x for x in kit.get("questions", []) if x.get("id") == body.question_id), None)
    if not q:
        raise KitError(Codes.NOT_FOUND, "question not found")
    points = q.get("outline_points") or [q.get("answer_outline", "")]
    ans = body.answer.lower()
    results = []
    for p in points:
        # fallback: literal word-overlap check; Jev Noul would run per point when key present
        words = [w.strip(".,;:!?()\"'").lower() for w in str(p).split() if len(w) > 3]
        hit = any(w in ans for w in words) if words else (str(p).lower() in ans)
        results.append({"point": p, "covered": bool(hit)})
    return {"results": results, "method": "literal-match fallback; Jev reads literally and won't credit implied points",
            "limits": "coverage check only, not a quality judgment"}
