"""Shared request/token rate limiter (token bucket, asyncio-safe).

One instance is shared by every concurrent generation so the model quota is
respected by construction rather than by retry storms.
"""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, requests_per_minute: float = 60.0, tokens_per_minute: float = 200000.0):
        self._req_interval = 60.0 / max(requests_per_minute, 1e-9)
        self._tok_rate = max(tokens_per_minute, 1e-9) / 60.0
        self._capacity = max(tokens_per_minute, 1.0)
        self._tokens = self._capacity
        self._next_request_at = 0.0
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._tok_rate)
            self._updated = now

    async def acquire(self, tokens: float = 0) -> None:
        """Wait until one request slot and `tokens` of budget are available."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._refill(now)
                wait_req = self._next_request_at - now
                wait_tok = ((tokens - self._tokens) / self._tok_rate) if tokens > self._tokens else 0.0
                wait = max(wait_req, wait_tok, 0.0)
                if wait <= 0:
                    self._next_request_at = now + self._req_interval
                    self._tokens = max(0.0, self._tokens - tokens)
                    return
            await asyncio.sleep(min(wait, 5.0))


def estimate_tokens(prompt: str) -> int:
    return max(1, len(prompt) // 4)
