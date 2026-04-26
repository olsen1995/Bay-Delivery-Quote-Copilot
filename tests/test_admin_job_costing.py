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


def _seed_job(job_id: str = "job-costing", status: str = "completed") -> dict[str, Any]:
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
        "service_type": "dump_run",
        "cash_total_cad": 240.0,
        "emt_total_cad": 271.2,
        "request_json": {"service_type": "dump_run"},
        "notes": "Original job notes",
        "completed_at": "2026-04-26T12:30:00" if status == "completed" else None,
    }
    storage.save_job(job)
    return job


def test_job_costing_schema_backfills_nullable_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-job-costing.sqlite3"
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
        "actual_disposal_cost_cad",
        "actual_fuel_cost_cad",
        "final_amount_collected_cad",
        "payment_method",
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
        actual_disposal_cost_cad=42.25,
        actual_fuel_cost_cad=18.75,
        final_amount_collected_cad=260.0,
        payment_method="emt",
        job_profit_status="profitable",
        quote_accuracy_note="Quoted baseline was close.",
        disposal_receipt_note="Receipt in Drive.",
    )

    assert updated is not None
    assert updated["actual_hours"] == 3.5
    assert updated["actual_crew_size"] == 2
    assert updated["actual_disposal_cost_cad"] == 42.25
    assert updated["actual_fuel_cost_cad"] == 18.75
    assert updated["final_amount_collected_cad"] == 260.0
    assert updated["payment_method"] == "emt"
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
    bad_payment = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"payment_method": "cheque"},
    )
    bad_profit = client.post(
        "/admin/api/jobs/job-costing/costing",
        headers=admin_headers,
        json={"job_profit_status": "excellent"},
    )

    assert bad_numeric.status_code == 422
    assert bad_payment.status_code == 422
    assert bad_profit.status_code == 422


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
            "actual_disposal_cost_cad": 60.0,
            "payment_method": "cash",
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
        actual_disposal_cost_cad=55.5,
        actual_fuel_cost_cad=20,
        final_amount_collected_cad=300,
        payment_method="other",
        job_profit_status="underquoted",
        quote_accuracy_note="More stairs than expected.",
        disposal_receipt_note="Scale ticket saved.",
    )

    payload = storage.export_db_to_json()
    job_rows = payload["tables"]["jobs"]
    exported = next(row for row in job_rows if row["job_id"] == "job-costing")
    assert exported["actual_hours"] == 4.0
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
    assert restored["actual_disposal_cost_cad"] == 55.5
    assert restored["actual_fuel_cost_cad"] == 20.0
    assert restored["final_amount_collected_cad"] == 300.0
    assert restored["payment_method"] == "other"
    assert restored["job_profit_status"] == "underquoted"
    assert restored["quote_accuracy_note"] == "More stairs than expected."
    assert restored["disposal_receipt_note"] == "Scale ticket saved."
