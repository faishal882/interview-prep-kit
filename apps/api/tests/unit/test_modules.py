"""Grounding, classification, ordering, merge, url-guard, prioritizer, dedupe."""
import time

from app.coverage.checker import compute_gaps
from app.domain.merge import merge_category
from app.domain.ordering import key_between
from app.persistence.repos_base import dedupe_key
from app.pipeline.steps.classify import classify_kind, classify_priority
from app.pipeline.steps.grounding import is_verbatim
from app.practice.prioritizer import order_queue
from app.retrieval.url_guard import validate_url


def test_paraphrase_rejected_whitespace_tolerated():
    jd = "We require  5+ years with React."
    assert is_verbatim("5+ years with React", jd)
    assert is_verbatim("- 5+ years with React.", jd)
    assert not is_verbatim("6 years of Vue", jd)


def test_classification_defaults_must():
    assert classify_priority("Build stuff") == "must"
    assert classify_priority("Kubernetes a plus", "Bonus points") == "nice"
    assert classify_priority("5+ years with React", "Required") == "must"
    assert classify_kind("mentor junior engineers") == "behavioural"


def test_ordering_between():
    k = key_between(None, None)
    k2 = key_between(k, None)
    k0 = key_between(None, k)
    assert k0 < k < k2
    assert key_between("a0", "a2") not in ("a0", "a2")


def test_merge_protected_survives_and_inflight():
    cur = [
        {"id": "q1", "prompt": "old", "category": "technical",
         "_meta": {"origin": "user", "edited": False, "pinned": False, "rev": 1, "order": "a0"}},
        {"id": "q2", "prompt": "victim", "category": "technical",
         "_meta": {"origin": "generated", "edited": False, "pinned": False, "rev": 1, "order": "a1"}},
    ]
    snap = {"q1": 1, "q2": 1}
    cur[1]["_meta"]["rev"] = 2  # in-flight edit
    merged = merge_category([c for c in cur if c["id"] == "q2"][:0] + [cur[0], cur[1]],
                            [{"id": "qn", "prompt": "new", "category": "technical"}], snap)
    ids = {m["id"] for m in merged}
    assert "q1" in ids and "q2" in ids and "qn" in ids


def test_merge_no_duplicates():
    cur = [{"id": "q1", "prompt": "Same prompt", "category": "technical",
            "_meta": {"origin": "user", "edited": False, "pinned": False, "rev": 1, "order": "a0"}}]
    fresh = [{"id": "qn", "prompt": "same prompt", "category": "technical"}]
    assert len(merge_category(cur, fresh, {"q1": 1})) == 1


def test_url_guard_private_rejected():
    ok, _ = validate_url("http://127.0.0.1/x", allow_private=False)
    assert not ok
    ok2, _ = validate_url("http://127.0.0.1/x", allow_private=True)
    assert ok2
    ok3, _ = validate_url("https://example.com/", allow_private=False)
    assert ok3
    ok4, _ = validate_url("ftp://example.com/", allow_private=False)
    assert not ok4


def test_prioritizer_unseen_before_mastered():
    now = time.time()
    cards = [{"id": "a", "priority": "must"}, {"id": "b", "priority": "must"}]
    hist = {"a": [], "b": [{"confidence": 3, "at": now}]}
    ordered = order_queue(cards, hist, now=now)
    assert ordered[0]["id"] == "a"


def test_dedupe_key_normalisation():
    k1 = dedupe_key("u", "Hello  World", "http://x/", 5)
    k2 = dedupe_key("u", "hello world", "http://x/", 5)
    k3 = dedupe_key("u", "hello world", "http://x/", 6)
    assert k1 == k2 and k1 != k3


def test_gaps_empty_when_all_covered():
    assert compute_gaps(["r1", "r2"], [{"requirement_ids": ["r1", "r2"]}]) == []
    assert compute_gaps(["r1", "r2"], [{"requirement_ids": ["r1"]}]) == ["r2"]
