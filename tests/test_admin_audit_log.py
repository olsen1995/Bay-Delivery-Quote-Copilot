import base64

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
