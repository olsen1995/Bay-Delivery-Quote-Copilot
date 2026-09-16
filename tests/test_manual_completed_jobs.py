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
    db_path = tmp_path / "manual-completed-jobs.sqlite3"
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
    return {"Authorization": f"Basic {token}", "Sec-Fetch-Site": "same-origin"}


def _entry(**overrides: Any) -> dict[str, Any]:
    entry = {
        "entry_id": overrides.pop("entry_id", "manual-entry-1"),
        "created_at": overrides.pop("created_at", "2026-05-17T10:00:00"),
        "updated_at": overrides.pop("updated_at", None),
        "operator_username": overrides.pop("operator_username", "admin"),
        "job_title": overrides.pop("job_title", "Backyard cleanup with teardown"),
        "service_type": overrides.pop("service_type", "haul_away"),
        "secondary_category": overrides.pop("secondary_category", "light_demolition"),
        "quoted_price_cad": overrides.pop("quoted_price_cad", 600.0),
        "actual_collected_cad": overrides.pop("actual_collected_cad", 600.0),
        "crew_size": overrides.pop("crew_size", 3),
        "duration_hours": overrides.pop("duration_hours", 3.0),
        "labour_hours": overrides.pop("labour_hours", None),
        "disposal_cost_cad": overrides.pop("disposal_cost_cad", 80.0),
        "fuel_cost_cad": overrides.pop("fuel_cost_cad", 25.0),
        "other_costs_cad": overrides.pop("other_costs_cad", 0.0),
        "difficulty": overrides.pop("difficulty", "hard"),
        "access_difficulty": overrides.pop("access_difficulty", "awkward"),
        "disassembly_required": overrides.pop("disassembly_required", True),
        "dense_materials": overrides.pop("dense_materials", False),
        "underquoted": overrides.pop("underquoted", False),
        "painful_job": overrides.pop("painful_job", False),
        "pricing_result": overrides.pop("pricing_result", "profitable"),
        "notes": overrides.pop("notes", "Photos in Drive folder. Fence/tarp teardown included."),
        "calibration_note": overrides.pop(
            "calibration_note",
            "Treat as haul-away plus light demolition, not a basic dump run.",
        ),
    }
    entry.update(overrides)
    return entry


def _seed_job(job_id: str = "lifecycle-completed") -> None:
    storage.save_job(
        {
            "job_id": job_id,
            "created_at": "2026-05-17T09:00:00",
            "status": "completed",
            "quote_id": f"quote-{job_id}",
            "request_id": f"request-{job_id}",
            "customer_name": "Lifecycle Customer",
            "customer_phone": "705-555-0101",
            "job_address": "123 Lifecycle St",
            "job_description_customer": "Lifecycle completed job",
            "job_description_internal": "Internal lifecycle job",
            "service_type": "dump_run",
            "cash_total_cad": 250.0,
            "emt_total_cad": 282.5,
            "request_json": {"service_type": "dump_run"},
            "notes": "Normal lifecycle job",
            "completed_at": "2026-05-17T11:00:00",
        }
    )
    storage.update_job_costing(
        job_id,
        actual_labor_cost_cad=80.0,
        actual_disposal_cost_cad=20.0,
        actual_fuel_cost_cad=10.0,
        actual_other_costs_cad=5.0,
        final_amount_collected_cad=250.0,
        payment_status="paid_in_full",
        job_profit_status="profitable",
    )


def test_manual_completed_jobs_schema_created_on_fresh_db(isolated_db: Path) -> None:
    assert "completed_job_calibration_entries" in storage.KNOWN_TABLES

    conn = storage._connect()
    try:
        columns = {
            row["name"]: row
            for row in conn.execute("PRAGMA table_info(completed_job_calibration_entries)").fetchall()
        }
    finally:
        conn.close()

    for required in [
        "entry_id",
        "created_at",
        "operator_username",
        "job_title",
        "service_type",
        "actual_collected_cad",
        "crew_size",
        "duration_hours",
        "pricing_result",
    ]:
        assert required in columns
        assert columns[required]["notnull"] == 1 or required == "entry_id"

    for optional in [
        "updated_at",
        "secondary_category",
        "quoted_price_cad",
        "labour_hours",
        "disposal_cost_cad",
        "fuel_cost_cad",
        "other_costs_cad",
        "difficulty",
        "access_difficulty",
        "notes",
        "calibration_note",
    ]:
        assert optional in columns


def test_legacy_db_initializes_manual_completed_jobs_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-manual-completed-jobs.sqlite3"
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
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, created_at, status, quote_id, request_id,
                service_type, cash_total_cad, emt_total_cad, request_json
            )
            VALUES ('legacy-job', '2026-05-17T08:00:00', 'completed', 'legacy-quote',
                    'legacy-request', 'dump_run', 100, 113, '{}')
            """
        )
        conn.commit()
    finally:
        conn.close()

    storage.init_db()

    conn = storage._connect()
    try:
        manual_columns = conn.execute("PRAGMA table_info(completed_job_calibration_entries)").fetchall()
        legacy_job = conn.execute("SELECT job_id FROM jobs WHERE job_id = 'legacy-job'").fetchone()
    finally:
        conn.close()

    assert manual_columns
    assert legacy_job is not None


def test_save_and_list_manual_completed_job_entries(isolated_db: Path) -> None:
    saved = storage.save_completed_job_calibration_entry(_entry())

    assert saved["entry_id"] == "manual-entry-1"
    assert saved["job_title"] == "Backyard cleanup with teardown"
    assert saved["actual_collected_cad"] == 600.0
    assert saved["labour_hours"] == 9.0
    assert saved["disassembly_required"] == 1
    assert saved["dense_materials"] == 0

    items = storage.list_completed_job_calibration_entries()
    assert len(items) == 1
    assert items[0]["entry_id"] == "manual-entry-1"
    assert items[0]["calibration_note"].startswith("Treat as haul-away")


def test_manual_completed_jobs_list_newest_first_and_caps_limit(isolated_db: Path) -> None:
    for index in range(30):
        storage.save_completed_job_calibration_entry(
            _entry(
                entry_id=f"manual-entry-{index:02d}",
                created_at=f"2026-05-17T10:{index:02d}:00",
                job_title=f"Manual job {index:02d}",
            )
        )

    default_items = storage.list_completed_job_calibration_entries()
    capped_items = storage.list_completed_job_calibration_entries(limit=999)
    invalid_limit_items = storage.list_completed_job_calibration_entries(limit=0)

    assert len(default_items) == 10
    assert default_items[0]["entry_id"] == "manual-entry-29"
    assert default_items[-1]["entry_id"] == "manual-entry-20"
    assert len(capped_items) == 25
    assert len(invalid_limit_items) == 10


def test_manual_completed_jobs_labour_hours_override(isolated_db: Path) -> None:
    saved = storage.save_completed_job_calibration_entry(
        _entry(entry_id="manual-entry-override", crew_size=3, duration_hours=3.0, labour_hours=8.5)
    )

    assert saved["labour_hours"] == 8.5


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_title", " "),
        ("service_type", ""),
        ("operator_username", ""),
        ("pricing_result", "excellent"),
        ("difficulty", "impossible"),
        ("access_difficulty", "blocked"),
        ("quoted_price_cad", -1),
        ("actual_collected_cad", 0),
        ("crew_size", 0),
        ("duration_hours", 0),
        ("labour_hours", -0.5),
        ("disposal_cost_cad", -1),
        ("fuel_cost_cad", -1),
        ("other_costs_cad", -1),
    ],
)
def test_manual_completed_jobs_validation_rejects_invalid_storage_values(
    isolated_db: Path,
    field: str,
    value: Any,
) -> None:
    with pytest.raises(ValueError):
        storage.save_completed_job_calibration_entry(_entry(**{field: value}))


def test_manual_completed_jobs_backup_export_import_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    isolated_db: Path,
) -> None:
    storage.save_completed_job_calibration_entry(_entry(entry_id="manual-entry-backup"))

    payload = storage.export_db_to_json()
    rows = payload["tables"]["completed_job_calibration_entries"]
    assert rows[0]["entry_id"] == "manual-entry-backup"
    assert rows[0]["labour_hours"] == 9.0

    restored_path = tmp_path / "restored-manual-completed-jobs.sqlite3"
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(restored_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    result = storage.import_db_from_json(payload)

    assert result["ok"] is True
    assert result["restored"]["completed_job_calibration_entries"] == 1
    restored = storage.list_completed_job_calibration_entries()
    assert restored[0]["entry_id"] == "manual-entry-backup"


def test_old_backup_without_manual_completed_jobs_table_restores(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "old-backup-restore.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    result = storage.import_db_from_json({"tables": {"quotes": [], "quote_requests": [], "jobs": []}})

    assert result["ok"] is True
    assert result["restored"]["completed_job_calibration_entries"] == 0
    assert storage.list_completed_job_calibration_entries() == []


def test_manual_completed_job_entry_does_not_create_lifecycle_records(isolated_db: Path) -> None:
    storage.save_completed_job_calibration_entry(_entry(entry_id="manual-entry-isolated"))

    conn = storage._connect()
    try:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            for table in ("quotes", "quote_requests", "jobs")
        }
    finally:
        conn.close()

    assert counts == {"quotes": 0, "quote_requests": 0, "jobs": 0}


def test_manual_completed_jobs_get_requires_admin_auth(client: TestClient, isolated_db: Path) -> None:
    resp = client.get("/admin/api/manual-completed-jobs")

    assert resp.status_code == 401


def test_manual_completed_jobs_post_requires_admin_auth(client: TestClient, isolated_db: Path) -> None:
    resp = client.post(
        "/admin/api/manual-completed-jobs",
        json={
            "job_title": "Unauthorized",
            "service_type": "haul_away",
            "actual_collected_cad": 100,
            "crew_size": 1,
            "duration_hours": 1,
            "pricing_result": "fair",
        },
    )

    assert resp.status_code == 401


def test_manual_completed_jobs_post_creates_entry_and_audit_log(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    resp = client.post(
        "/admin/api/manual-completed-jobs",
        headers=admin_headers,
        json={
            "job_title": "Old shed removal and haul-away",
            "service_type": "demolition",
            "secondary_category": "shed_removal",
            "quoted_price_cad": 1200,
            "actual_collected_cad": 1200,
            "crew_size": 2,
            "duration_hours": 3,
            "pricing_result": "profitable",
            "disassembly_required": True,
            "notes": "Receipt number 123. Photos in Drive.",
            "calibration_note": "Price as premium demolition plus haul-away.",
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    entry = payload["entry"]
    assert entry["entry_id"]
    assert entry["operator_username"] == "admin"
    assert entry["job_title"] == "Old shed removal and haul-away"
    assert entry["labour_hours"] == 6.0
    assert entry["disassembly_required"] == 1

    audit_items = storage.list_admin_audit_log(limit=10)
    assert any(
        item["action_type"] == "create_manual_completed_job_calibration_entry"
        and item["entity_type"] == "completed_job_calibration_entry"
        and item["record_id"] == entry["entry_id"]
        and item["success"] is True
        for item in audit_items
    )


def test_manual_completed_jobs_post_validation_failure_does_not_create_entry(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    resp = client.post(
        "/admin/api/manual-completed-jobs",
        headers=admin_headers,
        json={
            "job_title": " ",
            "service_type": "haul_away",
            "actual_collected_cad": 0,
            "crew_size": 1,
            "duration_hours": 1,
            "pricing_result": "fair",
        },
    )

    assert resp.status_code == 422
    assert storage.list_completed_job_calibration_entries() == []


def test_manual_completed_jobs_get_returns_newest_entries_with_limit_cap(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    for index in range(30):
        storage.save_completed_job_calibration_entry(
            _entry(
                entry_id=f"api-manual-entry-{index:02d}",
                created_at=f"2026-05-17T11:{index:02d}:00",
                job_title=f"API manual job {index:02d}",
            )
        )

    resp = client.get("/admin/api/manual-completed-jobs?limit=999", headers=admin_headers)

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 25
    assert items[0]["entry_id"] == "api-manual-entry-29"
    assert items[-1]["entry_id"] == "api-manual-entry-05"
    assert resp.json()["total"] == 30
    assert resp.json()["has_more"] is True
    assert resp.json()["limit"] == 25
    assert resp.json()["offset"] == 0


def test_manual_completed_jobs_search_paginates_beyond_first_page(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    for index in range(30):
        storage.save_completed_job_calibration_entry(
            _entry(
                entry_id=f"search-entry-{index:02d}",
                created_at=f"2026-05-17T11:{index:02d}:00",
                job_title=f"Historical cleanup {index:02d}",
                service_type="haul_away" if index != 2 else "demolition",
                actual_collected_cad=600 + index,
                notes="Partner referral evidence" if index == 2 else "Other source",
            )
        )

    second_page = client.get(
        "/admin/api/manual-completed-jobs?limit=10&offset=20",
        headers=admin_headers,
    )
    assert second_page.status_code == 200
    payload = second_page.json()
    assert len(payload["items"]) == 10
    assert payload["total"] == 30
    assert payload["offset"] == 20
    assert payload["has_more"] is False
    assert payload["items"][-1]["entry_id"] == "search-entry-00"

    filtered = client.get(
        "/admin/api/manual-completed-jobs?search=Partner%20referral&service_type=demolition&actual_collected_cad=602",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["has_more"] is False
    assert filtered.json()["items"][0]["entry_id"] == "search-entry-02"


def test_manual_completed_jobs_duplicate_create_returns_existing_entry(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    original = _entry(entry_id="existing-calibration")
    storage.save_completed_job_calibration_entry(original)
    response = client.post(
        "/admin/api/manual-completed-jobs",
        headers=admin_headers,
        json={
            "job_title": "  BACKYARD   cleanup with teardown ",
            "service_type": "HAUL_AWAY",
            "actual_collected_cad": 600,
            "crew_size": 3,
            "duration_hours": 3,
            "pricing_result": "profitable",
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "manual_completed_job_duplicate"
    assert detail["existing_entry"]["entry_id"] == "existing-calibration"
    assert len(storage.list_completed_job_calibration_entries()) == 1
    assert any(
        item["action_type"] == "create_manual_completed_job_calibration_entry"
        and item["record_id"] != "existing-calibration"
        and item["success"] is False
        and "existing-calibration" in str(item["error_summary"])
        for item in storage.list_admin_audit_log(limit=10)
    )


def test_manual_completed_jobs_similar_distinct_job_can_be_created(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    storage.save_completed_job_calibration_entry(_entry(entry_id="first-cleanup"))
    response = client.post(
        "/admin/api/manual-completed-jobs",
        headers=admin_headers,
        json={
            "job_title": "Backyard cleanup with teardown - second property",
            "service_type": "haul_away",
            "actual_collected_cad": 600,
            "crew_size": 3,
            "duration_hours": 3,
            "pricing_result": "profitable",
            "notes": "Similar scope, separate confirmed job.",
        },
    )
    assert response.status_code == 200
    assert len(storage.list_completed_job_calibration_entries()) == 2


def test_manual_completed_jobs_patch_updates_only_target_and_audits(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    original = storage.save_completed_job_calibration_entry(
        _entry(entry_id="entry-to-enrich", notes=None, disposal_cost_cad=None)
    )
    storage.save_completed_job_calibration_entry(
        _entry(entry_id="other-entry", job_title="Other job", actual_collected_cad=700)
    )
    response = client.patch(
        "/admin/api/manual-completed-jobs/entry-to-enrich",
        headers=admin_headers,
        json={"notes": "Receipt confirmed.", "disposal_cost_cad": 130},
    )
    assert response.status_code == 200
    updated = response.json()["entry"]
    assert updated["notes"] == "Receipt confirmed."
    assert updated["disposal_cost_cad"] == 130
    assert updated["created_at"] == original["created_at"]
    assert updated["operator_username"] == original["operator_username"]
    assert updated["updated_at"]
    assert updated["actual_collected_cad"] == original["actual_collected_cad"]
    assert len(storage.list_completed_job_calibration_entries()) == 2
    assert storage.get_completed_job_calibration_entry("other-entry")["notes"] == original["notes"]
    assert any(
        item["action_type"] == "update_manual_completed_job_calibration_entry"
        and item["record_id"] == "entry-to-enrich"
        and item["success"] is True
        for item in storage.list_admin_audit_log(limit=10)
    )


def test_manual_completed_jobs_patch_missing_and_unauthorized_fail_safely(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    unauthorized = client.patch(
        "/admin/api/manual-completed-jobs/missing-entry", json={"notes": "No"}
    )
    assert unauthorized.status_code == 401

    missing = client.patch(
        "/admin/api/manual-completed-jobs/missing-entry",
        headers=admin_headers,
        json={"notes": "No"},
    )
    assert missing.status_code == 404
    assert storage.list_completed_job_calibration_entries() == []
    assert any(
        item["action_type"] == "update_manual_completed_job_calibration_entry"
        and item["record_id"] == "missing-entry"
        and item["success"] is False
        for item in storage.list_admin_audit_log(limit=10)
    )


def test_manual_completed_jobs_patch_cannot_duplicate_another_entry(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    storage.save_completed_job_calibration_entry(_entry(entry_id="existing-entry"))
    storage.save_completed_job_calibration_entry(
        _entry(
            entry_id="different-entry",
            job_title="Different cleanup",
            actual_collected_cad=700,
        )
    )
    response = client.patch(
        "/admin/api/manual-completed-jobs/different-entry",
        headers=admin_headers,
        json={
            "job_title": "Backyard cleanup with teardown",
            "actual_collected_cad": 600,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["existing_entry"]["entry_id"] == "existing-entry"
    unchanged = storage.get_completed_job_calibration_entry("different-entry")
    assert unchanged["job_title"] == "Different cleanup"
    assert unchanged["actual_collected_cad"] == 700
    assert len(storage.list_completed_job_calibration_entries()) == 2


def test_manual_completed_jobs_do_not_affect_completed_job_profit_report(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    storage.save_completed_job_calibration_entry(
        _entry(entry_id="manual-entry-report-boundary", job_title="Manual calibration only")
    )
    _seed_job("lifecycle-completed")

    resp = client.get("/admin/api/completed-job-profit-report", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    job_ids = {item["job_id"] for item in payload["jobs"]}
    assert job_ids == {"lifecycle-completed"}
    assert "manual-entry-report-boundary" not in job_ids
    assert "Manual calibration only" not in str(payload)
