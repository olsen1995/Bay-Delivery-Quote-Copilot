from __future__ import annotations

import base64
from datetime import date, timedelta
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app import storage
from app.main import app
from app.services import booking_notification_service


FUTURE_BOOKING_DATE = (date.today() + timedelta(days=1)).isoformat()
NOTIFICATION_ENV_VARS = (
    "BOOKING_REQUEST_NOTIFICATIONS_ENABLED",
    "BOOKING_NOTIFICATION_EMAIL_TO",
    "BOOKING_NOTIFICATION_EMAIL_FROM",
    "BOOKING_NOTIFICATION_SMTP_HOST",
    "BOOKING_NOTIFICATION_SMTP_PORT",
    "BOOKING_NOTIFICATION_SMTP_USERNAME",
    "BOOKING_NOTIFICATION_SMTP_PASSWORD",
    "BOOKING_NOTIFICATION_SMTP_STARTTLS",
    "BOOKING_NOTIFICATION_EMAIL_REPLY_TO",
    "APP_BASE_URL",
)


@pytest.fixture(autouse=True)
def isolated_db_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_db_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "booking-notifications.sqlite3"
    storage.init_db()
    storage._TABLE_COL_CACHE.clear()

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    for env_name in NOTIFICATION_ENV_VARS:
        monkeypatch.delenv(env_name, raising=False)

    try:
        yield
    finally:
        storage.DB_PATH = original_db_path
        storage._TABLE_COL_CACHE.clear()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _enable_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKING_REQUEST_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("BOOKING_NOTIFICATION_EMAIL_TO", "ops@baydelivery.test")
    monkeypatch.setenv("BOOKING_NOTIFICATION_EMAIL_FROM", "site@baydelivery.test")
    monkeypatch.setenv("BOOKING_NOTIFICATION_SMTP_HOST", "smtp.baydelivery.test")
    monkeypatch.setenv("BOOKING_NOTIFICATION_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("BOOKING_NOTIFICATION_SMTP_PASSWORD", "super-secret-password")
    monkeypatch.setenv("APP_BASE_URL", "https://bay-delivery-quote-copilot.onrender.com")


def _quote_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer_name": "Austin Test Customer",
        "customer_phone": "(705) 555-0101",
        "job_address": "123 Main St",
        "description": "Remove a couch and boxes",
        "service_type": "haul_away",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "trailer_fill_estimate": "under_quarter",
        "pickup_address": "10 Pickup Rd",
        "dropoff_address": "20 Dropoff Ave",
    }
    payload.update(overrides)
    return payload


def _calculate_quote(client: TestClient) -> dict[str, object]:
    response = client.post("/quote/calculate", json=_quote_payload())
    assert response.status_code == 200
    return response.json()


def _accept_quote(client: TestClient, quote: dict[str, object]) -> dict[str, object]:
    response = client.post(
        f"/quote/{quote['quote_id']}/decision",
        json={"action": "accept", "accept_token": quote["accept_token"]},
    )
    assert response.status_code == 200
    return response.json()


def _submit_booking(
    client: TestClient,
    quote_id: str,
    booking_token: str,
    *,
    notes: str = "Please call when outside.",
) -> dict[str, object]:
    response = client.post(
        f"/quote/{quote_id}/booking",
        json={
            "booking_token": booking_token,
            "requested_job_date": FUTURE_BOOKING_DATE,
            "requested_time_window": "morning",
            "notes": notes,
        },
    )
    assert response.status_code == 200
    return response.json()


def _seed_customer_accepted_request() -> str:
    storage.save_quote_request(
        {
            "request_id": "req-admin-no-notify",
            "created_at": "2026-05-19T10:00:00",
            "status": "customer_accepted",
            "quote_id": "quote-admin-no-notify",
            "customer_name": "Admin Test",
            "customer_phone": "(705) 555-0101",
            "job_address": "Admin St",
            "job_description_customer": "desc",
            "job_description_internal": "desc",
            "service_type": "haul_away",
            "cash_total_cad": 100.0,
            "emt_total_cad": 113.0,
            "request_json": {"service_type": "haul_away"},
            "notes": "admin seeded",
            "requested_job_date": FUTURE_BOOKING_DATE,
            "requested_time_window": "morning",
            "customer_accepted_at": "2026-05-19T10:00:00",
            "admin_approved_at": None,
            "accept_token": "accept-token",
            "booking_token": "booking-token",
            "booking_token_created_at": "2026-05-19T10:00:00",
        }
    )
    return "req-admin-no-notify"


def test_booking_submission_sends_one_internal_notification_and_dedupes_retry(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_notifications(monkeypatch)
    sent_messages: list[dict[str, str]] = []

    def fake_send(config, subject: str, body: str) -> None:
        sent_messages.append({"to": config.email_to, "subject": subject, "body": body})

    monkeypatch.setattr(booking_notification_service, "_send_smtp_email", fake_send)

    quote = _calculate_quote(client)
    accepted = _accept_quote(client, quote)

    assert storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted") is None

    first = _submit_booking(client, str(quote["quote_id"]), str(accepted["booking_token"]))
    second = _submit_booking(
        client,
        str(quote["quote_id"]),
        str(accepted["booking_token"]),
        notes="Retry should not send a second email.",
    )

    assert first == {"ok": True, "request_id": accepted["request_id"]}
    assert second == first
    assert len(sent_messages) == 1
    attempt = storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted")
    assert attempt is not None
    assert attempt["status"] == "sent"
    assert attempt["attempt_count"] == 1
    assert attempt["recipient"] == "ops@baydelivery.test"


def test_non_booking_routes_do_not_send_or_record_notification(
    client: TestClient,
    admin_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_notifications(monkeypatch)
    sent_messages: list[str] = []
    monkeypatch.setattr(
        booking_notification_service,
        "_send_smtp_email",
        lambda _config, _subject, _body: sent_messages.append(_subject),
    )

    quote = _calculate_quote(client)
    view_response = client.get(
        f"/quote/{quote['quote_id']}/view",
        headers={"Authorization": f"Bearer {quote['accept_token']}"},
    )
    accepted = _accept_quote(client, quote)
    client.get("/admin/api/quote-requests", headers=admin_headers)
    request_id = _seed_customer_accepted_request()
    followup_response = client.post(
        f"/admin/api/quote-requests/{request_id}/followup-status",
        headers=admin_headers,
        json={"followup_status": "needs_followup"},
    )
    decision_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=admin_headers,
        json={"action": "approve"},
    )

    assert view_response.status_code == 200
    assert followup_response.status_code == 200
    assert decision_response.status_code == 200
    assert sent_messages == []
    assert storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted") is None
    assert storage.list_notification_attempts(limit=10) == []


def test_disabled_notifications_skip_without_breaking_booking_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_messages: list[str] = []
    monkeypatch.setattr(
        booking_notification_service,
        "_send_smtp_email",
        lambda _config, _subject, _body: sent_messages.append(_subject),
    )
    quote = _calculate_quote(client)
    accepted = _accept_quote(client, quote)

    result = _submit_booking(client, str(quote["quote_id"]), str(accepted["booking_token"]))

    assert result == {"ok": True, "request_id": accepted["request_id"]}
    assert sent_messages == []
    attempt = storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted")
    assert attempt is not None
    assert attempt["status"] == "skipped"
    assert attempt["last_error"] == "notifications disabled"


def test_missing_smtp_config_skips_safely_without_sending(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOKING_REQUEST_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("BOOKING_NOTIFICATION_SMTP_PASSWORD", "super-secret-password")
    sent_messages: list[str] = []
    monkeypatch.setattr(
        booking_notification_service,
        "_send_smtp_email",
        lambda _config, _subject, _body: sent_messages.append(_subject),
    )
    quote = _calculate_quote(client)
    accepted = _accept_quote(client, quote)

    result = _submit_booking(client, str(quote["quote_id"]), str(accepted["booking_token"]))

    assert result == {"ok": True, "request_id": accepted["request_id"]}
    assert sent_messages == []
    attempt = storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted")
    assert attempt is not None
    assert attempt["status"] == "skipped"
    assert "missing notification config" in str(attempt["last_error"])
    assert "super-secret-password" not in str(attempt["last_error"])


def test_smtp_failure_is_sanitized_and_does_not_break_booking_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_notifications(monkeypatch)
    quote = _calculate_quote(client)
    accepted = _accept_quote(client, quote)

    def fake_send(_config, _subject: str, _body: str) -> None:
        raise RuntimeError("SMTP exploded with password super-secret-password")

    monkeypatch.setattr(booking_notification_service, "_send_smtp_email", fake_send)

    result = _submit_booking(client, str(quote["quote_id"]), str(accepted["booking_token"]))

    assert result == {"ok": True, "request_id": accepted["request_id"]}
    attempt = storage.get_notification_attempt(accepted["request_id"], "customer_booking_submitted")
    assert attempt is not None
    assert attempt["status"] == "failed"
    assert attempt["attempt_count"] == 1
    assert "RuntimeError" in str(attempt["last_error"])
    assert "super-secret-password" not in str(attempt["last_error"])


def test_email_body_contains_operator_fields_without_customer_promise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_notifications(monkeypatch)
    request_record = {
        "request_id": "req-email-body",
        "quote_id": "quote-email-body",
        "customer_name": "Austin Test Customer",
        "customer_phone": "(705) 555-0101",
        "service_type": "haul_away",
        "job_address": "123 Main St",
        "request_json": {"pickup_address": "10 Pickup Rd", "dropoff_address": "20 Dropoff Ave"},
        "requested_job_date": "2026-05-21",
        "requested_time_window": "morning",
        "cash_total_cad": 100.0,
        "emt_total_cad": 113.0,
        "notes": "Please call when outside.",
    }

    subject, body = booking_notification_service.compose_booking_notification_email(request_record)

    assert subject == "New Bay Delivery booking request: Austin Test Customer (req-email-body)"
    for expected in (
        "Austin Test Customer",
        "(705) 555-0101",
        "haul_away",
        "123 Main St",
        "10 Pickup Rd",
        "20 Dropoff Ave",
        "2026-05-21",
        "morning",
        "$100.00",
        "$113.00",
        "Please call when outside.",
        "https://bay-delivery-quote-copilot.onrender.com/admin",
        "quote-email-body",
        "req-email-body",
    ):
        assert expected in body

    lower_body = body.lower()
    assert "confirmation" not in lower_body
    assert "calendar" not in lower_body
    assert "customer was contacted" not in lower_body


def test_notification_attempts_survive_backup_restore(tmp_path: Path) -> None:
    assert "notification_attempts" in storage.KNOWN_TABLES
    reserved = storage.reserve_notification_attempt(
        request_id="req-backup-notification",
        event_type="customer_booking_submitted",
        quote_id="quote-backup-notification",
        channel="email",
        recipient="ops@baydelivery.test",
        created_at="2026-05-19T10:00:00",
    )
    assert reserved is not None
    storage.mark_notification_attempt_sent(
        "req-backup-notification",
        "customer_booking_submitted",
        sent_at="2026-05-19T10:01:00",
    )

    payload = storage.export_db_to_json()

    assert len(payload["tables"]["notification_attempts"]) == 1
    assert payload["tables"]["notification_attempts"][0]["status"] == "sent"

    storage.DB_PATH = tmp_path / "restored-notifications.sqlite3"
    storage.init_db()
    result = storage.import_db_from_json(payload)
    restored = storage.get_notification_attempt("req-backup-notification", "customer_booking_submitted")

    assert result["ok"] is True
    assert result["restored"]["notification_attempts"] == 1
    assert restored is not None
    assert restored["status"] == "sent"
    assert restored["sent_at"] == "2026-05-19T10:01:00"
