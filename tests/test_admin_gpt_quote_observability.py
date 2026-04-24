import base64

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    monkeypatch.setenv("BAYDELIVERY_DB_PATH", str(tmp_path / "test-admin-gpt-observability.sqlite3"))
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
def setup_observability_log(isolated_db: None) -> None:
    conn = storage._connect()
    try:
        conn.execute("DELETE FROM gpt_quote_observability")
        conn.commit()
    finally:
        conn.close()

    storage.save_gpt_quote_observability_event(
        {
            "timestamp": "2026-04-20T08:15:00+00:00",
            "route_name": "/api/gpt/quote",
            "success": True,
            "normalized_service_type": "junk_removal",
            "cash_total_cad": 175.0,
            "emt_total_cad": 197.75,
            "confidence_level": "medium",
            "risk_flags": ["stairs"],
            "failure_reason": None,
            "latency_ms": 145,
        }
    )
    storage.save_gpt_quote_observability_event(
        {
            "timestamp": "2026-04-20T09:30:00+00:00",
            "route_name": "/api/gpt/quote",
            "success": False,
            "normalized_service_type": None,
            "cash_total_cad": None,
            "emt_total_cad": None,
            "confidence_level": None,
            "risk_flags": [],
            "failure_reason": "validation_error",
            "latency_ms": 32,
        }
    )
    storage.save_gpt_quote_observability_event(
        {
            "timestamp": "2026-04-20T10:45:00+00:00",
            "route_name": "/api/gpt/quote",
            "success": True,
            "normalized_service_type": "move",
            "cash_total_cad": 420.0,
            "emt_total_cad": 474.6,
            "confidence_level": "high",
            "risk_flags": ["long_carry", "heavy_item"],
            "failure_reason": None,
            "latency_ms": 88,
        }
    )


def make_basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_unauthenticated_access_denied(client: TestClient) -> None:
    resp = client.get("/admin/api/gpt-quote-observability")
    assert resp.status_code == 401


def test_authenticated_access_succeeds(client: TestClient, admin_creds: tuple[str, str]) -> None:
    username, password = admin_creds
    resp = client.get("/admin/api/gpt-quote-observability", headers=make_basic_auth(username, password))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_response_shape_and_descending_order(client: TestClient, admin_creds: tuple[str, str]) -> None:
    username, password = admin_creds
    resp = client.get("/admin/api/gpt-quote-observability", headers=make_basic_auth(username, password))

    items = resp.json()["items"]
    assert len(items) == 3
    assert [item["timestamp"] for item in items] == [
        "2026-04-20T10:45:00+00:00",
        "2026-04-20T09:30:00+00:00",
        "2026-04-20T08:15:00+00:00",
    ]

    entry = items[0]
    assert set(entry.keys()) == {
        "timestamp",
        "route_name",
        "success",
        "normalized_service_type",
        "cash_total_cad",
        "emt_total_cad",
        "confidence_level",
        "risk_flags",
        "failure_reason",
        "latency_ms",
    }
    assert isinstance(entry["timestamp"], str)
    assert isinstance(entry["route_name"], str)
    assert isinstance(entry["success"], bool)
    assert entry["normalized_service_type"] is None or isinstance(entry["normalized_service_type"], str)
    assert entry["cash_total_cad"] is None or isinstance(entry["cash_total_cad"], float)
    assert entry["emt_total_cad"] is None or isinstance(entry["emt_total_cad"], float)
    assert entry["confidence_level"] is None or isinstance(entry["confidence_level"], str)
    assert isinstance(entry["risk_flags"], list)
    assert entry["failure_reason"] is None or isinstance(entry["failure_reason"], str)
    assert entry["latency_ms"] is None or isinstance(entry["latency_ms"], int)
