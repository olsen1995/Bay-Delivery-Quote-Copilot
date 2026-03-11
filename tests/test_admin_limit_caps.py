import base64

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def admin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def test_admin_quotes_limit_is_capped(monkeypatch: pytest.MonkeyPatch, admin_env: None) -> None:
    seen: dict[str, int] = {}

    def fake_list_quotes(limit: int = 50):
        seen["limit"] = limit
        return []

    monkeypatch.setattr("app.main.list_quotes", fake_list_quotes)

    with TestClient(app) as client:
        resp = client.get("/admin/api/quotes?limit=9999", headers=_admin_headers())

    assert resp.status_code == 200
    assert seen["limit"] == 500
    assert resp.json() == {"items": []}


def test_admin_quotes_default_limit_unchanged(monkeypatch: pytest.MonkeyPatch, admin_env: None) -> None:
    seen: dict[str, int] = {}

    def fake_list_quotes(limit: int = 50):
        seen["limit"] = limit
        return []

    monkeypatch.setattr("app.main.list_quotes", fake_list_quotes)

    with TestClient(app) as client:
        resp = client.get("/admin/api/quotes", headers=_admin_headers())

    assert resp.status_code == 200
    assert seen["limit"] == 50
    assert resp.json() == {"items": []}
