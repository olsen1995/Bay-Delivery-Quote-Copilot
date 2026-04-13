import base64
import json

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


VALID_FILE_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(tmp_path / "test-drive-restore.sqlite3"))


@pytest.fixture(autouse=True)
def setup_audit_log(isolated_db: None) -> None:
    storage.init_db()
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM admin_audit_log")
        conn.commit()
    finally:
        conn.close()


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def latest_audit_entry() -> dict[str, object]:
    return storage.list_admin_audit_log(limit=1)[0]


def test_drive_restore_requires_admin(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", json={"file_id": VALID_FILE_ID})

    assert resp.status_code == 401


def test_drive_restore_happy_path(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda background_tasks: None)

    payload = {
        "meta": {"format": "bay-delivery-sqlite-backup", "version": 1},
        "tables": {},
    }

    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: json.dumps(payload).encode("utf-8"))
    monkeypatch.setattr("app.main.import_db_from_json", lambda data: {"ok": True, "restored": {"quotes": 2, "jobs": 1}})

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": VALID_FILE_ID})

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "restored": {"quotes": 2, "jobs": 1},
        "restored_from_file_id": VALID_FILE_ID,
    }
    entry = latest_audit_entry()
    assert entry["operator_username"] == "admin"
    assert entry["action_type"] == "drive_restore"
    assert entry["entity_type"] == "drive_backup"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is True
    assert entry["error_summary"] is None


def test_drive_restore_invalid_structure(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)

    payload = {"meta": {"format": "bay-delivery-sqlite-backup", "version": 1}, "tables": []}
    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: json.dumps(payload).encode("utf-8"))

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": VALID_FILE_ID})

    assert resp.status_code == 400
    assert "tables" in resp.json()["detail"]
    entry = latest_audit_entry()
    assert entry["operator_username"] == "admin"
    assert entry["action_type"] == "drive_restore"
    assert entry["entity_type"] == "drive_backup"
    assert entry["record_id"] == VALID_FILE_ID
    assert entry["success"] is False
    assert entry["error_summary"] == "Backup payload missing 'tables' object."


def test_drive_restore_malformed_json(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)

    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: b"not-json")

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": VALID_FILE_ID})

    assert resp.status_code == 400
    assert "Invalid backup JSON" in resp.json()["detail"]


def test_drive_restore_rejects_malformed_file_id(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with TestClient(app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers=_admin_headers(),
            json={"file_id": "bad<script>"},
        )

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert isinstance(detail, list)
    assert any("file ID" in str(item.get("msg", "")) for item in detail if isinstance(item, dict))
