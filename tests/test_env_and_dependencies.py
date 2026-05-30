import importlib
import builtins
import logging
import os
import pytest

from fastapi.testclient import TestClient


_RENDER_ENV_MARKERS = ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_HOSTNAME")


# helpers for reloading main with fresh environment

def _reload_main_with_env(env_vars: dict[str, str]) -> object:
    # clear both envs then set provided ones
    for var in (
        "BAYDELIVERY_CORS_ORIGINS",
        "CORS_ORIGINS",
        "LOCAL_TIMEZONE",
        "BAYDELIVERY_COMMIT_SHA",
        "RENDER_GIT_COMMIT",
        *_RENDER_ENV_MARKERS,
    ):
        os.environ.pop(var, None)
    os.environ.update(env_vars)
    # reload module so CORS middleware is reconfigured
    import app.main as main
    importlib.reload(main)
    return main


def test_warns_when_local_timezone_missing(caplog):
    caplog.set_level(logging.WARNING)

    _reload_main_with_env({"BAYDELIVERY_CORS_ORIGINS": "https://foo"})

    assert "LOCAL_TIMEZONE is unset; falling back to UTC." in caplog.text


def test_warns_when_local_timezone_invalid(caplog):
    caplog.set_level(logging.WARNING)

    _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "LOCAL_TIMEZONE": "Mars/Olympus",
        }
    )

    assert "LOCAL_TIMEZONE='Mars/Olympus' is invalid; falling back to UTC." in caplog.text


def test_warns_when_using_legacy_cors_env(caplog):
    caplog.set_level(logging.WARNING)

    _reload_main_with_env(
        {
            "CORS_ORIGINS": "https://bar",
            "LOCAL_TIMEZONE": "America/Toronto",
        }
    )

    assert "BAYDELIVERY_CORS_ORIGINS is unset; using legacy CORS_ORIGINS." in caplog.text


def test_warns_when_using_localhost_cors_defaults(caplog):
    caplog.set_level(logging.WARNING)

    _reload_main_with_env({"LOCAL_TIMEZONE": "America/Toronto"})

    assert "BAYDELIVERY_CORS_ORIGINS is unset; falling back to localhost CORS defaults." in caplog.text


def test_cors_from_new_env(monkeypatch):
    # ensure the configured origin is actually allowed by making a real request
    main = _reload_main_with_env({"BAYDELIVERY_CORS_ORIGINS": "https://foo"})
    with TestClient(main.app) as client:
        resp = client.get("/", headers={"Origin": "https://foo"})
    assert resp.headers.get("access-control-allow-origin") == "https://foo"


def test_cors_fallback_old_env(monkeypatch):
    main = _reload_main_with_env({"CORS_ORIGINS": "https://bar"})
    with TestClient(main.app) as client:
        resp = client.get("/", headers={"Origin": "https://bar"})
    assert resp.headers.get("access-control-allow-origin") == "https://bar"


def test_cors_default(monkeypatch):
    main = _reload_main_with_env({})
    # default origins include the localhost values from the code
    with TestClient(main.app) as client:
        resp = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_api_docs_remain_available_without_render_markers() -> None:
    main = _reload_main_with_env({"BAYDELIVERY_CORS_ORIGINS": "https://foo"})

    with TestClient(main.app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize("render_marker", _RENDER_ENV_MARKERS)
def test_api_docs_are_disabled_when_render_marker_is_present(render_marker: str) -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            render_marker: "render-test",
        }
    )

    with TestClient(main.app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_health_remains_available_when_render_marker_is_present() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "RENDER_SERVICE_ID": "srv-test",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200


def test_health_commit_is_null_when_commit_envs_missing() -> None:
    main = _reload_main_with_env({"BAYDELIVERY_CORS_ORIGINS": "https://foo"})

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] is None


def test_health_commit_prefers_explicit_baydelivery_commit_sha() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "BAYDELIVERY_COMMIT_SHA": "ABCDEF1234567890ABCDEF1234567890ABCDEF12",
            "RENDER_GIT_COMMIT": "abcdef1234567890abcdef1234567890abcdef12",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] == "abcdef123456"


def test_health_commit_returns_null_for_short_explicit_commit() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "BAYDELIVERY_COMMIT_SHA": "abcdef12345",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] is None


def test_health_commit_returns_null_for_non_hex_explicit_commit() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "BAYDELIVERY_COMMIT_SHA": "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] is None


def test_health_commit_falls_back_to_render_git_commit() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "RENDER_GIT_COMMIT": "abcdef1234567890abcdef1234567890abcdef12",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] == "abcdef123456"


def test_health_commit_falls_back_when_explicit_commit_invalid() -> None:
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://foo",
            "BAYDELIVERY_COMMIT_SHA": "not-a-valid-commit",
            "RENDER_GIT_COMMIT": "abcdef1234567890abcdef1234567890abcdef12",
        }
    )

    with TestClient(main.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["commit"] == "abcdef123456"


def _admin_basic_header() -> str:
    import base64

    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return f"Basic {token}"


_DRIVE_RESTORE_PAYLOAD = {"file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"}

_PUBLIC_QUOTE_PAYLOAD = {
    "customer_name": "Origin Tester",
    "customer_phone": "705-555-0100",
    "job_address": "123 Main St",
    "job_description_customer": "desc",
    "description": "desc",
    "service_type": "haul_away",
    "payment_method": "cash",
    "pickup_address": "1 Pickup Rd",
    "dropoff_address": "2 Dropoff Ave",
    "estimated_hours": 1.0,
    "crew_size": 1,
    "garbage_bag_count": 0,
    "trailer_fill_estimate": "under_quarter",
    "mattresses_count": 0,
    "box_springs_count": 0,
    "scrap_pickup_location": "curbside",
    "travel_zone": "in_town",
}


def test_admin_post_allows_matching_origin(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )
    monkeypatch.setattr(main, "_drive_enabled", lambda: False)

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Origin": "https://admin.example.com",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 501
    assert "Google Drive not configured." in resp.json()["detail"]


def test_admin_post_rejects_mismatched_origin(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Origin": "https://evil.example.com",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed for admin POST request."


def test_admin_post_rejects_missing_all_browser_provenance_headers(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={"Authorization": _admin_basic_header()},
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed for admin POST request."


def test_admin_post_allows_missing_origin_with_matching_referer(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )
    monkeypatch.setattr(main, "_drive_enabled", lambda: False)

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Referer": "https://admin.example.com/admin",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 501
    assert "Google Drive not configured." in resp.json()["detail"]


def test_admin_post_allows_missing_origin_with_same_origin_browser_context(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )
    monkeypatch.setattr(main, "_drive_enabled", lambda: False)

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Sec-Fetch-Site": "same-origin",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 501
    assert "Google Drive not configured." in resp.json()["detail"]


def test_admin_post_rejects_missing_origin_with_cross_site_browser_context(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Sec-Fetch-Site": "cross-site",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed for admin POST request."


def test_admin_post_rejects_missing_origin_with_hostile_referer(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with TestClient(main.app) as client:
        resp = client.post(
            "/admin/api/drive/restore",
            headers={
                "Authorization": _admin_basic_header(),
                "Referer": "https://evil.example.com/admin",
            },
            json=_DRIVE_RESTORE_PAYLOAD,
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed for admin POST request."


def test_admin_get_read_endpoint_is_not_subject_to_post_origin_gate(monkeypatch):
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )
    monkeypatch.setattr(main, "_drive_enabled", lambda: False)

    with TestClient(main.app) as client:
        resp = client.get("/admin/api/drive/status", headers={"Authorization": _admin_basic_header()})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "drive_configured": False}


def test_public_quote_calculate_is_not_subject_to_admin_post_origin_gate():
    main = _reload_main_with_env(
        {
            "BAYDELIVERY_CORS_ORIGINS": "https://admin.example.com",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with TestClient(main.app) as client:
        resp = client.post("/quote/calculate", json=_PUBLIC_QUOTE_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["request"]["service_type"] == "haul_away"


def test_google_drive_libs_optional(monkeypatch):
    """Ensure gdrive module can be imported and functions gracefully when google-auth missing."""
    # force any google import to fail
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("google"):
            raise ModuleNotFoundError(f"No module named {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    import importlib
    import app.gdrive as gdrive
    importlib.reload(gdrive)

    # basic API should exist without error
    assert callable(gdrive.is_configured)

    # _require_google_libs should raise DriveNotConfigured when deps are missing
    with pytest.raises(gdrive.DriveNotConfigured):
        gdrive._require_google_libs()
