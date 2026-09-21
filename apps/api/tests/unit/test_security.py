"""Phase 11: cookies, closed registration, quotas, throttle, bounds, origins, errors."""
import asyncio
import time
import uuid

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def authed_open():
    c = TestClient(create_app())
    c.post("/api/auth/register", json={"email": f"s-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    return c


def test_cookie_flags_follow_environment():
    from fastapi import Response
    from app.api.routers.auth import session_cookie
    r = Response()
    session_cookie(r, "tok", secure=True)
    cookie = r.headers.get("set-cookie", "").lower()
    assert "secure" in cookie and "httponly" in cookie
    r2 = Response()
    session_cookie(r2, "tok", secure=False)
    assert "secure" not in r2.headers.get("set-cookie", "").lower()


def test_registration_closed_by_default_operator_and_reopen(monkeypatch):
    import app.api.routers.auth as auth_mod

    monkeypatch.setattr(auth_mod, "get_settings", lambda: Settings(REGISTRATION_OPEN=False))
    c = TestClient(create_app())
    r = c.post("/api/auth/register", json={"email": "x@t.co", "password": "password123"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"

    monkeypatch.setattr(auth_mod, "get_settings", lambda: Settings(REGISTRATION_OPEN=True))
    r2 = c.post("/api/auth/register", json={"email": f"y-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    assert r2.status_code == 200


def test_quotas_refuse_with_clear_errors(monkeypatch):
    c = authed_open()
    from app.persistence.store import get_store
    store = get_store()
    me = c.get("/api/me").json()

    from app.jobs.runner import new_job
    ghost = new_job("ghost", user_id=me["id"])
    ghost["status"] = "running"
    asyncio.run(store.jobs.create(ghost))
    try:
        # second concurrent generation refused while one runs
        r = c.post("/api/kits", json={"jd": "Need Rust. Required: Rust.", "company_url": "", "days": 2})
        assert r.status_code == 429
        assert "already running" in r.json()["error"]["message"]
    finally:
        asyncio.run(store.jobs.delete(ghost["id"]))

    # stored-kit cap enforced
    import app.api.routers.kits as kits_mod
    capped = Settings(MAX_STORED_KITS=0, MAX_KITS_PER_DAY=1000, MAX_CONCURRENT_PER_USER=100)
    monkeypatch.setattr(kits_mod, "get_settings", lambda: capped)
    r = c.post("/api/kits", json={"jd": "Need Go. Required: Go.", "company_url": "", "days": 2})
    assert r.status_code == 429
    assert "storage limit" in r.json()["error"]["message"]

    # daily cap enforced (zero allowance refuses the very first creation)
    daily = Settings(MAX_STORED_KITS=1000, MAX_KITS_PER_DAY=0, MAX_CONCURRENT_PER_USER=100)
    monkeypatch.setattr(kits_mod, "get_settings", lambda: daily)
    r = c.post("/api/kits", json={"jd": "Need Go. Required: Go.", "company_url": "", "days": 2})
    assert r.status_code == 429
    assert "daily" in r.json()["error"]["message"]


def test_login_throttle_per_address_and_account():
    c = TestClient(create_app())
    email = f"t-{uuid.uuid4().hex[:6]}@t.co"
    c.post("/api/auth/register", json={"email": email, "password": "password123"})
    # wrong password from the default client throttles that account+address…
    for _ in range(8):
        assert c.post("/api/auth/login", json={"email": email, "password": "wrongpass1"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": email, "password": "wrongpass1"}).status_code == 429
    # …but a wrong-email guess is a different account key and does not lock the user out
    other = f"nobody-{uuid.uuid4().hex[:6]}@t.co"
    assert c.post("/api/auth/login", json={"email": other, "password": "wrongpass1"}).status_code == 401
    # throttle store stays bounded
    from app.persistence.repos_memory import MemoryThrottles
    t = MemoryThrottles()
    for i in range(MemoryThrottles.MAX_KEYS + 10):
        asyncio.run(t.set_times(f"k{i}", [1.0]))
    assert len(t._times) <= MemoryThrottles.MAX_KEYS


def test_oversized_password_rejected_without_hashing():
    c = TestClient(create_app())
    big = "x" * (1024 * 1024 + 10)
    t0 = time.monotonic()
    r = c.post("/api/auth/register", json={"email": "big@t.co", "password": big})
    assert time.monotonic() - t0 < 5.0
    assert r.status_code in (413, 422)


def test_production_origin_fail_closed(monkeypatch):
    from types import SimpleNamespace
    from starlette.requests import Request
    from app.api import deps as deps_mod
    from app.domain.errors import KitError

    def req(method, origin):
        scope = {"type": "http", "method": method, "headers": []}
        if origin is not None:
            scope["headers"] = [(b"origin", origin.encode())]
        return Request(scope)

    monkeypatch.setattr(deps_mod, "get_settings",
                        lambda: SimpleNamespace(ENV="production", ALLOWED_ORIGINS="https://app.test"))
    try:
        deps_mod.check_origin(req("POST", "https://evil.test"))
        raise AssertionError("evil origin accepted")
    except KitError:
        pass
    try:
        deps_mod.check_origin(req("POST", None))
        raise AssertionError("missing origin accepted")
    except KitError:
        pass
    deps_mod.check_origin(req("POST", "https://app.test"))
    deps_mod.check_origin(req("GET", None))


def test_unexpected_errors_are_generic_with_reference_id(monkeypatch):
    c = TestClient(create_app(), raise_server_exceptions=False)
    c.post("/api/auth/register", json={"email": f"s-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    from app.persistence.store import get_store

    async def boom(kit_id):
        raise RuntimeError("secret internals exploded")

    store = get_store()
    monkeypatch.setattr(store.kits, "get", boom)
    r = c.get("/api/kits/anything")
    assert r.status_code == 500
    body = r.json()["error"]
    assert body["message"] == "unexpected error"
    assert "trace_id" in body and body["trace_id"]
    assert "secret" not in body["message"] and "RuntimeError" not in str(body)


def test_responses_omit_internal_fields():
    c = authed_open()
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 1})
    kit_id, job_id = r.json()["kit_id"], r.json()["job_id"]
    kit = c.get(f"/api/kits/{kit_id}").json()
    assert "user_id" not in kit and "dedupe_key" not in kit
    job = c.get(f"/api/jobs/{job_id}").json()
    assert "user_id" not in job and "heartbeat" not in job and "attempts" not in job
    for _ in range(60):
        time.sleep(0.2)
        if c.get(f"/api/kits/{kit_id}").json().get("status") == "ready":
            break
