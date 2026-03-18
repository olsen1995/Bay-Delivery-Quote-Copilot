import base64
from pathlib import Path

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
