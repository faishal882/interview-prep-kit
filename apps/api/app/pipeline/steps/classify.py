"""Heuristic kind/priority classifier (the single classifier used by the pipeline)."""
from __future__ import annotations

import re

MUST_RE = re.compile(r"\b(required|must|need|essential|minimum|min\.?|\+?\d+\s*\+?\s*years?|mandatory)\b", re.I)
NICE_RE = re.compile(r"\b(plus|bonus|preferred|prefer|nice|a plus|good to have|optional)\b", re.I)
BEHAV_RE = re.compile(r"\b(mentor|communicat|collaborat|lead|team|stakeholder|culture|ownership|conflict|feedback)\b", re.I)
DOMAIN_RE = re.compile(r"\b(finance|health|payments?|e-?commerce|logistics|marketing|sales|legal|hr)\b", re.I)


def classify_kind(text: str) -> str:
    if BEHAV_RE.search(text):
        return "behavioural"
    if DOMAIN_RE.search(text):
        return "domain"
    return "technical"


def classify_priority(text: str, heading: str = "") -> str:
    blob = f"{heading} {text}"
    if NICE_RE.search(blob):
        # explicit must beats nice? 'required' in same line wins for must
        if MUST_RE.search(text):
            return "must"
        return "nice"
    return "must"
