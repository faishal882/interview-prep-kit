"""Repository-layer errors."""
from __future__ import annotations


class ConflictError(Exception):
    """A uniqueness guarantee refused the write (duplicate email, active job)."""
