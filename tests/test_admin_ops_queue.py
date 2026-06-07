import base64
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import quote_engine
from app import storage
from app.main import app
from app.services import quote_risk_scoring


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


def _seed_quote(
    quote_id: str,
    *,
    created_at: str = "2099-04-28T09:00:00",
    admin_status: str = "pending",
    request_overrides: dict[str, Any] | None = None,
) -> None:
    request = {
        "customer_name": f"Customer {quote_id}",
        "customer_phone": "705-555-0101",
        "job_address": f"{quote_id} Main St",
        "job_description_customer": "Small delivery",
        "service_type": "delivery",
    }
    if request_overrides:
        request.update(request_overrides)
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": request,
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
    submitted_at: str | None = None,
) -> None:
    accepted_or_approved_at = submitted_at or created_at
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
            "customer_accepted_at": accepted_or_approved_at if status == "customer_accepted" else None,
            "admin_approved_at": accepted_or_approved_at if status == "admin_approved" else None,
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
    scheduled_end: str | None = None,
    google_calendar_event_id: str | None = None,
    costing: dict[str, Any] | None = None,
    request_json: dict[str, Any] | None = None,
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
        "request_json": request_json if request_json is not None else {"service_type": "dump_run"},
        "notes": None,
        "scheduled_start": scheduled_start,
        "scheduled_end": scheduled_end if scheduled_end is not None else ("2026-05-10T14:00:00+00:00" if scheduled_start else None),
        "google_calendar_event_id": google_calendar_event_id,
        "completed_at": "2026-04-28T12:30:00" if status == "completed" else None,
    }
    if costing:
        record.update(costing)
    storage.save_job(record)


def _cards(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["key"]: card for card in payload["cards"]}


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


def test_admin_ops_queue_returns_stable_zero_count_daily_ops_board(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload) == {"generated_at", "counts", "cards", "accepted_not_booked_items"}
    assert "sections" not in payload
    assert [card["key"] for card in payload["cards"]] == [
        "new_requests",
        "needs_followup",
        "accepted_not_booked",
        "upcoming_jobs",
        "completed_missing_costs",
        "owner_review",
        "stale_quotes",
    ]
    assert all(card["count"] == 0 for card in payload["cards"])
    for card in payload["cards"]:
        assert card["label"]
        assert card["description"]
        assert payload["counts"][card["key"]] == card["count"]
    assert payload["accepted_not_booked_items"] == []


def test_admin_ops_queue_daily_ops_board_counts_existing_attention_queues(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_quote("q-new")
    _seed_request("req-new", quote_id="q-new", status="customer_pending")

    _seed_quote("q-followup")
    _seed_request(
        "req-followup",
        quote_id="q-followup",
        status="customer_pending",
        followup_status="needs_followup",
    )
    _seed_quote("q-accepted")
    _seed_request("req-accepted", quote_id="q-accepted", status="customer_accepted")

    _seed_quote("q-linked-job")
    _seed_request("req-linked-job", quote_id="q-linked-job", status="customer_accepted")
    _seed_job("job-linked-unscheduled", quote_id="q-linked-job", request_id="req-linked-job")

    _seed_quote("q-upcoming")
    _seed_request("req-upcoming", quote_id="q-upcoming", status="admin_approved")
    _seed_job(
        "job-upcoming",
        quote_id="q-upcoming",
        request_id="req-upcoming",
        status="scheduled",
        scheduled_start="2099-05-10T12:00:00+00:00",
        scheduled_end="2099-05-10T14:00:00+00:00",
    )
    _seed_job(
        "job-malformed-schedule",
        quote_id="q-malformed-schedule",
        request_id="req-malformed-schedule",
        status="scheduled",
        scheduled_start="not-a-date",
        scheduled_end="also-not-a-date",
    )

    _seed_job("job-completed-missing", quote_id="q-costing", request_id="missing-request", status="completed")
    _seed_job(
        "job-zero-cost-valid",
        quote_id="q-zero-cost-valid",
        request_id="req-zero-cost-valid",
        status="completed",
        costing={
            "actual_hours": 0,
            "actual_crew_size": 1,
            "actual_labor_cost_cad": 0,
            "actual_disposal_cost_cad": 0,
            "actual_fuel_cost_cad": 0,
            "actual_other_costs_cad": 0,
            "final_amount_collected_cad": 0,
            "payment_status": "paid_in_full",
            "job_profit_status": "fair",
        },
    )

    _seed_quote(
        "q-owner-review",
        created_at="2099-01-01T09:00:00",
        request_overrides={"service_type": "haul_away", "dense_material_type": "concrete"},
    )
    _seed_quote(
        "q-low-risk-advisory",
        created_at="2099-01-01T10:00:00",
        request_overrides={"service_type": "small_move", "weather_protection_required": True},
    )
    _seed_quote("q-malformed-owner", created_at="2099-01-01T11:00:00", request_overrides={})
    with storage._connect() as conn:
        conn.execute(
            "UPDATE quotes SET request_json = ? WHERE quote_id = ?",
            ("not-json", "q-malformed-owner"),
        )
        conn.commit()

    _seed_quote("q-stale", created_at="2000-01-01T09:00:00")
    _seed_quote("q-expired-stale", created_at="2000-01-01T09:00:00", admin_status="expired")

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    cards = _cards(payload)
    assert cards["new_requests"]["count"] == 2
    assert cards["needs_followup"]["count"] == 1
    assert cards["accepted_not_booked"]["count"] == 2
    assert cards["upcoming_jobs"]["count"] == 1
    assert cards["completed_missing_costs"]["count"] == 1
    assert cards["owner_review"]["count"] == 1
    assert cards["stale_quotes"]["count"] == 1


def test_admin_ops_queue_response_is_capped_stable_and_read_only(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    total_records = 55
    expected_detail_cap = 50
    for index in range(total_records):
        quote_id = f"q-cap-{index:02d}"
        if index == 0:
            created_at = "2099-01-01T08:00:00"
            submitted_at = "2099-05-01T12:00:00"
        elif index in (1, 2):
            created_at = f"2099-01-0{index + 1}T08:00:00"
            submitted_at = "2099-05-01T11:00:00"
        else:
            created_at = f"2099-04-01T10:{index:02d}:00"
            submitted_at = f"2099-04-01T09:{59 - index:02d}:00"
        _seed_quote(quote_id, created_at=created_at)
        _seed_request(
            f"req-cap-{index:02d}",
            quote_id=quote_id,
            created_at=created_at,
            submitted_at=submitted_at,
        )

    _seed_quote("q-excluded-scheduled")
    _seed_request("req-excluded-scheduled", quote_id="q-excluded-scheduled", status="admin_approved")
    _seed_job(
        "job-excluded-scheduled",
        quote_id="q-excluded-scheduled",
        request_id="req-excluded-scheduled",
        status="scheduled",
        scheduled_start="2099-04-02T12:00:00+00:00",
        scheduled_end="2099-04-02T14:00:00+00:00",
    )
    _seed_job("job-excluded-completed", quote_id="q-excluded-completed", request_id="req-excluded-completed", status="completed")
    _seed_job("job-excluded-cancelled", quote_id="q-excluded-cancelled", request_id="req-excluded-cancelled", status="cancelled")

    before_requests = storage.list_quote_requests(limit=100, include_followup_status=True)
    before_jobs = storage.list_jobs(limit=100)
    before_quotes = storage.list_quotes(limit=100)

    first = client.get("/admin/api/ops-queue", headers=admin_headers)
    second = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert _cards(first_payload) == _cards(second_payload)
    assert first_payload["accepted_not_booked_items"] == second_payload["accepted_not_booked_items"]
    assert first_payload["counts"]["accepted_not_booked"] == total_records
    assert _cards(first_payload)["accepted_not_booked"]["count"] == total_records
    assert len(first_payload["accepted_not_booked_items"]) == expected_detail_cap
    assert [item["item_id"] for item in first_payload["accepted_not_booked_items"][:3]] == [
        "req-cap-00",
        "req-cap-01",
        "req-cap-02",
    ]
    returned_ids = {item["item_id"] for item in first_payload["accepted_not_booked_items"]}
    assert "req-cap-00" in returned_ids
    assert "req-cap-54" not in returned_ids
    assert "job-excluded-scheduled" not in returned_ids
    assert "job-excluded-completed" not in returned_ids
    assert "job-excluded-cancelled" not in returned_ids
    assert storage.list_quote_requests(limit=100, include_followup_status=True) == before_requests
    assert storage.list_jobs(limit=100) == before_jobs
    assert storage.list_quotes(limit=100) == before_quotes


def test_admin_ops_queue_includes_accepted_not_booked_detail_items(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_quote("q-request")
    _seed_request("req-request", quote_id="q-request", status="customer_accepted")

    _seed_quote("q-admin-approved")
    _seed_request("req-admin-approved", quote_id="q-admin-approved", status="admin_approved")

    _seed_quote("q-job")
    _seed_request("req-job", quote_id="q-job", status="admin_approved")
    _seed_job("job-unscheduled", quote_id="q-job", request_id="req-job", status="approved")

    _seed_quote("q-scheduled-linked")
    _seed_request("req-scheduled-linked", quote_id="q-scheduled-linked", status="admin_approved")
    _seed_job(
        "job-scheduled-linked",
        quote_id="q-scheduled-linked",
        request_id="req-scheduled-linked",
        status="scheduled",
        google_calendar_event_id="calendar-linked-event",
    )

    _seed_quote("q-scheduled")
    _seed_request("req-scheduled", quote_id="q-scheduled", status="admin_approved")
    _seed_job(
        "job-scheduled",
        quote_id="q-scheduled",
        request_id="req-scheduled",
        status="scheduled",
        scheduled_start="2099-05-10T12:00:00+00:00",
        scheduled_end="2099-05-10T14:00:00+00:00",
    )

    _seed_job("job-completed", quote_id="q-completed", request_id="req-completed", status="completed")

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["counts"]["accepted_not_booked"] == 4

    items = {item["item_id"]: item for item in payload["accepted_not_booked_items"]}
    assert set(items) == {"req-request", "req-admin-approved", "job-unscheduled", "job-scheduled-linked"}

    accepted_request = items["req-request"]
    assert accepted_request["item_type"] == "request"
    assert accepted_request["job_id"] is None
    assert accepted_request["scheduling_ready"] is False
    assert accepted_request["recommended_action"] == "approve_request"
    assert "job_id" in accepted_request["missing_scheduling_fields"]
    assert "scheduled_start" in accepted_request["missing_scheduling_fields"]

    approved_request = items["req-admin-approved"]
    assert approved_request["recommended_action"] == "needs_job"
    assert approved_request["scheduling_ready"] is False

    unscheduled_job = items["job-unscheduled"]
    assert unscheduled_job["item_type"] == "job"
    assert unscheduled_job["job_id"] == "job-unscheduled"
    assert unscheduled_job["scheduling_ready"] is True
    assert unscheduled_job["recommended_action"] == "schedule_job"
    assert unscheduled_job["requested_job_date"] == "2026-05-10"
    assert unscheduled_job["requested_time_window"] == "morning"
    assert "scheduled_start" in unscheduled_job["missing_scheduling_fields"]
    assert "scheduled_end" in unscheduled_job["missing_scheduling_fields"]
    assert unscheduled_job["google_calendar_event_id"] is None

    scheduled_linked_job = items["job-scheduled-linked"]
    assert scheduled_linked_job["status"] == "scheduled"
    assert scheduled_linked_job["job_id"] == "job-scheduled-linked"
    assert scheduled_linked_job["google_calendar_event_id"] == "calendar-linked-event"
    assert scheduled_linked_job["scheduling_ready"] is True
    assert scheduled_linked_job["recommended_action"] == "schedule_job"
    assert "scheduled_start" in scheduled_linked_job["missing_scheduling_fields"]


def test_admin_ops_queue_accepted_not_booked_detail_reports_missing_customer_preferences(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_quote("q-job-missing-preferences")
    _seed_request(
        "req-job-missing-preferences",
        quote_id="q-job-missing-preferences",
        status="admin_approved",
        requested_job_date=None,
        requested_time_window=None,
    )
    _seed_job(
        "job-missing-preferences",
        quote_id="q-job-missing-preferences",
        request_id="req-job-missing-preferences",
        status="approved",
    )

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    item = next(item for item in resp.json()["accepted_not_booked_items"] if item["item_id"] == "job-missing-preferences")
    assert item["scheduling_ready"] is True
    assert item["preferred_window_label"] == "Not provided"
    assert "requested_job_date" in item["missing_scheduling_fields"]
    assert "requested_time_window" in item["missing_scheduling_fields"]
    assert "confirm timing manually" in item["scheduling_summary"].lower()


def test_admin_ops_queue_does_not_require_full_item_hydration(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote("q-accepted-targeted")
    _seed_request("req-accepted-targeted", quote_id="q-accepted-targeted")
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
    assert resp.json()["counts"]["accepted_not_booked"] == 1
    assert resp.json()["counts"]["completed_missing_costs"] == 1


def test_owner_review_counts_completed_profit_flags_without_advisory_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_job(
        "job-underquoted",
        quote_id="q-underquoted",
        request_id="req-underquoted",
        status="completed",
        costing={
            "actual_hours": 2.5,
            "actual_crew_size": 2,
            "actual_labor_cost_cad": 120,
            "actual_disposal_cost_cad": 0,
            "actual_fuel_cost_cad": 0,
            "actual_other_costs_cad": 0,
            "final_amount_collected_cad": 260.0,
            "payment_status": "paid_in_full",
            "job_profit_status": "underquoted",
        },
    )

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("completed profit flags should be counted in SQL")

    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_advisory_prefilter_does_not_truncate_older_manual_review(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_candidate_limit = 250
    for index in range(previous_candidate_limit + 5):
        _seed_quote(
            f"q-owner-noise-{index:03d}",
            created_at=f"2099-04-{(index % 28) + 1:02d}T09:{index % 60:02d}:00",
        )
    _seed_quote(
        "q-owner-older-risk",
        created_at="2099-01-01T09:00:00",
        request_overrides={"service_type": "haul_away", "dense_material_type": "concrete"},
    )

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_structured_signal_count_does_not_recompute_unbounded_advisory(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    total_owner_review = 300
    for index in range(total_owner_review):
        _seed_quote(
            f"q-owner-sql-{index:03d}",
            created_at=f"2099-03-{(index % 28) + 1:02d}T09:{index % 60:02d}:00",
            request_overrides={"service_type": "haul_away", "demolition_ripout": True},
        )

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should not recompute advisory in Python")

    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == total_owner_review


def test_owner_review_does_not_call_pricing_engine(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-no-pricing",
        request_overrides={"service_type": "haul_away", "demolition_ripout": True},
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_counts_text_derived_demolition_without_pricing_or_advisory_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-text-demo",
        request_overrides={
            "service_type": "demolition",
            "description": "16x10 shed teardown",
            "job_description_customer": "16x10 shed teardown",
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_demolition_owner_review_text_signals_match_engine_owner_review_phrases() -> None:
    expected_signals = (
        set(quote_engine._DEMOLITION_ACCESS_RISK_PHRASES)
        | set(quote_engine._DEMOLITION_UNKNOWN_SCOPE_PHRASES)
        | set(quote_engine._DEMOLITION_HEAVY_MATERIAL_PHRASES)
        | set(quote_engine._DEMOLITION_STRUCTURE_PHRASES)
    )

    assert sorted(expected_signals - set(storage._DEMOLITION_OWNER_REVIEW_TEXT_SIGNALS)) == []


@pytest.mark.parametrize(
    "description",
    [
        "Possible asbestos insulation removal.",
        "Hazardous material demolition.",
        "Dirt from demolition cleanup.",
    ],
)
def test_owner_review_counts_hazardous_and_dirt_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-hazard-dirt",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize(
    "description",
    [
        "Roofing material demolition.",
        "Roof tear-off demolition with roof debris.",
        "Roof tear\noff demolition.",
    ],
)
def test_owner_review_counts_roof_heavy_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-roof-heavy",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize(
    "description",
    [
        "Waterproofing material demo.",
        "Proofing demolition.",
    ],
)
def test_owner_review_does_not_count_roofing_substring_false_positives_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-roof-substring-near-miss",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 0


@pytest.mark.parametrize(
    "description",
    [
        "Interior bulkhead selective demolition near utilities, HVAC, and plumbing.",
        "Ceiling opening demolition around furnace ducting and water heater plumbing.",
        "Remove wall around plumbing.",
        "Remove wall near utility line.",
        "Remove wall\naround plumbing.",
    ],
)
def test_owner_review_counts_utility_adjacent_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-utility-adjacent",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_counts_split_field_utility_adjacent_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-demo-utility-adjacent-split",
        request_overrides={
            "service_type": "demolition",
            "description": "Interior bulkhead selective demolition.",
            "job_description_customer": "Near HVAC and plumbing.",
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_does_not_count_split_field_utility_room_near_miss_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-demo-utility-room-near-miss",
        request_overrides={
            "service_type": "demolition",
            "description": "Interior wall removal.",
            "job_description_customer": "Customer has a utility room nearby.",
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 0


@pytest.mark.parametrize(
    "description",
    [
        "Remove a kitchen unit.",
        "Demolition of a wall unit.",
        "Remove interior wall.",
        "Small controlled drywall and plaster demo.",
        "Small controlled drywall demo around plumbing.",
    ],
)
def test_owner_review_does_not_count_bare_unit_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-bare-unit",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 0


@pytest.mark.parametrize(
    "description",
    [
        "Backyard demolition debris with no driveway access.",
        "Back yard shed rip-out with no photos.",
        "Inside removal from downstairs with a long carry.",
        "Demolition debris without photos and unknown disposal volume.",
        "Hidden rubble and lath and plaster from interior demolition.",
        "Bathroom tiles and blocks from demolition.",
    ],
)
def test_owner_review_counts_engine_demolition_text_signals_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-engine-text",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize(
    "description",
    [
        "Tight-access demolition cleanup.",
        "No-photo demolition debris.",
        "Back-yard demolition cleanup.",
        "No-driveway-access demolition debris.",
        "Long-carry demolition debris.",
        "Inside-removal demolition cleanup.",
    ],
)
def test_owner_review_counts_punctuation_normalized_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    description: str,
) -> None:
    _seed_quote(
        "q-owner-demo-punctuation",
        request_overrides={
            "service_type": "demolition",
            "description": description,
            "job_description_customer": description,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize("material_field", ["construction_debris_type", "dense_material_type"])
def test_owner_review_counts_structured_unknown_demolition_materials_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    material_field: str,
) -> None:
    _seed_quote(
        f"q-owner-demo-other-{material_field}",
        request_overrides={
            "service_type": "demolition",
            "description": "Small controlled cleanup",
            "job_description_customer": "Small controlled cleanup",
            material_field: "other",
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize(
    ("material_field", "material_value"),
    [
        ("construction_debris_type", "tile"),
        ("construction_debris_type", "shingles"),
        ("dense_material_type", "tile"),
        ("dense_material_type", "shingles"),
    ],
)
def test_owner_review_counts_structured_tile_shingle_demolition_materials_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    material_field: str,
    material_value: str,
) -> None:
    _seed_quote(
        f"q-owner-demo-{material_field}-{material_value}",
        request_overrides={
            "service_type": "demolition",
            "description": "Small controlled cleanup",
            "job_description_customer": "Small controlled cleanup",
            material_field: material_value,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_counts_demolition_dense_material_checkbox_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-demo-dense-checkbox",
        request_overrides={
            "service_type": "demolition",
            "description": "Small controlled cleanup",
            "job_description_customer": "Small controlled cleanup",
            "has_dense_materials": True,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


@pytest.mark.parametrize(
    "request_overrides",
    [
        {"access_difficulty": "difficult"},
        {"floor_count": 2},
        {"basement_or_inside_removal": True},
        {"stairs_count": 1},
    ],
)
def test_owner_review_counts_structured_demolition_access_risk_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    request_overrides: dict[str, Any],
) -> None:
    _seed_quote(
        "q-owner-demo-access",
        request_overrides={
            "service_type": "demolition",
            "description": "Small controlled cleanup",
            "job_description_customer": "Small controlled cleanup",
            **request_overrides,
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


def test_owner_review_counts_shingle_demolition_text_without_recompute(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_quote(
        "q-owner-demo-shingles",
        request_overrides={
            "service_type": "demolition",
            "description": "Wet roof shingles tear-off",
            "job_description_customer": "Wet roof shingles tear-off",
        },
    )

    def fail_pricing(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review read model must not call calculate_quote")

    def fail_advisory(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("owner review count should use SQL signals, not advisory recompute")

    monkeypatch.setattr(quote_engine, "calculate_quote", fail_pricing)
    monkeypatch.setattr(quote_risk_scoring, "build_quote_risk_advisory", fail_advisory)

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["owner_review"] == 1


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
    assert resp.json()["counts"]["completed_missing_costs"] == 1


def test_completed_job_with_core_costing_including_zero_costs_is_not_marked_missing(
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
            "actual_labor_cost_cad": 0,
            "actual_disposal_cost_cad": 0,
            "actual_fuel_cost_cad": 0,
            "actual_other_costs_cad": 0,
            "final_amount_collected_cad": 260.0,
            "payment_status": "paid_in_full",
            "job_profit_status": "profitable",
        },
    )

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["completed_missing_costs"] == 0


def test_stale_pending_estimates_beyond_display_cap_are_counted(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    total_stale = 12
    for index in range(total_stale):
        _seed_quote(
            f"q-stale-{index:05d}",
            created_at=f"2000-01-{(index % 28) + 1:02d}T09:00:00",
        )
    _seed_quote("q-expired-stale", created_at="2000-01-01T09:00:00", admin_status="expired")

    resp = client.get("/admin/api/ops-queue", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["counts"]["stale_quotes"] == total_stale
    assert _cards(resp.json())["stale_quotes"]["count"] == total_stale
