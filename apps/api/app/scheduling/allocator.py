"""Deterministic schedule allocator (pure)."""
from __future__ import annotations

MINUTES: dict[tuple[str, int], int] = {
    ("technical", 1): 10, ("technical", 2): 15, ("technical", 3): 20,
    ("behavioural", 1): 8, ("behavioural", 2): 10, ("behavioural", 3): 12,
    ("system-design", 1): 20, ("system-design", 2): 30, ("system-design", 3): 40,
    ("company-fit", 1): 6, ("company-fit", 2): 8, ("company-fit", 3): 10,
}
CATEGORY_ORDER = ["technical", "behavioural", "system-design", "company-fit"]


def _weight(q: dict, prio: dict[str, str]) -> int:
    diff = q.get("difficulty", 1)
    w = 1
    for rid in q.get("requirement_ids", []):
        w = max(w, 2 if prio.get(rid) == "must" else 1)
    return int(diff) * w


def allocate(
    questions: list[dict],
    requirements: list[dict],
    days: int,
) -> tuple[list[dict], list[str]]:
    """Return (days_list, warnings). Exactly `days` days, integer minutes."""
    warnings: list[str] = []
    prio = {r.get("id"): r.get("priority", "must") for r in requirements}
    req_text = {r.get("id"): r.get("text", "") for r in requirements}
    if days < 1:
        days = 1
    if not questions:
        out = [
            {
                "day": i + 1,
                "focus": "No questions — description was thin; research the role yourself",
                "question_ids": [],
                "minutes": 0,
            }
            for i in range(days)
        ]
        return out, warnings

    ordered = sorted(
        questions,
        key=lambda q: (-_weight(q, prio), CATEGORY_ORDER.index(q.get("category", "technical")), q.get("id", "")),
    )
    minutes_of = {q["id"]: MINUTES.get((q.get("category"), q.get("difficulty", 1)), 10) for q in ordered}

    if days == 1:
        ids = [q["id"] for q in ordered]
        total = sum(minutes_of[i] for i in ids)
        top = ordered[0]
        focus = f"Day 1 — {top.get('category')}: {(req_text.get((top.get('requirement_ids') or [''])[0], top.get('prompt', '')) or '')[:80]}"
        return [{"day": 1, "focus": focus, "question_ids": ids, "minutes": total}], warnings

    if len(ordered) >= days:
        # front-loaded split: earlier days get the extra questions; ordered
        # desc by weight so harder/high-priority material lands early.
        base, rem = divmod(len(ordered), days)
        buckets: list[list[dict]] = []
        idx = 0
        for d in range(days):
            size = base + (1 if d < rem else 0)
            buckets.append(ordered[idx: idx + size])
            idx += size
        out = []
        for i, bucket in enumerate(buckets):
            ids = [q["id"] for q in bucket]
            total = sum(minutes_of[qid] for qid in ids)
            top = bucket[0]
            focus = f"Day {i+1} — {top.get('category')}: {(req_text.get((top.get('requirement_ids') or [''])[0], '') or top.get('prompt', ''))[:80]}"
            out.append({"day": i + 1, "focus": focus, "question_ids": ids, "minutes": total})
    else:
        # Q < N: one question per day in weight order, then spaced-review days
        out = []
        for i, q in enumerate(ordered):
            focus = f"Day {i+1} — {q.get('category')}: {(req_text.get((q.get('requirement_ids') or [''])[0], '') or q.get('prompt', ''))[:80]}"
            out.append({"day": i + 1, "focus": focus, "question_ids": [q["id"]], "minutes": minutes_of[q["id"]]})
        # expanding-interval review days repeating highest-weight questions
        gaps = [1, 2, 4]
        qi = 0
        for d in range(len(ordered), days):
            q = ordered[qi % len(ordered)]
            focus = f"Day {d+1} — review: {q.get('category')}: {(req_text.get((q.get('requirement_ids') or [''])[0], '') or q.get('prompt', ''))[:60]}"
            out.append({"day": d + 1, "focus": focus, "question_ids": [q["id"]], "minutes": minutes_of[q["id"]]})
            if (d - len(ordered) + 1) in gaps or True:
                qi += 1  # cycle through top questions; expanding interval approximated

    avg = sum(d["minutes"] for d in out) / max(days, 1)
    if avg > 180:
        warnings.append(f"average daily load {avg:.0f} min exceeds 180 min; consider more days")
    return out, warnings
