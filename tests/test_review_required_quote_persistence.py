from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture(autouse=True)
def restore_storage_path() -> None:
    original_db_path = storage.DB_PATH
    storage._TABLE_COL_CACHE.clear()
    try:
        yield
    finally:
        storage.DB_PATH = original_db_path
        storage._TABLE_COL_CACHE.clear()


def _create_total_cad_schema(tmp_path: Path, *, total_not_null: bool) -> Path:
    db_path = tmp_path / ("quotes-total-not-null.sqlite3" if total_not_null else "quotes-total-nullable.sqlite3")
    total_constraint = "REAL NOT NULL" if total_not_null else "REAL"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE quotes (
                quote_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                job_type TEXT NOT NULL,
                total_cad {total_constraint},
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    storage.DB_PATH = db_path
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    return db_path


def _public_route_payload(
    service_type: str,
    *,
    pickup_address: str,
    dropoff_address: str,
) -> dict[str, Any]:
    return {
        "customer_name": "Persistence Route Tester",
        "customer_phone": "705-555-0184",
        "job_address": pickup_address,
        "job_description_customer": "Move a couch and table",
        "description": "Move a couch and table",
        "service_type": service_type,
        "payment_method": "cash",
        "pickup_address": pickup_address,
        "dropoff_address": dropoff_address,
        "estimated_hours": 4.0 if service_type == "small_move" else 1.0,
        "crew_size": 2 if service_type == "small_move" else 1,
        "garbage_bag_count": 0,
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": "in_town",
    }


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Sec-Fetch-Site": "same-origin",
    }


def _quote_row(db_path: Path, quote_id: str) -> sqlite3.Row:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT *, typeof(total_cad) AS total_cad_type FROM quotes WHERE quote_id = ?",
            (quote_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return row


def _exported_quote(quote_id: str) -> dict[str, Any]:
    payload = storage.export_db_to_json()
    return next(row for row in payload["tables"]["quotes"] if row["quote_id"] == quote_id)


def _linked_authoritative_backup(tmp_path: Path) -> tuple[dict[str, Any], str, str]:
    storage.DB_PATH = tmp_path / "linked-authoritative-source.sqlite3"
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    quote_id = "restored-linked-quote"
    request_id = "restored-linked-request"
    created_at = "2026-07-31T12:00:00+00:00"
    request_payload = {
        "customer_name": "Restore Safety Tester",
        "customer_phone": "705-555-0194",
        "job_address": "123 Main Street, North Bay, ON",
        "service_type": "small_move",
        "route_classification": {
            "status": "authoritative",
            "source": "backend_address_locality_v1",
            "reason": "both_locations_north_bay",
            "travel_zone": "in_town",
        },
    }
    response_payload = {
        "status": "authoritative",
        "authoritative": True,
        "cash_total_cad": 275.0,
        "emt_total_cad": 310.75,
        "job_description_internal": "Restore workflow safety test",
        "disclaimer": "test",
    }
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": request_payload,
            "response": response_payload,
            "accept_token": "source-accept-token",
        }
    )
    storage.save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": "Restore Safety Tester",
            "customer_phone": "705-555-0194",
            "job_address": "123 Main Street, North Bay, ON",
            "job_description_customer": "Move a couch and table",
            "job_description_internal": "Restore workflow safety test",
            "service_type": "small_move",
            "cash_total_cad": 275.0,
            "emt_total_cad": 310.75,
            "request_json": request_payload,
            "notes": None,
            "requested_job_date": None,
            "requested_time_window": None,
            "customer_accepted_at": created_at,
            "admin_approved_at": None,
            "accept_token": "source-accept-token",
            "booking_token": "source-booking-token",
            "booking_token_created_at": created_at,
        }
    )
    return storage.export_db_to_json(), quote_id, request_id


@pytest.mark.parametrize("total_not_null", [False, True], ids=["nullable", "legacy-not-null"])
@pytest.mark.parametrize("service_type", ["small_move", "item_delivery"])
def test_review_required_quote_has_no_application_visible_total_across_supported_schemas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    total_not_null: bool,
    service_type: str,
) -> None:
    db_path = _create_total_cad_schema(tmp_path, total_not_null=total_not_null)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with TestClient(app) as client:
        response = client.post(
            "/quote/calculate",
            json=_public_route_payload(
                service_type,
                pickup_address="123 Main Street, North Bay, ON",
                dropoff_address="456 Elm Street, Sudbury, ON",
            ),
        )
        assert response.status_code == 202
        quote = response.json()
        quote_id = quote["quote_id"]
        assert quote["status"] == "review_required"
        assert quote["authoritative"] is False
        assert "accept_token" not in quote
        assert "total_cad" not in quote
        assert "total_cad" not in quote["response"]

        detail = storage.get_quote_record(quote_id)
        listed = next(item for item in storage.list_quotes() if item["quote_id"] == quote_id)
        admin_list = client.get("/admin/api/quotes", headers=_admin_headers())

    assert detail is not None
    for application_record in (detail, listed):
        assert application_record["status"] == "review_required"
        assert application_record["authoritative"] is False
        assert application_record["accept_token"] is None
        assert "total_cad" not in application_record

    assert admin_list.status_code == 200
    admin_quote = next(item for item in admin_list.json()["items"] if item["quote_id"] == quote_id)
    assert admin_quote["status"] == "review_required"
    assert admin_quote["admin_status"] == "pending"
    assert admin_quote["authoritative"] is False
    assert "total_cad" not in admin_quote

    raw = _quote_row(db_path, quote_id)
    if total_not_null:
        assert raw["total_cad_type"] == "text"
        assert not isinstance(raw["total_cad"], (int, float))
    else:
        assert raw["total_cad"] is None
        assert raw["total_cad_type"] == "null"
    assert raw["accept_token"] is None

    exported = _exported_quote(quote_id)
    assert exported["total_cad"] is None
    assert exported["accept_token"] is None


@pytest.mark.parametrize("total_not_null", [False, True], ids=["nullable", "legacy-not-null"])
def test_authoritative_quote_retains_real_total_across_supported_schemas(
    tmp_path: Path,
    total_not_null: bool,
) -> None:
    db_path = _create_total_cad_schema(tmp_path, total_not_null=total_not_null)

    with TestClient(app) as client:
        response = client.post(
            "/quote/calculate",
            json=_public_route_payload(
                "small_move",
                pickup_address="123 Main Street, North Bay, ON P1A 1A1",
                dropoff_address="456 Oak Avenue, North Bay, Ontario, P1B 2B2, Canada",
            ),
        )

    assert response.status_code == 200
    quote = response.json()
    expected_total = quote["response"]["cash_total_cad"]
    assert expected_total > 0

    raw = _quote_row(db_path, quote["quote_id"])
    assert raw["total_cad"] == expected_total
    assert raw["total_cad_type"] == "real"

    detail = storage.get_quote_record(quote["quote_id"])
    assert detail is not None
    assert detail["status"] == "authoritative"
    assert detail["authoritative"] is True
    assert detail["admin_status"] == "pending"
    assert detail["total_cad"] == expected_total

    listed = next(item for item in storage.list_quotes() if item["quote_id"] == quote["quote_id"])
    assert listed["admin_status"] == "pending"
    assert listed["total_cad"] == expected_total
    assert _exported_quote(quote["quote_id"])["total_cad"] == expected_total


def test_existing_legacy_zero_review_total_is_suppressed_without_mutating_database(tmp_path: Path) -> None:
    db_path = _create_total_cad_schema(tmp_path, total_not_null=True)
    request = {
        "service_type": "small_move",
        "route_classification": {"status": "review_required", "travel_zone": None},
    }
    response = {"status": "review_required", "authoritative": False}
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO quotes
                (quote_id, created_at, job_type, total_cad, request_json, response_json, accept_token, admin_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-zero-review",
                "2026-07-23T01:57:26+00:00",
                "small_move",
                0.0,
                json.dumps(request),
                json.dumps(response),
                None,
                "pending",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    detail = storage.get_quote_record("legacy-zero-review")
    listed = next(item for item in storage.list_quotes() if item["quote_id"] == "legacy-zero-review")
    exported = _exported_quote("legacy-zero-review")

    assert detail is not None
    for application_record in (detail, listed):
        assert application_record["status"] == "review_required"
        assert application_record["authoritative"] is False
        assert "total_cad" not in application_record
    assert exported["total_cad"] is None

    raw = _quote_row(db_path, "legacy-zero-review")
    assert raw["total_cad"] == 0.0
    assert raw["total_cad_type"] == "real"


def test_review_required_backup_round_trip_preserves_no_price_or_accept_token_in_legacy_schema(
    tmp_path: Path,
) -> None:
    db_path = _create_total_cad_schema(tmp_path, total_not_null=True)

    with TestClient(app) as client:
        response = client.post(
            "/quote/calculate",
            json=_public_route_payload(
                "item_delivery",
                pickup_address="North Bay",
                dropoff_address="Sudbury",
            ),
        )
    assert response.status_code == 202
    quote_id = response.json()["quote_id"]

    backup = storage.export_db_to_json()
    exported = next(row for row in backup["tables"]["quotes"] if row["quote_id"] == quote_id)
    assert exported["total_cad"] is None
    assert exported["accept_token"] is None

    restored = storage.import_db_from_json(backup)

    assert restored["restored"]["quotes"] == 1
    detail = storage.get_quote_record(quote_id)
    assert detail is not None
    assert detail["status"] == "review_required"
    assert detail["authoritative"] is False
    assert detail["accept_token"] is None
    assert "total_cad" not in detail

    raw = _quote_row(db_path, quote_id)
    assert raw["total_cad_type"] == "text"
    assert not isinstance(raw["total_cad"], (int, float))
    assert raw["accept_token"] is None


def test_restore_rejects_review_required_quote_with_linked_workflow_before_token_rotation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    backup, quote_id, request_id = _linked_authoritative_backup(tmp_path)
    quote_row = next(row for row in backup["tables"]["quotes"] if row["quote_id"] == quote_id)
    request_row = next(
        row for row in backup["tables"]["quote_requests"] if row["request_id"] == request_id
    )
    quote_row["request_json"]["route_classification"].update(
        {"status": "review_required", "travel_zone": None}
    )
    quote_row["response_json"] = {"status": "review_required", "authoritative": False}
    quote_row["accept_token"] = "stale-review-accept-token"
    if "total_cad" in quote_row:
        quote_row["total_cad"] = 0.0
    request_row["accept_token"] = "stale-review-accept-token"
    request_row["booking_token"] = "stale-review-booking-token"

    storage.DB_PATH = tmp_path / "rejected-review-workflow-target.sqlite3"
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    storage.save_quote(
        {
            "quote_id": "existing-target-quote",
            "created_at": "2026-07-31T11:00:00+00:00",
            "request": {"service_type": "haul_away"},
            "response": {"cash_total_cad": 100.0, "emt_total_cad": 113.0},
            "accept_token": "existing-target-token",
        }
    )

    token_rotation_calls: list[bool] = []

    def fail_if_token_rotation_runs() -> str:
        token_rotation_calls.append(True)
        raise AssertionError("inconsistent review-only backups must fail before token rotation")

    monkeypatch.setattr(storage, "_fresh_workflow_token", fail_if_token_rotation_runs)

    with pytest.raises(ValueError, match="review-required quote.*linked workflow"):
        storage.import_db_from_json(backup)

    assert token_rotation_calls == []
    assert storage.get_quote_record("existing-target-quote") is not None
    assert storage.get_quote_record(quote_id) is None
    assert storage.get_quote_request_record(request_id) is None
    assert storage.get_job_by_quote_id(quote_id) is None

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    with TestClient(app) as client:
        booking = client.post(
            f"/quote/{quote_id}/booking",
            json={
                "booking_token": "stale-review-booking-token",
                "requested_job_date": "2099-01-01",
                "requested_time_window": "morning",
                "notes": None,
            },
        )
        approval = client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=_admin_headers(),
            json={"action": "approve"},
        )

    assert booking.status_code == 404
    assert approval.status_code == 404
    assert storage.get_job_by_quote_id(quote_id) is None


def test_authoritative_quote_with_linked_workflow_restores_and_rotates_tokens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    backup, quote_id, request_id = _linked_authoritative_backup(tmp_path)

    storage.DB_PATH = tmp_path / "authoritative-workflow-target.sqlite3"
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    result = storage.import_db_from_json(backup)

    restored_quote = storage.get_quote_record(quote_id)
    restored_request = storage.get_quote_request_record(request_id)
    assert result["restored"]["quotes"] == 1
    assert result["restored"]["quote_requests"] == 1
    assert restored_quote is not None
    assert restored_request is not None
    assert restored_quote["status"] == "authoritative"
    assert restored_quote["accept_token"] not in {
        None,
        storage.BACKUP_TOKEN_ROTATION_PLACEHOLDER,
        "source-accept-token",
    }
    assert restored_request["accept_token"] == restored_quote["accept_token"]
    assert restored_request["booking_token"] not in {
        None,
        storage.BACKUP_TOKEN_ROTATION_PLACEHOLDER,
        "source-booking-token",
    }

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    with TestClient(app) as client:
        booking = client.post(
            f"/quote/{quote_id}/booking",
            json={
                "booking_token": restored_request["booking_token"],
                "requested_job_date": "2099-01-01",
                "requested_time_window": "morning",
                "notes": None,
            },
        )
        approval = client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=_admin_headers(),
            json={"action": "approve"},
        )

    assert booking.status_code == 200
    assert approval.status_code == 200
    assert approval.json()["request"]["status"] == "admin_approved"
    assert storage.get_job_by_quote_id(quote_id) is not None
