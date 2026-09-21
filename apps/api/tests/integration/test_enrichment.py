"""Phase 2: company-name fallback, hiring-typed signals, hiring-page log."""
import asyncio
import os

os.environ["FAKE_LLM"] = "1"

from app.llm.fake import FakeLLM
from app.pipeline.orchestrator import run_case
from app.pipeline.steps import signals as signals_mod
from app.retrieval.page_typer import (
    domain_label,
    find_hiring_page,
    page_type,
    resolve_company_name,
    site_declared_name,
)

from .fixture_sites import ACME_HIRING, ACME_INDEX, NOHIRING_INDEX, serve


def test_page_typing_hiring_vs_about():
    hiring = {"final_url": "http://acme.test/zz-careers-hidden-42", "title": "", "text": "jobs"}
    assert page_type(hiring) == "hiring"
    about = {"final_url": "http://acme.test/about", "title": "About us",
             "text": "We value coding and culture and values."}
    assert page_type(about) == "other"
    titled = {"final_url": "http://acme.test/x", "title": "How we hire", "text": "hello"}
    assert page_type(titled) == "hiring"


def test_about_page_words_do_not_trigger_signals():
    pages = [{"final_url": "http://acme.test/about", "title": "About",
              "text": "We love coding and our values. Join our culture of mentorship."}]
    flags = signals_mod.analyze(pages)
    assert set(flags.values()) <= {"false", "unknown"}
    assert "true" not in flags.values()
    assert find_hiring_page(pages) is None
    # a hiring page with plain text yields explicit false, not unknown
    plain = [{"final_url": "http://acme.test/jobs", "title": "Jobs",
              "text": "We are hiring engineers. Apply now."}]
    flags2 = signals_mod.analyze(plain)
    assert flags2 == {"has_take_home": "false", "has_system_design_round": "false",
                      "has_coding_round": "false", "has_behavioural_round": "false"}


def test_hiring_page_take_home_sets_only_that_signal():
    pages = [{"final_url": "http://acme.test/careers", "title": "Careers",
              "text": "Our process starts with a take-home assignment."}]
    flags = signals_mod.analyze(pages)
    assert flags["has_take_home"] == "true"
    assert flags["has_system_design_round"] == "false"
    assert flags["has_coding_round"] == "false"
    assert find_hiring_page(pages) == "http://acme.test/careers"


def test_no_pages_yields_unknown_signals():
    assert signals_mod.analyze([]) == {"has_take_home": "unknown", "has_system_design_round": "unknown",
                                       "has_coding_round": "unknown", "has_behavioural_round": "unknown"}


def test_company_name_fallback_chain():
    assert resolve_company_name("Initech", [], "http://x.test") == ("Initech", "jd")
    pages = [{"final_url": "http://127.0.0.1:1/", "depth": 0, "title": "Acme Corp",
              "site_name": "Acme", "text": ""}]
    assert resolve_company_name("", pages, "http://whatever.test") == ("Acme", "site")
    assert site_declared_name([{"depth": 0, "title": "Acme — Careers", "site_name": "", "text": ""}]) == "Acme"
    assert resolve_company_name("", [], "https://careers.bigco.com/jobs") == ("Bigco", "domain")
    assert resolve_company_name("", [], "") == ("", "none")
    assert domain_label("https://shop.example.co.uk/") == "Example"


def _script(requirements, questions=(), flashcards=(), brief=None):
    script = {
        "REQUIREMENTS": [{"requirements": requirements, "responsibilities": [], "role": {"title": "Engineer"}}],
        "QUESTIONS:": [{"questions": list(q)} for q in questions] or [{"questions": []}],
        "FLASHCARDS": [{"flashcards": list(flashcards)}],
    }
    if brief:
        script["BRIEF"] = [brief]
    return script


def test_description_without_company_uses_site_name():
    srv = serve({"/": (200, "text/html", ACME_INDEX),
                 "/about": (200, "text/html", "<html><body>about</body></html>")})
    port = srv.server_address[1]
    jd = "Engineer\nRequired: Python."
    script = _script([{"text": "Python", "evidence": "Python", "section_heading": ""}],
                     [[{"prompt": "Q", "answer_outline": "O", "outline_points": [],
                        "requirement_ids": ["r1"], "difficulty": 1}]])
    deps = {"llm": FakeLLM(script), "allow_private": True, "max_pages": 6, "depth": 1}
    kit, log = asyncio.run(run_case({"jd": jd, "company_url": f"http://127.0.0.1:{port}/", "days": 2}, deps))
    srv.shutdown()
    assert kit["source"]["company"] == "Acme"
    assert log["company_name_source"] == "site"


def test_research_log_names_hiring_page_or_none():
    srv = serve({"/": (200, "text/html", ACME_INDEX),
                 "/zz-careers-hidden-42": (200, "text/html", ACME_HIRING)})
    port = srv.server_address[1]
    jd = "Engineer\nRequired: Python."
    script = _script([{"text": "Python", "evidence": "Python", "section_heading": ""}])
    deps = {"llm": FakeLLM(script), "allow_private": True, "max_pages": 6, "depth": 1}
    _kit, log = asyncio.run(run_case({"jd": jd, "company_url": f"http://127.0.0.1:{port}/", "days": 2}, deps))
    srv.shutdown()
    assert log["hiring_page"] and "zz-careers-hidden-42" in log["hiring_page"]

    srv2 = serve({"/": (200, "text/html", NOHIRING_INDEX),
                  "/about": (200, "text/html", "<html><body>About: we love coding and values.</body></html>")})
    port2 = srv2.server_address[1]
    deps2 = {"llm": FakeLLM(script), "allow_private": True, "max_pages": 6, "depth": 1}
    kit2, log2 = asyncio.run(run_case({"jd": jd, "company_url": f"http://127.0.0.1:{port2}/", "days": 2}, deps2))
    srv2.shutdown()
    assert log2["hiring_page"] is None
    assert "true" not in kit2["research_log"]["hiring_signals"].values()
