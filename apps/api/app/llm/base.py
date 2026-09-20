"""LLM provider protocol + shared types."""
from __future__ import annotations

from typing import Any, Protocol


class ProviderError(Exception):
    def __init__(self, message: str, *, retry_after: float | None = None, status: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.status = status

    @property
    def rate_limited(self) -> bool:
        return self.status == 429 or self.retry_after is not None


class LLMProvider(Protocol):
    name: str

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        ...
