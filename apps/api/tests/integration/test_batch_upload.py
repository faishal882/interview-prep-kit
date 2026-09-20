"""Web batch upload tests: caps, per-entry reports, dedupe."""
import os
import uuid

os.environ["FAKE_LLM"] = "1"

from fastapi.testclient import TestClient

from app.main import create_app


def authed():
    c = TestClient(create_app())
    c.post("/api/auth/register", json={"email": f"batch-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    return c


def test_batch_accepts_valid_rejects_malformed():
    c = authed()
    body = [
        {"jd": "Need Python. Required: Python.", "company_url": "", "days": 2},
        {"jd": "", "company_url": "", "days": 2},
        {"jd": "Need Go. Required: Go.", "company_url": "", "days": 99},
    ]
    r = c.post("/api/kits/batch", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["accepted"]) == 1
    assert len(data["rejected"]) == 2


def test_batch_rejects_more_than_ten():
    c = authed()
    body = [{"jd": "Need Python. Required: Python.", "company_url": "", "days": 2} for _ in range(11)]
    r = c.post("/api/kits/batch", json=body)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"


def test_batch_duplicate_follows_dedupe():
    c = authed()
    entry = {"jd": "Need Rust. Required: Rust.", "company_url": "", "days": 2}
    first = c.post("/api/kits/batch", json=[entry]).json()
    second = c.post("/api/kits/batch", json=[entry]).json()
    assert first["accepted"][0]["kit_id"] == second["accepted"][0]["kit_id"]
    assert second["accepted"][0].get("duplicate") is True
