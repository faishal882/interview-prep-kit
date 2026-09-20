"""Full pipeline integration with FakeLLM + fixture sites."""
import asyncio
import os

os.environ["FAKE_LLM"] = "1"

from app.llm.fake import FakeLLM
from app.pipeline.orchestrator import run_case
from app.validation.kit_validator import validate_kit

from .fixture_sites import ACME_HIRING, ACME_INDEX, NOHIRING_INDEX, serve


def deps_for(script=None):
    llm = FakeLLM(script)
    return {"llm": llm, "allow_private": True, "max_pages": 12, "depth": 2}


def test_buried_hiring_page_found_by_ranked_links():
    srv = serve({"/acme/": (200, "text/html", ACME_INDEX),
                 "/about": (200, "text/html", "<html><body>About Acme</body></html>"),
                 "/zz-careers-hidden-42": (200, "text/html", ACME_HIRING),
                 "/blog": (200, "text/html", "<html><body>blog</body></html>")})
    port = srv.server_address[1]
    jd = "Backend Engineer\nRequired: 5+ years with Python. Bonus: Kubernetes experience."
    script = {
        "REQUIREMENTS": [{"requirements": [
            {"text": "5+ years with Python", "evidence": "5+ years with Python", "section_heading": "Required"},
            {"text": "Kubernetes experience", "evidence": "Kubernetes experience", "section_heading": "Bonus"}],
            "responsibilities": [], "role": {"title": "Backend Engineer"}}],
        "QUESTIONS:": [
            {"questions": [{"prompt": "Explain Python GIL", "answer_outline": "Outline.",
                            "outline_points": ["GIL"], "requirement_ids": ["r1"], "difficulty": 2}]},
            {"questions": []}, {"questions": []},
            {"questions": [{"prompt": "K8s follow-up", "answer_outline": "Outline.",
                            "outline_points": [], "requirement_ids": ["r2"], "difficulty": 1}]},
        ],
        "FLASHCARDS": [{"flashcards": [{"front": "Python", "back": "Lang", "requirement_ids": ["r1"]}]}],
        "BRIEF": [{"summary": "Acme builds widgets.", "what_they_do": "Widgets.", "hiring_process": "Take-home then system design."}],
    }
    kit, _log = asyncio.run(run_case({"jd": jd, "company_url": f"http://127.0.0.1:{port}/acme/", "days": 3}, deps_for(script)))
    srv.shutdown()
    assert validate_kit(kit) == []
    assert any("zz-careers" in u or str(port) in u for u in kit["source"]["pages_used"])
    assert kit["role"]["requirements"][0]["priority"] == "must"
    assert kit["role"]["requirements"][1]["priority"] == "nice"
    assert kit["coverage"]["uncovered_requirement_ids"] == []


def test_nohiring_404_timeout_yield_ok_kits():
    srv404 = serve({})
    p404 = srv404.server_address[1]
    jd = "Engineer\nRequired: Python."
    script = {
        "REQUIREMENTS": [{"requirements": [{"text": "Python", "evidence": "Python", "section_heading": ""}],
                                           "responsibilities": [], "role": {}}],
        "QUESTIONS:": [{"questions": [{"prompt": "Q", "answer_outline": "O", "outline_points": [],
                                       "requirement_ids": ["r1"], "difficulty": 1}]}],
        "FLASHCARDS": [{"flashcards": []}],
    }
    kit, log = asyncio.run(run_case({"jd": jd, "company_url": f"http://127.0.0.1:{p404}/missing", "days": 2}, deps_for(script)))
    srv404.shutdown()
    assert validate_kit(kit) == []
    assert "could not retrieve" in kit["company_brief"]["summary"].lower()
    assert kit["source"]["pages_used"] == []


def test_second_pass_closes_gap():
    jd = "Engineer\nRequired: Python. Required: Docker."
    script = {
        "REQUIREMENTS": [{"requirements": [
            {"text": "Python", "evidence": "Python", "section_heading": ""},
            {"text": "Docker", "evidence": "Docker", "section_heading": ""}],
            "responsibilities": [], "role": {}}],
        "QUESTIONS:": [
            {"questions": [{"prompt": "Python Q", "answer_outline": "O", "outline_points": [],
                            "requirement_ids": ["r1"], "difficulty": 1}]},
            {"questions": [{"prompt": "Docker Q", "answer_outline": "O", "outline_points": [],
                            "requirement_ids": ["r2"], "difficulty": 1}]},
            {"questions": []},
        ],
        "FLASHCARDS": [{"flashcards": []}],
    }
    kit, _ = asyncio.run(run_case({"jd": jd, "company_url": "", "days": 2},
                                  {**deps_for(script), "skip_retrieval": True}))
    assert kit["coverage"]["passes"] >= 2
    assert kit["coverage"]["uncovered_requirement_ids"] == []


def test_thin_jd_flagged_and_invalid_json_repaired():
    from app.llm.router import generate as gen
    from app.llm.base import ProviderError

    class ExplodingLLM:
        name = "boom"
        def __init__(self):
            self.n = 0

        async def generate_structured(self, prompt, schema):
            self.n += 1
            if self.n == 1:
                return {"wrong": []}  # missing required key -> triggers repair
            return {"requirements": [], "responsibilities": [], "role": {}}

    llm = ExplodingLLM()
    raw, _ = asyncio.run(gen(llm, "REQUIREMENTS test", {"type": "object", "required": ["requirements"], "properties": {}}))
    assert llm.n == 2  # exactly one repair attempt

    kit, _ = asyncio.run(run_case({"jd": "Hi", "company_url": "", "days": 1},
                                  {**deps_for({"REQUIREMENTS": [{"requirements": [], "responsibilities": [], "role": {}}],
                                              "QUESTIONS:": [{"questions": []}],
                                              "FLASHCARDS": [{"flashcards": []}]}), "skip_retrieval": True}))
    assert kit["research_log"]["thin_jd"] is True
    assert any("thin" in w for w in kit["warnings"])
