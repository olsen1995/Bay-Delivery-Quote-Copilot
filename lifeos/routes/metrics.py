# lifeos/routes/metrics.py
"""
Phase 37 — Optional Metrics API

Read-only.
Soft-failing.
System behavior unchanged if absent.
"""

from lifeos.metrics.aggregator import aggregate_reads


def get_metrics(window: str | None = None):
    try:
        return aggregate_reads(window=window)
    except Exception:
        # Fail soft: partial or empty response is acceptable
        return {}
