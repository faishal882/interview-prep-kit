"""Hiring-signal analyzer: flags that change question generation.

Signals are computed ONLY from pages typed as hiring-related, using strict
round-level patterns — an ordinary about page mentioning "coding" or "values"
must never set a hiring signal.
"""
from __future__ import annotations

import re

from app.retrieval.page_typer import page_type

PATTERNS: dict[str, tuple[str, ...]] = {
    # a real take-home step, not the word "assignment" in prose
    "has_take_home": (
        r"take-home", r"takehome", r"take home (assignment|project|challenge|exercise)",
        r"home assignment",
    ),
    "has_system_design_round": (
        r"system[-\s]?design (round|interview)",
    ),
    "has_coding_round": (
        r"coding (round|interview|challenge|test)", r"live coding",
        r"pair programming", r"leetcode", r"hackerrank", r"codility",
    ),
    "has_behavioural_round": (
        r"behavioural (interview|round)", r"behavioral (interview|round)",
        r"culture[-\s]?fit (interview|round)", r"values (interview|round)",
    ),
}


def analyze(pages: list[dict]) -> dict[str, str]:
    """Analyze hiring-typed pages; 'unknown' when there are none."""
    hiring = [p for p in pages if page_type(p) == "hiring"]
    if not hiring:
        return {k: "unknown" for k in PATTERNS}
    blob = "\n".join(p.get("text", "") for p in hiring).lower()
    out = {}
    for key, patterns in PATTERNS.items():
        out[key] = "true" if any(re.search(p, blob) for p in patterns) else "false"
    return out
