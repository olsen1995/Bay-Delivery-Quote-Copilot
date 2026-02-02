import json
from pathlib import Path

_CANON_ROOT = Path(__file__).resolve().parent
_TREE_DIR = _CANON_ROOT / "trees"


def get_trees():
    trees = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_TREE_DIR.glob("*.json"))
    ]
    return {"trees": trees}
