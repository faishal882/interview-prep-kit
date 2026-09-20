"""Confidence-weighted practice prioritizer (pure)."""
from __future__ import annotations

import time


def priority_score(card: dict, reviews: list[dict], now: float | None = None) -> float:
    now = now if now is not None else time.time()
    if not reviews:
        conf_norm = 0.25  # unseen: before mastered, after known-weak
        hours = 0.0
    else:
        last = max(reviews, key=lambda r: r.get("at", 0))
        conf_norm = (last.get("confidence", 2) - 1) / 2
        hours = (now - last.get("at", now)) / 3600
    must_boost = 0.15 if card.get("priority") == "must" else 0.0
    return (1 - conf_norm) + 0.1 * min(hours / 24, 3) + must_boost


def order_queue(cards: list[dict], history: dict[str, list[dict]], now: float | None = None, limit: int = 10) -> list[dict]:
    scored = [(priority_score(c, history.get(c.get("id", ""), []), now), c) for c in cards]
    scored.sort(key=lambda t: -t[0])
    return [c for _, c in scored[:limit]]
