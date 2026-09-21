"""Batch runner: cases file -> results file. Two concurrent, per-case deadline, continue on failure."""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import get_settings, require_credentials  # noqa: E402
from app.domain.errors import Codes, KitError  # noqa: E402
from app.llm.fake import FakeLLM  # noqa: E402
from app.llm.gemini import GeminiProvider  # noqa: E402
from app.pipeline.orchestrator import run_case  # noqa: E402

VERSION = "1.0"
PER_CASE_TIMEOUT = 240


def build_deps() -> dict:
    s = get_settings()
    if os.environ.get("FAKE_LLM") or s.FAKE_LLM:
        llm = FakeLLM()
        return {"llm": llm, "allow_private": True,
                "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH}
    require_credentials(s)
    llm = GeminiProvider(os.environ.get("GEMINI_API_KEY") or s.GEMINI_API_KEY, s.GEMINI_MODEL)
    return {"llm": llm, "allow_private": True, "max_pages": s.MAX_CRAWL_PAGES, "depth": s.CRAWL_DEPTH}


def normalize_cases(cases: object) -> list[dict]:
    """Validate the batch file shape up front; make ids unique with a recorded note."""
    if not isinstance(cases, list):
        raise KitError(Codes.INVALID_INPUT, "cases file must be a JSON array")
    if len(cases) > 100:
        raise KitError(Codes.INVALID_INPUT, "too many cases (max 100)")
    seen: set[str] = set()
    out: list[dict] = []
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            raise KitError(Codes.INVALID_INPUT, f"case {i} is not an object")
        cid = str(c.get("id") or f"case-{i}")
        note = None
        if cid in seen:
            suffix = 2
            while f"{cid}-{suffix}" in seen:
                suffix += 1
            cid = f"{cid}-{suffix}"
            note = "duplicate id made unique"
        seen.add(cid)
        entry = dict(c)
        entry["id"] = cid
        if note:
            entry["_note"] = note
        out.append(entry)
    return out


def _check_days(case: dict) -> str | None:
    raw = case.get("days", 5)
    if isinstance(raw, bool):
        return "days must be 1..60"
    try:
        days = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "days must be 1..60"
    if not 1 <= days <= 60:
        return "days must be 1..60"
    return None


async def run_one(case: dict, deps: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        cid = case.get("id", "?")
        note = case.get("_note")
        try:
            if not case.get("jd") or not str(case["jd"]).strip():
                return {"id": cid, "status": "failed", "kit": None,
                        "error": {"code": Codes.INVALID_INPUT, "message": "empty jd"}}
            day_err = _check_days(case)
            if day_err:
                return {"id": cid, "status": "failed", "kit": None,
                        "error": {"code": Codes.INVALID_INPUT, "message": day_err}}
            try:
                kit, _log = await asyncio.wait_for(run_case(case, deps), timeout=PER_CASE_TIMEOUT)
            except asyncio.TimeoutError:
                # try partial? orchestrator either returns or raises; on timeout no kit
                return {"id": cid, "status": "failed", "kit": None,
                        "error": {"code": Codes.TIMEOUT, "message": "per-case deadline exceeded"}}
            result = {"id": cid, "status": "ok", "kit": kit, "error": None}
            if note:
                result["note"] = note
            return result
        except KitError as ke:
            code = ke.code
            if code in (Codes.INVALID_INPUT, Codes.LLM_UNAVAILABLE, Codes.KIT_INVALID, Codes.TIMEOUT, Codes.MISSING_CREDENTIALS):
                return {"id": cid, "status": "failed", "kit": None, "error": {"code": code, "message": ke.message}}
            return {"id": cid, "status": "failed", "kit": None, "error": {"code": Codes.KIT_INVALID, "message": ke.message}}
        except Exception as exc:
            return {"id": cid, "status": "failed", "kit": None,
                    "error": {"code": Codes.KIT_INVALID, "message": str(exc)[:300]}}


def write_atomic(path: str, payload: dict) -> None:
    """Write output atomically so an interrupted run never leaves a half-written file."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".out-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


async def main_async(inp: str, out: str) -> int:
    try:
        deps = build_deps()
    except KitError as ke:
        print(f"{ke.code}: {ke.message}", file=sys.stderr)
        return 2
    try:
        with open(inp) as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID_INPUT: cannot read cases file: {exc}", file=sys.stderr)
        return 2
    try:
        cases = normalize_cases(raw)
    except KitError as ke:
        print(f"{ke.code}: {ke.message}", file=sys.stderr)
        return 2
    sem = asyncio.Semaphore(2)
    results = await asyncio.gather(*(run_one(c, deps, sem) for c in cases))
    payload = {"version": VERSION,
               "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "kits": results}
    write_atomic(out, payload)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main_async(args.input, args.output)))


if __name__ == "__main__":
    main()
