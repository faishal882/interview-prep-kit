"""Phase 13: every operation declares a typed response; OpenAPI is the source."""
from app.main import create_app


def _operations():
    spec = create_app().openapi()
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in ("get", "post", "patch", "delete", "put"):
                continue
            yield f"{method.upper()} {path}", op


def _schema_ref(op):
    responses = op.get("responses", {})
    ok = responses.get("200") or responses.get("201") or {}
    content = (ok.get("content") or {}).get("application/json", {})
    return content.get("schema") or {}


def _is_typed(schema: dict) -> bool:
    if schema.get("$ref"):
        return True
    variants = schema.get("anyOf", []) + schema.get("oneOf", [])
    return bool(variants) and all(v.get("$ref") for v in variants)


def test_every_operation_has_typed_response():
    untyped = [name for name, op in _operations() if not _is_typed(_schema_ref(op))]
    assert untyped == [], f"untyped responses: {untyped}"


def _member_models(schema: dict) -> list[str]:
    if schema.get("$ref"):
        return [schema["$ref"].split("/")[-1]]
    out = []
    for variant in schema.get("anyOf", []) + schema.get("oneOf", []):
        if variant.get("$ref"):
            out.append(variant["$ref"].split("/")[-1])
    return out


def test_response_schemas_have_declared_properties():
    spec = create_app().openapi()
    components = spec.get("components", {}).get("schemas", {})
    for name, op in _operations():
        members = _member_models(_schema_ref(op))
        assert members, f"{name} declares no response model"
        for model in members:
            assert model in components, name
            schema = components[model]
            if "oneOf" in schema or "anyOf" in schema:
                continue  # union members each declare their own properties below
            props = schema.get("properties", {})
            assert props, f"{name} -> {model} declares no properties"


def test_union_members_declare_properties():
    spec = create_app().openapi()
    components = spec.get("components", {}).get("schemas", {})
    for name, op in _operations():
        schema = _schema_ref(op)
        if "$ref" in schema:
            continue
        for variant in schema.get("oneOf", []) + schema.get("anyOf", []):
            member = variant.get("$ref", "").split("/")[-1]
            assert member in components, (name, member)
            assert components[member].get("properties"), (name, member)
