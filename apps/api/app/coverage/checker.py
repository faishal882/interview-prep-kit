"""Pure coverage checker: set arithmetic only."""
from __future__ import annotations


def compute_gaps(
    requirement_ids: list[str],
    questions: list[dict],
    verified_links: dict[str, list[str]] | None = None,
) -> list[str]:
    if not requirement_ids:
        return []
    if verified_links is not None:
        covered: set[str] = set()
        for _qid, rids in verified_links.items():
            covered.update(rids)
    else:
        covered = set()
        for q in questions:
            covered.update(q.get("requirement_ids", []))
    req_set = set(requirement_ids)
    return sorted([r for r in req_set if r not in covered])
