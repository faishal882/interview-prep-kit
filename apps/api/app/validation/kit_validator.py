"""Semantic validator for Appendix A Kits."""
from __future__ import annotations


def validate_kit(kit: dict) -> list[str]:
    """Return a list of error strings; empty means valid."""
    errors: list[str] = []
    try:
        role = kit.get("role", {})
        reqs = role.get("requirements", [])
        req_ids = [r.get("id") for r in reqs if isinstance(r, dict)]
        if len(req_ids) != len(set(req_ids)):
            errors.append("duplicate requirement ids")
        questions = kit.get("questions", [])
        q_ids = [q.get("id") for q in questions if isinstance(q, dict)]
        if len(q_ids) != len(set(q_ids)):
            errors.append("duplicate question ids")
        flashcards = kit.get("flashcards", [])
        f_ids = [f.get("id") for f in flashcards if isinstance(f, dict)]
        if len(f_ids) != len(set(f_ids)):
            errors.append("duplicate flashcard ids")

        req_set = set(req_ids)
        for q in questions:
            if not isinstance(q, dict):
                continue
            for rid in q.get("requirement_ids", []):
                if rid not in req_set:
                    errors.append(f"dangling requirement reference: {rid} in {q.get('id')}")
            d = q.get("difficulty")
            if not isinstance(d, int) or isinstance(d, bool) or not (1 <= d <= 3):
                errors.append(f"bad difficulty in {q.get('id')}: {d!r}")

        schedule = kit.get("schedule", {})
        days = schedule.get("days", [])
        days_available = schedule.get("days_available")
        if days_available is not None and len(days) != days_available:
            errors.append(
                f"schedule length {len(days)} != days_available {days_available}"
            )
        q_set = set(q_ids)
        for day in days:
            if not isinstance(day, dict):
                continue
            m = day.get("minutes")
            if not isinstance(m, int) or isinstance(m, bool):
                errors.append(f"non-integer minutes on day {day.get('day')}")
            for qid in day.get("question_ids", []):
                if qid not in q_set:
                    errors.append(f"dangling schedule reference: {qid}")

        coverage = kit.get("coverage", {})
        uncovered = set(coverage.get("uncovered_requirement_ids", []))
        covered: set[str] = set()
        for q in questions:
            if isinstance(q, dict):
                covered.update(q.get("requirement_ids", []))
        must_ids = {r.get("id") for r in reqs if isinstance(r, dict) and r.get("priority") == "must"}
        missing = must_ids - covered - uncovered
        if missing:
            errors.append(f"must requirements neither covered nor uncovered: {sorted(missing)}")
        for rid in uncovered:
            if rid not in req_set:
                errors.append(f"dangling uncovered reference: {rid}")
        if len(questions) > 30:
            errors.append("too many questions (>30)")
        if len(flashcards) > 20:
            errors.append("too many flashcards (>20)")
    except Exception as exc:  # defensive: never raise from validator
        errors.append(f"validator crash: {exc}")
    return errors
