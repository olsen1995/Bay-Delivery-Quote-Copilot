import importlib
import os
import builtins
import pytest

from fastapi.testclient import TestClient


# helpers for reloading main with fresh environment

def _reload_main_with_env(env_vars: dict[str, str]) -> object:
    # clear both envs then set provided ones
    for var in ("BAYDELIVERY_CORS_ORIGINS", "CORS_ORIGINS"):
        os.environ.pop(var, None)
    os.environ.update(env_vars)
    # reload module so CORS middleware is reconfigured
    import app.main as main
    importlib.reload(main)
    return main


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
