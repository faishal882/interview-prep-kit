"""Practice: queue, reviews, summary, weak spots, answer check (literal-match coverage)."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import current_user, get_kit_or_404
from app.domain.errors import Codes, KitError
from app.persistence.store import get_store
from app.practice.prioritizer import order_queue

router = APIRouter()


@router.get("/api/kits/{kit_id}/practice/queue")
async def queue(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    store = get_store()
    cards = kit.get("flashcards", [])
    must_ids = {r["id"] for r in kit.get("role", {}).get("requirements", []) if r.get("priority") == "must"}
    enriched = [{**c, "priority": "must" if set(c.get("requirement_ids", [])) & must_ids else "nice"} for c in cards]
    hist = {c["id"]: await store.practice.reviews(f"{kit_id}:{c['id']}") for c in cards}
    ordered = order_queue(enriched, hist)
    return {"queue": [c["id"] for c in ordered]}


class Review(BaseModel):
    flashcard_id: str
    confidence: int


@router.post("/api/kits/{kit_id}/practice/reviews")
async def review(kit_id: str, body: Review, user: dict = Depends(current_user)) -> dict:
    if body.confidence not in (1, 2, 3):
        raise KitError(Codes.INVALID_INPUT, "confidence 1..3")
    await get_kit_or_404(kit_id, user["id"])
    key = f"{kit_id}:{body.flashcard_id}"
    await get_store().practice.append_review(key, {"confidence": body.confidence, "at": time.time()})
    return {"ok": True}


@router.get("/api/kits/{kit_id}/practice/summary")
async def summary(kit_id: str, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    store = get_store()
    cards = kit.get("flashcards", [])
    covered = sum(1 for c in cards if await store.practice.reviews(f"{kit_id}:{c['id']}"))
    return {"total": len(cards), "covered": covered, "uncovered": len(cards) - covered}


@router.get("/api/kits/{kit_id}/practice/weak-spots")
async def weak_spots(kit_id: str, user: dict = Depends(current_user)) -> dict:
    """Rank Requirements by readiness with reasons (practice Confidence, coverage, priority)."""
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    store = get_store()
    reqs = (kit.get("role") or {}).get("requirements", [])
    questions = kit.get("questions", [])
    cards = kit.get("flashcards", [])
    by_req_q = {r["id"]: [q["id"] for q in questions if r["id"] in q.get("requirement_ids", [])] for r in reqs}
    by_req_f = {r["id"]: [c["id"] for c in cards if r["id"] in (c.get("requirement_ids") or [])] for r in reqs}
    spots = []
    for r in reqs:
        fids = by_req_f.get(r["id"], [])
        practised = [fid for fid in fids if await store.practice.reviews(f"{kit_id}:{fid}")]
        low = any((await store.practice.reviews(f"{kit_id}:{fid}"))[-1].get("confidence", 3) <= 2 for fid in practised)
        reasons = []
        if not practised:
            reasons.append("never practised")
        if low:
            reasons.append("low Confidence")
        if not by_req_q.get(r["id"]):
            reasons.append("no Question")
        if not fids:
            reasons.append("no Flashcard")
        score = (3 if r.get("priority") == "must" else 0) + (3 if not by_req_q.get(r["id"]) else 0) + (1 if not fids else 0) + (2 if not practised else 0) + (2 if low else 0)
        spots.append({"requirement_id": r["id"], "reasons": reasons, "score": score,
                      "question_ids": by_req_q.get(r["id"], []), "flashcard_ids": fids})
    spots.sort(key=lambda s: (-s["score"], s["requirement_id"]))
    return {"spots": spots}


class CheckBody(BaseModel):
    question_id: str
    answer: str


@router.post("/api/kits/{kit_id}/practice/check")
async def check(kit_id: str, body: CheckBody, user: dict = Depends(current_user)) -> dict:
    k = await get_kit_or_404(kit_id, user["id"])
    kit = k.get("kit") or {}
    q = next((x for x in kit.get("questions", []) if x.get("id") == body.question_id), None)
    if not q:
        raise KitError(Codes.NOT_FOUND, "question not found")
    points = q.get("outline_points") or [q.get("answer_outline", "")]
    ans = body.answer.lower()
    results = []
    for p in points:
        # literal word-overlap check per outline point
        words = [w.strip(".,;:!?()\"'").lower() for w in str(p).split() if len(w) > 3]
        hit = any(w in ans for w in words) if words else (str(p).lower() in ans)
        results.append({"point": p, "covered": bool(hit)})
    return {"results": results, "method": "literal word-overlap per outline point",
            "limits": "coverage check only, not a quality judgment; implied points are not credited"}
