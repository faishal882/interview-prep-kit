"""Fractional-index ordering keys (simplified, lexicographically sortable)."""
from __future__ import annotations


def key_between(a: str | None, b: str | None) -> str:
    """Return a key strictly between a and b (None = unbounded)."""
    if a is None and b is None:
        return "a0"
    if a is None:
        assert b is not None
        return _decrement(b)
    if b is None:
        return _increment(a)
    if a >= b:
        return _increment(a)
    # find common prefix, then midpoint in last differing char
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    if i < len(a) and i < len(b):
        ca, cb = ord(a[i]), ord(b[i])
        if cb - ca > 1:
            return a[:i] + chr((ca + cb) // 2)
        return a[: i + 1] + "0"
    # a is a prefix of b
    return a + "0"


def _increment(k: str) -> str:
    # increment trailing base36-ish run; simple: append/advance last char
    last = k[-1]
    if last == "z":
        return k + "0"
    if last == "9":
        return k[:-1] + "a" if k[:-1] else "a"
    return k[:-1] + chr(ord(last) + 1)


def _decrement(k: str) -> str:
    first = k[0]
    if first > "0":
        return chr(ord(first) - 1) + k[1:] if len(k) > 1 else chr(ord(first) - 1)
    return "0" + k
