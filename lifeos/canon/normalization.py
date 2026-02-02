"""
Phase 33 — Canon Normalization Layer (Authoritative)

This module is the SINGLE source of truth for:
- Snapshot structure
- Snapshot ordering
- Digest structure
- Digest ordering
- Hash inputs

Rules:
- Total: every snapshot/digest path MUST pass through here
- Closed: no bypasses, no flags, no partial usage
- Side-effect free
"""

from __future__ import annotations
import json
from typing import Any
from canon.ordering_rules import apply_ordering_rules


NORMALIZATION_VERSION = "1.0.1"


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}

    if isinstance(obj, list):
        return [_normalize(v) for v in obj]

    return obj


def normalize(obj: dict) -> dict:
    """
    Apply declared ordering rules, then recursively normalize.
    Returns a fully normalized Python object.
    """
    ordered = apply_ordering_rules(obj)
    return _normalize(ordered)


def normalize_to_bytes(obj: dict) -> bytes:
    """
    Canonical UTF-8 JSON bytes for hashing and comparison.
    """
    normalized = normalize(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
