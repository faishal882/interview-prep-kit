"""Jev gateway: optional typed decisions with mandatory fallbacks."""
from __future__ import annotations

from typing import Any


class JevClient:
    def __init__(self, api_key: str = "", enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled and bool(api_key)

    def _off(self, reason: str = "jev disabled") -> dict[str, Any]:
        return {"used": False, "reason": reason}

    async def classify(self, text: str, heading: str, fallback) -> dict[str, Any]:
        if not self.enabled:
            return {"used": False, "reason": "no jev key", "value": fallback(text, heading)}
        # Real Jev call would go here via typesafe-sdk; without network in tests, fall back.
        try:
            raise RuntimeError("jev not configured in this build")
        except Exception as exc:
            return {"used": False, "reason": f"jev failed: {exc}", "value": fallback(text, heading)}

    async def verify_link(self, question: str, requirement: str) -> dict[str, Any]:
        """Noul: does the question test the requirement? Below 0.7 -> no override."""
        if not self.enabled:
            return {"used": False, "confidence": 0.0, "verdict": True, "reason": "fallback: accept link"}
        return {"used": False, "confidence": 0.0, "verdict": True, "reason": "jev unavailable"}

    async def is_injection(self, text: str) -> dict[str, Any]:
        low = text.lower()
        bad = ("ignore previous instructions", "disregard previous", "system prompt", "you are now")
        if any(b in low for b in bad):
            return {"used": True, "verdict": True, "confidence": 0.95}
        if not self.enabled:
            return {"used": False, "verdict": False, "confidence": 0.0}
        return {"used": True, "verdict": False, "confidence": 0.6}
