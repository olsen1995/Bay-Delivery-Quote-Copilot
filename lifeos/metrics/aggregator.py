# lifeos/metrics/aggregator.py
"""
Phase 37 — Read-Side Aggregation Engine

- Derived ONLY from existing audit logs (Phase 35)
- Optional use of provenance envelope (Phase 36)
- Best-effort, rebuildable, discardable
- Descriptive only (no runtime influence)
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


_AUDIT_LOG = Path("audit_logs/canon_reads.log")


def _within_window(ts: int, *, window: Optional[str]) -> bool:
    if window is None:
        return True

    now = int(time.time())

    if window == "last_24h":
        return ts >= now - 24 * 3600
    if window == "last_7d":
        return ts >= now - 7 * 24 * 3600

    # Unknown or custom windows are treated as best-effort pass-through
    return True


def aggregate_reads(*, window: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggregate read counts by allowed dimensions.
    Returns partial results if data is missing or malformed.
    """
    results: Dict[str, int] = {}

    if not _AUDIT_LOG.exists():
        return {}

    with _AUDIT_LOG.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue  # tolerate malformed lines

            ts = rec.get("timestamp")
            if not isinstance(ts, int) or not _within_window(ts, window=window):
                continue

            subject = rec.get("subject")
            resource = rec.get("resource")
            canon_version = rec.get("canon_version")
            lineage_id = None

            prov = rec.get("provenance")
            if isinstance(prov, dict):
                lineage_id = prov.get("lineage_id")

            key = (
                subject,
                resource,
                canon_version,
                lineage_id,
            )

            results[key] = results.get(key, 0) + 1

    # Shape-only determinism: stable serialization order
    return {
        "window": window,
        "metrics": [
            {
                "subject": k[0],
                "resource": k[1],
                "canon_version": k[2],
                "lineage_id": k[3],
                "read_count": v,
            }
            for k, v in sorted(results.items(), key=lambda i: str(i[0]))
        ],
    }
