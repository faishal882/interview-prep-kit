"""Correct fractional-index ordering keys (lexicographically sortable).

Keys are base36 strings interpreted as fractions in [0, 1): value(k) =
sum(digit_i * 36**-(i+1)). New keys are computed with exact rational
arithmetic, so every insert lands strictly between its neighbours and keys
are always unique. Old stored keys ("a0", …) parse as fractions too, so
existing kits keep sorting and can be reordered without migration.

Rebalancing: when a key grows past KEY_LENGTH_LIMIT, the whole scope is
reassigned short evenly-spaced keys (deterministic, order-preserving).
"""
from __future__ import annotations

from fractions import Fraction

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE = 36
FIRST_KEY = "h"
KEY_LENGTH_LIMIT = 32
_ENCODE_CAP = 64


def _value(key: str) -> Fraction:
    total = Fraction(0)
    for i, ch in enumerate(key):
        total += Fraction(DIGITS.index(ch), BASE ** (i + 1))
    return total


def _encode_between(lo: Fraction, hi: Fraction) -> str:
    """Shortest-prefix digit string with a value strictly inside (lo, hi)."""
    assert Fraction(0) <= lo < hi <= Fraction(1)
    mid = (lo + hi) / 2
    digits: list[int] = []
    remainder = mid
    for _ in range(_ENCODE_CAP):
        remainder *= BASE
        digit = int(remainder)
        digits.append(min(digit, BASE - 1))
        remainder -= digits[-1]
        if remainder == 0:
            break
    while _digits_value(digits) <= lo:
        remainder *= BASE
        digit = int(remainder)
        digits.append(min(digit, BASE - 1))
        remainder -= digits[-1]
    return "".join(DIGITS[d] for d in digits)


def _digits_value(digits: list[int]) -> Fraction:
    total = Fraction(0)
    for i, d in enumerate(digits):
        total += Fraction(d, BASE ** (i + 1))
    return total


def key_between(a: str | None, b: str | None) -> str:
    """Return a key strictly between a and b (None = unbounded)."""
    if a is None and b is None:
        return FIRST_KEY
    if a is None:
        assert b is not None
        return _encode_between(Fraction(0), _value(b))
    if b is None:
        return _encode_between(_value(a), Fraction(1))
    va, vb = _value(a), _value(b)
    if not va < vb:
        return _encode_between(vb, Fraction(1))
    return _encode_between(va, vb)


def needs_rebalance(key: str) -> bool:
    return len(key) > KEY_LENGTH_LIMIT


def rebalance(n: int) -> list[str]:
    """n short evenly-spaced keys, strictly increasing, deterministic."""
    width = 1
    while BASE**width < n + 2:
        width += 1
    span = BASE**width
    out = []
    for i in range(n):
        idx = (span * (i + 1)) // (n + 1)
        key = ""
        for _ in range(width):
            key = DIGITS[idx % BASE] + key
            idx //= BASE
        out.append(key)
    return out
