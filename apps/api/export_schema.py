"""Export fixtures/kit.schema.json from the Pydantic models (contract source of truth)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.domain.kit import Kit

schema = Kit.model_json_schema()
out = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "kit.schema.json")
with open(os.path.normpath(out), "w") as f:
    json.dump(schema, f, indent=2)
print("wrote", os.path.normpath(out))
