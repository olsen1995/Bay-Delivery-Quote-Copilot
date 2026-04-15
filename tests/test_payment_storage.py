from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import storage


PUBLIC_QUOTE_REQUEST_KEYS = {
    "request_id",
    "created_at",
    "status",
    "quote_id",
    "customer_name",
    "customer_phone",
    "job_address",
    "job_description_customer",
    "job_description_internal",
    "service_type",
    "cash_total_cad",
    "emt_total_cad",
    "request_json",
    "notes",
    "requested_job_date",
    "requested_time_window",
    "customer_accepted_at",
    "admin_approved_at",
    "accept_token",
    "booking_token",
    "booking_token_created_at",
}


@pytest.fixture(autouse=True)
def restore_db_path() -> None:
    original_db_path = storage.DB_PATH
    try:
        yield
    finally:
        storage.DB_PATH = original_db_path
        storage._TABLE_COL_CACHE.clear()


def _init_tmp_db(tmp_path: Path, name: str = "payments.sqlite3") -> Path:
    db_path = tmp_path / name
    storage.DB_PATH = db_path
    storage.init_db()
    return db_path


def _base_quote_request(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "request_id": "req-payment-1",
        "created_at": "2026-04-15T09:00:00",
        "status": "customer_accepted",
        "quote_id": "quote-payment-1",
        "customer_name": "Test Customer",
        "customer_phone": "(705) 555-0101",
        "job_address": "123 Main St",
        "job_description_customer": "Remove a small load",
        "job_description_internal": "Remove a small load",
        "service_type": "haul_away",
        "cash_total_cad": 100.0,
        "emt_total_cad": 113.0,
        "request_json": {"service_type": "haul_away"},
        "notes": "keep existing flow",
        "requested_job_date": "2026-04-20",
        "requested_time_window": "morning",
        "customer_accepted_at": "2026-04-15T09:05:00",
        "admin_approved_at": None,
        "accept_token": "accept-token",
        "booking_token": "booking-token",
        "booking_token_created_at": "2026-04-15T09:05:00",
        "deposit_required_cad": None,
        "deposit_status": None,
        "deposit_paid_at": None,
        "deposit_refund_status": None,
        "deposit_refunded_at": None,
        "deposit_last_error": None,
    }
    record.update(overrides)
    return record


def test_init_db_creates_payment_groundwork_schema(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    conn = storage._connect()
    try:
        quote_request_cols = {
            row["name"]: row for row in conn.execute("PRAGMA table_info(quote_requests)").fetchall()
        }
        payment_attempt_cols = {
            row["name"]: row for row in conn.execute("PRAGMA table_info(payment_attempts)").fetchall()
        }
        webhook_event_cols = {
            row["name"]: row for row in conn.execute("PRAGMA table_info(webhook_events)").fetchall()
        }
    finally:
        conn.close()

    assert "payment_attempts" in storage.KNOWN_TABLES
    assert "webhook_events" in storage.KNOWN_TABLES
    assert quote_request_cols["deposit_required_cad"]["notnull"] == 0
    assert quote_request_cols["deposit_status"]["notnull"] == 0
    assert quote_request_cols["deposit_paid_at"]["notnull"] == 0
    assert quote_request_cols["deposit_refund_status"]["notnull"] == 0
    assert quote_request_cols["deposit_refunded_at"]["notnull"] == 0
    assert quote_request_cols["deposit_last_error"]["notnull"] == 0
    assert set(payment_attempt_cols) == {
        "payment_attempt_id",
        "request_id",
        "provider",
        "amount_cad",
        "checkout_session_id",
        "payment_intent_id",
        "status",
        "created_at",
        "updated_at",
        "refund_id",
        "last_error",
    }
    assert set(webhook_event_cols) == {
        "provider_event_id",
        "provider",
        "event_type",
        "received_at",
        "processed_at",
        "payload_json",
    }


def test_quote_request_payment_fields_round_trip_without_changing_public_shape(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_quote_request(
        _base_quote_request(
            deposit_required_cad=56.5,
            deposit_status="required",
            deposit_last_error="temporary provider timeout",
        )
    )

    public_record = storage.get_quote_request("req-payment-1")
    internal_record = storage.get_quote_request_record("req-payment-1")

    assert public_record is not None
    assert internal_record is not None
    assert set(public_record.keys()) == PUBLIC_QUOTE_REQUEST_KEYS
    assert "deposit_status" not in public_record
    assert internal_record["deposit_required_cad"] == 56.5
    assert internal_record["deposit_status"] == "required"
    assert internal_record["deposit_last_error"] == "temporary provider timeout"

    updated_public = storage.update_quote_request(
        "req-payment-1",
        notes="customer flow unchanged",
        deposit_status="paid",
        deposit_paid_at="2026-04-15T09:30:00",
    )
    updated_internal = storage.get_quote_request_record("req-payment-1")

    assert updated_public is not None
    assert updated_internal is not None
    assert set(updated_public.keys()) == PUBLIC_QUOTE_REQUEST_KEYS
    assert updated_public["notes"] == "customer flow unchanged"
    assert updated_internal["deposit_required_cad"] == 56.5
    assert updated_internal["deposit_status"] == "paid"
    assert updated_internal["deposit_paid_at"] == "2026-04-15T09:30:00"

    listed_public = storage.list_quote_requests(limit=10)
    assert len(listed_public) == 1
    assert set(listed_public[0].keys()) == PUBLIC_QUOTE_REQUEST_KEYS


def test_quote_request_deposit_status_is_nullable_and_restricted(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_quote_request(_base_quote_request())
    record = storage.get_quote_request_record("req-payment-1")
    assert record is not None
    assert record["deposit_status"] is None

    with pytest.raises(ValueError, match="deposit_status"):
        storage.save_quote_request(_base_quote_request(request_id="req-bad-deposit", deposit_status="queued"))

    conn = storage._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO quote_requests
                (request_id, created_at, status, quote_id, customer_name, customer_phone, job_address,
                 job_description_customer, job_description_internal, service_type, cash_total_cad,
                 emt_total_cad, request_json, deposit_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "req-sql-bad-deposit",
                    "2026-04-15T10:00:00",
                    "customer_accepted",
                    "quote-sql-bad-deposit",
                    "SQL Test",
                    None,
                    "Anywhere",
                    "desc",
                    "desc",
                    "haul_away",
                    100.0,
                    113.0,
                    "{}",
                    "queued",
                ),
            )
    finally:
        conn.close()


def test_init_db_backfills_deposit_columns_on_older_quote_requests_table(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-payment.sqlite3"
    storage.DB_PATH = db_path

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
                "req-legacy",
                "2026-04-15T10:15:00",
                "customer_accepted",
                "quote-legacy",
                "Legacy Customer",
                None,
                "Legacy St",
                "Legacy desc",
                "Legacy desc",
                "haul_away",
                100.0,
                113.0,
                "{}",
                "legacy note",
                None,
                None,
                None,
                None,
                "legacy-accept",
                None,
                None,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    storage.init_db()

    legacy_record = storage.get_quote_request_record("req-legacy")
    assert legacy_record is not None
    assert legacy_record["deposit_required_cad"] is None
    assert legacy_record["deposit_status"] is None
    assert legacy_record["deposit_paid_at"] is None
    assert legacy_record["deposit_refund_status"] is None
    assert legacy_record["deposit_refunded_at"] is None
    assert legacy_record["deposit_last_error"] is None

    conn = storage._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE quote_requests SET deposit_status = ? WHERE request_id = ?",
                ("queued", "req-legacy"),
            )
    finally:
        conn.close()


def test_payment_attempts_round_trip_and_status_validation(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_payment_attempt(
        {
            "payment_attempt_id": "pay-attempt-1",
            "request_id": "req-payment-1",
            "provider": "stripe",
            "amount_cad": 56.5,
            "checkout_session_id": None,
            "payment_intent_id": None,
            "status": "created",
            "created_at": "2026-04-15T09:20:00",
            "updated_at": "2026-04-15T09:20:00",
            "refund_id": None,
            "last_error": None,
        }
    )

    attempt = storage.get_payment_attempt("pay-attempt-1")
    assert attempt is not None
    assert attempt["status"] == "created"
    assert attempt["amount_cad"] == 56.5

    updated = storage.update_payment_attempt(
        "pay-attempt-1",
        status="pending",
        checkout_session_id="cs_test_123",
        updated_at="2026-04-15T09:21:00",
    )
    assert updated is not None
    assert updated["status"] == "pending"
    assert updated["checkout_session_id"] == "cs_test_123"

    items = storage.list_payment_attempts_for_request("req-payment-1")
    assert len(items) == 1
    assert items[0]["payment_attempt_id"] == "pay-attempt-1"

    with pytest.raises(ValueError, match="payment_attempt.status"):
        storage.save_payment_attempt(
            {
                "payment_attempt_id": "pay-attempt-bad",
                "request_id": "req-payment-1",
                "provider": "stripe",
                "amount_cad": 56.5,
                "checkout_session_id": None,
                "payment_intent_id": None,
                "status": "processing",
                "created_at": "2026-04-15T09:20:00",
                "updated_at": "2026-04-15T09:20:00",
                "refund_id": None,
                "last_error": None,
            }
        )

    conn = storage._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO payment_attempts
                (payment_attempt_id, request_id, provider, amount_cad, checkout_session_id,
                 payment_intent_id, status, created_at, updated_at, refund_id, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "pay-attempt-sql-bad",
                    "req-payment-1",
                    "stripe",
                    56.5,
                    None,
                    None,
                    "processing",
                    "2026-04-15T09:20:00",
                    "2026-04-15T09:20:00",
                    None,
                    None,
                ),
            )
    finally:
        conn.close()


def test_webhook_events_round_trip_and_uniqueness(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_webhook_event(
        {
            "provider_event_id": "evt_123",
            "provider": "stripe",
            "event_type": "checkout.session.completed",
            "received_at": "2026-04-15T09:40:00",
            "processed_at": None,
            "payload_json": {"id": "evt_123", "type": "checkout.session.completed"},
        }
    )

    event = storage.get_webhook_event("stripe", "evt_123")
    assert event is not None
    assert event["payload_json"]["id"] == "evt_123"
    assert event["processed_at"] is None

    processed = storage.mark_webhook_event_processed(
        "stripe",
        "evt_123",
        processed_at="2026-04-15T09:41:00",
    )
    assert processed is not None
    assert processed["processed_at"] == "2026-04-15T09:41:00"

    with pytest.raises(sqlite3.IntegrityError):
        storage.save_webhook_event(
            {
                "provider_event_id": "evt_123",
                "provider": "stripe",
                "event_type": "checkout.session.completed",
                "received_at": "2026-04-15T09:42:00",
                "processed_at": None,
                "payload_json": {"id": "evt_123"},
            }
        )


def test_payment_groundwork_survives_backup_restore(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_quote_request(
        _base_quote_request(
            deposit_required_cad=56.5,
            deposit_status="pending",
            deposit_last_error="pending checkout creation",
        )
    )
    storage.save_payment_attempt(
        {
            "payment_attempt_id": "pay-attempt-export",
            "request_id": "req-payment-1",
            "provider": "stripe",
            "amount_cad": 56.5,
            "checkout_session_id": "cs_export_1",
            "payment_intent_id": "pi_export_1",
            "status": "pending",
            "created_at": "2026-04-15T09:45:00",
            "updated_at": "2026-04-15T09:45:00",
            "refund_id": None,
            "last_error": None,
        }
    )
    storage.save_webhook_event(
        {
            "provider_event_id": "evt_export_1",
            "provider": "stripe",
            "event_type": "payment_intent.payment_failed",
            "received_at": "2026-04-15T09:46:00",
            "processed_at": "2026-04-15T09:47:00",
            "payload_json": {"id": "evt_export_1", "status": "failed"},
        }
    )

    payload = storage.export_db_to_json()

    assert payload["tables"]["quote_requests"][0]["deposit_status"] == "pending"
    assert payload["tables"]["payment_attempts"][0]["status"] == "pending"
    assert payload["tables"]["webhook_events"][0]["payload_json"]["id"] == "evt_export_1"

    storage.DB_PATH = tmp_path / "payments-restored.sqlite3"
    storage.init_db()
    result = storage.import_db_from_json(payload)

    restored_request = storage.get_quote_request_record("req-payment-1")
    restored_attempt = storage.get_payment_attempt("pay-attempt-export")
    restored_event = storage.get_webhook_event("stripe", "evt_export_1")

    assert result["ok"] is True
    assert result["restored"]["payment_attempts"] == 1
    assert result["restored"]["webhook_events"] == 1
    assert restored_request is not None
    assert restored_request["deposit_status"] == "pending"
    assert restored_request["deposit_last_error"] == "pending checkout creation"
    assert restored_attempt is not None
    assert restored_attempt["payment_intent_id"] == "pi_export_1"
    assert restored_event is not None
    assert restored_event["payload_json"]["status"] == "failed"
