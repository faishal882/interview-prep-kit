"""Retry helper honouring provider hints (429/5xx, Retry-After)."""
from __future__ import annotations

import asyncio
import random


async def with_retry(fn, *, attempts: int = 4, base: float = 2.0, cap: float = 60.0):
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 - provider-agnostic
            last = exc
            hint = getattr(exc, "retry_after", None)
            status = getattr(exc, "status", None)
            if status is not None and status not in (429, 500, 502, 503, 504):
                raise
            delay = hint if hint is not None else min(cap, base * (2**i))
            delay = delay * (0.8 + 0.4 * random.random())
            if i == attempts - 1:
                break
            await asyncio.sleep(delay)
    assert last is not None
    raise last
