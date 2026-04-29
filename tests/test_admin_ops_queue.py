import base64
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.services.admin_ops_queue import SECTION_ITEM_LIMIT


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "admin-ops-queue.sqlite3"
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


def _seed_quote(quote_id: str, *, created_at: str = "2026-04-28T09:00:00", admin_status: str = "pending") -> None:
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": {
                "customer_name": f"Customer {quote_id}",
                "customer_phone": "705-555-0101",
                "job_address": f"{quote_id} Main St",
                "job_description_customer": "Small delivery",
                "service_type": "delivery",
            },
            "response": {
                "cash_total_cad": 120.0,
                "emt_total_cad": 135.6,
                "job_description_internal": "Internal delivery notes",
            },
            "accept_token": f"accept-{quote_id}",
            "admin_status": admin_status,
        }
    )


def _seed_request(
    request_id: str,
    *,
    quote_id: str,
    status: str = "customer_accepted",
    followup_status: str | None = None,
    requested_job_date: str | None = "2026-05-10",
    requested_time_window: str | None = "morning",
    created_at: str = "2026-04-28T10:00:00",
) -> None:
    storage.save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": status,
            "quote_id": quote_id,
            "customer_name": f"Request {request_id}",
            "customer_phone": "705-555-0102",
            "job_address": f"{request_id} Request Rd",
            "job_description_customer": "Pickup request",
            "job_description_internal": "Internal pickup request",
            "service_type": "haul_away",
            "cash_total_cad": 160.0,
            "emt_total_cad": 180.8,
            "request_json": {"service_type": "haul_away"},
            "notes": None,
            "requested_job_date": requested_job_date,
            "requested_time_window": requested_time_window,
            "customer_accepted_at": created_at if status == "customer_accepted" else None,
            "admin_approved_at": None,
            "accept_token": f"accept-{quote_id}",
            "booking_token": f"booking-{quote_id}",
            "booking_token_created_at": created_at,
            "followup_status": followup_status,
        }
    )


def _seed_job(
    job_id: str,
    *,
    quote_id: str,
    request_id: str,
    status: str = "approved",
    created_at: str = "2026-04-28T11:00:00",
    scheduled_start: str | None = None,
    costing: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "job_id": job_id,
        "created_at": created_at,
        "status": status,
        "quote_id": quote_id,
        "request_id": request_id,
        "customer_name": f"Job {job_id}",
        "customer_phone": "705-555-0103",
        "job_address": f"{job_id} Job Ave",
        "job_description_customer": "Approved job",
        "job_description_internal": "Internal approved job",
        "service_type": "dump_run",
        "cash_total_cad": 220.0,
        "emt_total_cad": 248.6,
        "request_json": {"service_type": "dump_run"},
        "notes": None,
        "scheduled_start": scheduled_start,
        "scheduled_end": "2026-05-10T14:00:00+00:00" if scheduled_start else None,
        "completed_at": "2026-04-28T12:30:00" if status == "completed" else None,
    }
    if costing:
        record.update(costing)
    storage.save_job(record)


def _sections(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {section["id"]: section for section in payload["sections"]}


def test_storage_list_helpers_offset_zero_preserves_default_order_and_offset_one_advances(
    isolated_db: Path,
) -> None:
    _seed_quote("q-old", created_at="2026-04-28T09:00:00")
    _seed_quote("q-new", created_at="2026-04-28T10:00:00")
    _seed_request("req-old", quote_id="q-old", created_at="2026-04-28T09:05:00")
    _seed_request("req-new", quote_id="q-new", created_at="2026-04-28T10:05:00")
    _seed_job("job-old", quote_id="q-old", request_id="req-old", created_at="2026-04-28T09:10:00")
    _seed_job("job-new", quote_id="q-new", request_id="req-new", created_at="2026-04-28T10:10:00")

    assert storage.list_quotes(limit=1) == storage.list_quotes(limit=1, offset=0)
    assert storage.list_quote_requests(limit=1, include_followup_status=True) == storage.list_quote_requests(
        limit=1,
        include_followup_status=True,
        offset=0,
    )
    assert storage.list_quote_requests(limit=1) == storage.list_quote_requests(limit=1, offset=0)
    assert storage.list_jobs(limit=1) == storage.list_jobs(limit=1, offset=0)
    assert storage.list_quotes(limit=1, offset=1)[0]["quote_id"] == "q-old"
    assert storage.list_quote_requests(limit=1, include_followup_status=True, offset=1)[0]["request_id"] == "req-old"
    assert storage.list_jobs(limit=1, offset=1)[0]["job_id"] == "job-old"


def test_admin_ops_queue_requires_auth(client: TestClient, isolated_db: Path) -> None:
    resp = client.get("/admin/api/ops-queue")

    assert resp.status_code == 401


def test_admin_ops_queue_surfaces_existing_attention_items(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_quote("q-accepted")
    _seed_request("req-accepted", quote_id="q-accepted")

    _seed_quote("q-followup")
    _seed_request(
        "req-followup",
        quote_id="q-followup",
        status="customer_pending",
        followup_status="needs_followup",
    )
    _seed_quote("q-closed-followup")
    _seed_request(
        "req-closed-followup",
        quote_id="q-closed-followup",
        status="customer_pending",
        followup_status="closed_no_followup",
    )

    _seed_job("job-completed-missing", quote_id="q-costing", request_id="missing-request", status="completed")

    _seed_quote("q-missing-schedule")
    _seed_request("req-missing-schedule", quote_id="q-missing-schedule")
    _seed_job("job-missing-schedule", quote_id="q-missing-schedule", request_id="req-missing-schedule")

    _seed_quote("q-missing-prefs")
    _seed_request(
        "req-missing-prefs",
        quote_id="q-missing-prefs",
        requested_job_date=None,
        requested_time_window=None,
    )
    _seed_job(
        "job-missing-prefs",
        quote_id="q-missing-prefs",
        request_id="req-missing-prefs",
        scheduled_start="2026-05-10T12:00:00+00:00",
    )

    _seed_quote("q-stale", created_at="2000-01-01T09:00:00")
    _seed_quote("q-expired-stale", created_at="2000-01-01T09:00:00", admin_status="expired")

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    sections = _sections(payload)
    assert payload["counts"]["accepted_needing_approval"] >= 1
    assert any(item["request_id"] == "req-accepted" for item in sections["accepted_needing_approval"]["items"])
    assert any(item["request_id"] == "req-followup" for item in sections["followup_marked"]["items"])
    assert all(item["request_id"] != "req-closed-followup" for item in sections["followup_marked"]["items"])
    assert any(item["job_id"] == "job-completed-missing" for item in sections["completed_missing_costing"]["items"])
    assert any(item["job_id"] == "job-missing-schedule" for item in sections["jobs_missing_schedule"]["items"])
    assert any(item["job_id"] == "job-missing-prefs" for item in sections["jobs_missing_booking_preferences"]["items"])
    assert any(item["quote_id"] == "q-stale" for item in sections["stale_pending_estimates"]["items"])
    assert all(item["quote_id"] != "q-expired-stale" for item in sections["stale_pending_estimates"]["items"])


def test_admin_ops_queue_response_is_capped_stable_and_read_only(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    total_records = SECTION_ITEM_LIMIT + 2
    for index in range(total_records):
        quote_id = f"q-cap-{index:02d}"
        _seed_quote(quote_id, created_at=f"2099-04-{(index % 28) + 1:02d}T09:00:00")
        _seed_request(
            f"req-cap-{index:02d}",
            quote_id=quote_id,
            created_at=f"2099-04-{(index % 28) + 1:02d}T10:00:00",
        )

    before_requests = storage.list_quote_requests(limit=50, include_followup_status=True)
    before_jobs = storage.list_jobs(limit=50)
    before_quotes = storage.list_quotes(limit=50)

    first = client.get("/admin/api/ops-queue", headers=admin_headers)
    second = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    first_sections = _sections(first.json())
    second_sections = _sections(second.json())
    assert first.json()["counts"]["accepted_needing_approval"] == total_records
    assert len(first_sections["accepted_needing_approval"]["items"]) == SECTION_ITEM_LIMIT
    assert first_sections["accepted_needing_approval"]["items"] == second_sections["accepted_needing_approval"]["items"]
    assert storage.list_quote_requests(limit=50, include_followup_status=True) == before_requests
    assert storage.list_jobs(limit=50) == before_jobs
    assert storage.list_quotes(limit=50) == before_quotes


def test_admin_ops_queue_does_not_require_full_item_hydration(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote("q-targeted")
    _seed_request("req-targeted", quote_id="q-targeted")
    _seed_job("job-targeted", quote_id="q-targeted", request_id="req-targeted", status="completed")

    def fail_hydration(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ops queue should use targeted source queries")

    monkeypatch.setattr(storage, "get_quote_request_record", fail_hydration)
    monkeypatch.setattr(storage, "get_quote_request", fail_hydration)
    monkeypatch.setattr(storage, "get_job", fail_hydration)
    monkeypatch.setattr(storage, "list_quotes", fail_hydration)
    monkeypatch.setattr(storage, "list_quote_requests", fail_hydration)
    monkeypatch.setattr(storage, "list_jobs", fail_hydration)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["accepted_needing_approval"] == 1
    assert resp.json()["counts"]["completed_missing_costing"] == 1


def test_completed_job_with_partial_core_costing_still_appears(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(
        "job-partial-costing",
        quote_id="q-partial-costing",
        request_id="req-partial-costing",
        status="completed",
        costing={"payment_status": "paid_in_full"},
    )

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    section = _sections(resp.json())["completed_missing_costing"]
    assert any(item["job_id"] == "job-partial-costing" for item in section["items"])


def test_completed_job_with_core_costing_is_not_marked_missing(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_job(
        "job-costed",
        quote_id="q-costed",
        request_id="req-costed",
        status="completed",
        costing={
            "actual_hours": 2.5,
            "actual_crew_size": 2,
            "final_amount_collected_cad": 260.0,
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
        },
    )

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    section = _sections(resp.json())["completed_missing_costing"]
    assert all(item["job_id"] != "job-costed" for item in section["items"])


def test_stale_pending_estimates_beyond_display_cap_are_counted(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    total_stale = SECTION_ITEM_LIMIT + 2
    for index in range(total_stale):
        _seed_quote(
            f"q-stale-{index:05d}",
            created_at=f"2000-01-{(index % 28) + 1:02d}T09:00:00",
        )
    _seed_quote("q-expired-stale", created_at="2000-01-01T09:00:00", admin_status="expired")

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    section = _sections(resp.json())["stale_pending_estimates"]
    assert resp.json()["counts"]["stale_pending_estimates"] == total_stale
    assert section["count"] == total_stale
    assert len(section["items"]) == SECTION_ITEM_LIMIT
    assert all(item["quote_id"] != "q-expired-stale" for item in section["items"])
