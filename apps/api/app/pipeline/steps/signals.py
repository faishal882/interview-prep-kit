"""Hiring-signal analyzer: flags that change question generation."""
from __future__ import annotations

import re


def analyze(texts: list[str]) -> dict[str, str]:
    blob = "\n".join(texts).lower()
    def flag(*words: str) -> str:
        return "true" if any(re.search(rf"\b{w}\b", blob) for w in words) else ("unknown" if not blob.strip() else "false")
    return {
        "has_take_home": flag("take-home", "takehome", "take home", "assignment"),
        "has_system_design_round": flag("system design", "architecture round", "design round"),
        "has_coding_round": flag("coding", "leetcode", "pairing", "live coding"),
        "has_behavioural_round": flag("behavioural", "behavioral", "values", "culture fit"),
    }
