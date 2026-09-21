"""Phase 6: gateway policy — fail-fast errors, hints, limiter, truncation, repair, key handling."""
import asyncio
import time

import httpx
import pytest
import respx

from app.domain.errors import Codes, KitError
from app.llm import router as router_mod
from app.llm.base import ProviderError, TruncatedError
from app.llm.gemini import GeminiProvider
from app.llm.limiter import RateLimiter
from app.llm.router import generate
from app.llm.validate import validate_against_schema

SCHEMA = {"type": "object", "required": ["requirements"], "properties": {"requirements": {"type": "array"}}}


class Boom:
    name = "boom"

    def __init__(self):
        self.calls = 0

    async def generate_structured(self, prompt, schema):
        self.calls += 1
        raise ValueError("programming error")


class Seq:
    name = "seq"

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0
        self.prompts = []

    async def generate_structured(self, prompt, schema):
        self.calls += 1
        self.prompts.append(prompt)
        behaviour = self.behaviours.pop(0)
        if isinstance(behaviour, BaseException):
            raise behaviour
        return behaviour


def _limiter():
    return RateLimiter(requests_per_minute=6000, tokens_per_minute=10**9)


def test_programming_error_fails_immediately():
    p = Boom()
    t0 = time.monotonic()
    with pytest.raises(ValueError):
        asyncio.run(generate(p, "x", SCHEMA, limiter=_limiter()))
    assert p.calls == 1
    assert time.monotonic() - t0 < 2.0


def test_rate_limit_hint_and_server_backoff_bounded():
    p = Seq([ProviderError("slow", retry_after=0.01, status=429),
             ProviderError("bad", status=503, transient=True),
             {"requirements": []}])
    out, _ = asyncio.run(generate(p, "x", SCHEMA, limiter=_limiter()))
    assert out == {"requirements": []} and p.calls == 3


def test_shared_limiter_serializes_concurrent_runs():
    async def go():
        lim = RateLimiter(requests_per_minute=120, tokens_per_minute=10**9)
        p = Seq([{"requirements": []}, {"requirements": []}])
        t0 = time.monotonic()
        await asyncio.gather(generate(p, "x", SCHEMA, limiter=lim),
                             generate(p, "y", SCHEMA, limiter=lim))
        return time.monotonic() - t0, p.calls
    elapsed, calls = asyncio.run(go())
    assert elapsed >= 0.4
    assert calls == 2


def test_truncated_output_retried_smaller():
    big = "z" * 3000
    p = Seq([TruncatedError(), {"requirements": []}])
    out, _ = asyncio.run(generate(p, big, SCHEMA, limiter=_limiter()))
    assert out == {"requirements": []}
    assert len(p.prompts[1]) < len(p.prompts[0])


def test_repair_attempt_is_itself_retry_protected():
    p = Seq([{"requirements": "not-a-list"},
             ProviderError("slow", retry_after=0.01, status=429),
             {"requirements": []}])
    out, _ = asyncio.run(generate(p, "x", SCHEMA, limiter=_limiter()))
    assert out == {"requirements": []} and p.calls == 3


def test_deep_validation_catches_nested_type_errors():
    schema = {
        "type": "object",
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["difficulty"],
                    "properties": {"difficulty": {"type": "integer"}},
                },
            }
        },
    }
    with pytest.raises(ValueError, match="difficulty"):
        validate_against_schema({"questions": [{"difficulty": "high"}]}, schema)
    p = Seq([{"questions": [{"difficulty": "high"}]}, {"questions": [{"difficulty": 2}]}])
    out, _ = asyncio.run(generate(p, "x", schema, limiter=_limiter()))
    assert out == {"questions": [{"difficulty": 2}]} and p.calls == 2


def test_usage_recorded_per_call():
    usage: list[dict] = []
    p = Seq([{"requirements": []}])
    asyncio.run(generate(p, "x" * 100, SCHEMA, limiter=_limiter(), usage=usage))
    assert usage and usage[0]["prompt_chars"] == 100 and usage[0]["latency_ms"] >= 0 and usage[0]["calls"] == 1


def test_key_in_header_not_url_and_not_in_errors():
    async def go():
        async with respx.mock(assert_all_called=False) as router:
            seen = {}

            def handler(request):
                seen["auth"] = request.headers.get("x-goog-api-key")
                seen["url"] = str(request.url)
                return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"requirements": []}'}]}, "finishReason": "STOP"}]})
            router.post("http://model.test/v1beta/models/m:generateContent").mock(side_effect=handler)
            provider = GeminiProvider("SECRETKEY", "m", base_url="http://model.test")
            out = await provider.generate_structured("hi", SCHEMA)
            assert out == {"requirements": []}
            assert seen["auth"] == "SECRETKEY"
            assert "key=" not in seen["url"] and "SECRET" not in seen["url"]

            def bad_handler(request):
                return httpx.Response(400, text="nope")
            router.post("http://model.test/v1beta/models/m:generateContent").mock(side_effect=bad_handler)
            try:
                await provider.generate_structured("hi", SCHEMA)
            except ProviderError as exc:
                assert "SECRETKEY" not in str(exc)
            else:
                raise AssertionError("should have raised")
    asyncio.run(go())


def _no_creds_settings(monkeypatch):
    # Patch the get_settings name resolved by each module under test
    # (both bind it with `from app.config import get_settings`).
    from types import SimpleNamespace
    import app.api.routers.kits as kits_mod
    import app.cli.evaluate as evalmod
    stub = SimpleNamespace(FAKE_LLM="", GEMINI_API_KEY="", GEMINI_MODEL="m",
                           ALLOW_PRIVATE_URLS=False, MAX_CRAWL_PAGES=4, CRAWL_DEPTH=1)
    monkeypatch.delenv("FAKE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(kits_mod, "get_settings", lambda: stub)
    monkeypatch.setattr(evalmod, "get_settings", lambda: stub)


def test_batch_fails_fast_without_key_or_explicit_fake(monkeypatch, tmp_path):
    _no_creds_settings(monkeypatch)
    from app.cli import evaluate as evalmod
    rc = asyncio.run(evalmod.main_async("/nonexistent.json", str(tmp_path / "o.json")))
    assert rc == 2


def test_server_deps_refuse_silent_fake(monkeypatch):
    _no_creds_settings(monkeypatch)
    from app.api.routers import kits as kits_mod
    with pytest.raises(KitError) as ei:
        kits_mod._deps_for_server()
    assert ei.value.code == Codes.MISSING_CREDENTIALS
    _ = router_mod  # keep import used
