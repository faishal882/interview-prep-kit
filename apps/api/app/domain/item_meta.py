"""Item metadata: origin/edited/pinned/revision/order (ADR-0004)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ItemMeta(BaseModel):
    origin: str = "generated"  # generated | user
    edited: bool = False
    pinned: bool = False
    rev: int = 1
    order: str = "a0"
    gen_run: str | None = None


def is_protected(meta: dict) -> bool:
    return (
        meta.get("origin") == "user" or bool(meta.get("edited")) or bool(meta.get("pinned"))
    )
