import base64
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


def test_admin_quote_detail_includes_internal_risk_assessment(temp_quote_db: None) -> None:
    with TestClient(app) as client:
        quote_resp = client.post("/quote/calculate", json=_quote_payload())
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

        review_resp = client.get(
            f"/quote/{quote_body['quote_id']}/view",
            headers={"Authorization": f"Bearer {quote_body['accept_token']}"},
        )

    assert review_resp.status_code == 200
    review_body = review_resp.json()
    assert "internal_risk_assessment" not in review_body
    assert "internal_risk_assessment" not in review_body["response"]
