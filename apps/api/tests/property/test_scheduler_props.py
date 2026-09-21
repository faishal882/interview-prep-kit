"""Property-based scheduler tests."""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.scheduling.allocator import MINUTES, allocate

cats = st.sampled_from(["technical", "behavioural", "system-design", "company-fit"])


def _minutes(q):
    return MINUTES.get((q.get("category"), q.get("difficulty", 1)), 10)


@settings(max_examples=60, deadline=None)
@given(
    n_q=st.integers(0, 8),
    n_days=st.integers(1, 10),
    seed=st.integers(0, 1000),
)
def test_invariants(n_q, n_days, seed):
    questions = [
        {"id": f"q{i}", "requirement_ids": ["r1"], "category": ["technical", "behavioural", "system-design", "company-fit"][(i + seed) % 4],
         "difficulty": ((i + seed) % 3) + 1, "prompt": f"p{i}"}
        for i in range(n_q)
    ]
    reqs = [{"id": "r1", "text": "req", "priority": "must"}]
    days, _ = allocate(questions, reqs, n_days)
    assert len(days) == n_days
    for d in days:
        assert isinstance(d["minutes"], int)
        for qid in d["question_ids"]:
            assert qid in {q["id"] for q in questions}
    if questions:
        seen = {qid for d in days for qid in d["question_ids"]}
        assert seen == {q["id"] for q in questions}


@settings(max_examples=60, deadline=None)
@given(
    n_q=st.integers(2, 8),
    n_days=st.integers(1, 7),
    seed=st.integers(0, 1000),
)
def test_minute_balance(n_q, n_days, seed):
    """With at least as many questions as days, day totals differ by at most
    the largest single question's minutes."""
    questions = [
        {"id": f"q{i}", "requirement_ids": ["r1"], "category": ["technical", "behavioural", "system-design", "company-fit"][(i + seed) % 4],
         "difficulty": ((i + seed) % 3) + 1, "prompt": f"p{i}"}
        for i in range(n_q)
    ]
    reqs = [{"id": "r1", "text": "req", "priority": "must"}]
    assume_days = min(n_days, n_q)
    days, _ = allocate(questions, reqs, assume_days)
    totals = [d["minutes"] for d in days]
    biggest = max(_minutes(q) for q in questions)
    assert max(totals) - min(totals) <= biggest


@settings(max_examples=60, deadline=None)
@given(
    n_q=st.integers(1, 5),
    extra_days=st.integers(1, 12),
    seed=st.integers(0, 1000),
)
def test_review_spacing_expands(n_q, extra_days, seed):
    """Review repeats of one question are spaced non-decreasingly apart, and
    the first review revisits the highest-weight question."""
    questions = [
        {"id": f"q{i}", "requirement_ids": ["r1"], "category": ["technical", "behavioural", "system-design", "company-fit"][(i + seed) % 4],
         "difficulty": ((i + seed) % 3) + 1, "prompt": f"p{i}"}
        for i in range(n_q)
    ]
    reqs = [{"id": "r1", "text": "req", "priority": "must"}]
    days, _ = allocate(questions, reqs, n_q + extra_days)
    review_days = days[n_q:]
    assert review_days[0]["question_ids"] == [days[0]["question_ids"][0]]
    positions: dict[str, list[int]] = {}
    for d in review_days:
        qid = d["question_ids"][0]
        positions.setdefault(qid, []).append(d["day"])
    for pos in positions.values():
        if len(pos) >= 3:
            gaps = [b - a for a, b in zip(pos, pos[1:])]
            assert all(b >= a for a, b in zip(gaps, gaps[1:]))
