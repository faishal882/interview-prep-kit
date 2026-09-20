"""Central configuration (pydantic-settings). Only GEMINI_API_KEY is required."""
from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "production"
    ALLOW_PRIVATE_URLS: bool = False
    MONGODB_URI: str = ""
    SESSION_SECRET: str = "dev-secret-change-me"
    ALLOWED_ORIGINS: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    TYPESAFE_API_KEY: str = ""
    JEV_ENABLED: bool = False
    SEARCH_API_KEY: str = ""
    MAX_CRAWL_PAGES: int = 12
    CRAWL_DEPTH: int = 2
    MAX_CONCURRENT_RUNS: int = 2
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "trao-api"
    DEBUG_CAPTURE_CONTENT: bool = False
    FAKE_LLM: str = ""  # set to "1" in tests to bypass credential check


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def require_credentials(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if s.FAKE_LLM:
        return
    if os.environ.get("FAKE_LLM"):
        return
    if not s.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
        from app.domain.errors import Codes, KitError

        raise KitError(Codes.MISSING_CREDENTIALS, "Missing GEMINI_API_KEY")
