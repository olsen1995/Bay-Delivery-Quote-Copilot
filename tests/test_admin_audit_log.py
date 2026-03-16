
import base64
import os
import sqlite3
import pytest

import pytest
from fastapi.testclient import TestClient


def make_basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
    monkeypatch.setenv("ADMIN_PASSWORD", "testpass")
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_creds():
    return ("testadmin", "testpass")

@pytest.fixture(autouse=True)
def setup_audit_log():
    # Insert a few audit log rows for testing
    conn = sqlite3.connect("app/data/bay_delivery.sqlite3")
    try:
        conn.execute("DELETE FROM admin_audit_log")
        for i in range(3):
            conn.execute(
                """
                INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"2026-03-16T12:0{i}:00", f"admin{i}", "test_action", "test_entity", f"rec{i}", 1, None)
            )
        conn.commit()
    finally:
        conn.close()
    yield
    # Cleanup after
    conn = sqlite3.connect("app/data/bay_delivery.sqlite3")
    try:
        conn.execute("DELETE FROM admin_audit_log")
        conn.commit()
    finally:
        conn.close()

def test_unauthenticated_access_denied(client):
    resp = client.get("/admin/api/audit-log")
    assert resp.status_code == 401 or resp.status_code == 403

def test_authenticated_access_succeeds(client, admin_creds):
    username, password = admin_creds
    headers = make_basic_auth(username, password)
    resp = client.get("/admin/api/audit-log", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_response_shape(client, admin_creds):
    username, password = admin_creds
    headers = make_basic_auth(username, password)
    resp = client.get("/admin/api/audit-log", headers=headers)
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
    # error_summary can be None or str
    assert entry["error_summary"] is None or isinstance(entry["error_summary"], str)

def test_fixed_limit(client, admin_creds):
    username, password = admin_creds
    headers = make_basic_auth(username, password)
    # Insert 60 rows to test limit
    conn = sqlite3.connect("app/data/bay_delivery.sqlite3")
    try:
        for i in range(60):
            conn.execute(
                """
                INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"2026-03-16T13:{i:02d}:00", f"adminX{i}", "bulk_action", "bulk_entity", f"recX{i}", 1, None)
            )
        conn.commit()
    finally:
        conn.close()
    resp = client.get("/admin/api/audit-log", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 50  # fixed limit
