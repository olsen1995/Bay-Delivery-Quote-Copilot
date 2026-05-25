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
    db_path = tmp_path / "admin-followup-status.sqlite3"
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


def _base_quote_request(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "request_id": "req-followup-1",
        "created_at": "2026-04-27T09:00:00",
        "status": "customer_accepted",
        "quote_id": "quote-followup-1",
        "customer_name": "Followup Customer",
        "customer_phone": "705-555-0101",
        "job_address": "123 Lead St",
        "job_description_customer": "Small pickup",
        "job_description_internal": "Small pickup",
        "service_type": "haul_away",
        "cash_total_cad": 120.0,
        "emt_total_cad": 135.6,
        "request_json": {"service_type": "haul_away"},
        "notes": None,
        "requested_job_date": None,
        "requested_time_window": None,
        "customer_accepted_at": "2026-04-27T09:01:00",
        "admin_approved_at": None,
        "accept_token": "accept-followup",
        "booking_token": "booking-followup",
        "booking_token_created_at": "2026-04-27T09:01:00",
    }
    record.update(overrides)
    return record


def test_init_db_adds_nullable_followup_status_to_legacy_quote_requests_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-followup.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    monkeypatch.delenv("BAYDELIVERY_DB_PATH", raising=False)
    storage._TABLE_COL_CACHE.clear()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE quote_requests (
                request_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                job_address TEXT,
                job_description_customer TEXT,
                job_description_internal TEXT,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                notes TEXT,
                requested_job_date TEXT,
                requested_time_window TEXT,
                customer_accepted_at TEXT,
                admin_approved_at TEXT,
                accept_token TEXT,
                booking_token TEXT,
                booking_token_created_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO quote_requests
            (request_id, created_at, status, quote_id, customer_name, customer_phone, job_address,
             job_description_customer, job_description_internal, service_type, cash_total_cad,
             emt_total_cad, request_json, notes, requested_job_date, requested_time_window,
             customer_accepted_at, admin_approved_at, accept_token, booking_token, booking_token_created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "req-legacy-followup",
                "2026-04-27T09:00:00",
                "customer_accepted",
                "quote-legacy-followup",
                "Legacy Customer",
                "705-555-0101",
                "Legacy St",
                "Legacy desc",
                "Legacy desc",
                "haul_away",
                120.0,
                135.6,
                "{}",
                None,
                None,
                None,
                "2026-04-27T09:01:00",
                None,
                "accept-legacy",
                "booking-legacy",
                "2026-04-27T09:01:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    storage.init_db()
    record = storage.get_quote_request_record("req-legacy-followup")
    assert record is not None
    assert record["followup_status"] is None

    conn = storage._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE quote_requests SET followup_status = ? WHERE request_id = ?",
                ("call_again_every_day", "req-legacy-followup"),
            )
    finally:
        conn.close()


def test_followup_status_survives_export_import_and_stays_out_of_public_shape(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    storage.save_quote_request(_base_quote_request(followup_status="waiting_on_customer"))

    public_record = storage.get_quote_request("req-followup-1")
    listed_public = storage.list_quote_requests(limit=10)
    internal_record = storage.get_quote_request_record("req-followup-1")

    assert public_record is not None
    assert internal_record is not None
    assert "followup_status" not in public_record
    assert "followup_status" not in listed_public[0]
    assert internal_record["followup_status"] == "waiting_on_customer"

    payload = storage.export_db_to_json()
    exported_request = next(row for row in payload["tables"]["quote_requests"] if row["request_id"] == "req-followup-1")
    assert exported_request["followup_status"] == "waiting_on_customer"

    monkeypatch.delenv("BAYDELIVERY_DB_PATH", raising=False)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "followup-restored.sqlite3")
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    result = storage.import_db_from_json(payload)
    restored = storage.get_quote_request_record("req-followup-1")

    assert result["ok"] is True
    assert restored is not None
    assert restored["followup_status"] == "waiting_on_customer"


def test_admin_followup_status_update_requires_auth(client: TestClient, isolated_db: Path) -> None:
    storage.save_quote_request(_base_quote_request())

    response = client.post(
        "/admin/api/quote-requests/req-followup-1/followup-status",
        json={"followup_status": "contacted"},
    )

    assert response.status_code == 401
    assert storage.get_quote_request_record("req-followup-1")["followup_status"] is None


def test_admin_followup_status_update_accepts_valid_values_and_clear(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    storage.save_quote_request(_base_quote_request())

    response = client.post(
        "/admin/api/quote-requests/req-followup-1/followup-status",
        headers=admin_headers,
        json={"followup_status": "contacted"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request"]["followup_status"] == "contacted"
    assert payload["request"]["status"] == "customer_accepted"
    assert storage.get_quote_request_record("req-followup-1")["followup_status"] == "contacted"

    audit_entry = storage.list_admin_audit_log(limit=1)[0]
    assert audit_entry["action_type"] == "update_followup_status"
    assert audit_entry["entity_type"] == "quote_request"
    assert audit_entry["record_id"] == "req-followup-1"
    assert audit_entry["success"] == 1

    list_response = client.get("/admin/api/quote-requests", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["followup_status"] == "contacted"

    clear_response = client.post(
        "/admin/api/quote-requests/req-followup-1/followup-status",
        headers=admin_headers,
        json={"followup_status": None},
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["request"]["followup_status"] is None
    assert storage.get_quote_request_record("req-followup-1")["status"] == "customer_accepted"


def test_admin_followup_status_update_rejects_invalid_values(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    storage.save_quote_request(_base_quote_request())

    response = client.post(
        "/admin/api/quote-requests/req-followup-1/followup-status",
        headers=admin_headers,
        json={"followup_status": "call_again_every_day"},
    )

    assert response.status_code == 422
    assert storage.get_quote_request_record("req-followup-1")["followup_status"] is None


def test_admin_followup_status_update_404_for_missing_request(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    response = client.post(
        "/admin/api/quote-requests/missing-request/followup-status",
        headers=admin_headers,
        json={"followup_status": "needs_followup"},
    )

    assert response.status_code == 404
