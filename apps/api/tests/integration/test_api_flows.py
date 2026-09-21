"""Editing, regeneration, practice, batch contract tests."""
import asyncio
import json
import os
import tempfile

os.environ["FAKE_LLM"] = "1"

from fastapi.testclient import TestClient

from app.cli import evaluate as evalmod
from app.main import create_app


def authed():
    import uuid
    c = TestClient(create_app())
    c.post("/api/auth/register", json={"email": f"ed-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    return c


def test_edit_sets_edited_and_delete_strips_schedule():
    c = authed()
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 2})
    kit_id = r.json()["kit_id"]
    import time
    for _ in range(50):
        time.sleep(0.1)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            break
    assert k.get("status") == "ready", k
    # add a question by hand
    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"prompt": "Mine", "answer_outline": "O", "requirement_ids": [], "category": "technical", "difficulty": 1}).json()
    assert q["_meta"]["origin"] == "user"
    # edit sets edited
    e = c.patch(f"/api/kits/{kit_id}/questions/{q['id']}", json={"prompt": "Mine v2"}).json()
    assert e["_meta"]["edited"] is True
    # stale revision rejected
    r2 = c.patch(f"/api/kits/{kit_id}/questions/{q['id']}", json={"rev": 1, "prompt": "stale"})
    assert r2.status_code == 409
    # delete strips from schedule: put it in schedule via regeneration? simpler: delete existing q1
    first_q = k["kit"]["questions"][0]["id"] if k["kit"]["questions"] else q["id"]
    c.delete(f"/api/kits/{kit_id}/questions/{first_q}")
    k2 = c.get(f"/api/kits/{kit_id}").json()
    for d in k2["kit"]["schedule"]["days"]:
        assert first_q not in d["question_ids"]


def test_regeneration_keeps_protected_and_proposal():
    c = authed()
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 2})
    kit_id = r.json()["kit_id"]
    import time
    for _ in range(50):
        time.sleep(0.1)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            break
    qs = k["kit"]["questions"]
    if qs:
        c.patch(f"/api/kits/{kit_id}/questions/{qs[0]['id']}", json={"prompt": "hand-edited"})
    # regenerate category keeps protected
    rr = c.post(f"/api/kits/{kit_id}/sections/questions:technical/regenerate").json()
    assert rr.get("ok") is True
    k2 = c.get(f"/api/kits/{kit_id}").json()
    prompts = [q["prompt"] for q in k2["kit"]["questions"]]
    if qs:
        assert "hand-edited" in prompts
    # edited brief -> proposal
    c.patch(f"/api/kits/{kit_id}/brief/x", json={"summary": "my take"})
    p = c.post(f"/api/kits/{kit_id}/sections/brief/regenerate").json()
    assert "proposal" in p


def test_practice_queue_review_summary_and_check():
    c = authed()
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 2})
    kit_id = r.json()["kit_id"]
    import time
    for _ in range(50):
        time.sleep(0.1)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            break
    q = c.get(f"/api/kits/{kit_id}/practice/queue")
    assert q.status_code == 200
    cards = k["kit"].get("flashcards", [])
    if cards:
        c.post(f"/api/kits/{kit_id}/practice/reviews",
               json={"flashcard_id": cards[0]["id"], "confidence": 3})
        s = c.get(f"/api/kits/{kit_id}/practice/summary").json()
        assert s["covered"] >= 1
    if k["kit"].get("questions"):
        chk = c.post(f"/api/kits/{kit_id}/practice/check",
                     json={"question_id": k["kit"]["questions"][0]["id"], "answer": "some answer"}).json()
        assert "results" in chk


def test_batch_contract(tmp_path=None):
    import asyncio
    cases = [{"id": "a", "jd": "Need Python. Required: Python.", "company_url": "", "days": 1},
             {"id": "b", "jd": "", "company_url": "", "days": 1}]
    inp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    out = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(cases, open(inp.name, "w"))
    inp.close(); out.close()
    rc = asyncio.run(evalmod.main_async(inp.name, out.name))
    assert rc == 0
    payload = json.load(open(out.name))
    assert payload["version"] == "1.0" and "generated_at" in payload
    by_id = {e["id"]: e for e in payload["kits"]}
    assert by_id["a"]["status"] == "ok" and by_id["a"]["kit"] is not None
    assert by_id["b"]["status"] == "failed" and by_id["b"]["kit"] is None
    # per-case days honoured
    assert by_id["a"]["kit"]["schedule"]["days_available"] == 1


def test_reorder_moves_and_rebalances_long_keys():
    from app.domain.ordering import KEY_LENGTH_LIMIT
    c = authed()
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": 2})
    kit_id = r.json()["kit_id"]
    import time
    for _ in range(50):
        time.sleep(0.1)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            break
    q1 = c.post(f"/api/kits/{kit_id}/questions",
                json={"prompt": "First", "answer_outline": "O", "requirement_ids": [], "category": "technical", "difficulty": 1}).json()
    q2 = c.post(f"/api/kits/{kit_id}/questions",
                json={"prompt": "Second", "answer_outline": "O", "requirement_ids": [], "category": "technical", "difficulty": 1}).json()
    # move second to front
    moved = c.post(f"/api/kits/{kit_id}/questions/reorder", json={"id": q2["id"], "after_id": None}).json()
    k = c.get(f"/api/kits/{kit_id}").json()
    tech = sorted([q for q in k["kit"]["questions"] if q["category"] == "technical"],
                  key=lambda q: q["_meta"]["order"])
    assert tech[0]["id"] == q2["id"]
    # force a long key directly, then reorder: the category is rebalanced to short keys
    from app.domain.ordering import KEY_LENGTH_LIMIT
    from app.persistence.memory import DB
    doc = DB.kits[kit_id]
    tech_qs = [q for q in doc["kit"]["questions"] if q["category"] == "technical"]
    tech_qs[0]["_meta"]["order"] = "h" + "0" * (KEY_LENGTH_LIMIT + 5)
    c.post(f"/api/kits/{kit_id}/questions/reorder", json={"id": tech_qs[1]["id"], "after_id": None})
    k2 = c.get(f"/api/kits/{kit_id}").json()
    orders = [q["_meta"]["order"] for q in k2["kit"]["questions"] if q["category"] == "technical"]
    assert len(set(orders)) == len(orders)
    assert all(len(o) <= KEY_LENGTH_LIMIT for o in orders)
