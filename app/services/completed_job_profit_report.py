from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.storage import load_completed_job_profit_report_sources

# Fields required for a row to be considered "complete" (trusted margin)
REQUIRED_COMPLETENESS_FIELDS = (
    "final_amount_collected_cad",
    "actual_labor_cost_cad",
    "actual_disposal_cost_cad",
    "actual_fuel_cost_cad",
    "actual_other_costs_cad",
    "payment_status",
)

# Margin threshold below which owner review is flagged
MARGIN_OWNER_REVIEW_THRESHOLD = 20.0

# job_profit_status values that always trigger owner review
OWNER_REVIEW_PROFIT_STATUSES = frozenset({"underquoted", "painful"})

INTERNAL_DISCLAIMER = (
    "Internal report only. Completed-job data helps owner review and future pricing "
    "calibration. It does not change quote prices."
)


def _is_field_present(value: Any) -> bool:
    """Return True if the value is non-None and non-blank."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _missing_fields(row: dict[str, Any]) -> list[str]:
    return [f for f in REQUIRED_COMPLETENESS_FIELDS if not _is_field_present(row.get(f))]


def _known_cost(row: dict[str, Any]) -> float | None:
    """Sum the four actual cost fields. Returns None if any is missing."""
    cost_fields = (
        "actual_labor_cost_cad",
        "actual_disposal_cost_cad",
        "actual_fuel_cost_cad",
        "actual_other_costs_cad",
    )
    values = [row.get(f) for f in cost_fields]
    if any(v is None for v in values):
        return None
    try:
        return sum(float(v) for v in values)
    except (TypeError, ValueError):
        return None


def _known_profit(collected: float, cost: float) -> float:
    return collected - cost


def _known_margin_pct(profit: float, collected: float) -> float | None:
    if collected <= 0:
        return None
    return (profit / collected) * 100.0


def _analyze_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return an annotated dict for a single completed job row."""
    missing = _missing_fields(row)
    is_complete = len(missing) == 0

    collected = row.get("final_amount_collected_cad")
    payment_status = row.get("payment_status") or ""
    profit_status = row.get("job_profit_status") or ""

    # Treat as incomplete if payment_status indicates unpaid/pending or collected is missing/zero
    unpaid = payment_status in ("not_paid_yet", "partial_payment") or not _is_field_present(collected)
    if unpaid and "payment_status" not in missing:
        missing = list(missing) + ["payment_status_unpaid"]
    if unpaid or not _is_field_present(collected):
        is_complete = False

    # Compute trusted figures only when complete and collected > 0
    known_cost_val = _known_cost(row) if is_complete else None
    known_profit_val: float | None = None
    known_margin_pct_val: float | None = None
    trusted_margin = False

    try:
        collected_float = float(collected) if _is_field_present(collected) else None
    except (TypeError, ValueError):
        collected_float = None

    if is_complete and collected_float is not None and collected_float > 0 and known_cost_val is not None:
        known_profit_val = _known_profit(collected_float, known_cost_val)
        known_margin_pct_val = _known_margin_pct(known_profit_val, collected_float)
        trusted_margin = True

    # Owner review logic
    owner_review = False
    owner_review_reasons: list[str] = []
    if profit_status in OWNER_REVIEW_PROFIT_STATUSES:
        owner_review = True
        owner_review_reasons.append(f"job_profit_status={profit_status}")
    if trusted_margin and known_margin_pct_val is not None and known_margin_pct_val < MARGIN_OWNER_REVIEW_THRESHOLD:
        owner_review = True
        owner_review_reasons.append(f"below_{MARGIN_OWNER_REVIEW_THRESHOLD:.0f}pct_margin")
    if unpaid and _is_field_present(collected):
        owner_review = True
        owner_review_reasons.append("payment_incomplete")

    return {
        "job_id": row.get("job_id"),
        "service_type": row.get("service_type") or "unknown",
        "customer_name": row.get("customer_name"),
        "scheduled_start": row.get("scheduled_start"),
        "payment_method": row.get("payment_method"),
        "payment_status": payment_status or None,
        "job_profit_status": profit_status or None,
        "final_amount_collected_cad": collected_float,
        "known_cost_cad": known_cost_val,
        "known_profit_cad": known_profit_val,
        "known_margin_pct": round(known_margin_pct_val, 2) if known_margin_pct_val is not None else None,
        "trusted_margin": trusted_margin,
        "is_complete": is_complete,
        "missing_fields": missing,
        "owner_review": owner_review,
        "owner_review_reasons": owner_review_reasons,
    }


def _build_category_breakdown(analyzed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate analyzed rows by service_type."""
    categories: dict[str, dict[str, Any]] = {}

    for row in analyzed_rows:
        cat = row["service_type"] or "unknown"
        if cat not in categories:
            categories[cat] = {
                "service_type": cat,
                "total_jobs": 0,
                "complete_rows": 0,
                "incomplete_rows": 0,
                "owner_review_count": 0,
                "underquoted_painful_count": 0,
                "known_profit_total_cad": 0.0,
                "_margin_sum": 0.0,
                "_margin_count": 0,
                "_collected_sum": 0.0,
                "_collected_count": 0,
            }
        entry = categories[cat]
        entry["total_jobs"] += 1
        if row["is_complete"]:
            entry["complete_rows"] += 1
        else:
            entry["incomplete_rows"] += 1
        if row["owner_review"]:
            entry["owner_review_count"] += 1
        if row.get("job_profit_status") in OWNER_REVIEW_PROFIT_STATUSES:
            entry["underquoted_painful_count"] += 1
        if row["trusted_margin"] and row["known_profit_cad"] is not None:
            entry["known_profit_total_cad"] += row["known_profit_cad"]
        if row["trusted_margin"] and row["known_margin_pct"] is not None:
            entry["_margin_sum"] += row["known_margin_pct"]
            entry["_margin_count"] += 1
        if row["trusted_margin"] and row["final_amount_collected_cad"] is not None:
            entry["_collected_sum"] += row["final_amount_collected_cad"]
            entry["_collected_count"] += 1

    result = []
    for cat_data in categories.values():
        avg_margin = (
            round(cat_data["_margin_sum"] / cat_data["_margin_count"], 2)
            if cat_data["_margin_count"] > 0
            else None
        )
        avg_collected = (
            round(cat_data["_collected_sum"] / cat_data["_collected_count"], 2)
            if cat_data["_collected_count"] > 0
            else None
        )
        result.append({
            "service_type": cat_data["service_type"],
            "total_jobs": cat_data["total_jobs"],
            "complete_rows": cat_data["complete_rows"],
            "incomplete_rows": cat_data["incomplete_rows"],
            "owner_review_count": cat_data["owner_review_count"],
            "underquoted_painful_count": cat_data["underquoted_painful_count"],
            "known_profit_total_cad": round(cat_data["known_profit_total_cad"], 2),
            "avg_known_margin_pct": avg_margin,
            "avg_collected_cad": avg_collected,
        })

    result.sort(key=lambda x: x["total_jobs"], reverse=True)
    return result


def _build_summary_cards(analyzed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(analyzed_rows)
    missing_costs = sum(1 for r in analyzed_rows if not r["is_complete"])
    owner_review = sum(1 for r in analyzed_rows if r["owner_review"])
    underquoted_painful = sum(
        1 for r in analyzed_rows if r.get("job_profit_status") in OWNER_REVIEW_PROFIT_STATUSES
    )

    trusted_rows = [r for r in analyzed_rows if r["trusted_margin"] and r["known_profit_cad"] is not None]
    known_profit_total = round(sum(r["known_profit_cad"] for r in trusted_rows), 2) if trusted_rows else None

    margin_vals = [r["known_margin_pct"] for r in trusted_rows if r["known_margin_pct"] is not None]
    avg_margin = round(sum(margin_vals) / len(margin_vals), 2) if margin_vals else None

    return [
        {"key": "completed_jobs_reviewed", "label": "Completed Jobs Reviewed", "value": total, "description": "Total completed jobs included in this report."},
        {"key": "missing_cost_data", "label": "Missing Cost Data", "value": missing_costs, "description": "Completed jobs missing required closeout or cost fields."},
        {"key": "owner_review", "label": "Owner Review", "value": owner_review, "description": "Jobs flagged for owner review: below 20% margin, underquoted, or painful."},
        {"key": "underquoted_painful", "label": "Underquoted / Painful", "value": underquoted_painful, "description": "Jobs explicitly marked as underquoted or painful."},
        {"key": "known_profit_total_cad", "label": "Known Profit Total", "value": known_profit_total, "description": "Total known profit from complete, trusted rows only."},
        {"key": "avg_known_margin_pct", "label": "Average Known Margin", "value": avg_margin, "description": "Average known margin % from complete, trusted rows only."},
    ]


def build_completed_job_profit_report(*, limit: int = 200) -> dict[str, Any]:
    """Build the complete profit review report from completed job rows.

    Read-only. Does not invoke pricing computation or modify any data.
    """
    raw_rows = load_completed_job_profit_report_sources(limit=limit)
    analyzed = [_analyze_row(row) for row in raw_rows]

    summary_cards = _build_summary_cards(analyzed)
    category_breakdown = _build_category_breakdown(analyzed)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": INTERNAL_DISCLAIMER,
        "summary_cards": summary_cards,
        "category_breakdown": category_breakdown,
        "jobs": analyzed,
    }
