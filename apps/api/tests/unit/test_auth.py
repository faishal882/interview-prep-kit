"""Auth + ownership tests via FastAPI TestClient."""
import os

os.environ["FAKE_LLM"] = "1"

from fastapi.testclient import TestClient

from app.main import create_app


def client():
    return TestClient(create_app())


def test_unauthenticated_401_envelope():
    c = client()
    r = c.get("/api/kits")
    assert r.status_code == 401
    assert "error" in r.json() and "trace_id" in r.json()["error"]


def test_register_login_flow_and_other_user_404():
    c = client()
    c.post("/api/auth/register", json={"email": "a@t.co", "password": "password123"})
    # second user
    c2 = client()
    c2.post("/api/auth/register", json={"email": "b@t.co", "password": "password123"})
    # user A creates kit
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 2})
    assert r.status_code in (200, 202), r.text
    kit_id = r.json()["kit_id"]
    # user B sees 404 (indistinguishable from missing)
    r2 = c2.get(f"/api/kits/{kit_id}")
    assert r2.status_code == 404


def test_origin_rejected_and_throttling():
    from app.config import get_settings
    get_settings().ALLOWED_ORIGINS = "https://good.example"
    c = client()
    r = c.post("/api/kits", json={"jd": "x", "company_url": "", "days": 1}, headers={"origin": "https://evil.example"})
    assert r.status_code in (401, 403)
    get_settings().ALLOWED_ORIGINS = ""
    c3 = client()
    for _ in range(9):
        c3.post("/api/auth/login", json={"email": "nobody@t.co", "password": "wrongpass1"})
    r = c3.post("/api/auth/login", json={"email": "nobody@t.co", "password": "wrongpass1"})
    assert r.status_code == 429
