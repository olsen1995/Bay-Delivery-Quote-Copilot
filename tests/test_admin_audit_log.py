import base64
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import storage


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(tmp_path / "test-admin-audit.sqlite3"))
    storage.init_db()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> TestClient:
    monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
    monkeypatch.setenv("ADMIN_PASSWORD", "testpass")
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_creds() -> tuple[str, str]:
    return ("testadmin", "testpass")


@pytest.fixture(autouse=True)
def setup_audit_log(isolated_db: None) -> None:
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM admin_audit_log")
        for i in range(3):
            conn.execute(
                """
                INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"2026-03-16T12:0{i}:00", f"admin{i}", "test_action", "test_entity", f"rec{i}", 1, None),
            )
        conn.commit()
    finally:
        conn.close()


def make_basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def latest_audit_entry() -> dict[str, object]:
    return storage.list_admin_audit_log(limit=1)[0]


def audit_log_count() -> int:
    return len(storage.list_admin_audit_log(limit=50))


def test_unauthenticated_access_denied(client: TestClient) -> None:
    resp = client.get("/admin/api/audit-log")
    assert resp.status_code in {401, 403}


def test_authenticated_access_succeeds(client: TestClient, admin_creds: tuple[str, str]) -> None:
    username, password = admin_creds
    resp = client.get("/admin/api/audit-log", headers=make_basic_auth(username, password))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_response_shape(client: TestClient, admin_creds: tuple[str, str]) -> None:
    username, password = admin_creds
    resp = client.get("/admin/api/audit-log", headers=make_basic_auth(username, password))
    items = resp.json()["items"]
    assert len(items) >= 1
    entry = items[0]
    assert set(entry.keys()) == {"timestamp", "operator_username", "action_type", "entity_type", "record_id", "success", "error_summary"}
    assert isinstance(entry["timestamp"], str)
    assert isinstance(entry["operator_username"], str)
    assert isinstance(entry["action_type"], str)
    assert isinstance(entry["entity_type"], str)
    assert isinstance(entry["record_id"], str)
    assert isinstance(entry["success"], bool)
    assert entry["error_summary"] is None or isinstance(entry["error_summary"], str)


def test_fixed_limit(client: TestClient, admin_creds: tuple[str, str]) -> None:
    username, password = admin_creds
    conn = storage._connect()
    try:
        for i in range(60):
            conn.execute(
                """
                INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"2026-03-16T13:{i:02d}:00", f"adminX{i}", "bulk_action", "bulk_entity", f"recX{i}", 1, None),
            )
        conn.commit()
    finally:
        conn.close()

    resp = client.get("/admin/api/audit-log", headers=make_basic_auth(username, password))
    items = resp.json()["items"]
    assert len(items) == 50


def test_db_export_writes_admin_audit_log(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    monkeypatch.setattr("app.main.export_db_to_json", lambda: {"meta": {}, "tables": {}})

    resp = client.get("/admin/api/db/export", headers=make_basic_auth(username, password))

    assert resp.status_code == 200
    entry = latest_audit_entry()
    assert entry["operator_username"] == username
    assert entry["action_type"] == "export_db"
    assert entry["entity_type"] == "database"
    assert entry["record_id"] == "primary"
    assert entry["success"] is True
    assert entry["error_summary"] is None


def test_admin_audit_log_survives_round_trip_backup_restore(tmp_path: pytest.TempPathFactory) -> None:
    conn = storage._connect()
    try:
        conn.execute(
            """
            INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-03-16T12:30:00", "restore-admin", "restore_test", "database", "rec-restore", 0, "expected failure"),
        )
        conn.commit()
    finally:
        conn.close()

    payload = storage.export_db_to_json()
    audit_rows = payload["tables"]["admin_audit_log"]
    assert len(audit_rows) == 4
    assert any(
        row["operator_username"] == "restore-admin"
        and row["action_type"] == "restore_test"
        and row["entity_type"] == "database"
        and row["record_id"] == "rec-restore"
        and row["success"] == 0
        and row["error_summary"] == "expected failure"
        for row in audit_rows
    )

    original_db_path = storage.DB_PATH
    try:
        storage.DB_PATH = tmp_path / "restored-admin-audit.sqlite3"
        storage.init_db()
        result = storage.import_db_from_json(payload)

        assert result["ok"] is True
        assert result["restored"]["admin_audit_log"] == 4

        restored_items = storage.list_admin_audit_log(limit=10)
        assert len(restored_items) == 4
        assert any(
            item["operator_username"] == "restore-admin"
            and item["action_type"] == "restore_test"
            and item["entity_type"] == "database"
            and item["record_id"] == "rec-restore"
            and item["success"] is False
            and item["error_summary"] == "expected failure"
            for item in restored_items
        )
    finally:
        storage.DB_PATH = original_db_path


def test_db_export_uses_resolved_runtime_db_path_in_metadata(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    monkeypatch.setattr("app.main.export_db_to_json", lambda: {"meta": {}, "tables": {}})

    resp = client.get("/admin/api/db/export", headers=make_basic_auth(username, password))

    assert resp.status_code == 200
    assert resp.json()["meta"]["db_path"] == str(storage._resolve_db_path())


def test_db_import_success_writes_admin_audit_log(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    monkeypatch.setattr("app.main.import_db_from_json", lambda payload: {"ok": True, "restored": {"quotes": 0}})
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: None)

    resp = client.post(
        "/admin/api/db/import",
        headers=make_basic_auth(username, password),
        json={"payload": {"tables": {}}},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "restored": {"quotes": 0}}
    entry = latest_audit_entry()
    assert entry["operator_username"] == username
    assert entry["action_type"] == "import_db"
    assert entry["entity_type"] == "database"
    assert entry["record_id"] == "primary"
    assert entry["success"] is True
    assert entry["error_summary"] is None


def test_db_import_failure_writes_failed_admin_audit_log(
    client: TestClient,
    admin_creds: tuple[str, str],
) -> None:
    username, password = admin_creds

    with pytest.raises(ValueError, match="Backup payload missing 'tables' object"):
        client.post(
            "/admin/api/db/import",
            headers=make_basic_auth(username, password),
            json={"payload": {"tables": []}},
        )

    entry = latest_audit_entry()
    assert entry["operator_username"] == username
    assert entry["action_type"] == "import_db"
    assert entry["entity_type"] == "database"
    assert entry["record_id"] == "primary"
    assert entry["success"] is False
    assert entry["error_summary"] == "Backup payload missing 'tables' object"


def test_db_import_validation_failure_writes_failed_admin_audit_log(
    client: TestClient,
    admin_creds: tuple[str, str],
) -> None:
    username, password = admin_creds

    resp = client.post(
        "/admin/api/db/import",
        headers=make_basic_auth(username, password),
        json={},
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == [
        {
            "type": "missing",
            "loc": ["body", "payload"],
            "msg": "Field required",
            "input": {},
        }
    ]
    entry = latest_audit_entry()
    assert entry["operator_username"] == username
    assert entry["action_type"] == "import_db"
    assert entry["entity_type"] == "database"
    assert entry["record_id"] == "primary"
    assert entry["success"] is False
    assert entry["error_summary"] == "body.payload: Field required"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        make_basic_auth("wrong-admin", "wrong-pass"),
    ],
)
def test_db_import_validation_failure_without_valid_admin_does_not_write_audit_log(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    before_count = audit_log_count()

    resp = client.post(
        "/admin/api/db/import",
        headers=headers,
        json={},
    )

    assert resp.status_code == 422
    assert audit_log_count() == before_count


def test_unrelated_validation_failure_does_not_write_admin_audit_log(client: TestClient) -> None:
    before_count = audit_log_count()

    resp = client.post("/quote/calculate", json={})

    assert resp.status_code == 422
    assert audit_log_count() == before_count


def test_drive_snapshot_writes_admin_audit_log(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr(
        "app.main._drive_snapshot_db",
        lambda: {
            "ok": True,
            "file_id": "snapshot-file-123",
            "web_view_link": "https://example.test/snapshot",
            "name": "bay_delivery_backup_test.json",
        },
    )

    resp = client.post("/admin/api/drive/snapshot", headers=make_basic_auth(username, password))

    assert resp.status_code == 200
    entry = latest_audit_entry()
    assert entry["operator_username"] == username
    assert entry["action_type"] == "drive_snapshot"
    assert entry["entity_type"] == "drive_backup"
    assert entry["record_id"] == "snapshot-file-123"
    assert entry["success"] is True
    assert entry["error_summary"] is None


def test_drive_snapshot_uses_resolved_runtime_db_path_in_metadata(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    uploaded_payloads: list[dict[str, object]] = []

    def _upload_bytes(**kwargs):
        uploaded_payloads.append(json.loads(kwargs["content"].decode("utf-8")))
        return SimpleNamespace(
            file_id="snapshot-file-456",
            web_view_link="https://example.test/snapshot-456",
            name=kwargs["filename"],
        )

    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main.export_db_to_json", lambda: {"meta": {}, "tables": {}})
    monkeypatch.setattr(
        "app.main.gdrive.ensure_vault_subfolders",
        lambda: {"db_backups": "db-backups-folder"},
    )
    monkeypatch.setattr("app.main.gdrive.upload_bytes", _upload_bytes)
    monkeypatch.setattr("app.main.gdrive.backup_keep_count", lambda: 50)
    monkeypatch.setattr("app.main.gdrive.list_files", lambda _parent_id, limit=200: [])

    resp = client.post("/admin/api/drive/snapshot", headers=make_basic_auth(username, password))

    assert resp.status_code == 200
    assert len(uploaded_payloads) == 1
    assert uploaded_payloads[0]["meta"]["db_path"] == str(storage._resolve_db_path())


def test_admin_audit_logging_is_best_effort_for_db_export(
    client: TestClient,
    admin_creds: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username, password = admin_creds
    monkeypatch.setattr("app.main.export_db_to_json", lambda: {"meta": {}, "tables": {}})
    monkeypatch.setattr("app.main.log_admin_audit", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("audit write failed")))

    resp = client.get("/admin/api/db/export", headers=make_basic_auth(username, password))

    assert resp.status_code == 200
