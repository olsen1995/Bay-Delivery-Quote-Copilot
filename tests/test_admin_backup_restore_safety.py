import base64
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


VALID_FILE_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
DB_CONFIRMATION = "IMPORT BAY DELIVERY DATABASE"
DRIVE_CONFIRMATION = "RESTORE BAY DELIVERY DATABASE"


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(tmp_path / "test-admin-backup-restore-safety.sqlite3"))
    storage.init_db()
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM admin_audit_log")
        conn.commit()
    finally:
        conn.close()


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


def _assert_no_key(data: Any, forbidden_key: str) -> None:
    if isinstance(data, dict):
        assert forbidden_key not in data
        for value in data.values():
            _assert_no_key(value, forbidden_key)
    elif isinstance(data, list):
        for value in data:
            _assert_no_key(value, forbidden_key)


def _assert_no_lists(data: Any) -> None:
    assert not isinstance(data, list)
    if isinstance(data, dict):
        for value in data.values():
            _assert_no_lists(value)


def _assert_no_forbidden_preview_content(data: Any) -> None:
    rendered = json.dumps(data, sort_keys=True)
    forbidden_fragments = [
        "tables",
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
    _assert_no_key(data, "tables")
    _assert_no_lists(data)
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
    _assert_no_key(data, "tables")
    _assert_no_lists(data)
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
    _assert_no_lists(data)
    _assert_no_forbidden_preview_content(data)
