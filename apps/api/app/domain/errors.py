"""Error codes shared by API and batch."""
from __future__ import annotations


class Codes:
    INVALID_INPUT = "INVALID_INPUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    KIT_INVALID = "KIT_INVALID"
    TIMEOUT = "TIMEOUT"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    COMPANY_UNREACHABLE = "COMPANY_UNREACHABLE"  # defined; unused (ok-with-log instead)
    UNAUTHORIZED = "UNAUTHORIZED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_GATEWAY = "BAD_GATEWAY"


class KitError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
