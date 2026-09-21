"""Central configuration: one validated settings object.

Production refuses to start without a reachable database, a model key and an
allowed-origin list (see validate_production); the scripted fake model is only
reachable through the explicit FAKE_LLM setting.
"""
from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "production"
    ALLOW_PRIVATE_URLS: bool = False
    MONGODB_URI: str = ""
    MONGODB_DB: str = "trao"
    ALLOWED_ORIGINS: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    SEARCH_API_KEY: str = ""
    MAX_CRAWL_PAGES: int = 12
    CRAWL_DEPTH: int = 2
    MAX_CONCURRENT_RUNS: int = 2
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "trao-api"
    DEBUG_CAPTURE_CONTENT: bool = False
    FAKE_LLM: str = ""  # explicit setting only; never an implicit fallback

    # Auth and quotas (registration closed by default; the operator command
    # provisions users, REGISTRATION_OPEN=true reopens explicitly)
    REGISTRATION_OPEN: bool = False
    SESSION_TTL_S: int = 7 * 24 * 3600
    MAX_KITS_PER_DAY: int = 10
    MAX_STORED_KITS: int = 50
    MAX_CONCURRENT_PER_USER: int = 1

    # Request limits
    MAX_JD_CHARS: int = 30000
    MAX_BODY_BYTES: int = 1048576
    MAX_BATCH_ENTRIES: int = 10

    # Generation deadlines
    STEP_TIMEOUT_S: int = 60
    OVERALL_TIMEOUT_S: int = 180

    # Model quota
    LLM_REQUESTS_PER_MINUTE: float = 60.0
    LLM_TOKENS_PER_MINUTE: float = 200000.0

    # Retrieval cache
    PAGE_CACHE_TTL_S: int = 3600


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Forget cached settings (tests only)."""
    global _settings
    _settings = None


def require_credentials(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if s.FAKE_LLM:
        return
    if os.environ.get("FAKE_LLM"):
        return
    if not s.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
        from app.domain.errors import Codes, KitError

        raise KitError(Codes.MISSING_CREDENTIALS, "Missing GEMINI_API_KEY")


def validate_production(settings: Settings | None = None) -> list[str]:
    """Every production misconfiguration, named in one list (empty = ok)."""
    s = settings or get_settings()
    problems: list[str] = []
    if not (s.MONGODB_URI or "").strip():
        problems.append("MONGODB_URI is required in production")
    if not (s.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or "").strip():
        problems.append("GEMINI_API_KEY is required in production")
    if s.FAKE_LLM or os.environ.get("FAKE_LLM"):
        problems.append("FAKE_LLM must not be set in production")
    if not [o.strip() for o in (s.ALLOWED_ORIGINS or "").split(",") if o.strip()]:
        problems.append("ALLOWED_ORIGINS is required in production")
    if s.MAX_CONCURRENT_RUNS < 1:
        problems.append("MAX_CONCURRENT_RUNS must be >= 1")
    return problems
