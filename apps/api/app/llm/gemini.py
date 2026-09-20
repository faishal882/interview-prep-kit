"""Gemini provider (REST generateContent, JSON mode)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ProviderError


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=body, params={"key": self.api_key})
        except Exception as exc:
            raise ProviderError(str(exc)) from exc
        if resp.status_code == 429:
            ra = resp.headers.get("retry-after")
            raise ProviderError("rate limited", retry_after=float(ra) if ra else 5.0, status=429)
        if resp.status_code >= 500:
            raise ProviderError(f"server {resp.status_code}", status=resp.status_code)
        if resp.status_code != 200:
            raise ProviderError(f"gemini {resp.status_code}: {resp.text[:300]}", status=resp.status_code)
        try:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as exc:
            raise ProviderError(f"bad gemini payload: {exc}") from exc
