"""Uniform sanitisation of model output: clamp or drop, never fail the Kit."""
from __future__ import annotations

from typing import Any

CATEGORIES = ("technical", "behavioural", "system-design", "company-fit")
KINDS = ("technical", "behavioural", "domain")
PRIORITIES = ("must", "nice")


def clamp_difficulty(value: Any) -> int:
    if isinstance(value, bool):
        return 2
    if isinstance(value, int) and 1 <= value <= 3:
        return value
    try:
        v = int(value)  # type: ignore[arg-type]
        if 1 <= v <= 3:
            return v
    except (TypeError, ValueError):
        pass
    return 2


def clean_str(value: Any, limit: int = 5000) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def sanitize_question(item: dict, valid_req_ids: set[str], category: str) -> dict | None:
    """Return a valid question dict or None (dropped)."""
    if not isinstance(item, dict):
        return None
    rids = [r for r in (item.get("requirement_ids") or []) if r in valid_req_ids]
    prompt = clean_str(item.get("prompt"), 2000)
    outline = clean_str(item.get("answer_outline"), 4000)
    if not rids or not prompt or not outline:
        return None
    points = [clean_str(x, 1000) for x in (item.get("outline_points") or []) if clean_str(x, 1000)]
    cat = item.get("category") if item.get("category") in CATEGORIES else category
    return {
        "requirement_ids": rids,
        "category": cat,
        "prompt": prompt,
        "answer_outline": outline,
        "difficulty": clamp_difficulty(item.get("difficulty")),
        "outline_points": points,
    }


def sanitize_flashcard(item: dict, valid_req_ids: set[str]) -> dict | None:
    if not isinstance(item, dict):
        return None
    front = clean_str(item.get("front"), 1000)
    back = clean_str(item.get("back"), 2000)
    if not front or not back:
        return None
    return {
        "front": front,
        "back": back,
        "requirement_ids": [r for r in (item.get("requirement_ids") or []) if r in valid_req_ids],
    }
