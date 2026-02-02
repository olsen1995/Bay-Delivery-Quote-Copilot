from canon.read_gate import assert_read_allowed
from canon.snapshot import build_snapshot
from audit.read_audit_hook import audit_read

_POLICY_VERSION = "1.0.0"


def get_snapshot_gpt():
    resource = assert_read_allowed(
        route="/canon/snapshot",
        subject="gpt"
    )
    result = build_snapshot()
    audit_read(
        subject="gpt",
        resource=resource,
        route="/canon/snapshot",
        policy_version=_POLICY_VERSION,
        snapshot_hash=result["integrity"]["snapshot_hash"],
    )
    return result

