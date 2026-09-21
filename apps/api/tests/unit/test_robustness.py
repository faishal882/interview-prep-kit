"""Phase 3: days validation, case ids, sanitisation, over-long JD, deadlines, batch file."""
import asyncio
import json
import os

os.environ["FAKE_LLM"] = "1"

import pytest

from app.cli import evaluate as evalmod
from app.domain.errors import Codes, KitError
from app.llm.fake import FakeLLM
from app.pipeline import orchestrator as orch
from app.pipeline.sanitize import clamp_difficulty, sanitize_flashcard, sanitize_question


def _deps(llm=None):
    return {"llm": llm or FakeLLM(), "allow_private": True, "max_pages": 2, "depth": 1,
            "step_timeout_s": 5, "overall_timeout_s": 30}


def test_days_bounds_fail_or_succeed():
    for bad in (0, -3, 61, "x", True):
        with pytest.raises(KitError) as ei:
            asyncio.run(orch.run_case({"jd": "Engineer\nRequired: Python.", "company_url": "", "days": bad}, _deps()))
        assert ei.value.code == Codes.INVALID_INPUT
    for good in (1, 60):
        kit, _ = asyncio.run(orch.run_case({"jd": "Engineer\nRequired: Python.", "company_url": "", "days": good}, _deps()))
        assert kit["schedule"]["days_available"] == good


def test_duplicate_ids_made_unique_with_note():
    cases = evalmod.normalize_cases([{"id": "a", "jd": "x"}, {"id": "a", "jd": "y"}, {"jd": "z"}])
    assert [c["id"] for c in cases] == ["a", "a-2", "case-2"]
    assert cases[1]["_note"] == "duplicate id made unique"
    with pytest.raises(KitError):
        evalmod.normalize_cases({"not": "a list"})
    with pytest.raises(KitError):
        evalmod.normalize_cases(["not-a-dict"])


def test_sanitize_clamps_or_drops():
    valid = {"r1"}
    assert sanitize_question({"prompt": "p", "answer_outline": "o", "requirement_ids": ["r1"], "difficulty": 99}, valid, "technical")["difficulty"] == 2
    assert sanitize_question({"prompt": "p", "answer_outline": "", "requirement_ids": ["r1"]}, valid, "technical") is None
    assert sanitize_question({"prompt": "", "answer_outline": "o", "requirement_ids": ["r1"]}, valid, "technical") is None
    assert sanitize_question({"prompt": "p", "answer_outline": "o", "requirement_ids": ["rx"]}, valid, "technical") is None
    assert sanitize_question({"prompt": "p", "answer_outline": "o", "requirement_ids": ["r1"], "difficulty": "x"}, valid, "technical")["difficulty"] == 2
    assert sanitize_flashcard({"front": "f", "back": "b", "requirement_ids": ["r1"]}, valid) is not None
    assert sanitize_flashcard({"front": "", "back": "b"}, valid) is None
    assert clamp_difficulty(True) == 2 and clamp_difficulty(3) == 3


def test_over_long_description_warned_not_silent():
    jd = "Engineer\nRequired: Python. " + ("x" * (orch.MAX_JD_CHARS + 100))
    script = {"REQUIREMENTS": [{"requirements": [{"text": "Python", "evidence": "Python", "section_heading": ""}],
                                "responsibilities": [], "role": {}}]}
    kit, _ = asyncio.run(orch.run_case({"jd": jd, "company_url": "", "days": 1},
                                       {"llm": FakeLLM(script), "allow_private": True}))
    assert any("truncated" in w for w in kit["warnings"])
    assert kit["source"]["jd_chars"] == orch.MAX_JD_CHARS < len(jd)


class HangingProvider:
    name = "hang"

    def __init__(self, script, hang_on=()):
        self._llm = FakeLLM(script)
        self._hang = hang_on

    async def generate_structured(self, prompt, schema):
        for marker in self._hang:
            if marker in prompt:
                await asyncio.sleep(30)
        return await self._llm.generate_structured(prompt, schema)


def _req_script():
    return {"REQUIREMENTS": [{"requirements": [{"text": "Python", "evidence": "Python", "section_heading": ""}],
                              "responsibilities": [], "role": {"title": "Engineer"}}]}


def test_hung_late_step_returns_partial_ok():
    llm = HangingProvider(_req_script(), hang_on=("QUESTIONS:", "FLASHCARDS", "BRIEF"))
    deps = {"llm": llm, "allow_private": True, "step_timeout_s": 0.2, "overall_timeout_s": 20}
    kit, _ = asyncio.run(orch.run_case({"jd": "Engineer\nRequired: Python.", "company_url": "", "days": 2}, deps))
    assert kit["role"]["requirements"]
    assert any("failed" in w or "timed out" in w or "deadline" in w for w in kit["warnings"]) or kit["coverage"]["uncovered_requirement_ids"]


def test_hung_extraction_yields_timeout():
    llm = HangingProvider({}, hang_on=("REQUIREMENTS",))
    deps = {"llm": llm, "allow_private": True, "step_timeout_s": 0.2, "overall_timeout_s": 5}
    with pytest.raises(KitError) as ei:
        asyncio.run(orch.run_case({"jd": "Engineer\nRequired: Python.", "company_url": "", "days": 2}, deps))
    assert ei.value.code == Codes.TIMEOUT


def test_malformed_cases_file_fails_before_work(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert asyncio.run(evalmod.main_async(str(bad), str(tmp_path / "o.json"))) == 2
    notlist = tmp_path / "notlist.json"
    notlist.write_text(json.dumps({"a": 1}))
    assert asyncio.run(evalmod.main_async(str(notlist), str(tmp_path / "o2.json"))) == 2
    assert not (tmp_path / "o2.json").exists()


def test_batch_days_and_empty_jd_are_failed_entries():
    async def go():
        deps = _deps()
        sem = asyncio.Semaphore(2)
        r1 = await evalmod.run_one({"id": "d0", "jd": "Engineer\nRequired: Python.", "days": 0}, deps, sem)
        r2 = await evalmod.run_one({"id": "e", "jd": "  ", "days": 2}, deps, sem)
        return r1, r2
    r1, r2 = asyncio.run(go())
    assert r1["status"] == "failed" and r1["error"]["code"] == Codes.INVALID_INPUT
    assert r2["status"] == "failed" and r2["error"]["code"] == Codes.INVALID_INPUT
