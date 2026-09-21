"""Phase 9: schemas, ids, conflicts, pruning, stale precision, minutes, export."""
import time
import uuid

from fastapi.testclient import TestClient

from app.main import create_app


def authed():
    c = TestClient(create_app())
    c.post("/api/auth/register", json={"email": f"in-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    return c


def ready_kit(c, days=2):
    r = c.post("/api/kits", json={"jd": "Need Python. Required: Python.", "company_url": "", "days": days})
    kit_id = r.json()["kit_id"]
    for _ in range(60):
        time.sleep(0.1)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            return kit_id, k
    raise AssertionError(f"kit never ready: {k}")


def test_mass_assignment_and_values_rejected_unchanged():
    c = authed()
    kit_id, k = ready_kit(c)
    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"prompt": "Mine", "answer_outline": "O", "requirement_ids": [],
                     "category": "technical", "difficulty": 1}).json()
    before = c.get(f"/api/kits/{kit_id}").json()["kit"]["questions"]
    bad_bodies = [
        {"rev": q["_meta"]["rev"], "prompt": "x", "unknown_field": 1},
        {"rev": q["_meta"]["rev"], "category": "nope"},
        {"rev": q["_meta"]["rev"], "difficulty": 999},
        {"rev": q["_meta"]["rev"], "requirement_ids": ["r-missing"]},
        {"rev": q["_meta"]["rev"], "id": "hijack", "prompt": "x"},
        {"rev": q["_meta"]["rev"], "_meta": {"rev": 99}, "prompt": "x"},
        {"prompt": "no-rev"},
    ]
    for body in bad_bodies:
        r = c.patch(f"/api/kits/{kit_id}/questions/{q['id']}", json=body)
        assert r.status_code in (400, 409, 422), body
    after = c.get(f"/api/kits/{kit_id}").json()["kit"]["questions"]
    assert before == after
    # bad creates rejected too
    assert c.post(f"/api/kits/{kit_id}/questions",
                  json={"prompt": "x", "answer_outline": "O", "category": "nope"}).status_code == 422
    assert c.post(f"/api/kits/{kit_id}/questions",
                  json={"prompt": "x", "answer_outline": "O", "difficulty": 99}).status_code == 422


def test_ids_are_server_assigned():
    c = authed()
    kit_id, _ = ready_kit(c)
    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"id": "client-evil", "prompt": "Mine", "answer_outline": "O",
                     "requirement_ids": [], "category": "technical", "difficulty": 1})
    assert q.status_code == 422  # unknown field id rejected outright


def test_requirement_delete_prunes_and_flags():
    c = authed()
    kit_id, _ = ready_kit(c)
    req = c.post(f"/api/kits/{kit_id}/requirements",
                 json={"text": "Must know Go", "kind": "technical", "priority": "must"}).json()
    rid = req["id"]
    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"prompt": "Go?", "answer_outline": "O", "requirement_ids": [rid],
                     "category": "technical", "difficulty": 1}).json()
    f = c.post(f"/api/kits/{kit_id}/flashcards",
               json={"front": "Go?", "back": "Yes", "requirement_ids": [rid]}).json()
    out = c.delete(f"/api/kits/{kit_id}/requirements/{rid}").json()
    assert out["ok"] is True and q["id"] in out["flagged"]
    k = c.get(f"/api/kits/{kit_id}").json()["kit"]
    assert all(rid != r["id"] for r in k["role"]["requirements"])
    assert all(rid not in qq.get("requirement_ids", []) for qq in k["questions"])
    assert all(rid not in (ff.get("requirement_ids") or []) for ff in k["flashcards"])
    assert rid not in k["coverage"]["uncovered_requirement_ids"]
    # deleting again is a clean 404
    assert c.delete(f"/api/kits/{kit_id}/requirements/{rid}").status_code == 404
    _ = f


def test_stale_flag_only_for_schedule_affecting_changes():
    c = authed()
    kit_id, _ = ready_kit(c)

    def stale():
        return bool(c.get(f"/api/kits/{kit_id}").json().get("schedule_stale"))

    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"prompt": "Mine", "answer_outline": "O", "requirement_ids": [],
                     "category": "technical", "difficulty": 1}).json()
    assert stale() is True
    # clear via rebuild, then pin-only must not raise the banner
    c.post(f"/api/kits/{kit_id}/sections/schedule/regenerate")
    assert stale() is False
    c.patch(f"/api/kits/{kit_id}/questions/{q['id']}", json={"rev": q["_meta"]["rev"], "pinned": True})
    assert stale() is False
    # reorder alone does not raise it either
    c.post(f"/api/kits/{kit_id}/questions/reorder", json={"id": q["id"], "after_id": None})
    assert stale() is False
    # flashcard edits do not raise it
    fc = c.post(f"/api/kits/{kit_id}/flashcards",
                json={"front": "F?", "back": "B", "requirement_ids": []}).json()
    c.patch(f"/api/kits/{kit_id}/flashcards/{fc['id']}", json={"rev": fc["_meta"]["rev"], "front": "F2"})
    assert stale() is False
    # a material question edit does
    k = c.get(f"/api/kits/{kit_id}").json()
    cur = next(qq for qq in k["kit"]["questions"] if qq["id"] == q["id"])
    c.patch(f"/api/kits/{kit_id}/questions/{q['id']}",
            json={"rev": cur["_meta"]["rev"], "prompt": "Mine changed"})
    assert stale() is True


def test_minutes_correct_after_delete_and_move():
    c = authed()
    kit_id, k = ready_kit(c, days=1)
    from app.scheduling.allocator import day_minutes
    for day in k["kit"]["schedule"]["days"]:
        assert day["minutes"] == day_minutes(day["question_ids"], k["kit"]["questions"])
    q = c.post(f"/api/kits/{kit_id}/questions",
               json={"prompt": "Extra", "answer_outline": "O", "requirement_ids": [],
                     "category": "technical", "difficulty": 1}).json()
    # put it on day 1, then delete it: minutes must track
    c.patch(f"/api/kits/{kit_id}/schedule/days/1",
            json={"question_ids": k["kit"]["schedule"]["days"][0]["question_ids"] + [q["id"]]})
    k2 = c.get(f"/api/kits/{kit_id}").json()["kit"]
    assert k2["schedule"]["days"][0]["minutes"] == day_minutes(k2["schedule"]["days"][0]["question_ids"], k2["questions"])
    c.delete(f"/api/kits/{kit_id}/questions/{q['id']}")
    k3 = c.get(f"/api/kits/{kit_id}").json()["kit"]
    for day in k3["schedule"]["days"]:
        assert day["minutes"] == day_minutes(day["question_ids"], k3["questions"])


def test_export_strips_metadata_and_refuses_invalid():
    c = authed()
    kit_id, _ = ready_kit(c)
    out = c.get(f"/api/kits/{kit_id}/export").json()
    assert "_brief_meta" not in out
    assert all("_meta" not in q for q in out["questions"])
    assert all("_meta" not in f for f in out["flashcards"])
    assert all("_meta" not in r and "evidence" not in r for r in out["role"]["requirements"])
    # corrupt the stored kit behind the export's back: export must refuse, not serve
    from app.persistence.store import get_store
    import asyncio
    store = get_store()
    doc = asyncio.run(store.kits.get(kit_id))
    doc["kit"]["schedule"]["days"][0]["minutes"] = "lots"
    asyncio.run(store.kits.save(doc))
    bad = c.get(f"/api/kits/{kit_id}/export")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "KIT_INVALID"
