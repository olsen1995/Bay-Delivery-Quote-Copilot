import base64
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "job-costing.sqlite3"
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{db_path}{suffix}")
        if path.exists():
            path.unlink()
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    return db_path


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, isolated_db: Path) -> TestClient:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _seed_job(
    job_id: str = "job-costing",
    status: str = "completed",
    service_type: str = "dump_run",
) -> dict[str, Any]:
    job = {
        "job_id": job_id,
        "created_at": "2026-04-26T10:00:00",
        "status": status,
        "quote_id": f"quote-{job_id}",
        "request_id": f"request-{job_id}",
        "customer_name": "Costing Customer",
        "customer_phone": "705-555-0101",
        "job_address": "123 Costing St",
        "job_description_customer": "Completed junk removal",
        "job_description_internal": "Internal details",
        "service_type": service_type,
        "cash_total_cad": 240.0,
        "emt_total_cad": 271.2,
        "request_json": {"service_type": service_type},
        "notes": "Original job notes",
        "completed_at": "2026-04-26T12:30:00" if status == "completed" else None,
    }
    storage.save_job(job)
    return job


def test_job_costing_schema_backfills_nullable_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-job-costing.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                job_address TEXT,
                job_description_customer TEXT,
                job_description_internal TEXT,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                notes TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    storage.init_db()

    conn = storage._connect()
    try:
        columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    finally:
        conn.close()

    for field in [
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
        "quote_accuracy_note",
        "disposal_receipt_note",
    ]:
        assert field in columns
        assert columns[field]["notnull"] == 0


def test_save_and_read_job_costing_data(isolated_db: Path) -> None:
    _seed_job()

    updated = storage.update_job_costing(
        "job-costing",
        actual_hours=3.5,
        actual_crew_size=2,
        actual_labor_cost_cad=105.0,
        actual_disposal_cost_cad=42.25,
        actual_fuel_cost_cad=18.75,
        actual_other_costs_cad=12.5,
        final_amount_collected_cad=260.0,
        payment_method="emt",
        payment_status="paid_in_full",
        job_profit_status="profitable",
        quote_accuracy_note="Quoted baseline was close.",
        disposal_receipt_note="Receipt in Drive.",
    )

    assert updated is not None
    assert updated["actual_hours"] == 3.5
    assert updated["actual_crew_size"] == 2
    assert updated["actual_labor_cost_cad"] == 105.0
    assert updated["actual_disposal_cost_cad"] == 42.25
    assert updated["actual_fuel_cost_cad"] == 18.75
    assert updated["actual_other_costs_cad"] == 12.5
    assert updated["final_amount_collected_cad"] == 260.0
    assert updated["payment_method"] == "emt"
    assert updated["payment_status"] == "paid_in_full"
    assert updated["job_profit_status"] == "profitable"
    assert updated["quote_accuracy_note"] == "Quoted baseline was close."
    assert updated["disposal_receipt_note"] == "Receipt in Drive."


def test_admin_job_costing_requires_auth(client: TestClient, isolated_db: Path) -> None:
    _seed_job()

    resp = client.post("/admin/api/jobs/job-costing/costing", json={"actual_hours": 2})

    assert resp.status_code == 401


def test_admin_job_costing_validates_numeric_and_vocab_fields(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job()

    bad_numeric = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"actual_disposal_cost_cad": -1},
    )
    bad_labor_cost = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"actual_labor_cost_cad": -1},
    )
    bad_other_cost = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"actual_other_costs_cad": -1},
    )
    bad_payment = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"payment_method": "cheque"},
    )
    bad_payment_status = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"payment_status": "overdue"},
    )
    bad_profit = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"job_profit_status": "excellent"},
    )

    assert bad_numeric.status_code == 422
    assert bad_labor_cost.status_code == 422
    assert bad_other_cost.status_code == 422
    assert bad_payment.status_code == 422
    assert bad_payment_status.status_code == 422
    assert bad_profit.status_code == 422


@pytest.mark.parametrize("payment_method", ["cash", "emt", "other"])
def test_admin_job_costing_accepts_payment_method_values(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    payment_method: str,
) -> None:
    _seed_job(job_id=f"job-{payment_method}")

    resp = client.post(
        f"/admin/api/jobs/job-{payment_method}/costing",
        headers=admin_headers,
        json={"payment_method": payment_method},
    )

    assert resp.status_code == 200
    assert resp.json()["job"]["payment_method"] == payment_method


@pytest.mark.parametrize("payment_method", ["not_paid_yet", "partial_payment"])
def test_admin_job_costing_rejects_payment_status_values_as_payment_methods(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    payment_method: str,
) -> None:
    _seed_job(job_id=f"job-{payment_method}")

    resp = client.post(
        f"/admin/api/jobs/job-{payment_method}/costing",
        headers=admin_headers,
        json={"payment_method": payment_method},
    )

    assert resp.status_code == 422


@pytest.mark.parametrize("payment_status", ["not_paid_yet", "partial_payment", "paid_in_full"])
def test_admin_job_costing_accepts_payment_status_values(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    payment_status: str,
) -> None:
    _seed_job(job_id=f"job-{payment_status}")

    resp = client.post(
        f"/admin/api/jobs/job-{payment_status}/costing",
        headers=admin_headers,
        json={"payment_status": payment_status},
    )

    assert resp.status_code == 200
    assert resp.json()["job"]["payment_status"] == payment_status
    assert resp.json()["job"]["payment_method"] is None


def test_storage_job_costing_rejects_invalid_payment_method_and_status(isolated_db: Path) -> None:
    _seed_job()

    with pytest.raises(ValueError, match="payment_method must be one of: cash, emt, other"):
        storage.update_job_costing("job-costing", payment_method="not_paid_yet")

    with pytest.raises(ValueError, match="payment_status must be one of: not_paid_yet, partial_payment, paid_in_full"):
        storage.update_job_costing("job-costing", payment_status="cash")


def test_admin_job_costing_is_completed_job_only(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(status="approved")

    resp = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"actual_hours": 2},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Job costing is only editable for completed jobs."


def test_admin_job_costing_preserves_quoted_totals(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job()

    resp = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={
            "final_amount_collected_cad": 275.0,
            "actual_labor_cost_cad": 85.0,
            "actual_disposal_cost_cad": 60.0,
            "actual_other_costs_cad": 15.0,
            "payment_method": "cash",
            "payment_status": "partial_payment",
            "job_profit_status": "fair",
        },
    )

    assert resp.status_code == 200
    job = resp.json()["job"]
    assert job["cash_total_cad"] == 240.0
    assert job["emt_total_cad"] == 271.2

    stored = storage.require_job("job-costing")
    assert stored["cash_total_cad"] == 240.0
    assert stored["emt_total_cad"] == 271.2
    assert stored["final_amount_collected_cad"] == 275.0
    assert stored["actual_labor_cost_cad"] == 85.0
    assert stored["actual_other_costs_cad"] == 15.0
    assert stored["payment_status"] == "partial_payment"


def test_job_costing_backup_export_import_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    isolated_db: Path,
) -> None:
    _seed_job()
    storage.update_job_costing(
        "job-costing",
        actual_hours=4,
        actual_crew_size=2,
        actual_labor_cost_cad=120,
        actual_disposal_cost_cad=55.5,
        actual_fuel_cost_cad=20,
        actual_other_costs_cad=8.25,
        final_amount_collected_cad=300,
        payment_method="other",
        payment_status="not_paid_yet",
        job_profit_status="underquoted",
        quote_accuracy_note="More stairs than expected.",
        disposal_receipt_note="Scale ticket saved.",
    )

    payload = storage.export_db_to_json()
    job_rows = payload["tables"]["jobs"]
    exported = next(row for row in job_rows if row["job_id"] == "job-costing")
    assert exported["actual_hours"] == 4.0
    assert exported["actual_labor_cost_cad"] == 120.0
    assert exported["actual_other_costs_cad"] == 8.25
    assert exported["payment_status"] == "not_paid_yet"
    assert exported["job_profit_status"] == "underquoted"

    restored_path = tmp_path / "restored-job-costing.sqlite3"
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(restored_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    result = storage.import_db_from_json(payload)

    assert result["ok"] is True
    assert result["restored"]["jobs"] == 1
    restored = storage.require_job("job-costing")
    assert restored["actual_hours"] == 4.0
    assert restored["actual_crew_size"] == 2
    assert restored["actual_labor_cost_cad"] == 120.0
    assert restored["actual_disposal_cost_cad"] == 55.5
    assert restored["actual_fuel_cost_cad"] == 20.0
    assert restored["actual_other_costs_cad"] == 8.25
    assert restored["final_amount_collected_cad"] == 300.0
    assert restored["payment_method"] == "other"
    assert restored["payment_status"] == "not_paid_yet"
    assert restored["job_profit_status"] == "underquoted"
    assert restored["quote_accuracy_note"] == "More stairs than expected."
    assert restored["disposal_receipt_note"] == "Scale ticket saved."


def test_legacy_payment_method_status_values_migrate_to_payment_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-payment-status.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                job_address TEXT,
                job_description_customer TEXT,
                job_description_internal TEXT,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                notes TEXT,
                payment_method TEXT CHECK (
                    payment_method IS NULL OR payment_method IN
                    ('cash', 'emt', 'other', 'not_paid_yet', 'partial_payment')
                )
            )
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, created_at, status, quote_id, request_id,
                service_type, cash_total_cad, emt_total_cad, request_json, notes, payment_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-partial",
                "2026-04-26T10:00:00",
                "completed",
                "quote-legacy",
                "request-legacy",
                "dump_run",
                240.0,
                271.2,
                "{}",
                None,
                "partial_payment",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    storage.init_db()

    migrated = storage.require_job("legacy-partial")
    assert migrated["payment_method"] is None
    assert migrated["payment_status"] == "partial_payment"


def test_legacy_backup_payment_method_status_values_import_as_payment_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-backup-payment-status.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    payload = {
        "meta": {"format": "bay-delivery-sqlite-backup", "version": 1},
        "tables": {
            "jobs": [
                {
                    "job_id": "legacy-backup-partial",
                    "created_at": "2026-04-26T10:00:00",
                    "status": "completed",
                    "quote_id": "quote-backup-legacy",
                    "request_id": "request-backup-legacy",
                    "service_type": "dump_run",
                    "cash_total_cad": 240.0,
                    "emt_total_cad": 271.2,
                    "request_json": {"service_type": "dump_run"},
                    "payment_method": "partial_payment",
                }
            ]
        },
    }

    result = storage.import_db_from_json(payload)

    assert result["ok"] is True
    restored = storage.require_job("legacy-backup-partial")
    assert restored["payment_method"] is None
    assert restored["payment_status"] == "partial_payment"


def test_completed_job_profit_report_requires_auth(client: TestClient, isolated_db: Path) -> None:
    _seed_job(job_id="report-auth", status="completed")

    resp = client.get("/admin/api/completed-job-profit-report")

    assert resp.status_code == 401


def test_completed_job_profit_report_includes_completed_jobs_only(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(job_id="report-completed-a", status="completed")
    _seed_job(job_id="report-completed-b", status="completed")
    _seed_job(job_id="report-scheduled", status="scheduled")

    resp = client.get("/admin/api/completed-job-profit-report", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    assert "summary_cards" in payload
    assert "category_breakdown" in payload
    job_ids = {item["job_id"] for item in payload["jobs"]}
    assert "report-completed-a" in job_ids
    assert "report-completed-b" in job_ids
    assert "report-scheduled" not in job_ids


def test_completed_job_profit_report_flags_incomplete_rows_and_untrusted_margin(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(job_id="report-incomplete", status="completed")

    resp = client.get("/admin/api/completed-job-profit-report", headers=admin_headers)

    assert resp.status_code == 200
    row = next(item for item in resp.json()["jobs"] if item["job_id"] == "report-incomplete")
    assert row["is_complete"] is False
    assert row["trusted_margin"] is False
    assert "actual_labor_cost_cad" in row["missing_fields"]
    assert row["known_margin_pct"] is None


def test_completed_job_profit_report_owner_review_margin_and_profit_status_rules(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(job_id="report-margin-low", status="completed")
    _seed_job(job_id="report-underquoted", status="completed")
    _seed_job(job_id="report-profitable", status="completed")

    storage.update_job_costing(
        "report-margin-low",
        actual_labor_cost_cad=120.0,
        actual_disposal_cost_cad=25.0,
        actual_fuel_cost_cad=10.0,
        actual_other_costs_cad=10.0,
        final_amount_collected_cad=180.0,
        payment_status="paid_in_full",
        job_profit_status="fair",
    )
    storage.update_job_costing(
        "report-underquoted",
        actual_labor_cost_cad=80.0,
        actual_disposal_cost_cad=10.0,
        actual_fuel_cost_cad=8.0,
        actual_other_costs_cad=5.0,
        final_amount_collected_cad=190.0,
        payment_status="paid_in_full",
        job_profit_status="underquoted",
    )
    storage.update_job_costing(
        "report-profitable",
        actual_labor_cost_cad=60.0,
        actual_disposal_cost_cad=10.0,
        actual_fuel_cost_cad=8.0,
        actual_other_costs_cad=5.0,
        final_amount_collected_cad=220.0,
        payment_status="paid_in_full",
        job_profit_status="profitable",
    )

    resp = client.get("/admin/api/completed-job-profit-report", headers=admin_headers)
    assert resp.status_code == 200
    rows = {item["job_id"]: item for item in resp.json()["jobs"]}

    assert rows["report-margin-low"]["trusted_margin"] is True
    assert rows["report-margin-low"]["known_margin_pct"] < 20.0
    assert rows["report-margin-low"]["owner_review"] is True

    assert rows["report-underquoted"]["owner_review"] is True
    assert rows["report-underquoted"]["job_profit_status"] == "underquoted"

    assert rows["report-profitable"]["trusted_margin"] is True
    assert rows["report-profitable"]["known_margin_pct"] > 20.0
    assert rows["report-profitable"]["owner_review"] is False


def test_completed_job_profit_report_category_breakdown_and_summary_cards(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(job_id="report-dump-1", status="completed")
    _seed_job(job_id="report-dump-2", status="completed")
    _seed_job(job_id="report-moving-1", status="completed", service_type="moving")

    storage.update_job_costing(
        "report-dump-1",
        actual_labor_cost_cad=90.0,
        actual_disposal_cost_cad=20.0,
        actual_fuel_cost_cad=10.0,
        actual_other_costs_cad=10.0,
        final_amount_collected_cad=220.0,
        payment_status="paid_in_full",
        job_profit_status="profitable",
    )
    storage.update_job_costing(
        "report-moving-1",
        actual_labor_cost_cad=120.0,
        actual_disposal_cost_cad=15.0,
        actual_fuel_cost_cad=14.0,
        actual_other_costs_cad=12.0,
        final_amount_collected_cad=230.0,
        payment_status="paid_in_full",
        job_profit_status="fair",
    )

    resp = client.get("/admin/api/completed-job-profit-report", headers=admin_headers)
    assert resp.status_code == 200
    payload = resp.json()

    category_map = {row["service_type"]: row for row in payload["category_breakdown"]}
    assert "dump_run" in category_map
    assert "moving" in category_map
    assert category_map["dump_run"]["total_jobs"] >= 2
    assert category_map["moving"]["total_jobs"] >= 1

    cards = {card["key"]: card for card in payload["summary_cards"]}
    assert cards["completed_jobs_reviewed"]["value"] >= 3
    assert "missing_cost_data" in cards
    assert "owner_review" in cards


def test_completed_job_profit_report_service_does_not_import_quote_engine() -> None:
    service_path = Path("app/services/completed_job_profit_report.py")
    source = service_path.read_text(encoding="utf-8")

    assert "from app.quote_engine import" not in source
    assert "import app.quote_engine" not in source
    assert "calculate_quote(" not in source
