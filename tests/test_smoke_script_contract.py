from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.quote_service import build_quote_artifacts
from scripts import smoke_test


def _post_deploy_responses(path: str) -> object:
    responses = {
        "/health": {"ok": True, "version": "0.10.1", "commit": "3544537f1c36"},
        "/": '<html><a href="/quote">Get a Quote</a></html>',
        "/quote": '<html><form id="quoteForm"></form></html>',
        "/admin": (
            '<html><h2>Admin Access</h2><input id="adminUsername" />'
            '<input id="adminPassword" /><button id="refreshBtn"></button>'
            '<div id="adminProtectedDashboard" hidden aria-hidden="true" style="display:none"></div></html>'
        ),
        "/admin/mobile": (
            '<html><h2>Mobile Login</h2><input id="mobileAdminUsername" />'
            '<input id="mobileAdminPassword" /><button id="loginBtn"></button>'
            '<div id="authenticatedShell" hidden></div></html>'
        ),
    }
    return responses[path]


def test_stateful_smoke_haul_away_payload_matches_quote_contract() -> None:
    payload = smoke_test._stateful_haul_away_quote_payload()

    artifacts = build_quote_artifacts(dict(payload))

    assert artifacts["normalized_request"]["service_type"] == "haul_away"
    assert artifacts["normalized_request"]["trailer_fill_estimate"] == "under_quarter"


def test_stateful_smoke_haul_away_payload_requires_load_detail() -> None:
    payload = smoke_test._stateful_haul_away_quote_payload()
    payload.pop("trailer_fill_estimate")

    with pytest.raises(HTTPException, match="Please add at least one load detail") as exc_info:
        build_quote_artifacts(payload)

    assert exc_info.value.status_code == 400


def test_stateful_smoke_uses_contract_valid_haul_away_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    quote_payloads: list[dict] = []

    monkeypatch.setattr(smoke_test, "_run_health_check", lambda: {})
    monkeypatch.setattr(smoke_test, "_run_public_customer_page_checks", lambda: None)
    monkeypatch.setattr(smoke_test, "_run_admin_read_checks", lambda health: None)

    def fake_api(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
        del headers
        if method == "POST" and path == "/quote/calculate":
            assert payload is not None
            quote_payloads.append(dict(payload))
            if payload.get("service_type") == "small_move" and not payload.get("pickup_address"):
                return 400, {"detail": "pickup_address and dropoff_address are required"}
            build_quote_artifacts(dict(payload))
            return 200, {"quote_id": f"quote-{len(quote_payloads)}", "accept_token": "token"}
        if method == "POST" and path.startswith("/quote/") and path.endswith("/decision"):
            return 200, {"ok": True}
        raise AssertionError(f"Unexpected smoke API call: {method} {path}")

    monkeypatch.setattr(smoke_test, "api", fake_api)

    assert smoke_test._run_stateful_workflow_smoke() == 0
    assert quote_payloads[0]["service_type"] == "haul_away"
    assert quote_payloads[0]["trailer_fill_estimate"] == "under_quarter"


def test_post_deploy_smoke_checks_health_public_pages_and_pre_auth_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
        del payload, headers
        calls.append((method, path))
        assert method == "GET"
        assert not path.startswith("/admin/api/")
        assert "upload" not in path
        assert "booking" not in path
        assert "decision" not in path
        return 200, _post_deploy_responses(path)

    monkeypatch.setattr(smoke_test, "api", fake_api)

    assert smoke_test._run_post_deploy_live_smoke() == 0
    assert calls == [
        ("GET", "/health"),
        ("GET", "/"),
        ("GET", "/quote"),
        ("GET", "/admin"),
        ("GET", "/admin/mobile"),
    ]


@pytest.mark.parametrize(
    "health",
    [
        {"ok": False, "version": "0.10.1", "commit": "3544537f1c36"},
        {"ok": True, "commit": "3544537f1c36"},
        {"ok": True, "version": "0.10.1"},
    ],
)
def test_post_deploy_smoke_requires_health_ok_version_and_commit(
    monkeypatch: pytest.MonkeyPatch,
    health: dict,
) -> None:
    def fake_api(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
        del method, payload, headers
        if path == "/health":
            return 200, health
        return 200, _post_deploy_responses(path)

    monkeypatch.setattr(smoke_test, "api", fake_api)

    with pytest.raises(AssertionError):
        smoke_test._run_post_deploy_live_smoke()


def test_post_deploy_mode_dispatches_to_post_deploy_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_post_deploy() -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(smoke_test, "_run_post_deploy_live_smoke", fake_post_deploy)
    monkeypatch.setattr(smoke_test.sys, "argv", ["smoke_test.py", "--mode", "post-deploy"])

    assert smoke_test.main() == 0
    assert called is True
