import json
from pathlib import Path

from canon.hash_utils import sha256_bytes
from canon.normalization import (
    NORMALIZATION_VERSION,
    normalize,
    normalize_to_bytes,
)
from meta.version import get_version

_CANON_ROOT = Path(__file__).resolve().parent
_POLICY_VERSION = "1.0.0"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_strategies() -> list[dict]:
    strategies_dir = _CANON_ROOT / "strategies"
    return [
        _load_json(path)
        for path in sorted(strategies_dir.glob("*.json"))
    ]


def _load_schemas() -> list[dict]:
    schema_dir = _CANON_ROOT / "schemas"
    return [
        _load_json(path)
        for path in sorted(schema_dir.glob("*.json"))
    ]


def _load_trees() -> list[dict]:
    tree_dir = _CANON_ROOT / "trees"
    return [
        _load_json(path)
        for path in sorted(tree_dir.glob("*.json"))
    ]


def _build_raw_snapshot() -> dict:
    return {
        "strategies": _load_strategies(),
        "schemas": _load_schemas(),
        "trees": _load_trees(),
    }


def build_snapshot():
    raw = _build_raw_snapshot()
    normalized = normalize(raw)
    snapshot_hash = sha256_bytes(normalize_to_bytes(raw))
    canon_version = get_version().get("canon_version", "unknown")

    return {
        "data": normalized,
        "integrity": {
            "snapshot_hash": snapshot_hash,
            "canon_version": canon_version,
            "normalization_version": NORMALIZATION_VERSION,
            "policy_version": _POLICY_VERSION,
        },
    }


def build_digest():
    raw = _build_raw_snapshot()
    normalized = normalize(raw)
    digest_hash = sha256_bytes(normalize_to_bytes(raw))
    canon_version = get_version().get("canon_version", "unknown")

    return {
        "data": normalized,
        "integrity": {
            "digest_hash": digest_hash,
            "canon_version": canon_version,
            "normalization_version": NORMALIZATION_VERSION,
        },
    }


def get_snapshot():
    return build_snapshot()


def get_digest():
    return build_digest()
