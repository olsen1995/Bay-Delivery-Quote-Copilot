import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(tmp_path / "test-drive-restore.sqlite3"))


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def test_drive_restore_requires_admin(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", json={"file_id": "file_123"})

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
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": "file_123"})

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "restored": {"quotes": 2, "jobs": 1},
        "restored_from_file_id": "file_123",
    }


def test_drive_restore_invalid_structure(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)

    payload = {"meta": {"format": "bay-delivery-sqlite-backup", "version": 1}, "tables": []}
    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: json.dumps(payload).encode("utf-8"))

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": "file_123"})

    assert resp.status_code == 400
    assert "tables" in resp.json()["detail"]


def test_drive_restore_malformed_json(monkeypatch: pytest.MonkeyPatch, isolated_db: None) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)

    monkeypatch.setattr("app.main.gdrive.download_file", lambda file_id: b"not-json")

    with TestClient(app) as client:
        resp = client.post("/admin/api/drive/restore", headers=_admin_headers(), json={"file_id": "file_123"})

    assert resp.status_code == 400
    assert "Invalid backup JSON" in resp.json()["detail"]
