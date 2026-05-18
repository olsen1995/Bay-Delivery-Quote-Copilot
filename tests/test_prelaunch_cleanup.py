from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from app import storage
from app.audit_log import log_admin_audit
from scripts import create_prelaunch_test_data_cleanup as cleanup_script


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "prelaunch-cleanup.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    return db_path


def _seed_quote(quote_id: str, *, created_at: str = "2026-05-18T10:00:00") -> None:
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": {
                "customer_name": f"Customer {quote_id}",
                "customer_phone": "705-555-0101",
                "job_address": f"{quote_id} Test St",
                "job_description_customer": f"Prelaunch test quote {quote_id}",
                "service_type": "dump_run",
            },
            "response": {
                "job_description_internal": f"Internal test quote {quote_id}",
                "cash_total_cad": 150.0,
                "emt_total_cad": 169.5,
            },
            "accept_token": f"accept-{quote_id}",
        }
    )


def _seed_quote_with_context(
    quote_id: str,
    *,
    created_at: str = "2026-05-18T10:00:00",
    customer_name: str = "Customer Example",
    service_type: str = "dump_run",
    job_address: str = "123 Example St",
    cash_total_cad: float = 150.0,
) -> None:
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": {
                "customer_name": customer_name,
                "customer_phone": "705-555-0101",
                "job_address": job_address,
                "job_description_customer": f"Prelaunch test quote {quote_id}",
                "service_type": service_type,
            },
            "response": {
                "job_description_internal": f"Internal test quote {quote_id}",
                "cash_total_cad": cash_total_cad,
                "emt_total_cad": round(cash_total_cad * 1.13, 2),
            },
            "accept_token": f"accept-{quote_id}",
        }
    )


def _seed_quote_request(request_id: str, quote_id: str, *, created_at: str = "2026-05-18T10:05:00") -> None:
    storage.save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": f"Customer {quote_id}",
            "customer_phone": "705-555-0101",
            "job_address": f"{quote_id} Test St",
            "job_description_customer": f"Accepted test request {request_id}",
            "job_description_internal": f"Internal request {request_id}",
            "service_type": "dump_run",
            "cash_total_cad": 150.0,
            "emt_total_cad": 169.5,
            "request_json": {"quote_id": quote_id},
            "notes": "Prelaunch test request",
            "requested_job_date": None,
            "requested_time_window": None,
            "customer_accepted_at": created_at,
            "admin_approved_at": None,
            "accept_token": f"accept-{quote_id}",
            "booking_token": f"booking-{request_id}",
            "booking_token_created_at": created_at,
        }
    )


def _seed_job(job_id: str, quote_id: str, request_id: str, *, created_at: str = "2026-05-18T10:10:00") -> None:
    storage.save_job(
        {
            "job_id": job_id,
            "created_at": created_at,
            "status": "approved",
            "quote_id": quote_id,
            "request_id": request_id,
            "customer_name": f"Customer {quote_id}",
            "customer_phone": "705-555-0101",
            "job_address": f"{quote_id} Test St",
            "job_description_customer": f"Approved test job {job_id}",
            "job_description_internal": f"Internal job {job_id}",
            "service_type": "dump_run",
            "cash_total_cad": 150.0,
            "emt_total_cad": 169.5,
            "request_json": {"quote_id": quote_id, "request_id": request_id},
            "notes": "Prelaunch test job",
        }
    )


def _seed_attachment(
    attachment_id: str,
    *,
    quote_id: str | None = None,
    request_id: str | None = None,
    job_id: str | None = None,
    created_at: str = "2026-05-18T10:15:00",
) -> None:
    storage.save_attachment(
        {
            "attachment_id": attachment_id,
            "created_at": created_at,
            "quote_id": quote_id,
            "request_id": request_id,
            "job_id": job_id,
            "filename": f"{attachment_id}.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 123,
            "drive_file_id": f"drive-{attachment_id}",
            "drive_web_view_link": f"https://example.com/{attachment_id}",
        }
    )


def _seed_manual_calibration_entries() -> None:
    storage.save_completed_job_calibration_entry(
        {
            "entry_id": "manual-real-1",
            "created_at": "2026-05-17T09:00:00",
            "updated_at": None,
            "operator_username": "austin",
            "job_title": "Backyard cleanup with tarp fence teardown",
            "service_type": "haul_away",
            "secondary_category": "light_demolition",
            "quoted_price_cad": 600.0,
            "actual_collected_cad": 600.0,
            "crew_size": 3,
            "duration_hours": 3.0,
            "labour_hours": None,
            "disposal_cost_cad": 80.0,
            "fuel_cost_cad": 25.0,
            "other_costs_cad": 0.0,
            "difficulty": "hard",
            "access_difficulty": "awkward",
            "disassembly_required": True,
            "dense_materials": False,
            "underquoted": False,
            "painful_job": False,
            "pricing_result": "profitable",
            "notes": "Real calibration record.",
            "calibration_note": "Preserve this row.",
        }
    )
    storage.save_completed_job_calibration_entry(
        {
            "entry_id": "manual-real-2",
            "created_at": "2026-05-17T10:00:00",
            "updated_at": None,
            "operator_username": "austin",
            "job_title": "Old shed removal and haul-away",
            "service_type": "demolition",
            "secondary_category": "shed_removal",
            "quoted_price_cad": 1200.0,
            "actual_collected_cad": 1200.0,
            "crew_size": 3,
            "duration_hours": 5.0,
            "labour_hours": None,
            "disposal_cost_cad": 150.0,
            "fuel_cost_cad": 40.0,
            "other_costs_cad": 0.0,
            "difficulty": "hard",
            "access_difficulty": "normal",
            "disassembly_required": True,
            "dense_materials": True,
            "underquoted": False,
            "painful_job": False,
            "pricing_result": "profitable",
            "notes": "Real calibration record.",
            "calibration_note": "Preserve this row.",
        }
    )


def _seed_test_lineage(quote_id: str, request_id: str, job_id: str) -> None:
    _seed_quote(quote_id)
    _seed_quote_request(request_id, quote_id)
    _seed_job(job_id, quote_id, request_id)
    _seed_attachment(f"att-quote-{quote_id}", quote_id=quote_id)
    _seed_attachment(f"att-request-{request_id}", request_id=request_id)
    _seed_attachment(f"att-job-{job_id}", job_id=job_id)


def test_plan_prelaunch_cleanup_resolves_only_allowlisted_lineage(isolated_db: Path) -> None:
    _seed_test_lineage("quote-clean-me", "request-clean-me", "job-clean-me")
    _seed_test_lineage("quote-keep-me", "request-keep-me", "job-keep-me")

    plan = storage.plan_prelaunch_test_data_cleanup(["quote-clean-me", "quote-missing"])

    assert plan["db_path"] == str(isolated_db)
    assert plan["requested_quote_ids"] == ["quote-clean-me", "quote-missing"]
    assert plan["found_quote_ids"] == ["quote-clean-me"]
    assert plan["missing_quote_ids"] == ["quote-missing"]
    assert plan["request_ids"] == ["request-clean-me"]
    assert plan["job_ids"] == ["job-clean-me"]
    assert set(plan["attachment_ids"]) == {
        "att-quote-quote-clean-me",
        "att-request-request-clean-me",
        "att-job-job-clean-me",
    }
    assert plan["counts"] == {"quotes": 1, "quote_requests": 1, "jobs": 1, "attachments": 3}


def test_apply_prelaunch_cleanup_deletes_only_allowlisted_lineage_and_preserves_real_records(
    isolated_db: Path,
) -> None:
    _seed_test_lineage("quote-clean-me", "request-clean-me", "job-clean-me")
    _seed_test_lineage("quote-keep-me", "request-keep-me", "job-keep-me")
    _seed_manual_calibration_entries()
    log_admin_audit(
        operator_username="austin",
        action_type="view",
        entity_type="quotes",
        record_id="quote-clean-me",
        success=True,
    )

    result = storage.apply_prelaunch_test_data_cleanup(["quote-clean-me"])

    assert result["deleted_quote_ids"] == ["quote-clean-me"]
    assert result["deleted_request_ids"] == ["request-clean-me"]
    assert result["deleted_job_ids"] == ["job-clean-me"]
    assert set(result["deleted_attachment_ids"]) == {
        "att-quote-quote-clean-me",
        "att-request-request-clean-me",
        "att-job-job-clean-me",
    }
    assert storage.get_quote_record("quote-clean-me") is None
    assert storage.get_quote_request_record("request-clean-me") is None
    assert storage.get_job("job-clean-me") is None
    assert storage.list_attachments(limit=20, quote_id="quote-clean-me") == []

    assert storage.get_quote_record("quote-keep-me") is not None
    assert storage.get_quote_request_record("request-keep-me") is not None
    assert storage.get_job("job-keep-me") is not None
    assert len(storage.list_completed_job_calibration_entries(limit=10)) == 2
    assert [item["job_title"] for item in storage.list_completed_job_calibration_entries(limit=10)] == [
        "Old shed removal and haul-away",
        "Backyard cleanup with tarp fence teardown",
    ]
    assert len(storage.list_admin_audit_log(limit=10)) == 1


def test_script_refuses_apply_without_backup_confirmation(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_test_lineage("quote-clean-me", "request-clean-me", "job-clean-me")

    assert cleanup_script.main(["--quote-id", "quote-clean-me", "--apply"]) == 2
    output = capsys.readouterr().out

    assert f"Database path: {isolated_db}" in output
    assert "Mode: APPLY" in output
    assert "REFUSED: --apply also requires --backup-confirmed." in output
    assert storage.get_quote_record("quote-clean-me") is not None


def test_script_list_quotes_shows_full_ids_and_context(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_quote_with_context(
        "quote-full-1",
        created_at="2026-05-18T09:00:00",
        customer_name="Test Pilot",
        service_type="haul_away",
        job_address="10 Launch Rd",
        cash_total_cad=600.0,
    )
    _seed_quote_with_context(
        "quote-full-2",
        created_at="2026-05-18T08:00:00",
        customer_name="Second Example",
        service_type="dump_run",
        job_address="22 Backup Ave",
        cash_total_cad=275.0,
    )

    assert cleanup_script.main(["--list-quotes", "--limit", "2"]) == 0
    output = capsys.readouterr().out

    assert "Mode: DRY RUN" not in output
    assert "Apply completed." not in output
    assert "quote-full-1" in output
    assert "quote-full-2" in output
    assert "Test Pilot" in output
    assert "haul_away" in output
    assert "10 Launch Rd" in output
    assert "600.0" in output
    assert "Second Example" in output
    assert "quote-clean-me" not in output
    assert storage.get_quote_record("quote-full-1") is not None
    assert storage.get_quote_record("quote-full-2") is not None


def test_script_runs_directly_from_repo_root_with_temp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "direct-prelaunch-cleanup.sqlite3"
    env = os.environ.copy()
    env["BAYDELIVERY_DB_PATH"] = str(db_path)

    previous_db_env = os.environ.get("BAYDELIVERY_DB_PATH")
    os.environ["BAYDELIVERY_DB_PATH"] = str(db_path)
    storage.DB_PATH = storage.DEFAULT_DB_PATH
    storage._TABLE_COL_CACHE.clear()
    try:
        storage.init_db()
        _seed_test_lineage("quote-clean-me", "request-clean-me", "job-clean-me")
    finally:
        if previous_db_env is None:
            os.environ.pop("BAYDELIVERY_DB_PATH", None)
        else:
            os.environ["BAYDELIVERY_DB_PATH"] = previous_db_env

    dry_run = subprocess.run(
        [sys.executable, "scripts/create_prelaunch_test_data_cleanup.py", "--quote-id", "quote-clean-me"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert dry_run.returncode == 0, dry_run.stderr
    assert "ModuleNotFoundError" not in dry_run.stderr
    assert f"Database path: {db_path}" in dry_run.stdout
    assert "Mode: DRY RUN" in dry_run.stdout
    assert "Dry run only. No rows were deleted." in dry_run.stdout

    apply_run = subprocess.run(
        [
            sys.executable,
            "scripts/create_prelaunch_test_data_cleanup.py",
            "--quote-id",
            "quote-clean-me",
            "--apply",
            "--backup-confirmed",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert apply_run.returncode == 0, apply_run.stderr
    assert "ModuleNotFoundError" not in apply_run.stderr
    assert "Apply completed." in apply_run.stdout

    previous_db_env = os.environ.get("BAYDELIVERY_DB_PATH")
    os.environ["BAYDELIVERY_DB_PATH"] = str(db_path)
    storage.DB_PATH = storage.DEFAULT_DB_PATH
    try:
        assert storage.get_quote_record("quote-clean-me") is None
    finally:
        if previous_db_env is None:
            os.environ.pop("BAYDELIVERY_DB_PATH", None)
        else:
            os.environ["BAYDELIVERY_DB_PATH"] = previous_db_env


def test_script_list_quotes_runs_directly_from_repo_root_with_temp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "direct-prelaunch-list.sqlite3"
    env = os.environ.copy()
    env["BAYDELIVERY_DB_PATH"] = str(db_path)

    previous_db_env = os.environ.get("BAYDELIVERY_DB_PATH")
    os.environ["BAYDELIVERY_DB_PATH"] = str(db_path)
    storage.DB_PATH = storage.DEFAULT_DB_PATH
    storage._TABLE_COL_CACHE.clear()
    try:
        storage.init_db()
        _seed_quote_with_context(
            "quote-full-1",
            created_at="2026-05-18T09:00:00",
            customer_name="Test Pilot",
            service_type="haul_away",
            job_address="10 Launch Rd",
            cash_total_cad=600.0,
        )
    finally:
        if previous_db_env is None:
            os.environ.pop("BAYDELIVERY_DB_PATH", None)
        else:
            os.environ["BAYDELIVERY_DB_PATH"] = previous_db_env

    list_run = subprocess.run(
        [
            sys.executable,
            "scripts/create_prelaunch_test_data_cleanup.py",
            "--list-quotes",
            "--limit",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert list_run.returncode == 0, list_run.stderr
    assert "ModuleNotFoundError" not in list_run.stderr
    assert f"Database path: {db_path}" in list_run.stdout
    assert "quote-full-1" in list_run.stdout
    assert "Test Pilot" in list_run.stdout
    assert "Dry run only. No rows were deleted." not in list_run.stdout

    previous_db_env = os.environ.get("BAYDELIVERY_DB_PATH")
    os.environ["BAYDELIVERY_DB_PATH"] = str(db_path)
    storage.DB_PATH = storage.DEFAULT_DB_PATH
    try:
        assert storage.get_quote_record("quote-full-1") is not None
    finally:
        if previous_db_env is None:
            os.environ.pop("BAYDELIVERY_DB_PATH", None)
        else:
            os.environ["BAYDELIVERY_DB_PATH"] = previous_db_env
