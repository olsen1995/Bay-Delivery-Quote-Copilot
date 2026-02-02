
from provenance.lineage_index import record_lineage_observation


def observe_lineage(provenance: dict | None) -> None:
    if provenance and "lineage_id" in provenance:
        record_lineage_observation(lineage_id=provenance["lineage_id"])

