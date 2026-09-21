"""Model gateway policy: shared limiting, truncation retry, deep validation.

One repair attempt on schema-invalid output, itself protected by retry for
genuine provider conditions. Truncated output is retried once with a smaller
prompt. Programming errors fail immediately. Usage and latency are recorded
per call.
"""
from __future__ import annotations

import time
from typing import Any

from .base import ProviderError, TruncatedError
from .limiter import RateLimiter, estimate_tokens
from .retry import with_retry
from .validate import validate_against_schema

_shared_limiter: RateLimiter | None = None


def shared_limiter(requests_per_minute: float = 60.0, tokens_per_minute: float = 200000.0) -> RateLimiter:
    global _shared_limiter
    if _shared_limiter is None:
        _shared_limiter = RateLimiter(requests_per_minute, tokens_per_minute)
    return _shared_limiter


def reset_shared_limiter() -> None:
    """Forget the process-wide limiter (tests only)."""
    global _shared_limiter
    _shared_limiter = None


def configure_shared_limiter(requests_per_minute: float, tokens_per_minute: float) -> RateLimiter:
    """Set the process-wide limiter from settings (server startup)."""
    global _shared_limiter
    _shared_limiter = RateLimiter(requests_per_minute, tokens_per_minute)
    return _shared_limiter


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…[truncated]"


async def generate(
    provider: Any,
    prompt: str,
    schema: dict[str, Any],
    *,
    repair_prompt: str | None = None,
    limiter: RateLimiter | None = None,
    usage: list[dict] | None = None,
    attempts: int = 4,
) -> tuple[dict[str, Any], str]:
    """Run one provider call with gateway policy; return (payload, provider name)."""
    t0 = time.monotonic()
    lim = limiter if limiter is not None else shared_limiter()
    await lim.acquire(estimate_tokens(prompt))
    calls = [0]

    async def _call(text: str) -> dict[str, Any]:
        calls[0] += 1
        return await provider.generate_structured(text, schema)

    async def _protected(text: str) -> dict[str, Any]:
        return await with_retry(lambda: _call(text), attempts=attempts)

    try:
        try:
            raw = await _protected(prompt)
        except TruncatedError:
            raw = await _protected(truncate(prompt, max(500, len(prompt) // 3)))
        try:
            validate_against_schema(raw, schema)
            return raw, provider.name
        except ValueError as ve:
            fix = (repair_prompt or "Fix the JSON so it matches the schema.") + f"\nSchema errors: {ve}"
            raw2 = await _protected(fix + "\n" + truncate(prompt, 4000))
            validate_against_schema(raw2, schema)
            return raw2, provider.name
    finally:
        if usage is not None:
            usage.append({
                "model": getattr(provider, "name", "?"),
                "prompt_chars": len(prompt),
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                "calls": calls[0],
            })
