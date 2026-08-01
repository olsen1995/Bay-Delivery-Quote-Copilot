import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


VALID_FILE_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
DB_CONFIRMATION = "IMPORT BAY DELIVERY DATABASE"
DRIVE_CONFIRMATION = "RESTORE BAY DELIVERY DATABASE"


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    db_path = tmp_path / "test-admin-backup-restore-safety.sqlite3"
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(db_path))
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM admin_audit_log")
        conn.commit()
    finally:
        conn.close()
    try:
        yield
    finally:
        storage._TABLE_COL_CACHE.clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> TestClient:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    return TestClient(app)


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}", "Sec-Fetch-Site": "same-origin"}


def _backup_payload() -> dict[str, Any]:
    return {
        "meta": {
            "format": "bay-delivery-sqlite-backup",
            "version": 1,
            "token": "do-not-return",
        },
        "tables": {
            "quotes": [
                {
                    "id": "quote-1",
                    "customer_name": "Alice Example",
                    "phone": "705-555-0100",
                    "address": "123 Main St",
                    "description": "private customer job",
                    "secret": "row-secret",
                }
            ],
            "quote_requests": [
                {
                    "id": "request-1",
                    "customer_name": "Bob Example",
                    "phone": "705-555-0101",
                    "address": "456 Oak St",
                    "description": "another private job",
                    "accept_token": "accept-token-value",
                }
            ],
            "legacy_private": [{"password": "row-password"}],
        },
    }


def _review_required_linked_workflow_payload(linked_table: str) -> dict[str, Any]:
    quote_id = "review-linked-quote"
    tables: dict[str, list[dict[str, Any]]] = {
        "quotes": [
            {
                "quote_id": quote_id,
                "created_at": "2026-08-01T12:00:00+00:00",
                "request_json": {
                    "service_type": "small_move",
                    "route_classification": {
                        "status": "review_required",
                        "travel_zone": None,
                    },
                },
                "response_json": {
                    "status": "review_required",
                    "authoritative": False,
                },
                "accept_token": None,
                "admin_status": "pending",
            }
        ],
        "quote_requests": [],
        "jobs": [],
    }
    if linked_table == "quote_requests":
        tables["quote_requests"].append(
            {
                "request_id": "review-linked-request",
                "quote_id": quote_id,
                "status": "customer_accepted",
                "accept_token": "stale-accept-token",
                "booking_token": "stale-booking-token",
            }
        )
    elif linked_table == "jobs":
        tables["jobs"].append(
            {
                "job_id": "review-linked-job",
                "quote_id": quote_id,
                "request_id": None,
                "status": "approved",
            }
        )
    else:
        raise AssertionError(f"Unsupported linked table: {linked_table}")

    return {
        "meta": {"format": "bay-delivery-sqlite-backup", "version": 1},
        "tables": tables,
    }


def _save_authoritative_quote(quote_id: str) -> None:
    storage.save_quote(
        {
            "quote_id": quote_id,
            "created_at": "2026-08-01T11:00:00+00:00",
            "request": {
                "service_type": "small_move",
                "route_classification": {
                    "status": "authoritative",
                    "travel_zone": "in_town",
                },
            },
            "response": {
                "status": "authoritative",
                "authoritative": True,
                "cash_total_cad": 250.0,
                "emt_total_cad": 282.5,
            },
            "accept_token": f"{quote_id}-accept-token",
        }
    )


def _assert_no_key(data: Any, forbidden_key: str) -> None:
    if isinstance(data, dict):
        assert forbidden_key not in data
        for value in data.values():
            _assert_no_key(value, forbidden_key)
    elif isinstance(data, list):
        for value in data:
            _assert_no_key(value, forbidden_key)


def _assert_no_row_arrays(data: Any) -> None:
    if isinstance(data, list):
        assert all(not isinstance(value, (dict, list)) for value in data)
        return
    if isinstance(data, dict):
        for value in data.values():
            _assert_no_row_arrays(value)


def _assert_no_forbidden_preview_content(data: Any) -> None:
    rendered = json.dumps(data, sort_keys=True)
    forbidden_fragments = [
        "Alice Example",
        "Bob Example",
        "705-555",
        "123 Main St",
        "456 Oak St",
        "private customer job",
        "another private job",
        "do-not-return",
        "accept-token-value",
        "row-secret",
        "row-password",
        "Authorization",
        "password",
        "secret",
        "phone",
        "address",
        "customer_name",
        "description",
        "accept_token",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in rendered


def _assert_preview_counts_all_known_tables(data: dict[str, Any]) -> None:
    counts = data["preview"]["known_table_counts"]
    assert set(counts) == set(storage.KNOWN_TABLES)
    assert data["preview"]["known_table_count"] == len(storage.KNOWN_TABLES)
    assert data["preview"]["omitted_known_tables"] == [
        table for table in storage.KNOWN_TABLES if table not in {"quotes", "quote_requests"}
    ]
    assert all(counts[table] == 0 for table in data["preview"]["omitted_known_tables"])


def latest_audit_entry() -> dict[str, object]:
    return storage.list_admin_audit_log(limit=1)[0]


def test_db_import_missing_confirmation_rejects_before_mutation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_import(_payload: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("import_db_from_json must not be called without confirmation")

    monkeypatch.setattr("app.main.import_db_from_json", _fail_import)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: (_ for _ in ()).throw(AssertionError("snapshot must not run")))

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload()},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Missing or invalid confirmation for database import."}
    entry = latest_audit_entry()
    assert entry["action_type"] == "db_import_confirmation_failed"
    assert entry["success"] is False
    assert entry["error_summary"] == "missing_confirm_action"


def test_db_import_wrong_confirmation_rejects_before_mutation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run")))

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload(), "confirm_action": "IMPORT WRONG DATABASE"},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Missing or invalid confirmation for database import."}
    entry = latest_audit_entry()
    assert entry["action_type"] == "db_import_confirmation_failed"
    assert entry["success"] is False
    assert entry["error_summary"] == "invalid_confirm_action"


def test_db_import_dry_run_returns_safe_preview_and_does_not_mutate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run for dry-run")))
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: (_ for _ in ()).throw(AssertionError("snapshot must not run for dry-run")))

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload(), "dry_run": True},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["would_restore"] is False
    assert data["preview"]["known_table_counts"]["quotes"] == 1
    assert data["preview"]["known_table_counts"]["quote_requests"] == 1
    assert data["preview"]["total_known_rows"] == 2
    assert data["preview"]["unknown_table_count"] == 1
    _assert_preview_counts_all_known_tables(data)
    _assert_no_key(data, "tables")
    _assert_no_row_arrays(data)
    _assert_no_forbidden_preview_content(data)
    entry = latest_audit_entry()
    assert entry["action_type"] == "db_import_dry_run"
    assert entry["success"] is True


def test_db_import_valid_confirmation_reaches_mutation_path_only_with_mock(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def _record_import(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {"ok": True, "restored": {"quotes": 1}}

    monkeypatch.setattr("app.main.import_db_from_json", _record_import)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: None)

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload(), "confirm_action": DB_CONFIRMATION},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "restored": {"quotes": 1}}
    assert calls == [_backup_payload()]
    entry = latest_audit_entry()
    assert entry["action_type"] == "import_db"
    assert entry["success"] is True


def test_drive_restore_missing_confirmation_rejects_before_drive_or_mutation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main._drive_enabled", lambda: (_ for _ in ()).throw(AssertionError("Drive must not be checked without confirmation")))
    monkeypatch.setattr("app.main.gdrive.download_file", lambda _file_id: (_ for _ in ()).throw(AssertionError("Drive download must not run")))
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run")))

    resp = client.post(
        "/admin/api/drive/restore",
        headers=_admin_headers(),
        json={"file_id": VALID_FILE_ID},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Missing or invalid confirmation for Drive restore."}
    entry = latest_audit_entry()
    assert entry["action_type"] == "drive_restore_confirmation_failed"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is False
    assert entry["error_summary"] == "missing_confirm_action"


def test_drive_restore_wrong_confirmation_rejects_before_drive_or_mutation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main._drive_enabled", lambda: (_ for _ in ()).throw(AssertionError("Drive must not be checked with wrong confirmation")))
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run")))

    resp = client.post(
        "/admin/api/drive/restore",
        headers=_admin_headers(),
        json={"file_id": VALID_FILE_ID, "confirm_action": "RESTORE WRONG DATABASE"},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "Missing or invalid confirmation for Drive restore."}
    entry = latest_audit_entry()
    assert entry["action_type"] == "drive_restore_confirmation_failed"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is False
    assert entry["error_summary"] == "invalid_confirm_action"


def test_drive_restore_dry_run_returns_safe_preview_and_does_not_mutate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: json.dumps(_backup_payload()).encode("utf-8"))
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run for dry-run")))
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: (_ for _ in ()).throw(AssertionError("snapshot must not run for dry-run")))

    resp = client.post(
        "/admin/api/drive/restore",
        headers=_admin_headers(),
        json={"file_id": VALID_FILE_ID, "dry_run": True},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["would_restore"] is False
    assert data["preview"]["known_table_counts"]["quotes"] == 1
    assert data["preview"]["known_table_counts"]["quote_requests"] == 1
    assert data["preview"]["total_known_rows"] == 2
    assert data["preview"]["unknown_table_count"] == 1
    assert data["restored_from_file_id"] == VALID_FILE_ID
    _assert_preview_counts_all_known_tables(data)
    _assert_no_key(data, "tables")
    _assert_no_row_arrays(data)
    _assert_no_forbidden_preview_content(data)
    entry = latest_audit_entry()
    assert entry["action_type"] == "drive_restore_dry_run"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is True


def test_drive_restore_valid_confirmation_reaches_mutation_path_only_with_mock(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: json.dumps(_backup_payload()).encode("utf-8"))
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: None)

    def _record_import(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {"ok": True, "restored": {"quotes": 1, "quote_requests": 1}}

    monkeypatch.setattr("app.main.import_db_from_json", _record_import)

    resp = client.post(
        "/admin/api/drive/restore",
        headers=_admin_headers(),
        json={"file_id": VALID_FILE_ID, "confirm_action": DRIVE_CONFIRMATION},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "restored": {"quotes": 1, "quote_requests": 1},
        "restored_from_file_id": VALID_FILE_ID,
    }
    assert calls == [_backup_payload()]
    entry = latest_audit_entry()
    assert entry["action_type"] == "drive_restore"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is True


@pytest.mark.parametrize("channel", ["database", "drive"])
@pytest.mark.parametrize("linked_table", ["quote_requests", "jobs"])
def test_review_required_linked_workflow_is_rejected_consistently_by_preview_and_restore(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    channel: str,
    linked_table: str,
) -> None:
    payload = _review_required_linked_workflow_payload(linked_table)
    _save_authoritative_quote("existing-target-quote")
    original_target = storage.get_quote_record("existing-target-quote")
    init_calls: list[bool] = []
    token_rotation_calls: list[bool] = []

    def fail_if_init_runs() -> None:
        init_calls.append(True)
        raise AssertionError("rejected preview or restore must not initialize the database")

    def fail_if_token_rotation_runs() -> str:
        token_rotation_calls.append(True)
        raise AssertionError("rejected preview or restore must not rotate tokens")

    monkeypatch.setattr(storage, "init_db", fail_if_init_runs)
    monkeypatch.setattr(storage, "_fresh_workflow_token", fail_if_token_rotation_runs)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)

    request_client = TestClient(app, raise_server_exceptions=False)
    try:
        if channel == "database":
            preview_response = request_client.post(
                "/admin/api/db/import",
                headers=_admin_headers(),
                json={"payload": payload, "dry_run": True},
            )
            restore_response = request_client.post(
                "/admin/api/db/import",
                headers=_admin_headers(),
                json={"payload": payload, "confirm_action": DB_CONFIRMATION},
            )
        else:
            monkeypatch.setattr("app.main._drive_enabled", lambda: True)
            monkeypatch.setattr(
                "app.main.gdrive.download_file",
                lambda _file_id: json.dumps(payload).encode("utf-8"),
            )
            preview_response = request_client.post(
                "/admin/api/drive/restore",
                headers=_admin_headers(),
                json={"file_id": VALID_FILE_ID, "dry_run": True},
            )
            restore_response = request_client.post(
                "/admin/api/drive/restore",
                headers=_admin_headers(),
                json={"file_id": VALID_FILE_ID, "confirm_action": DRIVE_CONFIRMATION},
            )
    finally:
        request_client.close()

    expected_error = {
        "detail": "Backup contains a review-required quote with linked workflow state"
    }
    assert preview_response.status_code == 400
    assert restore_response.status_code == 400
    assert preview_response.json() == expected_error
    assert restore_response.json() == expected_error
    assert storage.get_quote_record("existing-target-quote") == original_target
    assert storage.get_quote_record("review-linked-quote") is None
    assert storage.get_quote_request_record("review-linked-request") is None
    assert storage.get_job_by_quote_id("review-linked-quote") is None
    assert init_calls == []
    assert token_rotation_calls == []


@pytest.mark.parametrize("channel", ["database", "drive"])
def test_authoritative_backup_previews_and_restores_successfully(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    channel: str,
) -> None:
    quote_id = f"authoritative-{channel}-restore"
    _save_authoritative_quote(quote_id)
    payload = storage.export_db_to_json()
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)

    if channel == "database":
        preview_response = client.post(
            "/admin/api/db/import",
            headers=_admin_headers(),
            json={"payload": payload, "dry_run": True},
        )
        restore_response = client.post(
            "/admin/api/db/import",
            headers=_admin_headers(),
            json={"payload": payload, "confirm_action": DB_CONFIRMATION},
        )
    else:
        monkeypatch.setattr("app.main._drive_enabled", lambda: True)
        monkeypatch.setattr(
            "app.main.gdrive.download_file",
            lambda _file_id: json.dumps(payload).encode("utf-8"),
        )
        preview_response = client.post(
            "/admin/api/drive/restore",
            headers=_admin_headers(),
            json={"file_id": VALID_FILE_ID, "dry_run": True},
        )
        restore_response = client.post(
            "/admin/api/drive/restore",
            headers=_admin_headers(),
            json={"file_id": VALID_FILE_ID, "confirm_action": DRIVE_CONFIRMATION},
        )

    assert preview_response.status_code == 200
    assert preview_response.json()["dry_run"] is True
    assert restore_response.status_code == 200
    restored = storage.get_quote_record(quote_id)
    assert restored is not None
    assert restored["status"] == "authoritative"
    assert restored["accept_token"] not in {
        None,
        storage.BACKUP_TOKEN_ROTATION_PLACEHOLDER,
        f"{quote_id}-accept-token",
    }


def test_confirmed_success_audit_metadata_is_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: {"ok": True, "restored": {"quotes": 1}})
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: None)

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload(), "confirm_action": DB_CONFIRMATION},
    )

    assert resp.status_code == 200
    entry = latest_audit_entry()
    assert entry["action_type"] == "import_db"
    assert entry["record_id"] == "primary"
    assert entry["error_summary"] is None
    _assert_no_forbidden_preview_content(entry)


def test_confirmation_failure_audit_metadata_is_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run")))

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={
            "payload": _backup_payload(),
            "confirm_action": "Alice Example 705-555-0100 row-secret",
        },
    )

    assert resp.status_code == 400
    entry = latest_audit_entry()
    assert entry["action_type"] == "db_import_confirmation_failed"
    assert entry["record_id"] == "primary"
    assert entry["success"] is False
    assert entry["error_summary"] == "invalid_confirm_action"
    _assert_no_forbidden_preview_content(entry)


def test_preview_output_excludes_sensitive_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.import_db_from_json", lambda _payload: (_ for _ in ()).throw(AssertionError("import must not run for preview")))

    resp = client.post(
        "/admin/api/db/import",
        headers=_admin_headers(),
        json={"payload": _backup_payload(), "dry_run": True, "confirm_action": "not needed for dry-run"},
    )

    assert resp.status_code == 200
    data = resp.json()
    _assert_no_key(data, "tables")
    _assert_no_row_arrays(data)
    _assert_no_forbidden_preview_content(data)
