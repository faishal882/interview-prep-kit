"""Regeneration merge rules (ADR-0004): protected items survive; in-flight edits survive."""
from __future__ import annotations

from .item_meta import is_protected


def merge_category(
    current: list[dict],
    fresh: list[dict],
    snapshot_revs: dict[str, int],
) -> list[dict]:
    """Merge freshly generated items into current for one Category.

    - Keep every protected item.
    - Keep any item whose rev changed since the job started (in-flight edit).
    - Drop unprotected, unchanged items in this category; add fresh ones.
    - Fresh items that duplicate a kept prompt are skipped.
    """
    kept_prompts = {
        (i.get("prompt") or "").strip().lower()
        for i in current
        if is_protected(i.get("_meta", {})) or i.get("_meta", {}).get("rev") != snapshot_revs.get(i.get("id"))
    }
    # items whose rev changed since snapshot survive regardless
    survivors: list[dict] = []
    for item in current:
        meta = item.get("_meta", {})
        if is_protected(meta):
            survivors.append(item)
        elif meta.get("rev") != snapshot_revs.get(item.get("id")):
            # in-flight edit bumped rev -> treat as protected
            survivors.append(item)
        # else: victim, dropped
    for item in fresh:
        p = (item.get("prompt") or "").strip().lower()
        if p and p in kept_prompts:
            continue
        survivors.append(item)
        if p:
            kept_prompts.add(p)
    return survivors
