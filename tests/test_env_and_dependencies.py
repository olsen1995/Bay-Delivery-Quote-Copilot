import importlib
import builtins
import logging
import os
import pytest

from fastapi.testclient import TestClient


# helpers for reloading main with fresh environment

def _reload_main_with_env(env_vars: dict[str, str]) -> object:
    # clear both envs then set provided ones
    for var in ("BAYDELIVERY_CORS_ORIGINS", "CORS_ORIGINS", "LOCAL_TIMEZONE"):
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


def _admin_basic_header() -> str:
    import base64

    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return f"Basic {token}"


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
            json={"file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"},
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
            json={"file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"},
        )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed for admin POST request."


def test_admin_post_allows_missing_origin_for_compatibility(monkeypatch):
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
            headers={"Authorization": _admin_basic_header()},
            json={"file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"},
        )

    assert resp.status_code == 501
    assert "Google Drive not configured." in resp.json()["detail"]


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
