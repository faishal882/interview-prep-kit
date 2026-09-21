"""Real regeneration reusing the pipeline's own steps.

Every function builds its result fully in memory and commits with a single
document save at the end — a failure before the commit leaves the Kit
byte-for-byte untouched. Category merges keep protected items and any item
whose revision changed since the job started (in-flight edits survive).
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable

from app.coverage.checker import compute_gaps
from app.domain.errors import Codes, KitError
from app.domain.merge import merge_category
from app.domain.ordering import key_between
from app.llm.router import generate as llm_generate
from app.pipeline.sanitize import sanitize_question
from app.pipeline.steps.brief import BRIEF_SCHEMA, HONEST_BRIEF, brief_prompt, build_brief
from app.pipeline.steps.questions import CATEGORIES, QUESTION_SCHEMA, question_prompt, route
from app.retrieval.crawler import crawl
from app.retrieval.injection import looks_like_instruction


def _flags(research_log: dict) -> dict[str, bool]:
    stored = (research_log or {}).get("hiring_signals", {})
    return {k: (v == "true") for k, v in stored.items()}


def _evidence(research_log: dict) -> bool:
    return bool((research_log or {}).get("pages_used"))


async def _gen(llm: Any, prompt: str, schema: dict, deps: dict) -> dict:
    step_timeout = float(deps.get("step_timeout_s", 60))
    try:
        raw, _ = await asyncio.wait_for(
            llm_generate(llm, prompt, schema, limiter=deps.get("limiter")), timeout=step_timeout)
        return raw
    except asyncio.TimeoutError as exc:
        raise KitError(Codes.TIMEOUT, "regeneration step deadline exceeded") from exc


async def _recrawl(company_url: str, deps: dict, research_log: dict) -> list[dict]:
    if not company_url:
        return []
    pages, _ = await crawl(
        company_url, budget=deps.get("max_pages", 6), depth=deps.get("depth", 1),
        allow_private=bool(deps.get("allow_private")), client=deps.get("http_client"),
        cache=deps.get("page_cache"), research_log=research_log,
    )
    return [p for p in pages if not looks_like_instruction(p.get("text", ""))]


def _fresh_order_keys(kit: dict, category: str, count: int) -> list[str]:
    orders = [q.get("_meta", {}).get("order", "") for q in kit.get("questions", [])
              if q.get("category") == category and q.get("_meta", {}).get("order")]
    cur = max(orders) if orders else None
    out = []
    for _ in range(count):
        cur = key_between(cur, None)
        out.append(cur)
    return out


async def regenerate_brief(store, kit_id: str, deps: dict, on_event: Callable[[dict], None]) -> dict:
    """Returns {'proposal': ...} when protected, {'replaced': True} otherwise."""
    doc = await store.kits.get(kit_id)
    kit = doc.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    on_event({"step": "regenerate:brief", "status": "running"})
    log: dict[str, Any] = {"fetches": [], "pages_fetched": []}
    pages = await _recrawl((doc.get("input") or {}).get("company_url", ""), deps, log)
    pages_used = [p["final_url"] for p in pages if p.get("text")]
    if pages:
        raw = await _gen(deps["llm"], brief_prompt([p.get("text", "") for p in pages]), BRIEF_SCHEMA, deps)
        new_brief = build_brief(raw, pages_used)
    else:
        new_brief = dict(HONEST_BRIEF)
    meta = kit.get("_brief_meta", {})
    if meta.get("edited") or meta.get("pinned"):
        doc.setdefault("proposals", {})["brief"] = {**new_brief, "status": "proposal"}
        await store.kits.save(doc)
        on_event({"step": "regenerate:brief", "status": "done", "message": "proposal ready"})
        return {"proposal": doc["proposals"]["brief"]}
    kit["company_brief"] = new_brief
    await store.kits.save(doc)
    on_event({"step": "regenerate:brief", "status": "done", "message": "brief replaced"})
    return {"replaced": True}


async def regenerate_category(store, kit_id: str, category: str, deps: dict,
                              on_event: Callable[[dict], None]) -> dict:
    if category not in CATEGORIES:
        raise KitError(Codes.NOT_FOUND, "unknown category")
    doc = await store.kits.get(kit_id)
    kit = doc.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    on_event({"step": f"regenerate:{category}", "status": "running"})
    snapshot = {q["id"]: q.get("_meta", {}).get("rev", 1) for q in kit["questions"]}
    research_log = kit.get("research_log", {})
    flags = _flags(research_log)
    routed = route(kit["role"]["requirements"], flags, _evidence(research_log))
    reqs = routed.get(category, [])
    kept_prompts = [q.get("prompt", "") for q in kit["questions"] if q.get("category") == category]
    fresh: list[dict] = []
    if reqs:
        prompt = question_prompt(category, reqs, flags, kept_prompts)
        try:
            raw = await _gen(deps["llm"], prompt, QUESTION_SCHEMA, deps)
        except KitError:
            raise
        except Exception as exc:
            raise KitError(Codes.LLM_UNAVAILABLE, f"category generation failed: {exc}") from exc
        valid = {r["id"] for r in kit["role"]["requirements"]}
        for item in (raw.get("questions") or [])[:10]:
            clean = sanitize_question(item, valid, category)
            if clean is None or clean["prompt"] in kept_prompts:
                continue
            clean["id"] = f"q-{uuid.uuid4().hex[:6]}"
            clean["_meta"] = {"origin": "generated", "edited": False, "pinned": False,
                              "rev": 1, "order": "", "gen_run": None}
            fresh.append(clean)
            kept_prompts.append(clean["prompt"])
    # atomic commit against a fresh read: in-flight edits survive via snapshot revs
    latest = await store.kits.get(kit_id)
    latest_kit = latest.get("kit")
    if not latest_kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    current_cat = [q for q in latest_kit["questions"] if q.get("category") == category]
    others = [q for q in latest_kit["questions"] if q.get("category") != category]
    merged = merge_category(current_cat, fresh, snapshot)
    orders = _fresh_order_keys({"questions": merged}, category, sum(1 for q in merged if not q.get("_meta", {}).get("order")))
    it = iter(orders)
    for q in merged:
        if not q.get("_meta", {}).get("order"):
            q["_meta"]["order"] = next(it)
    latest_kit["questions"] = others + merged
    reqs_all = [r["id"] for r in latest_kit["role"]["requirements"]]
    latest_kit.setdefault("coverage", {})["uncovered_requirement_ids"] = compute_gaps(reqs_all, latest_kit["questions"])
    await store.kits.save(latest)
    on_event({"step": f"regenerate:{category}", "status": "done",
              "message": f"{len(fresh)} new questions"})
    return {"ok": True, "fresh": len(fresh)}


async def generate_for_requirement(store, kit_id: str, requirement_id: str, deps: dict,
                                   on_event: Callable[[dict], None]) -> dict:
    doc = await store.kits.get(kit_id)
    kit = doc.get("kit")
    if not kit:
        raise KitError(Codes.NOT_FOUND, "kit not ready")
    req = next((r for r in kit["role"]["requirements"] if r.get("id") == requirement_id), None)
    if not req:
        raise KitError(Codes.NOT_FOUND, "requirement not found")
    on_event({"step": f"generate:{requirement_id}", "status": "running"})
    research_log = kit.get("research_log", {})
    flags = _flags(research_log)
    routed = route([req], flags, _evidence(research_log))
    category = next((c for c in CATEGORIES if routed.get(c)), "technical")
    kept = [q.get("prompt", "") for q in kit["questions"]]
    prompt = question_prompt(category, [req], flags, kept)
    try:
        raw = await _gen(deps["llm"], prompt, QUESTION_SCHEMA, deps)
    except KitError:
        raise
    except Exception as exc:
        raise KitError(Codes.LLM_UNAVAILABLE, f"targeted generation failed: {exc}") from exc
    valid = {r["id"] for r in kit["role"]["requirements"]}
    added = []
    orders = _fresh_order_keys(kit, category, 3)
    for item in (raw.get("questions") or [])[:3]:
        clean = sanitize_question(item, valid, category)
        if clean is None or requirement_id not in clean["requirement_ids"]:
            continue
        if clean["prompt"] in kept:
            continue
        clean["id"] = f"q-{uuid.uuid4().hex[:6]}"
        clean["_meta"] = {"origin": "generated", "edited": False, "pinned": False,
                          "rev": 1, "order": orders[len(added)], "gen_run": None}
        kit["questions"].append(clean)
        kept.append(clean["prompt"])
        added.append(clean["id"])
    reqs_all = [r["id"] for r in kit["role"]["requirements"]]
    kit.setdefault("coverage", {})["uncovered_requirement_ids"] = compute_gaps(reqs_all, kit["questions"])
    await store.kits.save(doc)
    on_event({"step": f"generate:{requirement_id}", "status": "done",
              "message": f"{len(added)} questions"})
    return {"ok": True, "question_ids": added}
