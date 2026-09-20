"""Property-based scheduler tests."""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.scheduling.allocator import allocate

cats = st.sampled_from(["technical", "behavioural", "system-design", "company-fit"])


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
