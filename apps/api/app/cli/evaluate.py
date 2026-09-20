"""Batch runner: cases file -> results file. Two concurrent, per-case deadline, continue on failure."""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import get_settings, require_credentials  # noqa: E402
from app.domain.errors import Codes, KitError  # noqa: E402
from app.jev.client import JevClient  # noqa: E402
from app.llm.fake import FakeLLM  # noqa: E402
from app.llm.gemini import GeminiProvider  # noqa: E402
from app.llm.groq import GroqProvider  # noqa: E402
from app.pipeline.orchestrator import run_case  # noqa: E402

VERSION = "1.0"
PER_CASE_TIMEOUT = 240


def build_deps() -> dict:
    s = get_settings()
    if os.environ.get("FAKE_LLM") or s.FAKE_LLM:
        llm = FakeLLM()
        return {"llm": llm, "providers": [llm], "jev": JevClient(), "allow_private": True,
                "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH}
    require_credentials(s)
    providers = []
    if s.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"):
        providers.append(GeminiProvider(os.environ.get("GEMINI_API_KEY") or s.GEMINI_API_KEY, s.GEMINI_MODEL))
    if s.GROQ_API_KEY or os.environ.get("GROQ_API_KEY"):
        providers.append(GroqProvider(os.environ.get("GROQ_API_KEY") or s.GROQ_API_KEY, s.GROQ_MODEL))
    jev = JevClient(os.environ.get("TYPESAFE_API_KEY") or s.TYPESAFE_API_KEY,
                    enabled=bool(os.environ.get("TYPESAFE_API_KEY") or s.TYPESAFE_API_KEY))
    return {"llm": providers[0] if providers else None, "providers": providers, "jev": jev,
            "allow_private": True, "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH}


async def run_one(case: dict, deps: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        cid = case.get("id", "?")
        try:
            if not case.get("jd") or not str(case["jd"]).strip():
                return {"id": cid, "status": "failed", "kit": None,
                        "error": {"code": Codes.INVALID_INPUT, "message": "empty jd"}}
            try:
                kit, _log = await asyncio.wait_for(run_case(case, deps), timeout=PER_CASE_TIMEOUT)
            except asyncio.TimeoutError:
                # try partial? orchestrator either returns or raises; on timeout no kit
                return {"id": cid, "status": "failed", "kit": None,
                        "error": {"code": Codes.TIMEOUT, "message": "per-case deadline exceeded"}}
            return {"id": cid, "status": "ok", "kit": kit, "error": None}
        except KitError as ke:
            code = ke.code
            if code in (Codes.INVALID_INPUT, Codes.LLM_UNAVAILABLE, Codes.KIT_INVALID, Codes.TIMEOUT, Codes.MISSING_CREDENTIALS):
                return {"id": cid, "status": "failed", "kit": None, "error": {"code": code, "message": ke.message}}
            return {"id": cid, "status": "failed", "kit": None, "error": {"code": Codes.KIT_INVALID, "message": ke.message}}
        except Exception as exc:
            return {"id": cid, "status": "failed", "kit": None,
                    "error": {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}}


async def main_async(inp: str, out: str) -> int:
    try:
        deps = build_deps()
    except KitError as ke:
        print(f"{ke.code}: {ke.message}", file=sys.stderr)
        return 2
    with open(inp) as f:
        cases = json.load(f)
    sem = asyncio.Semaphore(2)
    results = await asyncio.gather(*(run_one(c, deps, sem) for c in cases))
    payload = {"version": VERSION,
               "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "kits": results}
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main_async(args.input, args.output)))


if __name__ == "__main__":
    main()
