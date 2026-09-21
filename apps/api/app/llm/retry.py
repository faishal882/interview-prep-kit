"""Retry helper: only genuine provider conditions are retried.

Programming errors (non-ProviderError, or non-transient ProviderError) fail
immediately with no sleeping. Provider hints (Retry-After) are honoured and
every wait is bounded.
"""
from __future__ import annotations

import asyncio
import random

from .base import ProviderError

MAX_DELAY_S = 60.0


async def with_retry(fn, *, attempts: int = 4, base: float = 2.0, cap: float = MAX_DELAY_S):
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return await fn()
        except ProviderError as exc:
            if not exc.transient:
                raise
            last = exc
            hint = exc.retry_after
            if hint is not None:
                delay = min(max(hint, 0.0), cap)
            else:
                delay = min(cap, base * (2**i))
            delay = delay * (0.8 + 0.4 * random.random())
            if i == attempts - 1:
                break
            await asyncio.sleep(delay)
        except Exception:
            raise
    assert last is not None
    raise last
