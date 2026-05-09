from __future__ import annotations

import ast
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app import storage
from scripts import analyze_completed_job_calibration as analysis
from scripts import seed_local_job_costing_data as seed_script


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "completed-job-analysis.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    return db_path


def _save_completed_job(
    job_id: str,
    *,
    service_type: str = "dump_run",
    cash_total: float = 200.0,
    emt_total: float = 226.0,
    costing: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "job_id": job_id,
        "created_at": "2026-05-09T10:00:00",
        "status": "completed",
        "quote_id": f"quote-{job_id}",
        "request_id": f"request-{job_id}",
        "customer_name": "Completed Job Analysis Customer",
        "customer_phone": "705-555-0101",
        "job_address": "123 Analysis St",
        "job_description_customer": "Completed analysis job",
        "job_description_internal": "Local analysis test job",
        "service_type": service_type,
        "cash_total_cad": cash_total,
        "emt_total_cad": emt_total,
        "request_json": {"service_type": service_type},
        "notes": "Test job",
        "completed_at": "2026-05-09T12:00:00",
    }
    if costing:
        record.update(costing)
    storage.save_job(record)


def _table_count(db_path: Path, table_name: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    finally:
        conn.close()


def _create_minimal_completed_jobs_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                actual_labor_cost_cad REAL,
                actual_disposal_cost_cad REAL,
                actual_fuel_cost_cad REAL,
                actual_other_costs_cad REAL,
                final_amount_collected_cad REAL,
                payment_status TEXT,
                job_profit_status TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, created_at, status, service_type, cash_total_cad, emt_total_cad,
                actual_labor_cost_cad, actual_disposal_cost_cad, actual_fuel_cost_cad,
                actual_other_costs_cad, final_amount_collected_cad, payment_status, job_profit_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "minimal-completed-job",
                "2026-05-09T10:00:00",
                "completed",
                "dump_run",
                100.0,
                113.0,
                20.0,
                10.0,
                5.0,
                0.0,
                100.0,
                "paid_in_full",
                "profitable",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_missing_db_exits_cleanly_without_creating_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "missing-analysis.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))

    assert analysis.main([]) == 0
    output = capsys.readouterr().out

    assert "No completed jobs found" in output
    assert "database file does not exist" in output
    assert "seed_local_job_costing_data.py" in output
    assert not db_path.exists()


def test_existing_db_analysis_does_not_create_sqlite_sidecar_files(tmp_path: Path) -> None:
    db_path = tmp_path / "existing-readonly.sqlite3"
    _create_minimal_completed_jobs_db(db_path)

    rows = analysis.analyze_completed_jobs(db_path)

    assert [row.job_id for row in rows] == ["minimal-completed-job"]
    assert not Path(f"{db_path}-wal").exists()
    assert not Path(f"{db_path}-shm").exists()


def test_no_completed_jobs_exits_cleanly(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert analysis.main([]) == 0
    output = capsys.readouterr().out

    assert str(isolated_db) in output
    assert "No completed jobs found" in output


def test_completed_job_cost_profit_and_margin_math(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _save_completed_job(
        "job-profitable",
        costing={
            "final_amount_collected_cad": 200.0,
            "actual_labor_cost_cad": 50.0,
            "actual_disposal_cost_cad": 25.0,
            "actual_fuel_cost_cad": 10.0,
            "actual_other_costs_cad": 5.0,
            "actual_hours": 1.0,
            "actual_crew_size": 1,
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
        },
    )

    rows = analysis.analyze_completed_jobs(isolated_db)

    assert len(rows) == 1
    assert rows[0].known_cost == 90.0
    assert rows[0].known_profit == 110.0
    assert rows[0].known_margin_pct == 55.0
    assert "BELOW_CONTRIBUTION_MARGIN" not in rows[0].risk_flags

    assert analysis.main([]) == 0
    output = capsys.readouterr().out
    assert "Completed Job Calibration Summary" in output
    assert "Average known margin: 55.0%" in output
    assert "job-profitable" in output


def test_below_margin_missing_cost_and_owner_review_flags(isolated_db: Path) -> None:
    _save_completed_job(
        "job-risk",
        costing={
            "final_amount_collected_cad": 100.0,
            "actual_labor_cost_cad": 90.0,
            "payment_status": "paid_in_full",
        },
    )

    row = analysis.analyze_completed_jobs(isolated_db)[0]

    assert row.known_cost == 90.0
    assert row.known_profit == 10.0
    assert row.known_margin_pct == 10.0
    assert "BELOW_CONTRIBUTION_MARGIN" in row.risk_flags
    assert "MISSING_COST_DATA" in row.risk_flags
    assert row.owner_review is True
    assert set(row.missing_fields).issuperset(
        {
            "actual_disposal_cost_cad",
            "actual_fuel_cost_cad",
            "actual_other_costs_cad",
            "actual_hours",
            "actual_crew_size",
            "job_profit_status",
        }
    )


def test_disposal_heavy_and_labour_underpriced_flags(isolated_db: Path) -> None:
    _save_completed_job(
        "job-heavy-disposal-move",
        service_type="small_move",
        cash_total=120.0,
        emt_total=135.60,
        costing={
            "final_amount_collected_cad": 120.0,
            "actual_labor_cost_cad": 55.0,
            "actual_disposal_cost_cad": 60.0,
            "actual_fuel_cost_cad": 10.0,
            "actual_other_costs_cad": 5.0,
            "actual_hours": 2.0,
            "actual_crew_size": 2,
            "payment_status": "partial_payment",
            "job_profit_status": "underquoted",
        },
    )

    row = analysis.analyze_completed_jobs(isolated_db)[0]

    assert row.known_cost == 130.0
    assert row.known_margin_pct == -8.3
    assert row.crew_rate_target_floor == 330.0
    assert "DISPOSAL_HEAVY_RISK" in row.risk_flags
    assert "LABOUR_UNDERPRICED_RISK" in row.risk_flags
    assert "PAYMENT_NOT_FULLY_COLLECTED" in row.risk_flags
    assert "OPERATOR_MARKED_UNDERPRICED" in row.risk_flags


def test_simulated_seed_jobs_are_analyzed_without_mutation(
    isolated_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert seed_script.main([]) == 0
    capsys.readouterr()
    before_counts = {
        "jobs": _table_count(isolated_db, "jobs"),
        "quotes": _table_count(isolated_db, "quotes"),
        "quote_requests": _table_count(isolated_db, "quote_requests"),
    }

    assert analysis.main([]) == 0
    output = capsys.readouterr().out
    after_counts = {
        "jobs": _table_count(isolated_db, "jobs"),
        "quotes": _table_count(isolated_db, "quotes"),
        "quote_requests": _table_count(isolated_db, "quote_requests"),
    }

    assert before_counts == {"jobs": 3, "quotes": 0, "quote_requests": 0}
    assert after_counts == before_counts
    assert "test-simulated-local-dump-run" in output
    assert "$153.00" in output
    assert "$67.00" in output
    assert "30.5%" in output
    assert "test-simulated-small-move" in output
    assert "test-simulated-demo-debris-cleanup" in output


def test_script_runs_directly_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "direct-analysis.sqlite3"
    env = os.environ.copy()
    env["BAYDELIVERY_DB_PATH"] = str(db_path)

    result = subprocess.run(
        [sys.executable, "scripts/analyze_completed_job_calibration.py"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    assert "No completed jobs found" in result.stdout
    assert not db_path.exists()


def test_analysis_script_has_no_direct_storage_write_or_quote_calls() -> None:
    script_path = REPO_ROOT / "scripts" / "analyze_completed_job_calibration.py"
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    forbidden_calls: list[str] = []
    forbidden_names = {
        "init_db",
        "_connect",
        "list_jobs",
        "save_job",
        "update_job_costing",
        "save_quote",
        "save_quote_request",
        "import_db_from_json",
        "build_quote_artifacts",
        "calculate_quote",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_names:
                forbidden_calls.append(node.func.attr)

    assert forbidden_calls == []
