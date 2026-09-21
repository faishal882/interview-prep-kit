"""Job document factory used by the API when enqueueing work.

Claim, heartbeat and stale recovery live in the repository layer and the
worker loop (`app.jobs.worker`) — not here.
"""
from __future__ import annotations

import time
import uuid

STEPS = [
    "ingest",
    "extract_requirements",
    "crawl_company",
    "research_discussion",
    "analyze_hiring_signals",
    "write_brief",
    "generate_questions",
    "generate_flashcards",
    "build_schedule",
    "assemble_kit",
]


def new_job(
    kit_id: str,
    *,
    user_id: str = "",
    kind: str = "generation",
    deadline: float | None = None,
    steps: list[str] | None = None,
) -> dict:
    now = time.time()
    names = steps if steps is not None else STEPS
    return {
        "id": uuid.uuid4().hex[:12],
        "kit_id": kit_id,
        "user_id": user_id,
        "kind": kind,
        "status": "pending",  # pending|running|done|failed
        "steps": [
            {"name": s, "status": "pending", "message": "", "started_at": None, "finished_at": None}
            for s in names
        ],
        "attempts": 0,
        "heartbeat": now,
        "created_at": now,
        "deadline": deadline if deadline is not None else now + 240.0,
        "error": None,
        "retryable": False,
    }
