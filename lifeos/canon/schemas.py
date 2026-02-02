import json
from pathlib import Path

_CANON_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _CANON_ROOT / "schemas"


def get_schemas():
    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_SCHEMA_DIR.glob("*.json"))
    ]
    return {"schemas": schemas}
