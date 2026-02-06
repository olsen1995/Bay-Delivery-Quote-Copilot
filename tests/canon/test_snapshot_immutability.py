from lifeos.canon.snapshot import get_snapshot
from lifeos.canon.digest import get_digest


def test_canon_snapshot_is_deterministic():
    """
    Canon snapshots must be deterministic.
    Repeated snapshot generation over unchanged Canon state
    must yield identical digests.
    """

    snapshot_a = get_snapshot()
    snapshot_b = get_snapshot()

    digest_a = get_digest(snapshot_a)
    digest_b = get_digest(snapshot_b)

    assert digest_a == digest_b, (
        "Canon snapshot digest changed without Canon content change. "
        "Snapshot boundaries must be immutable."
    )