"""Store selection: in-memory by default, MongoDB when MONGODB_URI is set.

The batch command never touches this module — it keeps using in-memory
repositories directly, so evaluation needs no database.
"""
from __future__ import annotations

from app.config import get_settings

from .repos_memory import MemoryStore

_memory = MemoryStore()
_mongo = None


def memory_store() -> MemoryStore:
    return _memory


def reset_stores() -> None:
    """Forget cached stores (tests only)."""
    global _mongo
    _mongo = None


def get_store():
    """Process-wide store from settings (cached)."""
    global _mongo
    s = get_settings()
    uri = (s.MONGODB_URI or "").strip()
    if not uri:
        return _memory
    if _mongo is None:
        from .repos_mongo import MongoStore

        db_name = (getattr(s, "MONGODB_DB", "") or "").strip() or "trao"
        _mongo = MongoStore(uri, db_name)
    return _mongo
