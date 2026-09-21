"""Scripted fake LLM for tests and offline batch runs."""
from __future__ import annotations

from typing import Any


class FakeLLM:
    name = "fake"

    def __init__(self, script: dict[str, list[dict[str, Any]]] | None = None):
        # script maps step-name substring -> queue of responses; deep-copied
        # so one instance never drains another's queues.
        import copy
        self.script = copy.deepcopy(script) if script else {}
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"prompt": prompt, "schema": schema})
        for key, queue in self.script.items():
            if key in prompt and queue:
                return queue.pop(0)
        # default: valid empty payload shaped by schema title hint
        return self._default(prompt)

    def _default(self, prompt: str) -> dict[str, Any]:
        if "REQUIREMENTS" in prompt:
            return {"requirements": [], "responsibilities": [], "role": {}}
        if "QUESTIONS:" in prompt:
            return {"questions": []}
        if "FLASHCARDS" in prompt:
            return {"flashcards": []}
        if "BRIEF" in prompt:
            return {"summary": "Summary.", "what_they_do": "They do things.", "hiring_process": ""}
        return {}
