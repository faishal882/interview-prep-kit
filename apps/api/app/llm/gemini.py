"""Gemini provider: one shared pooled client, key in a header.

The model key is sent as `x-goog-api-key`, never as a URL parameter, so it
cannot appear in logged addresses. Connections are pooled and reused across
all concurrent generations in the process.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ProviderError, TruncatedError

_client: httpx.AsyncClient | None = None


def shared_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=10),
        )
    return _client


async def close_shared_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash",
                 client: httpx.AsyncClient | None = None, base_url: str = "https://generativelanguage.googleapis.com"):
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self.model = model
        self._client = client
        self._base_url = base_url.rstrip("/")

    def _client_or_shared(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return shared_client()

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/v1beta/models/{self.model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }
        client = self._client_or_shared()
        try:
            resp = await client.post(url, json=body, headers={"x-goog-api-key": self._api_key})
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise ProviderError(f"network: {type(exc).__name__}", transient=True) from exc
        if resp.status_code == 429:
            ra = resp.headers.get("retry-after")
            try:
                hint = float(ra) if ra is not None else 5.0
            except ValueError:
                hint = 5.0
            raise ProviderError("rate limited", retry_after=hint, status=429)
        if resp.status_code >= 500:
            raise ProviderError(f"server {resp.status_code}", status=resp.status_code, transient=True)
        if resp.status_code != 200:
            raise ProviderError(f"gemini {resp.status_code}", status=resp.status_code, transient=False)
        try:
            data = resp.json()
        except Exception as exc:
            raise ProviderError("bad gemini payload: not JSON", transient=False) from exc
        try:
            candidates = data.get("candidates") or []
            first = candidates[0] if candidates else {}
            finish = first.get("finishReason", "STOP")
            parts = (first.get("content") or {}).get("parts") or []
            text = next((p.get("text") for p in parts if isinstance(p, dict) and p.get("text")), "")
        except Exception as exc:
            raise ProviderError("bad gemini payload: shape", transient=False) from exc
        if not text:
            if finish == "MAX_TOKENS":
                raise TruncatedError()
            raise ProviderError(f"bad gemini payload: empty (finish={finish})", transient=False)
        try:
            return json.loads(text)
        except Exception as exc:
            raise ProviderError("bad gemini payload: not JSON", transient=False) from exc
