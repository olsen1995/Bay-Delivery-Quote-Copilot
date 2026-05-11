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
    scheduled_end: str | None = None,
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
    assert set(payload) == {"generated_at", "counts", "cards"}
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
    total_records = 12
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
    assert _cards(first.json()) == _cards(second.json())
    assert first.json()["counts"]["accepted_not_booked"] == total_records
    assert storage.list_quote_requests(limit=50, include_followup_status=True) == before_requests
    assert storage.list_jobs(limit=50) == before_jobs
    assert storage.list_quotes(limit=50) == before_quotes


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
