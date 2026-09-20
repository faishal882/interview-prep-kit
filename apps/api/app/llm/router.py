"""Single-LLM generation: retry/backoff plus exactly one repair attempt on invalid output."""
from __future__ import annotations

from typing import Any

from .base import ProviderError
from .retry import with_retry


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…[truncated]"


async def generate(
    provider: Any,
    prompt: str,
    schema: dict[str, Any],
    *,
    repair_prompt: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Run one provider; on invalid output make exactly one repair attempt."""
    raw = await with_retry(lambda: provider.generate_structured(prompt, schema))
    try:
        _check_shape(raw, schema)
        return raw, provider.name
    except ValueError as ve:
        # one repair attempt with the validation error included
        fix = (repair_prompt or "Fix the JSON so it matches the schema.") + f"\nError: {ve}"
        raw2 = await provider.generate_structured(fix + "\n" + prompt, schema)
        _check_shape(raw2, schema)
        return raw2, provider.name


def _check_shape(payload: Any, schema: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("top-level must be an object")
    for key in schema.get("required", []):
        if key not in payload:
            raise ValueError(f"missing key: {key}")
