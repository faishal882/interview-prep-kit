"""Groq provider (OpenAI-compatible chat completions, json_object)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ProviderError


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Respond with JSON matching this schema: {json.dumps(schema)}"},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except Exception as exc:
            raise ProviderError(str(exc)) from exc
        if resp.status_code == 429:
            ra = resp.headers.get("retry-after")
            raise ProviderError("rate limited", retry_after=float(ra) if ra else 5.0, status=429)
        if resp.status_code >= 500:
            raise ProviderError(f"server {resp.status_code}", status=resp.status_code)
        if resp.status_code != 200:
            raise ProviderError(f"groq {resp.status_code}: {resp.text[:300]}", status=resp.status_code)
        try:
            data = resp.json()
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as exc:
            raise ProviderError(f"bad groq payload: {exc}") from exc
