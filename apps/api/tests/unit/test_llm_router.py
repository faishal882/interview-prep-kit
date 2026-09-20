"""Single-LLM generation: retry + exactly-one-repair tests (fake providers, no network)."""
import asyncio

from app.llm.base import ProviderError
from app.llm.router import generate


class Flaky:
    name = "flaky"

    def __init__(self, fails: int):
        self.fails = fails
        self.calls = 0

    async def generate_structured(self, prompt, schema):
        self.calls += 1
        if self.calls <= self.fails:
            raise ProviderError("slow down", retry_after=0.01, status=429)
        return {"requirements": []}


class Dead:
    name = "dead"

    async def generate_structured(self, prompt, schema):
        raise ProviderError("bad request", status=400)


def test_rate_limit_retried_with_backoff():
    f = Flaky(2)
    out, who = asyncio.run(generate(f, "REQUIREMENTS", {"type": "object", "required": [], "properties": {}}))
    assert who == "flaky" and f.calls == 3


def test_provider_failure_raises():
    try:
        asyncio.run(generate(Dead(), "x", {"type": "object", "required": [], "properties": {}}))
    except ProviderError:
        return
    raise AssertionError("should have raised")
