from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import storage
from scripts.run_price_calibration_mocks import (
    CREW_RATE_TARGETS,
    EXTRA_HELPER_CUSTOMER_FACING_HOURLY_RANGE,
    OPERATING_COST_ASSUMPTIONS,
)


CORE_COST_FIELDS = (
    "actual_labor_cost_cad",
    "actual_disposal_cost_cad",
    "actual_fuel_cost_cad",
    "actual_other_costs_cad",
)
CONTEXT_COSTING_FIELDS = (
    "actual_hours",
    "actual_crew_size",
    "final_amount_collected_cad",
    "payment_status",
    "job_profit_status",
)
JOB_COLUMNS = (
    "job_id",
    "created_at",
    "status",
    "customer_name",
    "service_type",
    "cash_total_cad",
    "emt_total_cad",
    "completed_at",
    "job_description_customer",
    "actual_hours",
    "actual_crew_size",
    "actual_labor_cost_cad",
    "actual_disposal_cost_cad",
    "actual_fuel_cost_cad",
    "actual_other_costs_cad",
    "final_amount_collected_cad",
    "payment_method",
    "payment_status",
    "job_profit_status",
)
MARGIN_FLOOR_PCT = OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct
DISPOSAL_HEAVY_MIN_CAD = 50.0
DISPOSAL_HEAVY_SHARE = 0.20


@dataclass(frozen=True)
class CompletedJobAnalysis:
    job_id: str
    service_type: str
    final_amount_collected: float | None
    actual_labor_cost: float | None
    actual_disposal_cost: float | None
    actual_fuel_cost: float | None
    actual_other_cost: float | None
    known_cost: float
    known_profit: float | None
    known_margin_pct: float | None
    payment_status: str | None
    job_profit_status: str | None
    missing_fields: tuple[str, ...]
    operating_cost_target_floor: float | None
    operating_cost_target_gap: float | None
    crew_rate_target_floor: float | None
    risk_flags: tuple[str, ...]
    owner_review: bool


@dataclass(frozen=True)
class Summary:
    job_count: int
    average_collected: float | None
    average_known_cost: float | None
    average_known_profit: float | None
    average_known_margin_pct: float | None
    below_margin_count: int
    missing_cost_count: int
    owner_review_count: int


def _resolved_db_path() -> Path:
    return storage._resolve_db_path()


def _read_only_connection(db_path: Path) -> sqlite3.Connection:
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    try:
        return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def _completed_job_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _table_columns(conn, "jobs")
    if "jobs" not in _tables(conn) or "status" not in columns:
        return []

    selected_columns = [column for column in JOB_COLUMNS if column in columns]
    if "job_id" not in selected_columns:
        return []

    select_sql = ", ".join(selected_columns)
    order_sql = "datetime(created_at) DESC, job_id ASC"
    if "completed_at" in columns:
        order_sql = "datetime(COALESCE(completed_at, created_at)) DESC, job_id ASC"
    rows = conn.execute(
        f"""
        SELECT {select_sql}
        FROM jobs
        WHERE status = 'completed'
        ORDER BY {order_sql}
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row["name"])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _known_cost(row: dict[str, Any]) -> float:
    return round(sum(_float_or_none(row.get(field)) or 0.0 for field in CORE_COST_FIELDS), 2)


def _missing_fields(row: dict[str, Any]) -> tuple[str, ...]:
    missing = [
        field
        for field in (*CORE_COST_FIELDS, *CONTEXT_COSTING_FIELDS)
        if row.get(field) is None or row.get(field) == ""
    ]
    return tuple(missing)


def _margin_pct(*, collected: float | None, profit: float | None) -> float | None:
    if collected is None or collected <= 0.0 or profit is None:
        return None
    return round((profit / collected) * 100.0, 1)


def _operating_cost_target_floor(known_cost: float) -> float | None:
    overhead_pct = OPERATING_COST_ASSUMPTIONS.admin_overhead_pct_of_revenue / 100.0
    margin_pct = OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct / 100.0
    denominator = 1.0 - overhead_pct - margin_pct
    if denominator <= 0.0:
        return None
    return round(known_cost / denominator, 2)


def _crew_rate_target_floor(row: dict[str, Any]) -> float | None:
    hours = _float_or_none(row.get("actual_hours"))
    crew_size_raw = row.get("actual_crew_size")
    if hours is None or crew_size_raw is None:
        return None
    crew_size = int(crew_size_raw)
    if hours <= 0.0 or crew_size <= 0:
        return None

    target = CREW_RATE_TARGETS.get(min(crew_size, 3))
    if target is None:
        return None

    target_hours = max(hours, target.minimum_billable_hours)
    floor = target.customer_facing_hourly_range[0] * target_hours
    if crew_size > 3:
        floor += (crew_size - 3) * EXTRA_HELPER_CUSTOMER_FACING_HOURLY_RANGE[0] * target_hours
    return round(floor, 2)


def _risk_flags(
    *,
    collected: float | None,
    known_margin_pct: float | None,
    missing_fields: tuple[str, ...],
    operating_cost_target_gap: float | None,
    crew_rate_target_floor: float | None,
    actual_disposal_cost: float | None,
    payment_status: str | None,
    job_profit_status: str | None,
) -> tuple[str, ...]:
    flags: list[str] = []
    if known_margin_pct is not None and known_margin_pct < MARGIN_FLOOR_PCT:
        flags.append("BELOW_CONTRIBUTION_MARGIN")
    if operating_cost_target_gap is not None and operating_cost_target_gap > 0.0:
        flags.append("UNDER_OPERATING_COST_TARGET")
    if missing_fields:
        flags.append("MISSING_COST_DATA")
    if actual_disposal_cost is not None and actual_disposal_cost >= DISPOSAL_HEAVY_MIN_CAD:
        if collected is None or collected <= 0.0 or (actual_disposal_cost / collected) >= DISPOSAL_HEAVY_SHARE:
            flags.append("DISPOSAL_HEAVY_RISK")
    if crew_rate_target_floor is not None and collected is not None and collected < crew_rate_target_floor:
        flags.append("LABOUR_UNDERPRICED_RISK")
    if payment_status is not None and payment_status != "paid_in_full":
        flags.append("PAYMENT_NOT_FULLY_COLLECTED")
    if job_profit_status in {"underquoted", "painful"}:
        flags.append("OPERATOR_MARKED_UNDERPRICED")
    return tuple(flags)


def _analyze_row(row: dict[str, Any]) -> CompletedJobAnalysis:
    collected = _float_or_none(row.get("final_amount_collected_cad"))
    known_cost = _known_cost(row)
    known_profit = round(collected - known_cost, 2) if collected is not None else None
    margin_pct = _margin_pct(collected=collected, profit=known_profit)
    missing = _missing_fields(row)
    target_floor = _operating_cost_target_floor(known_cost)
    target_gap = (
        round(max(target_floor - collected, 0.0), 2)
        if target_floor is not None and collected is not None
        else None
    )
    crew_floor = _crew_rate_target_floor(row)
    payment_status = _str_or_none(row.get("payment_status"))
    job_profit_status = _str_or_none(row.get("job_profit_status"))
    flags = _risk_flags(
        collected=collected,
        known_margin_pct=margin_pct,
        missing_fields=missing,
        operating_cost_target_gap=target_gap,
        crew_rate_target_floor=crew_floor,
        actual_disposal_cost=_float_or_none(row.get("actual_disposal_cost_cad")),
        payment_status=payment_status,
        job_profit_status=job_profit_status,
    )
    return CompletedJobAnalysis(
        job_id=str(row.get("job_id") or ""),
        service_type=str(row.get("service_type") or "unknown"),
        final_amount_collected=collected,
        actual_labor_cost=_float_or_none(row.get("actual_labor_cost_cad")),
        actual_disposal_cost=_float_or_none(row.get("actual_disposal_cost_cad")),
        actual_fuel_cost=_float_or_none(row.get("actual_fuel_cost_cad")),
        actual_other_cost=_float_or_none(row.get("actual_other_costs_cad")),
        known_cost=known_cost,
        known_profit=known_profit,
        known_margin_pct=margin_pct,
        payment_status=payment_status,
        job_profit_status=job_profit_status,
        missing_fields=missing,
        operating_cost_target_floor=target_floor,
        operating_cost_target_gap=target_gap,
        crew_rate_target_floor=crew_floor,
        risk_flags=flags,
        owner_review=bool(flags),
    )


def analyze_completed_jobs(db_path: Path | None = None) -> list[CompletedJobAnalysis]:
    target = db_path or _resolved_db_path()
    if not target.exists():
        return []

    conn = _read_only_connection(target)
    try:
        return [_analyze_row(row) for row in _completed_job_rows(conn)]
    finally:
        conn.close()


def _average(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def summarize(results: Sequence[CompletedJobAnalysis]) -> Summary:
    return Summary(
        job_count=len(results),
        average_collected=_average([r.final_amount_collected for r in results if r.final_amount_collected is not None]),
        average_known_cost=_average([r.known_cost for r in results]),
        average_known_profit=_average([r.known_profit for r in results if r.known_profit is not None]),
        average_known_margin_pct=_average([r.known_margin_pct for r in results if r.known_margin_pct is not None]),
        below_margin_count=sum("BELOW_CONTRIBUTION_MARGIN" in r.risk_flags for r in results),
        missing_cost_count=sum("MISSING_COST_DATA" in r.risk_flags for r in results),
        owner_review_count=sum(r.owner_review for r in results),
    )


def _money(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _text(value: str | None) -> str:
    return value or "N/A"


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def _risk_sort_key(result: CompletedJobAnalysis) -> tuple[int, float, float]:
    target_gap = result.operating_cost_target_gap or 0.0
    profit_loss = -(result.known_profit or 0.0)
    return (len(result.risk_flags), target_gap, profit_loss)


def print_report(results: Sequence[CompletedJobAnalysis], *, db_path: Path) -> None:
    print("Bay Delivery Completed Job Calibration Analysis")
    print("Local/read-only analysis. No quote totals, app pricing, or production records are changed.")
    print(f"Target DB: {db_path}")
    print(
        "Comparison assumptions: "
        f"{MARGIN_FLOOR_PCT:.0f}% contribution margin floor, "
        f"{OPERATING_COST_ASSUMPTIONS.admin_overhead_pct_of_revenue:.0f}% overhead target."
    )
    if not db_path.exists():
        print()
        print("No completed jobs found: database file does not exist.")
        print(r"To create local simulated jobs explicitly, run: .\.venv\Scripts\python.exe scripts\seed_local_job_costing_data.py")
        return
    if not results:
        print()
        print("No completed jobs found in the local jobs table.")
        print(r"To create local simulated jobs explicitly, run: .\.venv\Scripts\python.exe scripts\seed_local_job_costing_data.py")
        return

    summary = summarize(results)
    print()
    print("Completed Job Calibration Summary")
    print("---------------------------------")
    print(f"Total completed jobs analyzed: {summary.job_count}")
    print(f"Average collected amount: {_money(summary.average_collected)}")
    print(f"Average known cost: {_money(summary.average_known_cost)}")
    print(f"Average known profit: {_money(summary.average_known_profit)}")
    print(f"Average known margin: {_pct(summary.average_known_margin_pct)}")
    print(f"Jobs below {MARGIN_FLOOR_PCT:.0f}% margin: {summary.below_margin_count}")
    print(f"Jobs with missing cost data: {summary.missing_cost_count}")
    print(f"Jobs needing owner review: {summary.owner_review_count}")

    print()
    print("Completed Jobs")
    print("--------------")
    _print_table(
        (
            "job",
            "service",
            "collected",
            "known cost",
            "profit",
            "margin",
            "target floor",
            "target gap",
            "payment",
            "profit status",
            "missing fields",
            "risk flags",
        ),
        [
            (
                result.job_id,
                result.service_type,
                _money(result.final_amount_collected),
                _money(result.known_cost),
                _money(result.known_profit),
                _pct(result.known_margin_pct),
                _money(result.operating_cost_target_floor),
                _money(result.operating_cost_target_gap),
                _text(result.payment_status),
                _text(result.job_profit_status),
                ", ".join(result.missing_fields) or "none",
                ", ".join(result.risk_flags) or "OK",
            )
            for result in results
        ],
    )

    review_rows = [result for result in results if result.owner_review]
    print()
    print("Highest-Risk Examples")
    print("---------------------")
    if not review_rows:
        print("No owner-review risks found.")
    else:
        _print_table(
            ("job", "service", "margin", "target gap", "risk flags"),
            [
                (
                    result.job_id,
                    result.service_type,
                    _pct(result.known_margin_pct),
                    _money(result.operating_cost_target_gap),
                    ", ".join(result.risk_flags),
                )
                for result in sorted(review_rows, key=_risk_sort_key, reverse=True)[:5]
            ],
        )

    print()
    print("Category Summary")
    print("----------------")
    category_rows: list[tuple[str, str, str, str, str, str]] = []
    for service_type in sorted({result.service_type for result in results}):
        service_results = [result for result in results if result.service_type == service_type]
        service_summary = summarize(service_results)
        category_rows.append(
            (
                service_type,
                str(service_summary.job_count),
                _money(service_summary.average_collected),
                _money(service_summary.average_known_profit),
                _pct(service_summary.average_known_margin_pct),
                str(service_summary.owner_review_count),
            )
        )
    _print_table(
        ("service", "jobs", "avg collected", "avg profit", "avg margin", "owner review"),
        category_rows,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only local analysis of completed-job costing against calibration assumptions."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional SQLite database path. Defaults to BAYDELIVERY_DB_PATH or the repo local DB path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    db_path = args.db_path or _resolved_db_path()
    results = analyze_completed_jobs(db_path)
    print_report(results, db_path=db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
