from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app, clear_gpt_quote_rate_limit_state
from app.services.quote_service import build_quote_artifacts


def _base_payload(service_type: str = "haul_away") -> dict:
    payload = {
        "service_type": service_type,
        "description": "GPT endpoint regression check",
        "pickup_address": "1 Pickup Rd",
        "dropoff_address": "2 Dropoff Ave",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "garbage_bag_count": 0,
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": "in_town",
        "access_difficulty": "normal",
    }
    if service_type == "haul_away":
        payload["trailer_fill_estimate"] = "under_quarter"
    return payload


def _translated_payload(payload: dict) -> dict:
    return {
        "service_type": payload.get("service_type"),
        "description": payload.get("description"),
        "job_description_customer": payload.get("description"),
        "pickup_address": payload.get("pickup_address"),
        "dropoff_address": payload.get("dropoff_address"),
        "estimated_hours": payload.get("estimated_hours", 0.0),
        "crew_size": payload.get("crew_size", 1),
        "garbage_bag_count": payload.get("garbage_bag_count", 0),
        "bag_type": payload.get("bag_type"),
        "trailer_fill_estimate": payload.get("trailer_fill_estimate"),
        "trailer_class": payload.get("trailer_class"),
        "mattresses_count": payload.get("mattresses_count", 0),
        "box_springs_count": payload.get("box_springs_count", 0),
        "scrap_pickup_location": payload.get("scrap_pickup_location", "curbside"),
        "travel_zone": payload.get("travel_zone", "in_town"),
        "access_difficulty": payload.get("access_difficulty", "normal"),
        "has_dense_materials": payload.get("has_dense_materials", False),
        "load_mode": payload.get("load_mode", "standard"),
    }


def _headers(token: str = "test-gpt-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _latest_event() -> dict:
    return storage.list_gpt_quote_observability(limit=1)[0]


@pytest.fixture()
def temp_quote_db(monkeypatch):
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    monkeypatch.setenv("GPT_INTERNAL_API_TOKEN", "test-gpt-token")

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "gpt-quote.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()
        yield

    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)


@pytest.fixture()
def client(temp_quote_db) -> TestClient:
    clear_gpt_quote_rate_limit_state()
    with TestClient(app) as test_client:
        yield test_client
    clear_gpt_quote_rate_limit_state()


def test_gpt_quote_returns_engine_backed_totals_without_persistence(client: TestClient) -> None:
    payload = _base_payload()

    response = client.post("/api/gpt/quote", headers=_headers(), json=payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "cash_total_cad",
        "emt_total_cad",
        "disclaimer",
        "normalized_service_type",
        "confidence_level",
        "risk_flags",
    }
    assert "quote_id" not in body
    assert "accept_token" not in body

    artifacts = build_quote_artifacts(_translated_payload(payload))
    assert body["cash_total_cad"] == artifacts["response"]["cash_total_cad"]
    assert body["emt_total_cad"] == artifacts["response"]["emt_total_cad"]
    assert body["disclaimer"] == artifacts["response"]["disclaimer"]
    assert body["normalized_service_type"] == artifacts["normalized_request"]["service_type"]
    assert body["confidence_level"] == artifacts["internal_risk_assessment"]["confidence_level"]
    assert body["risk_flags"] == artifacts["internal_risk_assessment"]["risk_flags"]
    assert storage.list_quotes() == []
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    event = events[0]
    assert event["route_name"] == "/api/gpt/quote"
    assert event["success"] is True
    assert event["normalized_service_type"] == artifacts["normalized_request"]["service_type"]
    assert event["cash_total_cad"] == artifacts["response"]["cash_total_cad"]
    assert event["emt_total_cad"] == artifacts["response"]["emt_total_cad"]
    assert event["confidence_level"] == artifacts["internal_risk_assessment"]["confidence_level"]
    assert event["risk_flags"] == artifacts["internal_risk_assessment"]["risk_flags"]
    assert event["failure_reason"] is None
    assert isinstance(event["latency_ms"], int)
    assert event["latency_ms"] >= 0
    assert event["server_grounding_revision"] is None
    assert event["caller_grounding_revision"] is None


def test_gpt_quote_invalid_enum_returns_400(client: TestClient) -> None:
    payload = _base_payload()
    payload["access_difficulty"] = "stairs??"

    response = client.post("/api/gpt/quote", headers=_headers(), json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid access_difficulty."}


def test_gpt_quote_invalid_service_type_returns_400(client: TestClient) -> None:
    payload = _base_payload(service_type="mystery_service")

    response = client.post("/api/gpt/quote", headers=_headers(), json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid service_type."}
    assert storage.list_quotes() == []
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    event = events[0]
    assert event["success"] is False
    assert event["failure_reason"] == "invalid_request"
    assert event["cash_total_cad"] is None
    assert event["emt_total_cad"] is None
    assert event["risk_flags"] == []
    assert event["server_grounding_revision"] is None
    assert event["caller_grounding_revision"] is None


def test_gpt_quote_empty_haul_away_returns_400(client: TestClient) -> None:
    payload = _base_payload()
    payload["trailer_fill_estimate"] = None

    response = client.post("/api/gpt/quote", headers=_headers(), json=payload)

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Please add at least one load detail so we can estimate your junk removal properly. "
            "Examples: bags, trailer space used, mattresses, box springs, or dense materials."
        )
    }


def test_gpt_quote_missing_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/gpt/quote", json=_base_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal API token."}
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    assert _latest_event()["failure_reason"] == "auth_failed"
    assert _latest_event()["server_grounding_revision"] is None
    assert _latest_event()["caller_grounding_revision"] is None


def test_gpt_quote_missing_token_on_malformed_body_returns_401_not_422(client: TestClient) -> None:
    response = client.post("/api/gpt/quote", json={"unexpected": "field"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal API token."}
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    assert _latest_event()["failure_reason"] == "auth_failed"
    assert _latest_event()["server_grounding_revision"] is None
    assert _latest_event()["caller_grounding_revision"] is None


def test_gpt_quote_invalid_token_on_malformed_body_returns_401_not_422(client: TestClient) -> None:
    response = client.post("/api/gpt/quote", headers=_headers("wrong-token"), json={"unexpected": "field"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal API token."}
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    assert _latest_event()["failure_reason"] == "auth_failed"
    assert _latest_event()["server_grounding_revision"] is None
    assert _latest_event()["caller_grounding_revision"] is None


def test_gpt_quote_valid_token_on_malformed_body_still_returns_422(client: TestClient) -> None:
    response = client.post("/api/gpt/quote", headers=_headers(), json={"unexpected": "field"})

    assert response.status_code == 422
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    event = events[0]
    assert event["success"] is False
    assert event["failure_reason"] == "validation_error"
    assert event["server_grounding_revision"] is None
    assert event["caller_grounding_revision"] is None


def test_gpt_quote_missing_env_token_fails_closed(monkeypatch) -> None:
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    monkeypatch.delenv("GPT_INTERNAL_API_TOKEN", raising=False)

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "gpt-quote-disabled.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()

        with TestClient(app) as client:
            response = client.post("/api/gpt/quote", headers=_headers(), json=_base_payload())
            events = storage.list_gpt_quote_observability(limit=10)

    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert len(events) == 1
    assert events[0]["success"] is False
    assert events[0]["failure_reason"] == "endpoint_disabled"
    assert events[0]["server_grounding_revision"] is None
    assert events[0]["caller_grounding_revision"] is None


def test_gpt_quote_unknown_field_returns_422(client: TestClient) -> None:
    payload = _base_payload()
    payload["customer_name"] = "Should not be accepted"

    response = client.post("/api/gpt/quote", headers=_headers(), json=payload)

    assert response.status_code == 422
    events = storage.list_gpt_quote_observability(limit=10)
    assert len(events) == 1
    assert events[0]["failure_reason"] == "validation_error"
    assert events[0]["server_grounding_revision"] is None
    assert events[0]["caller_grounding_revision"] is None


def test_gpt_quote_rate_limit_logs_once(client: TestClient) -> None:
    for _ in range(10):
        response = client.post("/api/gpt/quote", headers=_headers(), json=_base_payload())
        assert response.status_code == 200

    blocked = client.post("/api/gpt/quote", headers=_headers(), json=_base_payload())

    assert blocked.status_code == 429
    events = storage.list_gpt_quote_observability(limit=20)
    assert len(events) == 11
    assert events[0]["success"] is False
    assert events[0]["failure_reason"] == "rate_limited"
    assert events[0]["server_grounding_revision"] is None
    assert events[0]["caller_grounding_revision"] is None


def test_gpt_quote_logs_server_authoritative_and_caller_declared_revisions(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setenv("GPT_GROUNDING_REVISION", "v0.10.1+manifest-abc123")
    headers = dict(_headers())
    headers["X-GPT-Grounding-Revision"] = "caller-2026-04-24"

    response = client.post("/api/gpt/quote", headers=headers, json=_base_payload())

    assert response.status_code == 200
    event = _latest_event()
    assert event["server_grounding_revision"] == "v0.10.1+manifest-abc123"
    assert event["caller_grounding_revision"] == "caller-2026-04-24"
