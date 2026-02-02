from lifeos.canon.read_gate import assert_read_allowed
from lifeos.canon.snapshot import build_digest
from lifeos.audit.read_audit_hook import audit_read

_POLICY_VERSION = "1.0.0"


def get_digest_internal():
    resource = assert_read_allowed(
        route="/canon/snapshot/digest",
        subject="internal"
    )
    result = build_digest()
    audit_read(
        subject="internal",
        resource=resource,
        route="/canon/snapshot/digest",
        policy_version=_POLICY_VERSION,
        digest_hash=result["integrity"]["digest_hash"],
    )
    return result
