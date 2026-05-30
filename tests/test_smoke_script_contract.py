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
            '<div id="adminProtectedDashboard" hidden aria-hidden="true"></div></html>'
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


def test_live_safe_health_version_check_passes_when_health_matches_repo_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.11.0\n", encoding="utf-8")

    monkeypatch.setattr(smoke_test, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("BASE_URL", "https://example.test/")

    smoke_test._check_health_version({"version": "0.11.0"})


def test_live_safe_health_version_check_reports_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.11.0\n", encoding="utf-8")

    monkeypatch.setattr(smoke_test, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("BASE_URL", "https://example.test/")

    with pytest.raises(AssertionError) as exc_info:
        smoke_test._check_health_version({"version": "0.10.9"})

    message = str(exc_info.value)
    assert "expected repo VERSION 0.11.0" in message
    assert "actual live /health version 0.10.9" in message
    assert "https://example.test/health" in message


def test_live_safe_health_version_check_reports_missing_live_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.11.0\n", encoding="utf-8")

    monkeypatch.setattr(smoke_test, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("BASE_URL", "https://example.test/")

    with pytest.raises(AssertionError) as exc_info:
        smoke_test._check_health_version({})

    message = str(exc_info.value)
    assert "expected repo VERSION 0.11.0" in message
    assert "actual live /health version <missing>" in message
    assert "https://example.test/health" in message


def test_live_safe_health_version_check_uses_existing_health_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_api(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
        del method, payload, headers
        if path == "/health":
            return 200, {"ok": False, "version": "0.11.0"}
        raise AssertionError(f"Unexpected smoke API call: {path}")

    monkeypatch.setattr(smoke_test, "api", fake_api)

    with pytest.raises(AssertionError, match=r"GET /health expected \{'ok': true\}"):
        smoke_test._run_live_safe_smoke(check_health_version=True)


def test_live_safe_health_commit_check_passes_when_health_matches_checked_out_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASE_URL", "https://example.test/")
    monkeypatch.setattr(smoke_test, "_checked_out_head_commit", lambda: "abcdef1234567890")

    smoke_test._check_health_commit({"commit": "abcdef123456"})


def test_live_safe_health_commit_check_reports_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BASE_URL", "https://example.test/")
    monkeypatch.setattr(smoke_test, "_checked_out_head_commit", lambda: "abcdef1234567890")

    with pytest.raises(AssertionError) as exc_info:
        smoke_test._check_health_commit({"commit": "feedface0000"})

    message = str(exc_info.value)
    assert "expected checked-out HEAD abcdef123456" in message
    assert "actual live /health commit feedface0000" in message
    assert "https://example.test/health" in message


def test_live_safe_health_commit_check_skips_when_live_commit_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BASE_URL", "https://example.test/")
    monkeypatch.setattr(smoke_test, "_checked_out_head_commit", lambda: "abcdef1234567890")

    smoke_test._check_health_commit({})

    captured = capsys.readouterr()
    assert "Deployed commit fingerprint unavailable; skipped exact commit match." in captured.out


def test_live_safe_without_commit_flag_does_not_read_checked_out_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, payload: dict | None = None, headers: dict | None = None):
        del payload, headers
        calls.append((method, path))
        if path == "/health":
            return 200, {"ok": True, "version": "0.11.0", "commit": "abcdef123456"}
        if path == "/":
            return 200, '<html><a href="/quote">Get a Quote</a></html>'
        if path == "/quote":
            return 200, '<html><form id="quoteForm"></form></html>'
        if path == "/admin":
            return 200, '<html><h2>Admin Access</h2><button id="refreshBtn"></button></html>'
        if path == "/admin/uploads":
            return 200, '<html><h2>Customer Uploads</h2><button id="btnSearch"></button></html>'
        if path == "/admin/api/uploads?limit=1":
            return 503, {"detail": "not configured"}
        raise AssertionError(f"Unexpected smoke API call: {method} {path}")

    def fail_if_called() -> str:
        raise AssertionError("checked-out HEAD should not be read without --check-health-commit")

    monkeypatch.setattr(smoke_test, "api", fake_api)
    monkeypatch.setattr(smoke_test, "_checked_out_head_commit", fail_if_called)
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    assert smoke_test._run_live_safe_smoke() == 0
    assert ("GET", "/health") in calls


def test_live_safe_mode_dispatches_health_version_check_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, bool] = {}

    def fake_live_safe(
        *,
        check_gpt_observability: bool = False,
        check_health_version: bool = False,
        check_health_commit: bool = False,
    ) -> int:
        received["check_gpt_observability"] = check_gpt_observability
        received["check_health_version"] = check_health_version
        received["check_health_commit"] = check_health_commit
        return 0

    monkeypatch.setattr(smoke_test, "_run_live_safe_smoke", fake_live_safe)
    monkeypatch.setattr(
        smoke_test.sys,
        "argv",
        ["smoke_test.py", "--mode", "live-safe", "--check-health-version"],
    )

    assert smoke_test.main() == 0
    assert received == {
        "check_gpt_observability": False,
        "check_health_version": True,
        "check_health_commit": False,
    }


def test_live_safe_mode_dispatches_health_commit_check_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, bool] = {}

    def fake_live_safe(
        *,
        check_gpt_observability: bool = False,
        check_health_version: bool = False,
        check_health_commit: bool = False,
    ) -> int:
        received["check_gpt_observability"] = check_gpt_observability
        received["check_health_version"] = check_health_version
        received["check_health_commit"] = check_health_commit
        return 0

    monkeypatch.setattr(smoke_test, "_run_live_safe_smoke", fake_live_safe)
    monkeypatch.setattr(
        smoke_test.sys,
        "argv",
        ["smoke_test.py", "--mode", "live-safe", "--check-health-commit"],
    )

    assert smoke_test.main() == 0
    assert received == {
        "check_gpt_observability": False,
        "check_health_version": False,
        "check_health_commit": True,
    }
