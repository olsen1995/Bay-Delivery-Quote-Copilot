
from audit.audit_writer import write_audit_record
from provenance.provenance_envelope import build_provenance_envelope


def audit_read_with_provenance(
    *,
    subject: str,
    resource: str,
    route: str,
    policy_version: str,
    canon_version: str,
    normalization_version: str,
    snapshot_hash: str | None = None,
    digest_hash: str | None = None,
) -> None:
    provenance = None

    if snapshot_hash is not None:
        provenance = build_provenance_envelope(
            canon_version=canon_version,
            snapshot_hash=snapshot_hash,
            normalization_version=normalization_version,
        )

    write_audit_record(
        event_type="canon_read",
        subject=subject,
        resource=resource,
        route=route,
        canon_version=canon_version,
        normalization_version=normalization_version,
        policy_version=policy_version,
        snapshot_hash=snapshot_hash,
        digest_hash=digest_hash,
        provenance=provenance,
    )

