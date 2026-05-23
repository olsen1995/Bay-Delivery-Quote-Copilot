import base64
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main as main_app
from app import storage
from app.main import app, clear_gpt_admin_notes_rate_limit_state


def _basic_auth(username: str = "admin", password: str = "secret") -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _gpt_auth(token: str = "test-gpt-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "gpt-admin-notes.sqlite3"
    monkeypatch.setattr(storage, "DB_PATH", storage.DEFAULT_DB_PATH)
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    monkeypatch.setenv("GPT_INTERNAL_API_TOKEN", "test-gpt-token")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    clear_gpt_admin_notes_rate_limit_state()
    yield db_path
    storage._TABLE_COL_CACHE.clear()
    clear_gpt_admin_notes_rate_limit_state()


@pytest.fixture()
def client(isolated_db: Path) -> TestClient:
    return TestClient(app, client=("127.0.0.1", 50000))


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "related_entity_type": "general",
        "note_type": "missing_info",
        "title": "Confirm access before booking",
        "summary": "Customer description is missing stair and parking details.",
        "recommendation": "Ask whether the truck can park close and whether stairs are involved.",
        "customer_message_draft": "Could you confirm parking access and stairs?",
        "risk_flags": ["access", "missing_info"],
        "follow_up_needed": True,
        "idempotency_key": "gpt-note-001",
    }
    payload.update(overrides)
    return payload


def _storage_note_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "note_id": "storage-note-1",
        "created_at": "2026-05-22T10:00:00-04:00",
        "updated_at": None,
        "source": "internal_gpt",
        "related_entity_type": "general",
        "related_entity_id": None,
        "note_type": "missing_info",
        "title": "Storage note",
        "summary": "Storage note summary.",
        "recommendation": None,
        "customer_message_draft": None,
        "risk_flags": [],
        "follow_up_needed": False,
        "customer_visible": False,
        "pricing_effect": "none",
        "review_status": "open",
        "idempotency_key": "storage-note-key",
        "payload_hash": "storage-note-hash",
        "server_grounding_revision": None,
        "caller_grounding_revision": None,
    }
    record.update(overrides)
    return record


def _audit_items() -> list[dict[str, Any]]:
    return storage.list_admin_audit_log(limit=50)


def _count_notes() -> int:
    conn = storage._connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM gpt_admin_notes").fetchone()
        return int(row["count"])
    finally:
        conn.close()


def _seed_related_records() -> dict[str, str]:
    quote_id = "quote-gpt-note"
    request_id = "request-gpt-note"
    job_id = "job-gpt-note"
    calibration_id = "calibration-gpt-note"
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": "2026-05-22T10:00:00",
            "request": {
                "customer_name": "GPT Note Customer",
                "customer_phone": "705-555-0101",
                "job_address": "123 Note St",
                "description": "Small cleanup",
                "service_type": "haul_away",
            },
            "response": {"cash_total_cad": 100.0, "emt_total_cad": 113.0},
            "accept_token": "accept-gpt-note",
        }
    )
    storage.save_quote_request(
        {
            "request_id": request_id,
            "created_at": "2026-05-22T10:05:00",
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": "GPT Note Customer",
            "customer_phone": "705-555-0101",
            "job_address": "123 Note St",
            "job_description_customer": "Small cleanup",
            "job_description_internal": None,
            "service_type": "haul_away",
            "cash_total_cad": 100.0,
            "emt_total_cad": 113.0,
            "request_json": {
                "service_type": "haul_away",
                "description": "Small cleanup",
            },
            "notes": None,
            "requested_job_date": None,
            "requested_time_window": None,
            "customer_accepted_at": "2026-05-22T10:05:00",
            "admin_approved_at": None,
            "accept_token": "accept-gpt-note",
            "booking_token": None,
            "booking_token_created_at": None,
            "followup_status": None,
        }
    )
    storage.save_job(
        {
            "job_id": job_id,
            "created_at": "2026-05-22T10:10:00",
            "status": "scheduled",
            "quote_id": quote_id,
            "request_id": request_id,
            "customer_name": "GPT Note Customer",
            "customer_phone": "705-555-0101",
            "job_address": "123 Note St",
            "job_description_customer": "Small cleanup",
            "job_description_internal": None,
            "service_type": "haul_away",
            "cash_total_cad": 100.0,
            "emt_total_cad": 113.0,
            "request_json": {
                "service_type": "haul_away",
                "description": "Small cleanup",
            },
            "google_calendar_event_id": None,
        }
    )
    storage.save_completed_job_calibration_entry(
        {
            "entry_id": calibration_id,
            "created_at": "2026-05-22T10:15:00",
            "updated_at": None,
            "operator_username": "admin",
            "job_title": "Backyard tarp/fence teardown",
            "service_type": "demolition",
            "actual_collected_cad": 600.0,
            "crew_size": 3,
            "duration_hours": 3,
            "pricing_result": "fair",
        }
    )
    return {
        "quote": quote_id,
        "quote_request": request_id,
        "job": job_id,
        "completed_job_calibration_entry": calibration_id,
    }


def test_gpt_admin_notes_schema_created_and_known_table_covered(isolated_db: Path) -> None:
    assert "gpt_admin_notes" in storage.KNOWN_TABLES

    conn = storage._connect()
    try:
        columns = {
            row["name"]: row
            for row in conn.execute("PRAGMA table_info(gpt_admin_notes)").fetchall()
        }
    finally:
        conn.close()

    expected_columns = {
        "note_id",
        "created_at",
        "updated_at",
        "source",
        "related_entity_type",
        "related_entity_id",
        "note_type",
        "title",
        "summary",
        "recommendation",
        "customer_message_draft",
        "risk_flags_json",
        "follow_up_needed",
        "customer_visible",
        "pricing_effect",
        "review_status",
        "idempotency_key",
        "payload_hash",
        "server_grounding_revision",
        "caller_grounding_revision",
    }
    assert expected_columns <= set(columns)
    for required in [
        "note_id",
        "created_at",
        "source",
        "related_entity_type",
        "note_type",
        "title",
        "summary",
        "risk_flags_json",
        "follow_up_needed",
        "customer_visible",
        "pricing_effect",
        "review_status",
        "payload_hash",
    ]:
        assert columns[required]["notnull"] == 1 or required == "note_id"


def test_gpt_admin_notes_post_requires_valid_bearer_without_audit_or_persistence(client: TestClient) -> None:
    missing = client.post("/api/gpt/admin-notes", json=_valid_payload())
    invalid = client.post("/api/gpt/admin-notes", headers=_gpt_auth("wrong-token"), json=_valid_payload())

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert _count_notes() == 0
    assert not [
        item
        for item in _audit_items()
        if item["action_type"] == "create_gpt_admin_note"
    ]


def test_gpt_admin_notes_post_fails_closed_when_token_unset(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GPT_INTERNAL_API_TOKEN", raising=False)

    response = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=_valid_payload())

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert _count_notes() == 0
    assert not [
        item
        for item in _audit_items()
        if item["action_type"] == "create_gpt_admin_note"
    ]


def test_gpt_admin_notes_create_hardcodes_safety_fields_and_writes_audit(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/gpt/admin-notes",
        headers={**_gpt_auth(), "x-gpt-grounding-revision": "caller-rev-1"},
        json=_valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["note_id"]

    notes = storage.list_gpt_admin_notes(limit=10)
    assert len(notes) == 1
    note = notes[0]
    assert note["note_id"] == body["note_id"]
    assert note["source"] == "internal_gpt"
    assert note["customer_visible"] is False
    assert note["pricing_effect"] == "none"
    assert note["review_status"] == "open"
    assert note["risk_flags"] == ["access", "missing_info"]
    assert note["follow_up_needed"] is True
    assert note["caller_grounding_revision"] == "caller-rev-1"

    audit = _audit_items()[0]
    assert audit["operator_username"] == "internal_gpt"
    assert audit["action_type"] == "create_gpt_admin_note"
    assert audit["entity_type"] == "gpt_admin_note"
    assert audit["record_id"] == body["note_id"]
    assert audit["success"] is True


@pytest.mark.parametrize(
    "field",
    [
        "customer_visible",
        "pricing_effect",
        "cash_total_cad",
        "discount_cad",
        "margin_percent",
        "profit_cad",
        "approve_quote_request",
        "schedule_job",
        "payment_status",
        "send_customer_sms",
        "photo_base64",
        "file_upload",
    ],
)
def test_gpt_admin_notes_rejects_forbidden_extra_fields_and_audits_when_authenticated(
    client: TestClient,
    field: str,
) -> None:
    payload = _valid_payload(idempotency_key=f"bad-{field}")
    payload[field] = "not allowed"

    response = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)

    assert response.status_code == 422
    assert _count_notes() == 0
    assert any(
        item["action_type"] == "create_gpt_admin_note"
        and item["success"] is False
        for item in _audit_items()
    )


def test_gpt_admin_notes_requires_related_entity_id_for_non_general_and_checks_existence(
    client: TestClient,
) -> None:
    missing_id = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(
            idempotency_key="missing-related-id",
            related_entity_type="job",
            related_entity_id=None,
        ),
    )
    missing_entity = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(
            idempotency_key="missing-related-entity",
            related_entity_type="job",
            related_entity_id="not-a-job",
        ),
    )

    assert missing_id.status_code == 422
    assert missing_entity.status_code == 404
    assert _count_notes() == 0
    assert any(
        item["action_type"] == "create_gpt_admin_note"
        and item["success"] is False
        for item in _audit_items()
    )


def test_gpt_admin_notes_accepts_practical_related_entity_types(client: TestClient) -> None:
    ids = _seed_related_records()

    for related_type, related_id in ids.items():
        response = client.post(
            "/api/gpt/admin-notes",
            headers=_gpt_auth(),
            json=_valid_payload(
                idempotency_key=f"related-{related_type}",
                related_entity_type=related_type,
                related_entity_id=related_id,
                note_type=(
                    "completed_job_calibration_observation"
                    if related_type == "completed_job_calibration_entry"
                    else "job_observation"
                ),
            ),
        )
        assert response.status_code == 200, response.text

    assert _count_notes() == 4


def test_gpt_admin_notes_idempotency_key_returns_existing_without_second_row(
    client: TestClient,
) -> None:
    payload = _valid_payload(idempotency_key="stable-idempotency-key")

    created = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)
    replayed = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)

    assert created.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["created"] is False
    assert replayed.json()["note_id"] == created.json()["note_id"]
    assert _count_notes() == 1


def test_gpt_admin_notes_post_handles_idempotency_insert_race(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _valid_payload(idempotency_key="race-idempotency-key")
    created = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)
    assert created.status_code == 200

    existing = storage.get_gpt_admin_note_by_idempotency_key("race-idempotency-key")
    assert existing is not None

    monkeypatch.setattr(main_app, "get_gpt_admin_note_by_idempotency_key", lambda _: None)

    def raise_idempotency_replay(*args: Any, **kwargs: Any) -> None:
        raise storage.GptAdminNoteIdempotencyReplay(existing)

    monkeypatch.setattr(main_app, "save_gpt_admin_note", raise_idempotency_replay)

    replayed = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(
            idempotency_key="race-idempotency-key",
            title="Race replay",
        ),
    )

    assert replayed.status_code == 200
    assert replayed.json() == {"note_id": created.json()["note_id"], "created": False}
    assert _count_notes() == 1


def test_save_gpt_admin_note_converts_idempotency_integrity_race(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = storage.save_gpt_admin_note(_storage_note_record())
    original_lookup = storage._get_gpt_admin_note_by_idempotency_key_conn
    call_count = 0

    def miss_then_find(conn: sqlite3.Connection, idempotency_key: str):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None
        return original_lookup(conn, idempotency_key)

    monkeypatch.setattr(storage, "_get_gpt_admin_note_by_idempotency_key_conn", miss_then_find)

    with pytest.raises(storage.GptAdminNoteIdempotencyReplay) as exc_info:
        storage.save_gpt_admin_note(
            _storage_note_record(
                note_id="storage-note-2",
                title="Second storage note",
                payload_hash="different-storage-note-hash",
            ),
            duplicate_since_created_at="2026-05-22T09:00:00-04:00",
        )

    assert call_count == 2
    assert exc_info.value.note["note_id"] == saved["note_id"]
    assert _count_notes() == 1


def test_gpt_admin_notes_exact_duplicate_payload_without_key_returns_409(
    client: TestClient,
) -> None:
    payload = _valid_payload()
    payload.pop("idempotency_key")

    created = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)
    duplicate = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=payload)

    assert created.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "duplicate_note"}
    assert _count_notes() == 1
    assert any(
        item["action_type"] == "create_gpt_admin_note"
        and item["success"] is False
        and item["error_summary"] == "duplicate_note"
        for item in _audit_items()
    )


def test_save_gpt_admin_note_checks_duplicate_payload_inside_insert_transaction(
    isolated_db: Path,
) -> None:
    saved = storage.save_gpt_admin_note(
        _storage_note_record(idempotency_key=None),
        duplicate_since_created_at="2026-05-22T09:00:00-04:00",
    )

    with pytest.raises(storage.GptAdminNoteDuplicatePayload) as exc_info:
        storage.save_gpt_admin_note(
            _storage_note_record(
                note_id="storage-note-2",
                title="Duplicate storage note",
                idempotency_key=None,
            ),
            duplicate_since_created_at="2026-05-22T09:00:00-04:00",
        )

    assert exc_info.value.note["note_id"] == saved["note_id"]
    assert _count_notes() == 1


def test_gpt_admin_notes_rate_limit_allows_five_successful_creates_per_minute(
    client: TestClient,
) -> None:
    for index in range(5):
        response = client.post(
            "/api/gpt/admin-notes",
            headers=_gpt_auth(),
            json=_valid_payload(
                idempotency_key=f"rate-{index}",
                title=f"Rate note {index}",
            ),
        )
        assert response.status_code == 200

    blocked = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(idempotency_key="rate-blocked", title="Rate blocked"),
    )

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "rate limit exceeded"}
    assert _count_notes() == 5


def test_admin_gpt_notes_get_requires_admin_auth_and_filters_newest_first(
    client: TestClient,
) -> None:
    ids = _seed_related_records()
    first = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(idempotency_key="first-note", title="First note"),
    )
    second = client.post(
        "/api/gpt/admin-notes",
        headers=_gpt_auth(),
        json=_valid_payload(
            idempotency_key="job-note",
            title="Job note",
            related_entity_type="job",
            related_entity_id=ids["job"],
            note_type="job_observation",
        ),
    )
    assert first.status_code == 200
    assert second.status_code == 200

    denied = client.get("/admin/api/gpt-notes")
    assert denied.status_code == 401

    listed = client.get("/admin/api/gpt-notes", headers=_basic_auth())
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert [item["note_id"] for item in items] == [
        second.json()["note_id"],
        first.json()["note_id"],
    ]

    filtered = client.get(
        f"/admin/api/gpt-notes?related_entity_type=job&related_entity_id={ids['job']}&review_status=open",
        headers=_basic_auth(),
    )
    assert filtered.status_code == 200
    filtered_items = filtered.json()["items"]
    assert len(filtered_items) == 1
    assert filtered_items[0]["related_entity_type"] == "job"
    assert filtered_items[0]["related_entity_id"] == ids["job"]


def test_list_gpt_admin_notes_orders_by_normalized_datetime_with_offsets(
    isolated_db: Path,
) -> None:
    storage.save_gpt_admin_note(
        _storage_note_record(
            note_id="newer-normalized",
            created_at="2026-05-22T10:30:00-04:00",
            title="Newer normalized",
            idempotency_key="newer-normalized",
            payload_hash="newer-normalized",
        )
    )
    storage.save_gpt_admin_note(
        _storage_note_record(
            note_id="older-lexical",
            created_at="2026-05-22T15:00:00+02:00",
            title="Older lexical",
            idempotency_key="older-lexical",
            payload_hash="older-lexical",
        )
    )

    items = storage.list_gpt_admin_notes(limit=10)

    assert [item["note_id"] for item in items] == [
        "newer-normalized",
        "older-lexical",
    ]


def test_gpt_admin_notes_survives_backup_export_import_round_trip(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=_valid_payload())
    assert created.status_code == 200

    payload = storage.export_db_to_json()
    assert "gpt_admin_notes" in payload["tables"]
    assert len(payload["tables"]["gpt_admin_notes"]) == 1

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "restored-gpt-admin-notes.sqlite3")
    storage._TABLE_COL_CACHE.clear()
    result = storage.import_db_from_json(payload)

    assert result["restored"]["gpt_admin_notes"] == 1
    restored = storage.list_gpt_admin_notes(limit=10)
    assert len(restored) == 1
    assert restored[0]["note_id"] == created.json()["note_id"]


def test_public_routes_do_not_expose_gpt_admin_notes(client: TestClient) -> None:
    created = client.post("/api/gpt/admin-notes", headers=_gpt_auth(), json=_valid_payload())
    assert created.status_code == 200

    assert client.get("/").status_code == 200
    assert client.get("/quote").status_code == 200
    assert client.get("/api/gpt/admin-notes").status_code in {404, 405}
    assert client.get("/quote/calculate").status_code in {404, 405}
