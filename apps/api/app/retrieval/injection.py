"""Instruction-style text detection for fetched/pasted content.

Fetched pages and pasted descriptions are always framed as delimited data in
prompts; this check is a second signal — pages that address the model or issue
instructions are dropped and logged, never fed to the model.
"""
from __future__ import annotations

MARKERS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous",
    "disregard all",
    "system prompt",
    "system instructions",
    "you are now",
    "reveal your prompt",
    "reveal the system",
    "forget your instructions",
    "forget all rules",
    "developer mode",
    "do anything now",
    "jailbreak",
    "prompt injection",
    "bypass the",
    "as an ai language",
)


def looks_like_instruction(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in MARKERS)
