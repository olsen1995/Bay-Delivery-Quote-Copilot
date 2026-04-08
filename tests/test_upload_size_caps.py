from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


def test_upload_over_12mb_returns_413():
    with TestClient(app) as client:
        response = client.post(
            "/quote/upload-photos",
            headers={"content-length": str((12 * 1024 * 1024) + 1)},
            content=b"",
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "payload too large"}


def test_normal_upload_succeeds(monkeypatch):
    monkeypatch.setattr(
        "app.main.get_quote_record",
        lambda quote_id: {"quote_id": quote_id, "accept_token": "token-1", "created_at": "2099-01-01T00:00:00+00:00"},
    )
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._drive_call", lambda _desc, fn: fn())
    monkeypatch.setattr("app.main.save_attachment", lambda _payload: None)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)

    monkeypatch.setattr(
        "app.main.gdrive.ensure_vault_subfolders",
        lambda: {"uploads": "uploads-folder"},
    )
    monkeypatch.setattr(
        "app.main.gdrive.ensure_folder",
        lambda _name, _parent: SimpleNamespace(file_id="quote-folder"),
    )
    monkeypatch.setattr(
        "app.main.gdrive.upload_bytes",
        lambda **_kwargs: SimpleNamespace(file_id="file-1", web_view_link="https://example.com/file-1"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/quote/upload-photos",
            data={"quote_id": "quote-1", "accept_token": "token-1"},
            files=[("files", ("image.jpg", b"\xff\xd8\xff" + (b"a" * 20), "image/jpeg"))],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["uploaded"]) == 1


def test_upload_missing_accept_token_returns_422_and_no_side_effects(monkeypatch):
    upload_calls = 0
    save_calls = 0

    def _upload_bytes(**_kwargs):
        nonlocal upload_calls
        upload_calls += 1
        return SimpleNamespace(file_id="file-1", web_view_link="https://example.com/file-1")

    def _save_attachment(_payload):
        nonlocal save_calls
        save_calls += 1

    monkeypatch.setattr(
        "app.main.get_quote_record",
        lambda quote_id: {"quote_id": quote_id, "accept_token": "token-1", "created_at": "2099-01-01T00:00:00+00:00"},
    )
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._drive_call", lambda _desc, fn: fn())
    monkeypatch.setattr("app.main.save_attachment", _save_attachment)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)
    monkeypatch.setattr("app.main.gdrive.upload_bytes", _upload_bytes)

    with TestClient(app) as client:
        response = client.post(
            "/quote/upload-photos",
            data={"quote_id": "quote-1"},
            files=[("files", ("image.jpg", b"\xff\xd8\xff" + (b"a" * 20), "image/jpeg"))],
        )

    assert response.status_code == 422
    assert upload_calls == 0
    assert save_calls == 0


def test_upload_invalid_accept_token_returns_401_and_no_side_effects(monkeypatch):
    upload_calls = 0
    save_calls = 0

    def _upload_bytes(**_kwargs):
        nonlocal upload_calls
        upload_calls += 1
        return SimpleNamespace(file_id="file-1", web_view_link="https://example.com/file-1")

    def _save_attachment(_payload):
        nonlocal save_calls
        save_calls += 1

    monkeypatch.setattr(
        "app.main.get_quote_record",
        lambda quote_id: {"quote_id": quote_id, "accept_token": "token-1", "created_at": "2099-01-01T00:00:00+00:00"},
    )
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._drive_call", lambda _desc, fn: fn())
    monkeypatch.setattr("app.main.save_attachment", _save_attachment)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)
    monkeypatch.setattr("app.main.gdrive.upload_bytes", _upload_bytes)

    with TestClient(app) as client:
        response = client.post(
            "/quote/upload-photos",
            data={"quote_id": "quote-1", "accept_token": "wrong-token"},
            files=[("files", ("image.jpg", b"\xff\xd8\xff" + (b"a" * 20), "image/jpeg"))],
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired accept token."}
    assert upload_calls == 0
    assert save_calls == 0


def test_upload_valid_accept_token_returns_200_with_unchanged_response_shape(monkeypatch):
    monkeypatch.setattr(
        "app.main.get_quote_record",
        lambda quote_id: {"quote_id": quote_id, "accept_token": "token-1", "created_at": "2099-01-01T00:00:00+00:00"},
    )
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._drive_call", lambda _desc, fn: fn())
    monkeypatch.setattr("app.main.save_attachment", lambda _payload: None)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)

    monkeypatch.setattr(
        "app.main.gdrive.ensure_vault_subfolders",
        lambda: {"uploads": "uploads-folder"},
    )
    monkeypatch.setattr(
        "app.main.gdrive.ensure_folder",
        lambda _name, _parent: SimpleNamespace(file_id="quote-folder"),
    )
    monkeypatch.setattr(
        "app.main.gdrive.upload_bytes",
        lambda **_kwargs: SimpleNamespace(file_id="file-1", web_view_link="https://example.com/file-1"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/quote/upload-photos",
            data={"quote_id": "quote-1", "accept_token": "token-1"},
            files=[("files", ("image.jpg", b"\xff\xd8\xff" + (b"a" * 20), "image/jpeg"))],
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"ok", "uploaded"}
    assert payload["ok"] is True
    assert isinstance(payload["uploaded"], list)
    assert len(payload["uploaded"]) == 1
    assert set(payload["uploaded"][0].keys()) == {
        "attachment_id",
        "filename",
        "drive_file_id",
        "drive_web_view_link",
    }


def test_admin_db_import_allows_larger_than_json_cap():
    with TestClient(app) as client:
        response = client.post(
            "/admin/api/db/import",
            headers={"content-length": str(1024 * 1024)},
            json={"meta": {}, "quotes": [], "quote_requests": [], "jobs": [], "attachments": []},
        )

    assert response.status_code != 413
