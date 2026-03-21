import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.services.quote_service import build_quote_artifacts


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
    monkeypatch.setattr(
        "app.main.screenshot_ocr_service.extract_attachment_ocr",
        lambda **_kwargs: {
            "status": "success",
            "text": "Taylor 415-555-0199 123 Example St 2026-04-12 morning",
            "preview": "Taylor 415-555-0199 123 Example St 2026-04-12 morning",
            "warning": None,
        },
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
        "autofill_suggestions",
        "autofill_missing_fields",
        "autofill_warnings",
    }
    assert body["status"] == "draft"
    assert body["recommendation_only"] is True
    assert body["quote_guidance"]["source"] == "existing_quote_pricing_logic"
    assert body["quote_guidance"]["service_type"] == "item_delivery"
    assert isinstance(body["quote_guidance"]["cash_total_cad"], float)
    assert isinstance(body["quote_guidance"]["emt_total_cad"], float)
    assert isinstance(body["quote_guidance"]["disclaimer"], str)
    assert body["quote_guidance"]["range"]["recommended_target_cash_cad"] == body["quote_guidance"]["cash_total_cad"]
    assert isinstance(body["quote_guidance"]["range"]["minimum_safe_cash_cad"], float)
    assert isinstance(body["quote_guidance"]["range"]["upper_reasonable_cash_cad"], float)
    assert body["quote_guidance"]["confidence"] in {"high", "medium", "low"}
    assert isinstance(body["quote_guidance"]["unknowns"], list)
    assert isinstance(body["quote_guidance"]["risk_notes"], list)
    assert body["quote_guidance"]["range_basis"]["anchor"] == "existing_quote_engine_cash_total"
    assert body["normalized_candidate"]["pickup_address"] == "1 Pickup Ave"
    assert body["normalized_candidate"]["dropoff_address"] == "2 Dropoff Rd"
    assert isinstance(body["autofill_suggestions"], dict)
    assert isinstance(body["autofill_missing_fields"], list)
    assert isinstance(body["autofill_warnings"], list)


def test_screenshot_assistant_message_autofill_suggestions_are_persisted_separately(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": (
                "Hi, my name is Taylor. You can reach me at 415-555-0199. "
                "The address is 123 Example St. I need junk removed on 2026-04-12 in the morning."
            ),
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.5, "crew_size": 2},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["autofill_suggestions"]["customer_name"] == {
        "value": "Taylor",
        "confidence": "medium",
        "source": "message",
        "needs_review": True,
    }
    assert body["autofill_suggestions"]["customer_phone"]["value"] == "(415) 555-0199"
    assert body["autofill_suggestions"]["job_address"]["value"] == "123 Example St"
    assert body["autofill_suggestions"]["requested_job_date"]["value"] == "2026-04-12"
    assert body["autofill_suggestions"]["requested_time_window"]["value"] == "morning"
    assert body["autofill_suggestions"]["description"]["source"] == "message"
    assert body["autofill_missing_fields"] == []
    assert body["normalized_candidate"]["customer_name"] == ""
    assert body["normalized_candidate"]["customer_phone"] == ""
    assert body["normalized_candidate"]["job_address"] == ""
    assert body["intake"]["autofill_suggestions"]["customer_phone"]["value"] == "(415) 555-0199"


def test_screenshot_assistant_message_autofill_reports_missing_fields_and_warnings(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["autofill_suggestions"] == {}
    assert body["autofill_missing_fields"] == [
        "customer_name",
        "customer_phone",
        "job_address",
        "description",
        "requested_job_date",
        "requested_time_window",
    ]
    assert body["autofill_warnings"] == ["Paste a customer message to generate autofill suggestions."]


def test_screenshot_assistant_quote_range_is_ordered_and_target_is_engine_anchor(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Reviewed haul-away request with enough detail for a normal recommendation.",
            "candidate_inputs": {
                "service_type": "haul_away",
                "estimated_hours": 2.0,
                "crew_size": 2,
                "garbage_bag_count": 8,
                "job_address": "123 Example St",
                "description": "Eight light bags from a garage with normal access and confirmed reviewed scope.",
            },
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    guidance = response.json()["quote_guidance"]
    assert guidance["range"]["minimum_safe_cash_cad"] <= guidance["range"]["recommended_target_cash_cad"]
    assert guidance["range"]["recommended_target_cash_cad"] <= guidance["range"]["upper_reasonable_cash_cad"]
    assert guidance["range"]["recommended_target_cash_cad"] == guidance["cash_total_cad"]


def test_screenshot_assistant_reviewed_description_in_normalized_payload_does_not_trigger_minimal_unknown(
    client: TestClient,
) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Reviewed haul-away request with pricing fields confirmed.",
            "candidate_inputs": {
                "service_type": "haul_away",
                "estimated_hours": 2.0,
                "crew_size": 2,
                "garbage_bag_count": 8,
                "job_address": "123 Example St",
                "description": "Eight reviewed bags from a garage with normal access and confirmed quoted scope.",
            },
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    guidance = response.json()["quote_guidance"]
    assert "Reviewed description is still minimal." not in guidance["unknowns"]
    assert guidance["confidence"] == "high"
    assert guidance["range"]["minimum_safe_cash_cad"] <= guidance["range"]["recommended_target_cash_cad"]


def test_screenshot_assistant_requested_date_and_window_round_trip_without_affecting_guidance(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Customer asked for morning availability and shared a haul-away request.",
            "requested_job_date": "2026-04-12",
            "requested_time_window": "morning",
            "candidate_inputs": {
                "service_type": "haul_away",
                "estimated_hours": 1.25,
                "crew_size": 2,
                "customer_name": "Taylor",
                "customer_phone": "(415) 555-0199",
                "job_address": "123 Example St",
                "description": "Reviewed draft description",
            },
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intake"]["requested_job_date"] == "2026-04-12"
    assert body["intake"]["requested_time_window"] == "morning"
    assert body["autofill_missing_fields"] == []
    assert body["normalized_candidate"]["customer_name"] == "Taylor"
    assert body["normalized_candidate"]["customer_phone"] == "(415) 555-0199"
    assert body["normalized_candidate"]["job_address"] == "123 Example St"
    assert body["normalized_candidate"]["job_description_customer"] == "Reviewed draft description"
    assert body["quote_guidance"]["service_type"] == "haul_away"

    detail = client.get(
        f"/admin/api/screenshot-assistant/analyses/{body['analysis_id']}",
        headers=admin_headers(),
    )
    assert detail.status_code == 200
    assert detail.json()["intake"]["requested_job_date"] == "2026-04-12"

    listing = client.get("/admin/api/screenshot-assistant/analyses", headers=admin_headers())
    assert listing.status_code == 200
    list_item = listing.json()["items"][0]
    assert "autofill_suggestions" not in list_item
    assert "autofill_suggestions" not in list_item["intake"]


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
    assert attachments[0]["ocr_json"]["status"] == "success"


def test_screenshot_assistant_upload_stores_ocr_failure_without_blocking_upload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_upload_mocks(monkeypatch)
    monkeypatch.setattr(
        "app.main.screenshot_ocr_service.extract_attachment_ocr",
        lambda **_kwargs: {
            "status": "failed",
            "text": "",
            "preview": "",
            "warning": "OCR failed for this screenshot. Upload still succeeded.",
        },
    )

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
    analysis_id = create_response.json()["analysis_id"]

    upload = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments",
        headers=admin_headers(),
        files=[("files", ("photo.jpg", b"\xff\xd8\xff" + (b"a" * 32), "image/jpeg"))],
    )

    assert upload.status_code == 200
    attachment = storage.list_attachments(analysis_id=analysis_id)[0]
    assert attachment["ocr_json"]["status"] == "failed"
    assert attachment["ocr_json"]["warning"] == "OCR failed for this screenshot. Upload still succeeded."


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


def test_screenshot_assistant_low_information_analysis_keeps_minimum_safe_at_target(client: TestClient) -> None:
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "",
            "candidate_inputs": {"estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    guidance = response.json()["quote_guidance"]
    assert guidance["confidence"] == "low"
    assert guidance["range"]["minimum_safe_cash_cad"] == guidance["range"]["recommended_target_cash_cad"]
    assert any("default assistant assumption" in item.lower() for item in guidance["unknowns"])
    assert any("reviewed description" in item.lower() for item in guidance["unknowns"])


def test_screenshot_assistant_ocr_autofill_can_fill_v1a_fields_without_message(client: TestClient) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-ocr-1",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "thread.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
            "ocr_json": {
                "status": "success",
                "text": "Hi my name is Taylor. Call me at 415-555-0199. Address is 123 Example St. 2026-04-12 morning.",
                "preview": "Hi my name is Taylor. Call me at 415-555-0199.",
                "warning": None,
            },
        }
    )

    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": ["att-ocr-1"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["autofill_suggestions"]["customer_name"]["source"] == "ocr"
    assert body["autofill_suggestions"]["customer_phone"]["value"] == "(415) 555-0199"
    assert body["autofill_suggestions"]["job_address"]["value"] == "123 Example St"
    assert body["autofill_suggestions"]["requested_job_date"]["value"] == "2026-04-12"
    assert body["autofill_suggestions"]["requested_time_window"]["value"] == "morning"
    assert body["autofill_suggestions"]["description"]["source"] == "ocr"
    assert body["normalized_candidate"]["customer_name"] == ""


def test_screenshot_assistant_combines_message_and_ocr_sources_without_overwriting_description(client: TestClient) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-ocr-2",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "thread.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
            "ocr_json": {
                "status": "success",
                "text": "My name is Taylor. 415-555-0199. 123 Example St.",
                "preview": "My name is Taylor. 415-555-0199. 123 Example St.",
                "warning": None,
            },
        }
    )

    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Hi, my name is Taylor. Please help with the address and phone from the screenshots.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {},
            "screenshot_attachment_ids": ["att-ocr-2"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["autofill_suggestions"]["customer_name"]["source"] == "message+ocr"
    assert body["autofill_suggestions"]["customer_phone"]["source"] == "ocr"
    assert body["autofill_suggestions"]["job_address"]["source"] == "ocr"
    assert body["autofill_suggestions"]["description"]["source"] == "message"
    assert body["autofill_suggestions"]["description"]["value"].startswith("Hi, my name is Taylor.")


def test_screenshot_assistant_minimum_safe_respects_active_engine_floors(client: TestClient) -> None:
    payload = {
        "service_type": "item_delivery",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "pickup_address": "1 Pickup Ave",
        "dropoff_address": "2 Dropoff Rd",
        "job_address": "2 Dropoff Rd",
        "description": "Reviewed item delivery with protected route details and enclosed trailer.",
        "trailer_class": "older_enclosed",
    }
    response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Reviewed delivery draft.",
            "candidate_inputs": payload,
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )

    assert response.status_code == 200
    guidance = response.json()["quote_guidance"]
    artifacts = build_quote_artifacts(payload)
    protected_floor = artifacts["engine_quote"]["_internal"]["item_delivery_protected_base_floor_cad"]
    assert protected_floor > 0
    assert guidance["range"]["minimum_safe_cash_cad"] >= protected_floor


def test_linked_screenshot_assistant_analysis_cannot_be_updated(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Initial draft",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0},
            "operator_overrides": {},
            "screenshot_attachment_ids": [],
        },
    )
    assert create_analysis.status_code == 200
    analysis_id = create_analysis.json()["analysis_id"]

    create_quote = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert create_quote.status_code == 200

    update_response = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "analysis_id": analysis_id,
            "message": "Updated draft",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 2.0},
            "operator_overrides": {"job_address": "456 Updated St"},
            "screenshot_attachment_ids": [],
        },
    )

    assert update_response.status_code == 409
    assert update_response.json() == {"detail": "Screenshot assistant analysis is locked after quote draft creation."}


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


def test_prepare_customer_handoff_from_linked_quote_draft_reuses_quote_request_and_keeps_attachment_linkage(
    client: TestClient,
) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-handoff",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "handoff.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-handoff",
            "drive_web_view_link": "https://example.com/handoff",
        }
    )

    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Prepare this quote for customer review.",
            "screenshot_attachment_ids": ["att-handoff"],
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {
                "job_address": "789 Handoff St",
                "customer_name": "Morgan",
                "customer_phone": "555-0202",
            },
        },
    )
    assert create_analysis.status_code == 200
    analysis_id = create_analysis.json()["analysis_id"]

    create_quote = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert create_quote.status_code == 200
    quote_id = create_quote.json()["quote"]["quote_id"]

    handoff_response = client.post(
        f"/admin/api/quotes/{quote_id}/handoff",
        headers=admin_headers(),
    )
    assert handoff_response.status_code == 200
    handoff_body = handoff_response.json()
    assert handoff_body["quote_id"] == quote_id
    assert handoff_body["status"] == "customer_pending"
    assert handoff_body["already_existed"] is False

    stored_request = storage.get_quote_request(handoff_body["request_id"])
    assert stored_request is not None
    assert stored_request["quote_id"] == quote_id

    attachments = storage.list_attachments(analysis_id=analysis_id)
    assert len(attachments) == 1
    assert attachments[0]["analysis_id"] == analysis_id
    assert attachments[0]["quote_id"] == quote_id
    assert attachments[0]["request_id"] is None


def test_screenshot_assistant_happy_path_full_chain_through_scheduling(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage.save_attachment(
        {
            "attachment_id": "att-full-chain",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "full-chain.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-full-chain",
            "drive_web_view_link": "https://example.com/full-chain",
        }
    )

    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Initial screenshot intake for a haul away request.",
            "screenshot_attachment_ids": ["att-full-chain"],
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {"job_address": "111 Intake Ln"},
        },
    )
    assert create_analysis.status_code == 200
    analysis_id = create_analysis.json()["analysis_id"]

    reviewed_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "analysis_id": analysis_id,
            "message": "Reviewed and ready for customer handoff.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.5, "crew_size": 2},
            "operator_overrides": {
                "job_address": "222 Reviewed Ave",
                "customer_name": "Jordan",
                "customer_phone": "555-0303",
                "description": "Reviewed haul away scope",
            },
            "screenshot_attachment_ids": ["att-full-chain"],
        },
    )
    assert reviewed_analysis.status_code == 200
    reviewed_body = reviewed_analysis.json()
    assert reviewed_body["analysis_id"] == analysis_id
    assert reviewed_body["normalized_candidate"]["job_address"] == "222 Reviewed Ave"

    create_quote = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert create_quote.status_code == 200
    quote_body = create_quote.json()
    quote_id = quote_body["quote"]["quote_id"]
    assert quote_body["analysis"]["quote_id"] == quote_id

    saved_analysis = storage.get_screenshot_assistant_analysis(analysis_id)
    assert saved_analysis is not None
    assert saved_analysis["quote_id"] == quote_id

    attachments = storage.list_attachments(analysis_id=analysis_id)
    assert len(attachments) == 1
    assert attachments[0]["quote_id"] == quote_id

    review_response = client.get(
        f"/quote/{quote_id}/view",
        params={"accept_token": storage.get_quote_record(quote_id)["accept_token"]},
    )
    assert review_response.status_code == 200
    assert review_response.json()["quote_id"] == quote_id

    handoff_response = client.post(
        f"/admin/api/quotes/{quote_id}/handoff",
        headers=admin_headers(),
    )
    assert handoff_response.status_code == 200
    handoff_body = handoff_response.json()
    request_id = handoff_body["request_id"]
    assert handoff_body["status"] == "customer_pending"

    accept_token = storage.get_quote_record(quote_id)["accept_token"]
    decision_response = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "accept", "accept_token": accept_token},
    )
    assert decision_response.status_code == 200
    decision_body = decision_response.json()
    assert decision_body["request_id"] == request_id
    assert decision_body["status"] == "customer_accepted"

    booking_response = client.post(
        f"/quote/{quote_id}/booking",
        json={
            "booking_token": decision_body["booking_token"],
            "requested_job_date": "2026-04-12",
            "requested_time_window": "morning",
            "notes": "Gate code 1234",
        },
    )
    assert booking_response.status_code == 200

    approval_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=admin_headers(),
        json={"action": "approve"},
    )
    assert approval_response.status_code == 200
    approval_body = approval_response.json()
    job = approval_body["job"]
    assert job is not None
    job_id = job["job_id"]
    assert approval_body["request"]["status"] == "admin_approved"
    assert job["quote_id"] == quote_id
    assert job["request_id"] == request_id

    monkeypatch.setattr("app.integrations.google_calendar_client.is_configured", lambda: True)
    monkeypatch.setattr("app.integrations.google_calendar_client.create_event", lambda *_args, **_kwargs: "event-full-chain")

    schedule_response = client.post(
        f"/admin/api/jobs/{job_id}/schedule",
        headers=admin_headers(),
        json={"scheduled_start": "2026-04-12T09:00:00", "scheduled_end": "2026-04-12T11:00:00"},
    )
    assert schedule_response.status_code == 200
    schedule_body = schedule_response.json()
    assert schedule_body["ok"] is True

    saved_request = storage.get_quote_request(request_id)
    assert saved_request is not None
    assert saved_request["status"] == "admin_approved"
    assert saved_request["requested_job_date"] == "2026-04-12"
    assert saved_request["requested_time_window"] == "morning"

    saved_job = storage.get_job(job_id)
    assert saved_job is not None
    assert saved_job["status"] == "approved"
    assert saved_job["scheduled_start"].startswith("2026-04-12T09:00:00")
    assert saved_job["scheduled_end"].startswith("2026-04-12T11:00:00")
    assert saved_job["calendar_sync_status"] == "synced"
    assert saved_job["google_calendar_event_id"] == "event-full-chain"


def test_screenshot_assistant_decline_path_blocks_booking_and_job_creation(client: TestClient) -> None:
    create_analysis = client.post(
        "/admin/api/screenshot-assistant/analyses/intake",
        headers=admin_headers(),
        json={
            "message": "Reviewed screenshot thread for decline guardrail coverage.",
            "candidate_inputs": {"service_type": "haul_away", "estimated_hours": 1.0, "crew_size": 1},
            "operator_overrides": {
                "job_address": "333 Decline Rd",
                "customer_name": "Casey",
                "customer_phone": "555-0404",
                "description": "Decline path scope",
            },
            "screenshot_attachment_ids": [],
        },
    )
    assert create_analysis.status_code == 200
    analysis_id = create_analysis.json()["analysis_id"]

    create_quote = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert create_quote.status_code == 200
    quote_id = create_quote.json()["quote"]["quote_id"]
    accept_token = storage.get_quote_record(quote_id)["accept_token"]

    handoff_response = client.post(
        f"/admin/api/quotes/{quote_id}/handoff",
        headers=admin_headers(),
    )
    assert handoff_response.status_code == 200
    request_id = handoff_response.json()["request_id"]

    decline_response = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "decline", "accept_token": accept_token},
    )
    assert decline_response.status_code == 200
    decline_body = decline_response.json()
    assert decline_body["request_id"] == request_id
    assert decline_body["status"] == "customer_declined"

    booking_response = client.post(
        f"/quote/{quote_id}/booking",
        json={
            "booking_token": "unused-after-decline",
            "requested_job_date": "2026-04-12",
            "requested_time_window": "afternoon",
        },
    )
    assert booking_response.status_code == 400
    assert booking_response.json() == {"detail": "Booking can only be submitted for accepted quotes."}

    approval_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=admin_headers(),
        json={"action": "approve"},
    )
    assert approval_response.status_code == 409
    approval_body = approval_response.json()
    assert approval_body["error"] == "invalid_status_transition"
    assert approval_body["from"] == "customer_declined"
    assert approval_body["to"] == "admin_approved"

    saved_request = storage.get_quote_request(request_id)
    assert saved_request is not None
    assert saved_request["status"] == "customer_declined"
    assert storage.get_job_by_quote_id(quote_id) is None


def test_linked_screenshot_assistant_analysis_cannot_receive_more_uploads(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_upload_mocks(monkeypatch)

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

    create_quote = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/quote-draft",
        headers=admin_headers(),
    )
    assert create_quote.status_code == 200

    upload_response = client.post(
        f"/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments",
        headers=admin_headers(),
        files=[("files", ("photo.jpg", b"\xff\xd8\xff" + (b"a" * 32), "image/jpeg"))],
    )
    assert upload_response.status_code == 409
    assert upload_response.json() == {"detail": "Screenshot assistant analysis is locked after quote draft creation."}


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
