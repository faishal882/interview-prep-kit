"""LLM provider protocol + shared types."""
from __future__ import annotations

from typing import Any, Protocol

RETRYABLE_STATUSES = (429, 500, 502, 503, 504)


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        status: int | None = None,
        transient: bool | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.status = status
        # transient = a genuine provider condition (rate limit, server error,
        # network failure). Programming errors and malformed payloads are not.
        if transient is None:
            transient = status in RETRYABLE_STATUSES
        self.transient = transient

    @property
    def rate_limited(self) -> bool:
        return self.status == 429 or self.retry_after is not None


class TruncatedError(ProviderError):
    """The provider cut the response off at its output limit (never retried as-is)."""

    def __init__(self, message: str = "response truncated at output limit"):
        super().__init__(message, transient=False)


class LLMProvider(Protocol):
    name: str

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        ...
