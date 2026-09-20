"""Scheduler example-based tests."""
from app.scheduling.allocator import allocate


def qs(n=4):
    cats = ["technical", "behavioural", "system-design", "company-fit"]
    return [{"id": f"q{i+1}", "requirement_ids": ["r1"], "category": cats[i % 4],
             "difficulty": (i % 3) + 1, "prompt": f"p{i}"} for i in range(n)]


def reqs():
    return [{"id": "r1", "text": "know things", "priority": "must"}]


def test_exact_days_and_valid_ids():
    days, _ = allocate(qs(4), reqs(), 3)
    assert len(days) == 3
    assert all(isinstance(d["minutes"], int) for d in days)
    valid = {f"q{i+1}" for i in range(4)}
    for d in days:
        assert set(d["question_ids"]) <= valid


def test_every_question_scheduled():
    days, _ = allocate(qs(5), reqs(), 2)
    seen = {qid for d in days for qid in d["question_ids"]}
    assert seen == {f"q{i+1}" for i in range(5)}


def test_front_loaded():
    q = [{"id": "q1", "requirement_ids": ["r1"], "category": "technical", "difficulty": 3, "prompt": "hard"},
         {"id": "q2", "requirement_ids": ["r2"], "category": "company-fit", "difficulty": 1, "prompt": "easy"}]
    r = [{"id": "r1", "text": "hard req", "priority": "must"}, {"id": "r2", "text": "easy", "priority": "nice"}]
    days, _ = allocate(q, r, 2)
    assert days[0]["question_ids"] == ["q1"]
    assert days[1]["question_ids"] == ["q2"]


def test_one_day_and_sixty_days():
    d1, _ = allocate(qs(3), reqs(), 1)
    assert len(d1) == 1 and len(d1[0]["question_ids"]) == 3
    d60, _ = allocate(qs(2), reqs(), 60)
    assert len(d60) == 60
    assert all(len(d["question_ids"]) >= 1 for d in d60)


def test_zero_questions():
    days, _ = allocate([], reqs(), 3)
    assert len(days) == 3
    assert all(d["question_ids"] == [] and d["minutes"] == 0 for d in days)


def test_deterministic():
    a, _ = allocate(qs(6), reqs(), 4)
    b, _ = allocate(qs(6), reqs(), 4)
    assert a == b
