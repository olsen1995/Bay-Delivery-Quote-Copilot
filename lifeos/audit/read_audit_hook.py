# lifeos/audit/read_audit_hook.py
"""
Phase 35 — Canon Read Audit Hook

- Executed ONLY after Phase 34 access gate allows
- Receives already-resolved subject
- Never re-resolves identity
"""

from lifeos.audit.audit_writer import write_audit_record
from lifeos.canon.router import CanonRouter
from lifeos.canon.normalization import NORMALIZATION_VERSION


def audit_read(
    *,
    subject: str,
    resource: str,
    route: str,
    policy_version: str,
    snapshot_hash: str | None = None,
    digest_hash: str | None = None,
) -> None:
    write_audit_record(
        event_type="canon_read",
        subject=subject,
        resource=resource,
        route=route,
        canon_version=CanonRouter.canon_version(),
        normalization_version=NORMALIZATION_VERSION,
        policy_version=policy_version,
        snapshot_hash=snapshot_hash,
        digest_hash=digest_hash,
    )
