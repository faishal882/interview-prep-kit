"""Heuristic link ranker: scores how likely a link describes hiring or the business."""
from __future__ import annotations

import re

GOOD = re.compile(r"(career|job|hiring|hiring-process|interview|handbook|about|team|culture|engineering|blog|values|work-here|join)", re.I)


def score(url: str, anchor: str, context: str = "") -> float:
    blob = f"{url} {anchor} {context}"
    m = GOOD.search(blob)
    base = 0.8 if m else 0.1
    if re.search(r"career|hiring|interview", blob, re.I):
        base += 0.15
    return min(base, 1.0)
