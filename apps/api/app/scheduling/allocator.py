"""Deterministic schedule allocator (pure).

Weight orders material (harder, higher-priority first); contiguous
minute-balanced partitions keep day totals close while preserving that order.
Fewer questions than days yields one question per day in weight order, then
Review days repeating top-weight questions at expanding intervals.
"""
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


def _prune(pairs: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Keep pareto-optimal (min, max) day-total pairs: no other pair is
    better-or-equal on both ends."""
    out = set()
    for mn, mx in pairs:
        if any(omn >= mn and omx <= mx and (omn, omx) != (mn, mx) for omn, omx in pairs):
            continue
        out.add((mn, mx))
    return out


def day_minutes(question_ids: list[str], questions: list[dict]) -> int:
    """Minutes for a day as the sum of its Questions' minutes (unknown ids count 0)."""
    table = {q["id"]: MINUTES.get((q.get("category"), q.get("difficulty", 1)), 10) for q in questions}
    return sum(table.get(qid, 0) for qid in question_ids)


def _focus(day_no: int, q: dict, req_text: dict[str, str], review: bool = False) -> str:
    tag = "review: " if review else ""
    src = req_text.get((q.get("requirement_ids") or [""])[0], "") or q.get("prompt", "")
    width = 60 if review else 80
    return f"Day {day_no} — {tag}{q.get('category')}: {src[:width]}"


def _balanced_split(sizes: list[int], days: int) -> list[tuple[int, int]]:
    """Contiguous non-empty index ranges minimizing max-min day total.

    With at least as many items as days this keeps day totals within one
    largest-item of each other. Deterministic.
    """
    n = len(sizes)
    prefix = [0]
    for s in sizes:
        prefix.append(prefix[-1] + s)
    dp: list[list[set[tuple[int, int]]]] = [[set() for _ in range(n + 1)] for _ in range(days + 1)]
    for i in range(1, n + 1):
        dp[1][i] = {(prefix[i], prefix[i])}
    for k in range(2, days + 1):
        for i in range(k, n + 1):
            cand = set()
            for j in range(k - 1, i):
                seg = prefix[i] - prefix[j]
                for pmn, pmx in dp[k - 1][j]:
                    cand.add((min(pmn, seg), max(pmx, seg)))
            dp[k][i] = _prune(cand)
    want = min(dp[days][n], key=lambda t: (t[1] - t[0], t[1], t[0]))
    ranges: list[tuple[int, int]] = []
    k, i = days, n
    while k > 1:
        for j in range(k - 1, i):
            seg = prefix[i] - prefix[j]
            for pmn, pmx in sorted(dp[k - 1][j]):
                if (min(pmn, seg), max(pmx, seg)) == want:
                    ranges.append((j, i))
                    want = (pmn, pmx)
                    i, k = j, k - 1
                    break
            else:
                continue
            break
    ranges.append((0, i))
    ranges.reverse()
    return ranges
    tag = "review: " if review else ""
    src = req_text.get((q.get("requirement_ids") or [""])[0], "") or q.get("prompt", "")
    width = 60 if review else 80
    return f"Day {day_no} — {tag}{q.get('category')}: {src[:width]}"


def _review_sequence(ordered: list[dict], needed: int) -> list[dict]:
    """Top-weight repeats in expanding cycles: q0 | q0,q1 | q0,q1,q2 | ….

    Repeats of any one question are spaced non-decreasingly apart, and the
    first review always revisits the highest-weight question.
    """
    out: list[dict] = []
    cycle = 1
    total = len(ordered)
    while len(out) < needed:
        out.extend(ordered[: min(cycle, total)])
        cycle += 1
    return out[:needed]


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
        return [{"day": 1, "focus": _focus(1, ordered[0], req_text),
                 "question_ids": ids, "minutes": total}], warnings

    if len(ordered) >= days:
        # optimal contiguous minute-balanced partition of the weight-ordered
        # list: day totals stay within one largest-question of each other
        # while harder material never lands later than easier material.
        sizes = [minutes_of[q["id"]] for q in ordered]
        out = []
        for d, (a, b) in enumerate(_balanced_split(sizes, days)):
            bucket = ordered[a:b]
            ids = [q["id"] for q in bucket]
            total = sum(minutes_of[qid] for qid in ids)
            out.append({"day": d + 1, "focus": _focus(d + 1, bucket[0], req_text),
                        "question_ids": ids, "minutes": total})
    else:
        # Q < N: one question per day in weight order, then expanding review days
        out = []
        for i, q in enumerate(ordered):
            out.append({"day": i + 1, "focus": _focus(i + 1, q, req_text),
                        "question_ids": [q["id"]], "minutes": minutes_of[q["id"]]})
        for j, q in enumerate(_review_sequence(ordered, days - len(ordered))):
            d = len(ordered) + j
            out.append({"day": d + 1, "focus": _focus(d + 1, q, req_text, review=True),
                        "question_ids": [q["id"]], "minutes": minutes_of[q["id"]]})

    avg = sum(d["minutes"] for d in out) / max(days, 1)
    if avg > 180:
        warnings.append(f"average daily load {avg:.0f} min exceeds 180 min; consider more days")
    return out, warnings
