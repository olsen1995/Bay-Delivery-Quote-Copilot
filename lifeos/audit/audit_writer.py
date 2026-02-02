# lifeos/audit/audit_writer.py
"""
Phase 35 — Canon Read Audit Writer

- Append-only
- External to Canon
- Best-effort (never blocks reads)
- Deterministic record shape & serialization
"""

import json
import sys
import time
import hashlib
from pathlib import Path
from typing import Optional


_AUDIT_LOG_PATH = Path("audit_logs/canon_reads.log")


def _canonical_json(obj: dict) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hash_record(serialized: str) -> str:
    h = hashlib.sha256()
    h.update(serialized.encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


def write_audit_record(
    *,
    event_type: str,
    subject: str,
    resource: str,
    route: str,
    canon_version: str,
    normalization_version: str,
    policy_version: str,
    snapshot_hash: Optional[str] = None,
    digest_hash: Optional[str] = None,
) -> None:
    record = {
        "event_type": event_type,
        "subject": subject,
        "resource": resource,
        "route": route,
        "snapshot_hash": snapshot_hash,
        "digest_hash": digest_hash,
        "policy_version": policy_version,
        "canon_version": canon_version,
        "normalization_version": normalization_version,
        "timestamp": int(time.time()),  # observational only
    }

    serialized = _canonical_json(record)
    record["record_hash"] = _hash_record(serialized)

    try:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(_canonical_json(record) + "\n")
    except Exception as e:
        # Silent failure, measurable
        print(f"[audit-log-error] {e}", file=sys.stderr)
