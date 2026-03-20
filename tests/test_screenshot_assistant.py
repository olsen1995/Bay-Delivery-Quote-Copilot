import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage.DB_PATH = tmp_path / "test-screenshot-assistant.sqlite3"
    storage._TABLE_COL_CACHE.clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    storage.init_db()
    yield
    storage._TABLE_COL_CACHE.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def configure_upload_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.main._drive_enabled", lambda: True)
    monkeypatch.setattr("app.main._maybe_auto_snapshot", lambda _background_tasks: None)
    monkeypatch.setattr("app.main._drive_call", lambda _desc, fn: fn())
    monkeypatch.setattr(
        "app.main.gdrive.ensure_vault_subfolders",
        lambda: {"uploads": "uploads-folder"},
    )
    monkeypatch.setattr(
        "app.main.gdrive.ensure_folder",
        lambda _name, _parent: SimpleNamespace(file_id="assistant-folder"),
    )
    monkeypatch.setattr(
        "app.main.gdrive.upload_bytes",
        lambda **_kwargs: SimpleNamespace(file_id="file-1", web_view_link="https://example.com/file-1"),
    )


def test_screenshot_assistant_admin_only_access_control(client: TestClient) -> None:
    payload = {
        "message": "Customer sent screenshots of a dump run.",
        "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.5, "crew_size": 2},
        "operator_overrides": {},
        "screenshot_attachment_ids": [],
    }

    unauthorized = client.post("/admin/api/screenshot-assistant/analyses/intake", json=payload)
    assert unauthorized.status_code in {401, 403}

    authorized = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json=payload,
    )
    assert authorized.status_code == 200

    listing = client.get("/admin/api/screenshot-assistant/analyses", headers=admin_headers())
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1


def test_screenshot_assistant_persists_analysis_and_links_attachments(client: TestClient) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-screenshot-1",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "prequote.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
        }
    )

    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Estimate this screenshot thread for haul away.",
            "screenshot_attachment_ids": ["att-screenshot-1"],
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.25, "crew_size": 2},
            "operator_overrides": {"job_address": "123 Example St"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    analysis_id = body["analysis_id"]

    saved = storage.get_screenshot_assistant_analysis(analysis_id)
    assert saved is not None
    assert saved["status"] == "draft"
    assert saved["operator_username"] == "admin"
    assert saved["guidance_json"]["recommendation_only"] is True

    linked_attachments = storage.list_attachments(analysis_id=analysis_id)
    assert len(linked_attachments) == 1
    assert linked_attachments[0]["attachment_id"] == "att-screenshot-1"

    exported = storage.export_db_to_json()
    analysis_rows = exported["tables"]["screenshot_assistant_analyses"]
    assert len(analysis_rows) == 1
    assert analysis_rows[0]["analysis_id"] == analysis_id
    assert analysis_rows[0]["guidance_json"]["recommendation_only"] is True


def test_screenshot_assistant_structured_output_contract(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Need a delivery recommendation from one condo to another.",
            "candidate_inputs": {
                "service_type": "item_delivery",
                "estimated_hours": 2.0,
                "crew_size": 2,
                "pickup_address": "1 Pickup Ave",
                "dropoff_address": "2 Dropoff Rd",
                "job_address": "2 Dropoff Rd",
            },
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "analysis_id",
        "created_at",
        "updated_at",
        "operator_username",
        "status",
        "quote_id",
        "intake",
        "normalized_candidate",
        "quote_guidance",
        "attachments",
        "recommendation_only",
    }
    assert body["status"] == "draft"
    assert body["recommendation_only"] is True
    assert body["quote_guidance"]["source"] == "existing_quote_pricing_logic"
    assert body["quote_guidance"]["service_type"] == "item_delivery"
    assert isinstance(body["quote_guidance"]["cash_total_cad"], float)
    assert isinstance(body["quote_guidance"]["emt_total_cad"], float)
    assert isinstance(body["quote_guidance"]["disclaimer"], str)
    assert body["normalized_candidate"]["pickup_address"] == "1 Pickup Ave"
    assert body["normalized_candidate"]["dropoff_address"] == "2 Dropoff Rd"


def test_screenshot_assistant_upload_requires_admin_and_persists_analysis_link(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_upload_mocks(monkeypatch)

    create_response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Start a draft before uploading screenshots.",
            "candidate_inputs": {"service_type": "haul_away"},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    assert create_response.status_code == 200
    analysis_id = create_response.json()["analysis_id"]

    unauthorized = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments",
        files=[("files", ("photo.jpg", b"\xff\xd8\xff" + (b"a" * 32), "image/jpeg"))],
    )
    assert unauthorized.status_code in {401, 403}

    authorized = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments",
        headers=admin_headers(),
        files=[("files", ("photo.jpg", b"\xff\xd8\xff" + (b"a" * 32), "image/jpeg"))],
    )
    assert authorized.status_code == 200

    payload = authorized.json()
    assert payload["ok"] is True
    assert payload["analysis_id"] == analysis_id
    assert len(payload["uploaded"]) == 1
    assert payload["uploaded"][0]["analysis_id"] == analysis_id

    attachments = storage.list_attachments(analysis_id=analysis_id)
    assert len(attachments) == 1
    assert attachments[0]["analysis_id"] == analysis_id
    assert attachments[0]["quote_id"] is None


def test_screenshot_assistant_upload_rejects_invalid_file_type(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_upload_mocks(monkeypatch)

    create_response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Draft for invalid upload validation.",
            "candidate_inputs": {"service_type": "haul_away"},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    analysis_id = create_response.json()["analysis_id"]

    response = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments",
        headers=admin_headers(),
        files=[("files", ("notes.txt", b"plain text is not an image", "text/plain"))],
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported image type (use JPG/PNG/WEBP/GIF)."}
    assert storage.list_attachments(analysis_id=analysis_id) == []


def test_screenshot_assistant_upload_over_12mb_returns_413(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/analysis-123/attachments",
        headers={"content-length": str((12 * 1024 * 1024) + 1), **admin_headers()},
        data=b"",
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "payload too large"}


def test_screenshot_assistant_analysis_can_be_updated_in_place(client: TestClient) -> None:
    create_response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Initial draft",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    update_response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "analysis_id": created["analysis_id"],
            "message": "Updated draft",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 2.0},
            "operator_overrides": {"job_address": "456 Updated St"},
            "screenshot_attachment_ids": [],
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["analysis_id"] == created["analysis_id"]
    assert updated["created_at"] == created["created_at"]
    assert updated["normalized_candidate"]["estimated_hours"] == 2.0
    assert updated["normalized_candidate"]["job_address"] == "456 Updated St"
    assert updated["quote_id"] is None


def test_create_quote_draft_from_screenshot_analysis_success_and_attachment_linkage(client: TestClient) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-analysis-quote",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "prequote.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
        }
    )

    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Customer asked for a haul away estimate.",
            "screenshot_attachment_ids": ["att-analysis-quote"],
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.5, "crew_size": 2},
            "operator_overrides": {"job_address": "123 Review St", "customer_name": "Taylor", "customer_phone": "555-0101"},
        },
    )
    assert create_analysis.status_code == 200
    analysis_id = create_analysis.json()["analysis_id"]

    response = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["analysis"]["analysis_id"] == analysis_id
    assert body["analysis"]["quote_id"] == body["quote"]["quote_id"]
    assert "accept_token" not in body["quote"]

    saved_quote = storage.get_quote_record(body["quote"]["quote_id"])
    assert saved_quote is not None
    assert saved_quote["request"]["job_address"] == "123 Review St"
    assert saved_quote["request"]["customer_name"] == "Taylor"
    assert saved_quote["request"]["customer_phone"] == "555-0101"

    saved_analysis = storage.get_screenshot_assistant_analysis(analysis_id)
    assert saved_analysis is not None
    assert saved_analysis["quote_id"] == body["quote"]["quote_id"]

    attachments = storage.list_attachments(analysis_id=analysis_id)
    assert len(attachments) == 1
    assert attachments[0]["analysis_id"] == analysis_id
    assert attachments[0]["quote_id"] == body["quote"]["quote_id"]


def test_create_quote_draft_from_screenshot_analysis_requires_admin(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Need a reviewed estimate.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    analysis_id = create_analysis.json()["analysis_id"]

    unauthorized = client.post(f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft")
    assert unauthorized.status_code in {401, 403}


def test_create_quote_draft_from_screenshot_analysis_missing_analysis_returns_404(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/missing-analysis/quote-draft",
        headers=admin_headers(),
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Screenshot assistant analysis not found."}

    audit_items = storage.list_admin_audit_log(limit=5)
    assert audit_items[0]["action_type"] == "create_quote_draft"
    assert audit_items[0]["entity_type"] == "screenshot_assistant_analysis"
    assert audit_items[0]["record_id"] == "missing-analysis"
    assert audit_items[0]["success"] is False


def test_create_quote_draft_from_screenshot_analysis_blocks_duplicate_creation(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Need a reviewed estimate.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    analysis_id = create_analysis.json()["analysis_id"]

    first = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert first.status_code == 200

    second = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "Quote draft already exists for this analysis."}


def test_create_quote_draft_uses_normalized_candidate_as_source_of_truth(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Raw message should not override reviewed values.",
            "candidate_inputs": {
                "service_type": "haul_away",
                "estimated_hours": 1.0,
                "crew_size": 1,
                "job_address": "111 Raw St",
                "customer_name": "Raw Name",
            },
            "operator_overrides": {
                "job_address": "222 Reviewed Ave",
                "estimated_hours": 2.5,
                "customer_name": "Reviewed Name",
            },
            "screenshot_attachment_ids": [],
        },
    )
    assert create_analysis.status_code == 200
    analysis = create_analysis.json()

    response = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis['analysis_id']}/quote-draft",
        headers=admin_headers(),
    )
    assert response.status_code == 200

    saved_quote = storage.get_quote_record(response.json()["quote"]["quote_id"])
    assert saved_quote is not None
    assert saved_quote["request"]["job_address"] == analysis["normalized_candidate"]["job_address"] == "222 Reviewed Ave"
    assert saved_quote["request"]["estimated_hours"] == analysis["normalized_candidate"]["estimated_hours"] == 2.5
    assert saved_quote["request"]["customer_name"] == analysis["normalized_candidate"]["customer_name"] == "Reviewed Name"


def test_create_quote_draft_logs_success_audit_entry(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Need a reviewed estimate.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    analysis_id = create_analysis.json()["analysis_id"]

    response = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert response.status_code == 200

    audit_items = storage.list_admin_audit_log(limit=10)
    matching = [item for item in audit_items if item["action_type"] == "create_quote_draft" and item["record_id"] == analysis_id]
    assert matching
    assert matching[0]["entity_type"] == "screenshot_assistant_analysis"
    assert matching[0]["success"] is True
