from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Sequence

from app import storage


TEST_LABEL = "TEST / SIMULATED"
RENDER_ENV_MARKERS = ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_HOSTNAME")


SEED_JOBS: tuple[dict[str, Any], ...] = (
    {
        "job_id": "test-simulated-local-dump-run",
        "quote_id": "quote-test-simulated-local-dump-run",
        "request_id": "request-test-simulated-local-dump-run",
        "created_at": "2026-05-08T09:00:00",
        "completed_at": "2026-05-08T11:30:00",
        "customer_name": f"{TEST_LABEL} - Local Costing Review",
        "customer_phone": "000-000-0000",
        "job_address": f"{TEST_LABEL} - North Bay local dev only",
        "job_description_customer": "TEST / Simulated local dump run",
        "job_description_internal": (
            f"{TEST_LABEL} local-only seed record. Expected known total cost $153, "
            "profit $67, margin 30.5%."
        ),
        "service_type": "dump_run",
        "cash_total_cad": 220.0,
        "emt_total_cad": 248.60,
        "notes": f"{TEST_LABEL} seed job for desktop completed-job costing review.",
        "closeout_notes": f"{TEST_LABEL} closeout note. Final collected: $220 cash.",
        "request_json": {
            "source": TEST_LABEL,
            "customer_facing_quote": "220 cash",
            "expected_known_total_cost_cad": 153.0,
            "expected_profit_cad": 67.0,
            "expected_margin_percent": 30.5,
        },
        "costing": {
            "actual_labor_cost_cad": 50.0,
            "actual_disposal_cost_cad": 58.0,
            "actual_fuel_cost_cad": 40.0,
            "actual_other_costs_cad": 5.0,
            "final_amount_collected_cad": 220.0,
            "payment_method": "cash",
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
            "quote_accuracy_note": "TEST / SIMULATED expected profit $67 and margin 30.5%.",
            "disposal_receipt_note": "TEST / SIMULATED disposal cost $58.",
        },
    },
    {
        "job_id": "test-simulated-small-move",
        "quote_id": "quote-test-simulated-small-move",
        "request_id": "request-test-simulated-small-move",
        "created_at": "2026-05-08T10:00:00",
        "completed_at": "2026-05-08T13:00:00",
        "customer_name": f"{TEST_LABEL} - Local Costing Review",
        "customer_phone": "000-000-0000",
        "job_address": f"{TEST_LABEL} - North Bay local dev only",
        "job_description_customer": "TEST / Simulated small move",
        "job_description_internal": (
            f"{TEST_LABEL} local-only seed record. Expected known total cost $158, "
            "profit $181, margin 53.4%."
        ),
        "service_type": "small_move",
        "cash_total_cad": 300.0,
        "emt_total_cad": 339.0,
        "notes": f"{TEST_LABEL} seed job for desktop completed-job costing review.",
        "closeout_notes": f"{TEST_LABEL} closeout note. Final collected: $339 EMT / e-transfer.",
        "request_json": {
            "source": TEST_LABEL,
            "customer_facing_quote": "300 plus HST",
            "expected_known_total_cost_cad": 158.0,
            "expected_profit_cad": 181.0,
            "expected_margin_percent": 53.4,
        },
        "costing": {
            "actual_labor_cost_cad": 108.0,
            "actual_disposal_cost_cad": 0.0,
            "actual_fuel_cost_cad": 40.0,
            "actual_other_costs_cad": 10.0,
            "final_amount_collected_cad": 339.0,
            "payment_method": "emt",
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
            "quote_accuracy_note": "TEST / SIMULATED expected profit $181 and margin 53.4%.",
            "disposal_receipt_note": "TEST / SIMULATED no disposal cost.",
        },
    },
    {
        "job_id": "test-simulated-demo-debris-cleanup",
        "quote_id": "quote-test-simulated-demo-debris-cleanup",
        "request_id": "request-test-simulated-demo-debris-cleanup",
        "created_at": "2026-05-08T11:00:00",
        "completed_at": "2026-05-08T15:00:00",
        "customer_name": f"{TEST_LABEL} - Local Costing Review",
        "customer_phone": "000-000-0000",
        "job_address": f"{TEST_LABEL} - North Bay local dev only",
        "job_description_customer": "TEST / Simulated demo debris cleanup",
        "job_description_internal": (
            f"{TEST_LABEL} local-only seed record. Expected known total cost $310, "
            "profit $165, margin 34.7%."
        ),
        "service_type": "demolition",
        "cash_total_cad": 475.0,
        "emt_total_cad": 536.75,
        "notes": f"{TEST_LABEL} seed job for desktop completed-job costing review.",
        "closeout_notes": f"{TEST_LABEL} closeout note. Final collected: $475 cash.",
        "request_json": {
            "source": TEST_LABEL,
            "customer_facing_quote": "475 cash",
            "expected_known_total_cost_cad": 310.0,
            "expected_profit_cad": 165.0,
            "expected_margin_percent": 34.7,
        },
        "costing": {
            "actual_labor_cost_cad": 144.0,
            "actual_disposal_cost_cad": 96.0,
            "actual_fuel_cost_cad": 55.0,
            "actual_other_costs_cad": 15.0,
            "final_amount_collected_cad": 475.0,
            "payment_method": "cash",
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
            "quote_accuracy_note": "TEST / SIMULATED expected profit $165 and margin 34.7%.",
            "disposal_receipt_note": "TEST / SIMULATED disposal cost $96.",
        },
    },
)


def _resolved_db_path() -> Path:
    return storage._resolve_db_path()


def _is_render_like_path(path: Path) -> bool:
    normalized = str(path).replace("\\", "/").lower()
    return normalized.startswith("/var/data") or "/var/data/" in normalized


def _refuse_if_not_local(db_path: Path) -> str | None:
    active_markers = [name for name in RENDER_ENV_MARKERS if os.getenv(name)]
    if active_markers:
        return f"Render environment marker(s) present: {', '.join(active_markers)}"
    if _is_render_like_path(db_path):
        return f"database path looks like Render persistent storage: {db_path}"
    return None


def _seed_label_present(job: dict[str, Any]) -> bool:
    fields = (
        "customer_name",
        "job_description_customer",
        "job_description_internal",
        "job_address",
        "notes",
        "closeout_notes",
    )
    return any(TEST_LABEL in str(job.get(field) or "") for field in fields)


def _job_from_seed(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": seed["job_id"],
        "created_at": seed["created_at"],
        "status": "completed",
        "quote_id": seed["quote_id"],
        "request_id": seed["request_id"],
        "customer_name": seed["customer_name"],
        "customer_phone": seed["customer_phone"],
        "job_address": seed["job_address"],
        "job_description_customer": seed["job_description_customer"],
        "job_description_internal": seed["job_description_internal"],
        "service_type": seed["service_type"],
        "cash_total_cad": seed["cash_total_cad"],
        "emt_total_cad": seed["emt_total_cad"],
        "request_json": seed["request_json"],
        "notes": seed["notes"],
        "completed_at": seed["completed_at"],
        "closeout_notes": seed["closeout_notes"],
    }


def _seed_jobs() -> int:
    created = 0
    for seed in SEED_JOBS:
        job_id = seed["job_id"]
        existing = storage.get_job(job_id)
        if existing:
            if _seed_label_present(existing):
                print(f"SKIPPED existing {job_id} - {existing.get('job_description_customer')}")
            else:
                print(f"PROTECTED collision {job_id} - existing job lacks {TEST_LABEL} label")
            continue

        storage.save_job(_job_from_seed(seed))
        storage.update_job_costing(job_id, **seed["costing"])
        print(f"CREATED {job_id} - {seed['job_description_customer']}")
        created += 1
    return created


def _delete_seed_job(job_id: str) -> None:
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()
    finally:
        conn.close()


def _cleanup_seed_jobs() -> int:
    deleted = 0
    for seed in SEED_JOBS:
        job_id = seed["job_id"]
        existing = storage.get_job(job_id)
        if not existing:
            print(f"SKIPPED missing {job_id} - no seed job found")
            continue
        if not _seed_label_present(existing):
            print(f"PROTECTED collision {job_id} - existing job lacks {TEST_LABEL} label")
            continue

        _delete_seed_job(job_id)
        print(f"DELETED {job_id} - {existing.get('job_description_customer')}")
        deleted += 1
    return deleted


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or remove local-only TEST / SIMULATED completed job costing records."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete only deterministic TEST / SIMULATED jobs created by this script.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    db_path = _resolved_db_path()
    print(f"Target DB: {db_path}")

    refusal = _refuse_if_not_local(db_path)
    if refusal:
        print(f"REFUSED local seed operation: {refusal}")
        return 2

    storage.init_db()
    if args.cleanup:
        _cleanup_seed_jobs()
    else:
        _seed_jobs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
