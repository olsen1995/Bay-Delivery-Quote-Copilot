from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import storage
from scripts import seed_local_job_costing_data as seed_script


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "seed-job-costing.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    return db_path


def test_seed_creates_three_completed_simulated_jobs_and_is_idempotent(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert seed_script.main([]) == 0
    first_output = capsys.readouterr().out

    assert first_output.count("CREATED") == 3
    assert "TEST / Simulated local dump run" in first_output
    assert "TEST / Simulated small move" in first_output
    assert "TEST / Simulated demo debris cleanup" in first_output

    expected_costing = {
        "test-simulated-local-dump-run": {
            "final_amount_collected_cad": 220.0,
            "payment_method": "cash",
            "actual_labor_cost_cad": 50.0,
            "actual_disposal_cost_cad": 58.0,
            "actual_fuel_cost_cad": 40.0,
            "actual_other_costs_cad": 5.0,
        },
        "test-simulated-small-move": {
            "final_amount_collected_cad": 339.0,
            "payment_method": "emt",
            "actual_labor_cost_cad": 108.0,
            "actual_disposal_cost_cad": 0.0,
            "actual_fuel_cost_cad": 40.0,
            "actual_other_costs_cad": 10.0,
        },
        "test-simulated-demo-debris-cleanup": {
            "final_amount_collected_cad": 475.0,
            "payment_method": "cash",
            "actual_labor_cost_cad": 144.0,
            "actual_disposal_cost_cad": 96.0,
            "actual_fuel_cost_cad": 55.0,
            "actual_other_costs_cad": 15.0,
        },
    }

    for job_id, expected in expected_costing.items():
        job = storage.require_job(job_id)
        assert job["status"] == "completed"
        assert "TEST / SIMULATED" in job["customer_name"]
        assert job["job_description_customer"].startswith("TEST / Simulated")
        assert job["payment_status"] == "paid_in_full"
        assert job["job_profit_status"] == "profitable"
        assert job["actual_hours"] is None
        assert job["actual_crew_size"] is None
        for field, value in expected.items():
            assert job[field] == value

    storage.update_job_costing(
        "test-simulated-local-dump-run",
        quote_accuracy_note="Local admin edit must survive rerun.",
    )

    assert seed_script.main([]) == 0
    second_output = capsys.readouterr().out

    assert second_output.count("SKIPPED existing") == 3
    assert storage.require_job("test-simulated-local-dump-run")["quote_accuracy_note"] == (
        "Local admin edit must survive rerun."
    )


def test_cleanup_removes_only_labeled_deterministic_seed_jobs(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert seed_script.main([]) == 0
    capsys.readouterr()

    protected_id = "test-simulated-local-dump-run"
    protected_job = storage.require_job(protected_id)
    protected_job["customer_name"] = "Real Local Customer"
    protected_job["job_address"] = "123 Real St"
    protected_job["job_description_customer"] = "Real local job"
    protected_job["job_description_internal"] = "Not a seed record"
    protected_job["notes"] = "Not test data"
    protected_job["closeout_notes"] = "Not test data"
    storage.save_job(protected_job)

    assert seed_script.main(["--cleanup"]) == 0
    output = capsys.readouterr().out

    assert "PROTECTED collision test-simulated-local-dump-run" in output
    assert output.count("DELETED") == 2
    assert storage.get_job(protected_id) is not None
    assert storage.get_job("test-simulated-small-move") is None
    assert storage.get_job("test-simulated-demo-debris-cleanup") is None


def test_cleanup_does_not_delete_non_seed_jobs(
    isolated_db: Path,
) -> None:
    storage.save_job(
        {
            "job_id": "real-local-job",
            "created_at": "2026-05-08T10:00:00",
            "status": "completed",
            "quote_id": "quote-real-local-job",
            "request_id": "request-real-local-job",
            "customer_name": "Real Local Customer",
            "customer_phone": "705-555-0101",
            "job_address": "123 Real St",
            "job_description_customer": "Real local completed job",
            "job_description_internal": "Local user-created job",
            "service_type": "dump_run",
            "cash_total_cad": 200.0,
            "emt_total_cad": 226.0,
            "request_json": {"service_type": "dump_run"},
            "notes": "Keep this job",
            "completed_at": "2026-05-08T12:00:00",
        }
    )

    assert seed_script.main(["--cleanup"]) == 0

    assert storage.get_job("real-local-job") is not None


def test_seed_refuses_render_like_environment(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")

    assert seed_script.main([]) == 2
    output = capsys.readouterr().out

    assert "REFUSED" in output
    assert "Render" in output


def test_seed_does_not_create_quote_request_rows(isolated_db: Path) -> None:
    assert seed_script.main([]) == 0

    conn = sqlite3.connect(isolated_db)
    try:
        count = conn.execute("SELECT COUNT(*) FROM quote_requests").fetchone()[0]
    finally:
        conn.close()

    assert count == 0
