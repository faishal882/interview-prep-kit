"""Phase 10: real regeneration with the scripted model.

Covers: protected survival, in-flight edit survival under concurrency, no
duplicates, genuine brief Proposal + accept/reject, targeted single-Requirement
generation, failure leaves the Kit untouched, coverage recomputed, real jobs.
"""
import asyncio
import copy
import time
import uuid

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.store import get_store
from app.regen import service as regen_service

from .fixture_sites import ACME_HIRING, ACME_INDEX, serve

SCRIPT = {
    "QUESTIONS:": [
        {"questions": [
            {"prompt": "Explain the GIL", "answer_outline": "Outline A.", "outline_points": ["GIL"],
             "requirement_ids": ["r1"], "difficulty": 2},
            {"prompt": "Describe asyncio", "answer_outline": "Outline B.", "outline_points": [],
             "requirement_ids": ["r1"], "difficulty": 2}]},
        {"questions": []},
    ],
    "BRIEF": [{"summary": "Acme builds widgets.", "what_they_do": "Widgets.",
               "hiring_process": "Take-home then system design."}],
}

REQS = [
    {"id": "r1", "text": "5+ years with Python", "kind": "technical", "priority": "must",
     "_meta": {"origin": "generated", "edited": False, "pinned": False, "rev": 1, "order": "", "gen_run": None}},
    {"id": "r2", "text": "Kubernetes experience", "kind": "technical", "priority": "nice",
     "_meta": {"origin": "generated", "edited": False, "pinned": False, "rev": 1, "order": "", "gen_run": None}},
]


def authed():
    c = TestClient(create_app())
    c.post("/api/auth/register", json={"email": f"rg-{uuid.uuid4().hex[:6]}@t.co", "password": "password123"})
    return c


def ready_kit(c, days=3, company_url=""):
    r = c.post("/api/kits", json={"jd": "Backend Engineer\nRequired: 5+ years with Python. Bonus: Kubernetes experience.",
                                  "company_url": company_url, "days": days})
    kit_id = r.json()["kit_id"]
    for _ in range(60):
        time.sleep(0.2)
        k = c.get(f"/api/kits/{kit_id}").json()
        if k.get("status") == "ready":
            return kit_id, k
    raise AssertionError(f"kit never ready: {k}")


def seed_questions(c, kit_id, specs):
    """Write pipeline-shaped questions (generated _meta) straight to the store."""
    store = get_store()
    doc = asyncio.run(store.kits.get(kit_id))
    doc["kit"]["role"]["requirements"] = copy.deepcopy(REQS)
    doc["kit"]["questions"] = [
        {"id": qid, "requirement_ids": rids, "category": "technical", "prompt": prompt,
         "answer_outline": "Outline.", "difficulty": 2, "outline_points": [],
         "_meta": {"origin": "generated", "edited": edited, "pinned": False,
                   "rev": 2 if edited else 1, "order": order, "gen_run": None}}
        for qid, rids, prompt, edited, order in specs
    ]
    doc["kit"]["coverage"] = {"uncovered_requirement_ids": ["r2"], "passes": 1}
    asyncio.run(store.kits.save(doc))
    return c.get(f"/api/kits/{kit_id}").json()


def wait_job(c, job_id, timeout=60):
    for _ in range(int(timeout * 2)):
        time.sleep(0.5)
        j = c.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "failed"):
            return j
    raise AssertionError(f"job {job_id} never finished")


def deps_for(llm):
    return {"llm": llm, "allow_private": True, "max_pages": 4, "depth": 1,
            "step_timeout_s": 10}


def test_category_regen_replaces_only_unprotected_with_genuine_prompts():
    from app.llm.fake import FakeLLM
    c = authed()
    kit_id, _ = ready_kit(c)
    k = seed_questions(c, kit_id, [
        ("qold", ["r1"], "Old probe question", False, "h"),
        ("qkeep", ["r1"], "hand-edited keeper", True, "i"),
    ])
    assert len([q for q in k["kit"]["questions"] if q["category"] == "technical"]) == 2
    events = []
    out = asyncio.run(regen_service.regenerate_category(
        get_store(), kit_id, "technical", deps_for(FakeLLM(SCRIPT)), events.append))
    assert out["fresh"] >= 1
    k2 = c.get(f"/api/kits/{kit_id}").json()
    prompts = [q["prompt"] for q in k2["kit"]["questions"] if q["category"] == "technical"]
    assert "hand-edited keeper" in prompts  # protected survives
    assert "Old probe question" not in prompts  # unprotected replaced
    assert not any("Regenerated technical question" in p or "(refreshed)" in p for p in prompts)
    assert any(p in ("Explain the GIL", "Describe asyncio") for p in prompts)  # genuine model text
    tech = [p.strip().lower() for p in prompts]
    assert len(set(tech)) == len(tech)  # no duplicates
    assert "uncovered_requirement_ids" in k2["kit"]["coverage"]


def test_concurrent_edit_survives_regeneration_run():
    from app.llm.fake import FakeLLM
    c = authed()
    kit_id, _ = ready_kit(c)
    seed_questions(c, kit_id, [("qold", ["r1"], "Old probe question", False, "h")])

    class Slow(FakeLLM):
        async def generate_structured(self, prompt, schema):
            if "QUESTIONS:" in prompt:
                await asyncio.sleep(2)
            return await super().generate_structured(prompt, schema)

    async def go():
        task = asyncio.create_task(regen_service.regenerate_category(
            get_store(), kit_id, "technical", deps_for(Slow(SCRIPT)), lambda e: None))
        await asyncio.sleep(0.5)
        # unprotected item edited mid-run bumps its rev: must survive the commit
        store = get_store()
        doc = await store.kits.get(kit_id)
        q = next(q for q in doc["kit"]["questions"] if q["id"] == "qold")
        q["prompt"] = "mid-run edit"
        q["_meta"]["edited"] = True
        q["_meta"]["rev"] += 1
        await store.kits.save(doc)
        return await task

    asyncio.run(go())
    k2 = c.get(f"/api/kits/{kit_id}").json()
    assert "mid-run edit" in [q["prompt"] for q in k2["kit"]["questions"]]


def test_failure_leaves_kit_untouched():
    from app.llm.base import ProviderError
    c = authed()
    kit_id, _ = ready_kit(c)
    seed_questions(c, kit_id, [("qold", ["r1"], "Old probe question", False, "h")])

    class Dead:
        name = "dead"

        async def generate_structured(self, prompt, schema):
            raise ProviderError("boom", status=500, transient=True)

    before = copy.deepcopy((c.get(f"/api/kits/{kit_id}").json())["kit"])
    try:
        asyncio.run(regen_service.regenerate_category(
            get_store(), kit_id, "technical", deps_for(Dead()), lambda e: None))
    except Exception:
        pass
    else:
        raise AssertionError("should have raised")
    after = (c.get(f"/api/kits/{kit_id}").json())["kit"]
    assert before == after


def test_brief_proposal_is_genuine_and_decided():
    from app.llm.fake import FakeLLM
    srv = serve({"/": (200, "text/html", ACME_INDEX),
                 "/zz-careers-hidden-42": (200, "text/html", ACME_HIRING)})
    port = srv.server_address[1]
    c = authed()
    kit_id, _ = ready_kit(c, company_url=f"http://127.0.0.1:{port}/")
    c.patch(f"/api/kits/{kit_id}/brief/x", json={"rev": 0, "summary": "my take"})
    out = asyncio.run(regen_service.regenerate_brief(
        get_store(), kit_id, deps_for(FakeLLM(SCRIPT)), lambda e: None))
    srv.shutdown()
    assert "proposal" in out and "regenerated proposal" not in out["proposal"]["summary"].lower()
    assert out["proposal"]["summary"] == "Acme builds widgets."
    # current text untouched until accepted
    assert c.get(f"/api/kits/{kit_id}").json()["kit"]["company_brief"]["summary"] == "my take"
    c.post(f"/api/kits/{kit_id}/sections/brief/accept")
    assert c.get(f"/api/kits/{kit_id}").json()["kit"]["company_brief"]["summary"] == "Acme builds widgets."


def test_untouched_brief_replaced_directly():
    from app.llm.fake import FakeLLM
    srv = serve({"/": (200, "text/html", ACME_INDEX)})
    port = srv.server_address[1]
    c = authed()
    kit_id, _ = ready_kit(c, company_url=f"http://127.0.0.1:{port}/")
    out = asyncio.run(regen_service.regenerate_brief(
        get_store(), kit_id, deps_for(FakeLLM(SCRIPT)), lambda e: None))
    srv.shutdown()
    assert out == {"replaced": True}
    assert c.get(f"/api/kits/{kit_id}").json()["kit"]["company_brief"]["summary"] == "Acme builds widgets."


def test_targeted_generation_covers_exactly_one_requirement():
    from app.llm.fake import FakeLLM
    c = authed()
    kit_id, k = ready_kit(c)
    req = c.post(f"/api/kits/{kit_id}/requirements",
                 json={"text": "Must know Rust", "kind": "technical", "priority": "must"}).json()
    before_ids = {q["id"] for q in k["kit"]["questions"]}
    before_prompts = {q["prompt"] for q in k["kit"]["questions"]}
    script = {"QUESTIONS:": [{"questions": [{"prompt": "Rust ownership?", "answer_outline": "O.",
                                              "outline_points": [], "requirement_ids": [req["id"]],
                                              "difficulty": 2}]}]}
    out = asyncio.run(regen_service.generate_for_requirement(
        get_store(), kit_id, req["id"], deps_for(FakeLLM(script)), lambda e: None))
    assert len(out["question_ids"]) == 1
    k2 = c.get(f"/api/kits/{kit_id}").json()["kit"]
    new = [q for q in k2["questions"] if q["id"] not in before_ids]
    assert len(new) == 1 and req["id"] in new[0]["requirement_ids"]
    assert {q["prompt"] for q in k2["questions"] if q["id"] in before_ids} == before_prompts
    assert req["id"] not in k2["coverage"]["uncovered_requirement_ids"]


def test_regeneration_is_a_real_job_with_progress():
    c = authed()
    kit_id, _ = ready_kit(c)
    r = c.post(f"/api/kits/{kit_id}/sections/questions:technical/regenerate")
    assert r.status_code == 200
    job = wait_job(c, r.json()["job_id"])
    assert job["status"] == "done"
    assert job["kind"] == "sections:questions:technical"
    assert job["steps"] and job["steps"][0]["status"] == "done"
