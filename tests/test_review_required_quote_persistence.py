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
    return {"Authorization": f"Basic {token}"}


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
    assert detail["total_cad"] == expected_total

    listed = next(item for item in storage.list_quotes() if item["quote_id"] == quote["quote_id"])
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
