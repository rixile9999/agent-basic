import json
from poc1.config import DSL_SCHEMA_DIR

def load_schema(width: str) -> dict:
    return json.loads((DSL_SCHEMA_DIR / f"{width}.json").read_text())
