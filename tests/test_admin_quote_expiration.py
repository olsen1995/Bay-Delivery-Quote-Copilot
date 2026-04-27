import base64
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "admin-quote-expiration.sqlite3"
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


def _seed_quote(quote_id: str, *, created_at: str = "2026-04-26T10:00:00") -> None:
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": created_at,
            "request": {
                "customer_name": "Estimate Customer",
                "customer_phone": "705-555-0101",
                "job_address": "123 Estimate St",
                "job_description_customer": "Stale test estimate",
                "service_type": "dump_run",
            },
            "response": {
                "job_description_internal": "Internal estimate details",
                "cash_total_cad": 120.0,
                "emt_total_cad": 135.6,
            },
            "accept_token": f"accept-{quote_id}",
        }
    )


def _seed_quote_request(quote_id: str, status: str) -> None:
    storage.save_quote_request(
        {
            "request_id": f"req-{quote_id}",
            "created_at": "2026-04-26T10:05:00",
            "status": status,
            "quote_id": quote_id,
            "customer_name": "Estimate Customer",
            "customer_phone": "705-555-0101",
            "job_address": "123 Estimate St",
            "job_description_customer": "Stale test estimate",
            "job_description_internal": "Internal estimate details",
            "service_type": "dump_run",
            "cash_total_cad": 120.0,
            "emt_total_cad": 135.6,
            "request_json": {"service_type": "dump_run"},
            "notes": None,
            "requested_job_date": None,
            "requested_time_window": None,
            "customer_accepted_at": None,
            "admin_approved_at": None,
            "accept_token": f"accept-{quote_id}",
            "booking_token": None,
            "booking_token_created_at": None,
        }
    )


def _quote_ids(items: list[dict[str, Any]]) -> list[str]:
    return [str(item["quote_id"]) for item in items]


def test_admin_expire_quote_requires_auth(client: TestClient, isolated_db: Path) -> None:
    _seed_quote("quote-auth")

    response = client.post("/admin/api/quotes/quote-auth/expire")

    assert response.status_code == 401
    assert storage.get_quote_record("quote-auth")["admin_status"] == "pending"


def test_admin_expire_quote_soft_hides_default_list_and_preserves_history(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _seed_quote("quote-active", created_at="2026-04-26T11:00:00")
    _seed_quote("quote-stale", created_at="2026-04-26T10:00:00")

    response = client.post("/admin/api/quotes/quote-stale/expire", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["quote"]["admin_status"] == "expired"
    assert storage.get_quote_record("quote-stale")["admin_status"] == "expired"
    assert _quote_ids(storage.list_quotes(limit=10)) == ["quote-active"]
    assert set(_quote_ids(storage.list_quotes(limit=10, include_expired=True))) == {"quote-active", "quote-stale"}

    admin_list = client.get("/admin/api/quotes", headers=admin_headers)
    assert admin_list.status_code == 200
    assert _quote_ids(admin_list.json()["items"]) == ["quote-active"]

    audit_entry = storage.list_admin_audit_log(limit=1)[0]
    assert audit_entry["action_type"] == "expire_quote"
    assert audit_entry["entity_type"] == "quote"
    assert audit_entry["record_id"] == "quote-stale"
    assert audit_entry["success"] is True

    backup_payload = storage.export_db_to_json()
    stale_backup = next(row for row in backup_payload["tables"]["quotes"] if row["quote_id"] == "quote-stale")
    assert stale_backup["admin_status"] == "expired"

    restored_path = tmp_path / "restored-admin-quote-expiration.sqlite3"
    monkeypatch.delenv("BAYDELIVERY_DB_PATH", raising=False)
    monkeypatch.setattr(storage, "DB_PATH", restored_path)
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    storage.import_db_from_json(backup_payload)

    assert storage.get_quote_record("quote-stale")["admin_status"] == "expired"
    assert _quote_ids(storage.list_quotes(limit=10)) == ["quote-active"]
    assert set(_quote_ids(storage.list_quotes(limit=10, include_expired=True))) == {"quote-active", "quote-stale"}


def test_legacy_quote_backup_without_admin_status_restores_as_pending(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _seed_quote("quote-legacy-backup")
    backup_payload = storage.export_db_to_json()
    for row in backup_payload["tables"]["quotes"]:
        row.pop("admin_status", None)

    restored_path = tmp_path / "restored-legacy-quote-expiration.sqlite3"
    monkeypatch.delenv("BAYDELIVERY_DB_PATH", raising=False)
    monkeypatch.setattr(storage, "DB_PATH", restored_path)
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    storage.import_db_from_json(backup_payload)

    restored_quote = storage.get_quote_record("quote-legacy-backup")
    assert restored_quote["admin_status"] == "pending"
    assert _quote_ids(storage.list_quotes(limit=10)) == ["quote-legacy-backup"]


@pytest.mark.parametrize("status", ["customer_accepted", "admin_approved"])
def test_admin_expire_quote_rejects_active_request_linked_quotes(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
    status: str,
) -> None:
    _seed_quote(f"quote-{status}")
    _seed_quote_request(f"quote-{status}", status)

    response = client.post(f"/admin/api/quotes/quote-{status}/expire", headers=admin_headers)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Quote has an active accepted or approved request and cannot be marked expired from Recent Estimates."
    }
    assert storage.get_quote_record(f"quote-{status}")["admin_status"] == "pending"
    assert _quote_ids(storage.list_quotes(limit=10)) == [f"quote-{status}"]


def test_admin_expire_quote_allows_customer_pending_request_linked_quote(
    client: TestClient,
    admin_headers: dict[str, str],
    isolated_db: Path,
) -> None:
    _seed_quote("quote-customer-pending")
    _seed_quote_request("quote-customer-pending", "customer_pending")

    response = client.post("/admin/api/quotes/quote-customer-pending/expire", headers=admin_headers)

    assert response.status_code == 200
    assert storage.get_quote_record("quote-customer-pending")["admin_status"] == "expired"
    assert storage.get_quote_request_by_quote_id("quote-customer-pending")["status"] == "customer_pending"
