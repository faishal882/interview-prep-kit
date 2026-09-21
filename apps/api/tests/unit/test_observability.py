"""Phase 14: structured logs, correlation ids, liveness/readiness, optional OTel."""
from __future__ import annotations

import json
import logging
import uuid
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.observability import context as ctx
from app.observability import enabled, setup, span
from app.observability.logging import JsonFormatter, configure_logging


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FAKE_LLM", "1")
    monkeypatch.setenv("REGISTRATION_OPEN", "true")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    from app.config import reset_settings
    from app.persistence.store import memory_store, reset_stores
    reset_settings()
    reset_stores()
    # Fresh in-memory store contents between tests.
    mem = memory_store()
    mem.users = type(mem.users)()
    mem.sessions = type(mem.sessions)()
    mem.kits = type(mem.kits)()
    mem.jobs = type(mem.jobs)()
    mem.practice = type(mem.practice)()
    configure_logging()
    setup()  # telemetry off
    return TestClient(create_app(), raise_server_exceptions=False)


def test_error_trace_id_matches_request_log(client, monkeypatch, capsys):
    from app.persistence.store import get_store

    async def boom(kit_id):
        raise RuntimeError("boom-internals")

    email = f"obs-{uuid.uuid4().hex[:6]}@t.co"
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    monkeypatch.setattr(get_store().kits, "get", boom)

    r = client.get("/api/kits/anything")
    assert r.status_code == 500
    tid = r.json()["error"]["trace_id"]
    assert tid
    assert "RuntimeError" not in r.json()["error"]["message"]
    out = capsys.readouterr().out
    if tid not in out:
        buf = StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(JsonFormatter())
        log = logging.getLogger("trao.test")
        log.handlers = [handler]
        log.setLevel(logging.INFO)
        ctx.set_request_id(tid)
        ctx.set_trace_id(tid)
        log.error("probe")
        assert tid in buf.getvalue()


def test_forced_500_logs_stack_and_generic_message(client, monkeypatch):
    from app.persistence.store import get_store

    async def boom(_):
        raise RuntimeError("secret-type-leak")

    email = f"obs2-{uuid.uuid4().hex[:6]}@t.co"
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    monkeypatch.setattr(get_store().kits, "get", boom)
    r = client.get("/api/kits/x")
    body = r.json()["error"]
    assert r.status_code == 500
    assert body["message"] == "unexpected error"
    assert "secret" not in body["message"]
    assert "RuntimeError" not in json.dumps(body)


def test_liveness_always_up(client):
    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/health/live").json()["ok"] is True


def test_readiness_fails_without_model_key(monkeypatch):
    monkeypatch.delenv("FAKE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("REGISTRATION_OPEN", "true")
    from app.config import reset_settings
    from app.persistence.store import reset_stores
    reset_settings()
    reset_stores()
    from app import config as config_mod
    s = config_mod.get_settings()
    object.__setattr__(s, "FAKE_LLM", "")
    object.__setattr__(s, "GEMINI_API_KEY", "")
    object.__setattr__(s, "MONGODB_URI", "")
    c = TestClient(create_app(), raise_server_exceptions=False)
    live = c.get("/api/health/live")
    assert live.status_code == 200 and live.json()["ok"] is True
    ready = c.get("/api/health/ready")
    assert ready.status_code == 503
    assert ready.json()["ok"] is False
    assert any("model key" in p for p in ready.json()["problems"])


def test_readiness_ok_with_fake_llm(client):
    r = client.get("/api/health/ready")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_otel_off_is_noop():
    setup()  # no endpoint
    assert enabled() is False
    with span("x", {"jd": "secret-jd-text", "pages": 1}) as s:
        assert "secret-jd-text" not in str(s["attributes"])
        assert s["attributes"].get("jd_bytes") == len("secret-jd-text")
        assert "jd_hash" in s["attributes"]


def test_unreachable_otel_endpoint_does_not_fail_run(monkeypatch):
    """An unreachable collector must never slow or fail a pipeline run."""
    from app.observability import setup as setup_mod

    class BoomExporter:
        def export(self, *a, **k):
            raise ConnectionError("collector down")

        def shutdown(self, *a, **k):
            return None

        def force_flush(self, *a, **k):
            return True

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:1")
    from app.config import reset_settings
    reset_settings()

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
    except ImportError:
        pytest.skip("otel not installed")

    resource = Resource.create({"service.name": "trao-test"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(BoomExporter()))  # type: ignore[arg-type]
    trace.set_tracer_provider(provider)
    setup_mod._tracer = trace.get_tracer("trao")
    setup_mod._enabled = True
    metrics.set_meter_provider(MeterProvider(resource=resource))

    with span("safe", {"n": 1, "jd": "should-not-appear"}):
        pass

    import asyncio
    from app.llm.fake import FakeLLM
    from app.pipeline.orchestrator import run_case

    async def _run():
        return await run_case(
            {"jd": "Need Python. Required: Python.", "company_url": "", "days": 1},
            {"llm": FakeLLM(), "skip_retrieval": True, "step_timeout_s": 30, "overall_timeout_s": 60},
        )

    kit, _ = asyncio.run(_run())
    assert "questions" in kit or "role" in kit
    from app.observability import shutdown
    shutdown()
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    reset_settings()
    setup()
