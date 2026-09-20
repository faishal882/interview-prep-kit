"""Evidence grounding: verbatim check (whitespace/bullet tolerant)."""
from __future__ import annotations

import re
import string


def normalize(text: str) -> str:
    text = text.lower()
    # drop bullet markers and punctuation for tolerance
    text = re.sub(r"^[\s\-\*\•\d\.\)]+", "", text.strip())
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_verbatim(evidence: str, jd: str) -> bool:
    ne, nj = normalize(evidence), normalize(jd)
    if not ne:
        return False
    return ne in nj
