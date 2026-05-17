import base64
import inspect
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app import storage
from app.main import app


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def _quote_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer_name": "Risk Visibility Tester",
        "customer_phone": "705-555-0144",
        "job_address": "44 Admin Review Rd",
        "job_description_customer": "Admin-only risk visibility",
        "description": "Admin-only risk visibility",
        "service_type": "haul_away",
        "payment_method": "cash",
        "estimated_hours": 2.0,
        "crew_size": 2,
        "garbage_bag_count": 3,
        "access_difficulty": "difficult",
    }
    payload.update(overrides)
    return payload


def _save_quote_request_for_quote(
    quote_body: dict[str, object],
    *,
    requested_job_date: str | None,
    requested_time_window: str | None,
) -> None:
    quote_id = str(quote_body["quote_id"])
    request_payload = quote_body["request"]
    response_payload = quote_body["response"]
    assert isinstance(request_payload, dict)
    assert isinstance(response_payload, dict)
    storage.save_quote_request(
        {
            "request_id": f"request-{quote_id}",
            "created_at": "2026-04-16T12:05:00-04:00",
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": request_payload.get("customer_name"),
            "customer_phone": request_payload.get("customer_phone"),
            "job_address": request_payload.get("job_address"),
            "job_description_customer": request_payload.get("job_description_customer"),
            "job_description_internal": response_payload.get("job_description_internal"),
            "service_type": request_payload.get("service_type"),
            "cash_total_cad": response_payload.get("cash_total_cad"),
            "emt_total_cad": response_payload.get("emt_total_cad"),
            "request_json": request_payload,
            "notes": None,
            "requested_job_date": requested_job_date,
            "requested_time_window": requested_time_window,
            "customer_accepted_at": "2026-04-16T12:05:00-04:00",
            "admin_approved_at": None,
            "accept_token": quote_body.get("accept_token"),
            "booking_token": "booking-token",
            "booking_token_created_at": "2026-04-16T12:05:00-04:00",
        }
    )


def _save_quote_attachment(quote_id: str) -> None:
    storage.save_attachment(
        {
            "attachment_id": f"attachment-{quote_id}",
            "created_at": "2026-04-16T12:10:00-04:00",
            "quote_id": quote_id,
            "request_id": None,
            "job_id": None,
            "analysis_id": None,
            "filename": "customer-photo.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 12345,
            "drive_file_id": "drive-photo",
            "drive_web_view_link": "https://example.com/customer-photo",
            "ocr_json": {},
        }
    )


def _save_prior_quote_request(
    *,
    request_id: str,
    quote_id: str,
    customer_name: str = "Prior Customer",
    customer_phone: str | None = "7055550144",
    created_at: str = "2026-04-15T09:00:00-04:00",
) -> None:
    storage.save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "job_address": "15 Prior Request Rd",
            "job_description_customer": "Prior request",
            "job_description_internal": "Prior request",
            "service_type": "haul_away",
            "cash_total_cad": 150.0,
            "emt_total_cad": 169.5,
            "request_json": {"customer_phone": customer_phone, "service_type": "haul_away"},
            "notes": None,
            "requested_job_date": None,
            "requested_time_window": None,
            "customer_accepted_at": created_at,
            "admin_approved_at": None,
            "accept_token": "prior-accept-token",
            "booking_token": None,
            "booking_token_created_at": None,
        }
    )


def _save_prior_job(
    *,
    job_id: str,
    quote_id: str,
    request_id: str,
    customer_phone: str | None = "(705) 555-0144",
    created_at: str = "2026-04-17T09:00:00-04:00",
) -> None:
    storage.save_job(
        {
            "job_id": job_id,
            "created_at": created_at,
            "status": "completed",
            "quote_id": quote_id,
            "request_id": request_id,
            "customer_name": "Prior Job Customer",
            "customer_phone": customer_phone,
            "job_address": "17 Prior Job Ave",
            "job_description_customer": "Prior job",
            "job_description_internal": "Prior job",
            "service_type": "haul_away",
            "cash_total_cad": 175.0,
            "emt_total_cad": 197.75,
            "request_json": {"customer_phone": customer_phone, "service_type": "haul_away"},
            "notes": None,
        }
    )


@pytest.fixture()
def temp_quote_db(monkeypatch: pytest.MonkeyPatch) -> None:
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    main_module._admin_failed_attempts.clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "admin-quote-risk.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()
        yield

    main_module._admin_failed_attempts.clear()
    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)


def test_admin_quote_detail_includes_lead_source_and_repeat_customer_history(temp_quote_db: None) -> None:
    _save_prior_quote_request(
        request_id="prior-request-match",
        quote_id="prior-request-quote",
        customer_phone="705.555.0144",
    )
    _save_prior_job(
        job_id="prior-job-match",
        quote_id="prior-job-quote",
        request_id="prior-job-request",
        customer_phone="+1 (705) 555-0144",
    )

    with TestClient(app) as client:
        quote_resp = client.post(
            "/quote/calculate",
            json=_quote_payload(lead_source="facebook", customer_phone="705-555-0144"),
        )
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["lead_source"] == {"value": "facebook", "label": "Facebook"}
    history = body["customer_history"]
    assert history["status"] == "repeat_customer"
    assert history["label"] == "Repeat customer"
    assert history["previous_requests"] == 1
    assert history["previous_jobs"] == 1
    assert history["previous_quotes"] == 0
    assert history["last_seen"] == "2026-04-17T09:00:00-04:00"


def test_customer_history_lookup_is_narrowed_by_phone_key() -> None:
    source = inspect.getsource(storage.load_customer_history_context)

    assert "SELECT request_id, quote_id, customer_phone, created_at FROM quote_requests" not in source
    assert "SELECT job_id, quote_id, customer_phone, created_at FROM jobs" not in source
    assert "SELECT quote_id, created_at, request_json FROM quotes" not in source
    assert "WHERE" in source
    assert "_sql_phone_match_predicate" in source


def test_admin_quote_detail_last_seen_uses_parsed_timestamp_ordering(temp_quote_db: None) -> None:
    _save_prior_quote_request(
        request_id="prior-request-zulu",
        quote_id="prior-request-zulu-quote",
        customer_phone="705-555-0144",
        created_at="2026-05-02T00:30:00Z",
    )
    _save_prior_job(
        job_id="prior-job-offset",
        quote_id="prior-job-offset-quote",
        request_id="prior-job-offset-request",
        customer_phone="1-705-555-0144",
        created_at="2026-05-01T20:45:00-04:00",
    )

    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload(customer_phone="705-555-0144"))
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    history = resp.json()["customer_history"]
    assert history["status"] == "repeat_customer"
    assert history["previous_requests"] == 1
    assert history["previous_jobs"] == 1
    assert history["last_seen"] == "2026-05-01T20:45:00-04:00"


def test_admin_quote_detail_marks_prior_quote_only_match_as_possible_repeat(temp_quote_db: None) -> None:
    storage.save_quote(
        {
            "quote_id": "prior-quote-only",
            "created_at": "2026-04-14T08:00:00-04:00",
            "request": {
                "customer_name": "Prior Quote Only",
                "customer_phone": "7055550144",
                "job_address": "14 Prior Quote Rd",
                "description": "Prior quote only",
                "service_type": "haul_away",
            },
            "response": {"cash_total_cad": 100.0, "emt_total_cad": 113.0},
            "accept_token": "prior-quote-token",
        }
    )

    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload(customer_phone="705-555-0144"))
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    history = resp.json()["customer_history"]
    assert history["status"] == "possible_repeat_customer"
    assert history["label"] == "Possible repeat customer"
    assert history["previous_requests"] == 0
    assert history["previous_jobs"] == 0
    assert history["previous_quotes"] == 1


def test_admin_quote_detail_excludes_current_quote_from_customer_history(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload(customer_phone="705-555-0144"))
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    history = resp.json()["customer_history"]
    assert history["status"] == "new_customer"
    assert history["label"] == "New customer"
    assert history["previous_requests"] == 0
    assert history["previous_jobs"] == 0
    assert history["previous_quotes"] == 0


def test_admin_quote_detail_does_not_use_name_only_match_as_repeat(temp_quote_db: None) -> None:
    _save_prior_quote_request(
        request_id="prior-name-only",
        quote_id="prior-name-only-quote",
        customer_name="Risk Visibility Tester",
        customer_phone="705-555-9999",
    )

    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload(customer_phone="705-555-0144"))
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    assert resp.json()["customer_history"]["label"] == "New customer"


def test_admin_quote_detail_reports_unavailable_history_for_unusable_legacy_phone(temp_quote_db: None) -> None:
    storage.save_quote(
        {
            "quote_id": "legacy-unusable-phone",
            "created_at": "2026-04-16T12:00:00-04:00",
            "request": {
                "customer_name": "Legacy Phone",
                "customer_phone": "call me",
                "job_address": "16 Legacy Rd",
                "description": "Legacy unusable phone",
                "service_type": "haul_away",
            },
            "response": {"cash_total_cad": 125.0, "emt_total_cad": 141.25},
            "accept_token": "legacy-token",
        }
    )

    with TestClient(app) as client:
        resp = client.get("/admin/api/quotes/legacy-unusable-phone", headers=_admin_headers())

    assert resp.status_code == 200
    history = resp.json()["customer_history"]
    assert history["status"] == "unavailable"
    assert history["label"] == "Customer history unavailable"


def test_admin_quote_detail_includes_internal_risk_assessment(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload(dense_material_type="concrete"))
        assert quote_resp.status_code == 200
        quote_id = quote_resp.json()["quote_id"]

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["quote_id"] == quote_id
    assert "internal_risk_assessment" in body
    assert body["internal_risk_assessment"]["confidence_level"] == "low"
    assert "access_volume_risk" in body["internal_risk_assessment"]["risk_flags"]
    assert "likely_underestimated_volume" in body["internal_risk_assessment"]["risk_flags"]
    assert body["quote_risk_advisory"]["customer_visible"] is False
    assert body["quote_risk_advisory"]["pricing_effect"] == "none"
    assert "DENSE_MATERIAL_RISK" in {
        flag["code"] for flag in body["quote_risk_advisory"]["risk_flags"]
    }
    assert body["quote_risk_summary"]["customer_visible"] is False
    assert body["quote_risk_summary"]["pricing_effect"] == "none"
    assert body["quote_risk_summary"]["risk_level"] == "owner_review"
    assert body["quote_risk_summary"]["suggested_action"] == "owner_review_before_approving"
    assert "heavy_material_risk" in body["quote_risk_summary"]["reasons"]
    assert "photos" in body["quote_risk_summary"]["missing_info"]


def test_admin_quote_detail_risk_summary_uses_persisted_scheduling_and_photo_context(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post(
            "/quote/calculate",
            json=_quote_payload(
                job_description_customer="Four garbage bags from garage",
                description="Four garbage bags from garage",
                estimated_hours=1.0,
                crew_size=1,
                garbage_bag_count=4,
                bag_type="light",
                trailer_fill_estimate="quarter",
                access_difficulty="normal",
            ),
        )
        assert quote_resp.status_code == 200
        quote_body = quote_resp.json()
        quote_id = quote_body["quote_id"]
        _save_quote_request_for_quote(
            quote_body,
            requested_job_date="2026-05-20",
            requested_time_window="morning",
        )
        _save_quote_attachment(quote_id)

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    summary = resp.json()["quote_risk_summary"]
    assert summary["customer_visible"] is False
    assert summary["pricing_effect"] == "none"
    assert "preferred_date" not in summary["missing_info"]
    assert "preferred_time_window" not in summary["missing_info"]
    assert "photos" not in summary["missing_info"]
    assert summary["suggested_action"] == "approve"


def test_admin_quote_detail_with_attachments_does_not_request_photos_from_advisory_text(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post(
            "/quote/calculate",
            json=_quote_payload(
                job_description_customer="Four bags of tile from garage",
                description="Four bags of tile from garage",
                estimated_hours=1.0,
                crew_size=1,
                garbage_bag_count=4,
                bag_type="heavy_mixed",
                trailer_fill_estimate="quarter",
                access_difficulty="normal",
                dense_material_type="tile",
            ),
        )
        assert quote_resp.status_code == 200
        quote_body = quote_resp.json()
        quote_id = quote_body["quote_id"]
        _save_quote_request_for_quote(
            quote_body,
            requested_job_date="2026-05-20",
            requested_time_window="morning",
        )
        _save_quote_attachment(quote_id)

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    summary = resp.json()["quote_risk_summary"]
    advisory_actions = resp.json()["quote_risk_advisory"]["suggested_actions"]
    assert any("photo" in action.lower() for action in advisory_actions)
    assert "photos" not in summary["missing_info"]
    assert summary["suggested_action"] != "request_photos"
    assert summary["suggested_action"] == "ask_followup"


def test_admin_quote_detail_risk_summary_keeps_missing_context_when_absent(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post(
            "/quote/calculate",
            json=_quote_payload(
                job_description_customer="Four garbage bags from garage",
                description="Four garbage bags from garage",
                estimated_hours=1.0,
                crew_size=1,
                garbage_bag_count=4,
                bag_type="light",
                trailer_fill_estimate="quarter",
                access_difficulty="normal",
            ),
        )
        assert quote_resp.status_code == 200
        quote_body = quote_resp.json()
        quote_id = quote_body["quote_id"]
        _save_quote_request_for_quote(
            quote_body,
            requested_job_date=None,
            requested_time_window=None,
        )

        resp = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert resp.status_code == 200
    summary = resp.json()["quote_risk_summary"]
    assert "preferred_date" in summary["missing_info"]
    assert "preferred_time_window" in summary["missing_info"]
    assert "photos" in summary["missing_info"]


def test_admin_quote_detail_returns_null_risk_assessment_when_risk_redrive_fails(temp_quote_db: None) -> None:
    storage.save_quote(
        {
            "quote_id": "legacy-riskless-quote",
            "created_at": "2026-04-16T12:00:00-04:00",
            "request": "legacy-string-request",
            "response": {
                "cash_total_cad": 125.0,
                "emt_total_cad": 141.25,
            },
            "accept_token": "legacy-token",
        }
    )

    with TestClient(app) as client:
        resp = client.get("/admin/api/quotes/legacy-riskless-quote", headers=_admin_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["quote_id"] == "legacy-riskless-quote"
    assert body["internal_risk_assessment"] is None
    assert body["quote_risk_advisory"] is None
    assert body["quote_risk_summary"] is None
    assert body["lead_source"] == {"value": "unknown", "label": "Unknown"}
    assert body["customer_history"]["label"] == "Customer history unavailable"


def test_admin_quote_detail_handles_null_request_and_response_payloads(temp_quote_db: None) -> None:
    storage.save_quote(
        {
            "quote_id": "legacy-null-payload-quote",
            "created_at": "2026-04-16T12:00:00-04:00",
            "request": None,
            "response": None,
            "accept_token": "legacy-null-token",
        }
    )

    with TestClient(app) as client:
        resp = client.get("/admin/api/quotes/legacy-null-payload-quote", headers=_admin_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["quote_id"] == "legacy-null-payload-quote"
    assert body["request"] is None
    assert body["response"] is None
    assert body["internal_risk_assessment"] is None
    assert body["quote_risk_advisory"] is None
    assert body["quote_risk_summary"] is None

    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    assert "const request = detail?.request ?? {};" in admin_js
    assert "const response = detail?.response ?? {};" in admin_js
    assert 'const safeRequest = typeof request === "object" && request !== null ? request : {};' in admin_js
    assert 'const safeResponse = typeof response === "object" && response !== null ? response : {};' in admin_js


def test_public_quote_responses_still_exclude_internal_risk_assessment(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload())

        assert quote_resp.status_code == 200
        quote_body = quote_resp.json()
        assert "internal_risk_assessment" not in quote_body
        assert "internal_risk_assessment" not in quote_body["response"]
        assert "quote_risk_advisory" not in quote_body
        assert "quote_risk_advisory" not in quote_body["response"]
        assert "quote_risk_summary" not in quote_body
        assert "quote_risk_summary" not in quote_body["response"]
        assert "customer_history" not in quote_body
        assert "customer_history" not in quote_body["response"]

        review_resp = client.get(
            f"/quote/{quote_body['quote_id']}/view",
            headers={"Authorization": f"Bearer {quote_body['accept_token']}"},
        )

    assert review_resp.status_code == 200
    review_body = review_resp.json()
    assert "internal_risk_assessment" not in review_body
    assert "internal_risk_assessment" not in review_body["response"]
    assert "quote_risk_advisory" not in review_body
    assert "quote_risk_advisory" not in review_body["response"]
    assert "quote_risk_summary" not in review_body
    assert "quote_risk_summary" not in review_body["response"]
    assert "customer_history" not in review_body
    assert "customer_history" not in review_body["response"]
