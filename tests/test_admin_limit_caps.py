import base64

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app


@pytest.fixture
def admin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _bad_admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:wrong").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture(autouse=True)
def clear_admin_attempts(monkeypatch: pytest.MonkeyPatch):
    main_module._admin_failed_attempts.clear()
    yield
    main_module._admin_failed_attempts.clear()
    monkeypatch.delenv("BAYDELIVERY_TRUST_X_FORWARDED_FOR", raising=False)


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


def test_admin_lockout_uses_trusted_forwarded_ip_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    admin_env: None,
) -> None:
    monkeypatch.setenv("BAYDELIVERY_TRUST_X_FORWARDED_FOR", "true")

    with TestClient(app) as client:
        for _ in range(main_module._admin_lockout_threshold):
            resp = client.get(
                "/admin/api/quotes",
                headers={**_bad_admin_headers(), "X-Forwarded-For": "203.0.113.5"},
            )
            assert resp.status_code == 401

        blocked = client.get(
            "/admin/api/quotes",
            headers={**_bad_admin_headers(), "X-Forwarded-For": "203.0.113.5"},
        )
        other_ip = client.get(
            "/admin/api/quotes",
            headers={**_bad_admin_headers(), "X-Forwarded-For": "203.0.113.6"},
        )

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many failed login attempts. Try again later."}
    assert other_ip.status_code == 401


def test_admin_lockout_ignores_forwarded_ip_when_trust_disabled(
    monkeypatch: pytest.MonkeyPatch,
    admin_env: None,
) -> None:
    monkeypatch.delenv("BAYDELIVERY_TRUST_X_FORWARDED_FOR", raising=False)

    with TestClient(app) as client:
        for _ in range(main_module._admin_lockout_threshold):
            resp = client.get(
                "/admin/api/quotes",
                headers={**_bad_admin_headers(), "X-Forwarded-For": "203.0.113.5"},
            )
            assert resp.status_code == 401

        blocked = client.get(
            "/admin/api/quotes",
            headers={**_bad_admin_headers(), "X-Forwarded-For": "203.0.113.6"},
        )

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many failed login attempts. Try again later."}
