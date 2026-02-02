from metrics.aggregator import aggregate_reads


def get_metrics(window: str | None = None):
    try:
        return aggregate_reads(window=window)
    except Exception:
        return {}
