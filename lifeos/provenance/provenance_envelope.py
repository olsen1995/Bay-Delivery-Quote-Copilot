"""
Phase 36 — Provenance Envelope

Redundant by design.
Sufficient to recompute lineage_id without external state.
"""

from provenance.lineage import derive_lineage_id


def build_provenance_envelope(
    *,
    canon_version: str,
    snapshot_hash: str,
    normalization_version: str,
) -> dict:
    lineage_id = derive_lineage_id(
        canon_version=canon_version,
        snapshot_hash=snapshot_hash,
        normalization_version=normalization_version,
    )

    return {
        "lineage_id": lineage_id,
        "canon_version": canon_version,
        "snapshot_hash": snapshot_hash,
        "normalization_version": normalization_version,
    }

