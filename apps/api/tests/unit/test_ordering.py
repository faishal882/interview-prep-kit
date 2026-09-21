"""Phase 5: correct fractional indexing — vectors, properties, stress, rebalance."""
import json
import os
import random

from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.ordering import KEY_LENGTH_LIMIT, key_between, needs_rebalance, rebalance

VECTORS = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "fixtures", "ordering-vectors.json")))


def _sorted_ok(keys):
    return len(set(keys)) == len(keys) and all(a < b for a, b in zip(sorted(keys), sorted(keys)[1:]))


def test_shared_vectors_match():
    for group in VECTORS:
        if group["name"] == "back-inserts":
            prev = None
            for op in group["ops"]:
                assert key_between(prev, None) == op["key"]
                prev = op["key"]
        elif group["name"] == "front-inserts":
            head = None
            for op in group["ops"]:
                assert key_between(None, head) == op["key"]
                head = op["key"]
        elif group["name"] in ("bisections", "legacy-neighbours"):
            for op in group["ops"]:
                assert key_between(op["a"], op["b"]) == op["key"]
        elif group["name"].startswith("rebalance-"):
            assert rebalance(group["count"]) == group["keys"]


@settings(max_examples=40, deadline=None)
@given(seed=st.integers(0, 100000))
def test_random_insert_sequences_stay_valid(seed):
    rng = random.Random(seed)
    keys: list[str] = []
    for _ in range(25):
        ordered = sorted(keys)
        r = rng.random()
        if not ordered or r < 0.3:
            keys.append(key_between(ordered[-1] if ordered else None, None))
        elif r < 0.6 or len(ordered) < 2:
            keys.append(key_between(None, ordered[0]))
        else:
            at = rng.randrange(len(ordered) - 1)
            keys.append(key_between(ordered[at], ordered[at + 1]))
        assert _sorted_ok(keys)


def test_front_inserts_and_bisections_stay_valid_and_bounded():
    keys: list[str] = []
    for _ in range(1000):
        keys.insert(0, key_between(None, keys[0] if keys else None))
        if needs_rebalance(keys[0]):
            keys = rebalance(len(keys))
    assert _sorted_ok(keys)
    assert all(len(k) <= KEY_LENGTH_LIMIT for k in keys)

    lo, hi = "h", "i"
    keys = [lo, hi]
    rng = random.Random(11)
    for _ in range(1000):
        ordered = sorted(keys)
        at = rng.randrange(len(ordered) - 1)
        k = key_between(ordered[at], ordered[at + 1])
        keys.append(k)
        if needs_rebalance(k):
            keys = rebalance(len(keys))
        assert _sorted_ok(keys)
    assert all(len(k) <= KEY_LENGTH_LIMIT for k in keys)


def test_legacy_keys_sort_and_reorder():
    assert "a0" < "a1" < "a2"
    k = key_between("a0", "a1")
    assert "a0" < k < "a1"
    assert key_between(None, "a0") < "a0"
    assert key_between("a2", None) > "a2"
    assert rebalance(3) == ["9", "i", "r"]
