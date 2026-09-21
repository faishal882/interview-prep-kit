"""Deep JSON-schema validation for model output (types, not only top-level keys)."""
from __future__ import annotations

from typing import Any


def validate_against_schema(payload: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Raise ValueError describing the first mismatch with its path."""
    kind = schema.get("type", "object")
    if kind == "object":
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected object, got {type(payload).__name__}")
        for key in schema.get("required", []):
            if key not in payload:
                raise ValueError(f"{path}: missing key: {key}")
        for key, subschema in (schema.get("properties") or {}).items():
            if key in payload:
                validate_against_schema(payload[key], subschema, f"{path}.{key}")
    elif kind == "array":
        if not isinstance(payload, list):
            raise ValueError(f"{path}: expected array, got {type(payload).__name__}")
        item_schema = schema.get("items") or {}
        for i, item in enumerate(payload):
            validate_against_schema(item, item_schema, f"{path}[{i}]")
    elif kind == "string":
        if not isinstance(payload, str):
            raise ValueError(f"{path}: expected string, got {type(payload).__name__}")
    elif kind == "integer":
        if not isinstance(payload, int) or isinstance(payload, bool):
            raise ValueError(f"{path}: expected integer, got {payload!r}")
    elif kind == "number":
        if not isinstance(payload, (int, float)) or isinstance(payload, bool):
            raise ValueError(f"{path}: expected number, got {payload!r}")
    elif kind == "boolean":
        if not isinstance(payload, bool):
            raise ValueError(f"{path}: expected boolean, got {payload!r}")
