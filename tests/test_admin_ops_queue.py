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
    scheduled_start: str | None = None,
    costing: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "job_id": job_id,
        "created_at": "2026-04-28T11:00:00",
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
    for index in range(SECTION_ITEM_LIMIT + 2):
        quote_id = f"q-cap-{index:02d}"
        _seed_quote(quote_id, created_at=f"2026-04-28T09:{index:02d}:00")
        _seed_request(
            f"req-cap-{index:02d}",
            quote_id=quote_id,
            created_at=f"2026-04-28T10:{index:02d}:00",
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
    assert first.json()["counts"]["accepted_needing_approval"] == SECTION_ITEM_LIMIT + 2
    assert len(first_sections["accepted_needing_approval"]["items"]) == SECTION_ITEM_LIMIT
    assert first_sections["accepted_needing_approval"]["items"] == second_sections["accepted_needing_approval"]["items"]
    assert storage.list_quote_requests(limit=50, include_followup_status=True) == before_requests
    assert storage.list_jobs(limit=50) == before_jobs
    assert storage.list_quotes(limit=50) == before_quotes


def test_completed_job_with_costing_is_not_marked_missing(
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
            "actual_disposal_cost_cad": 40.0,
            "actual_fuel_cost_cad": 15.0,
            "final_amount_collected_cad": 260.0,
            "payment_method": "cash",
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
        },
    )

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    section = _sections(resp.json())["completed_missing_costing"]
    assert all(item["job_id"] != "job-costed" for item in section["items"])
