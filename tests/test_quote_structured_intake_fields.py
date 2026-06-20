from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app import storage
from app.main import app
from app.services import quote_service


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}", "Sec-Fetch-Site": "same-origin"}


def _base_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "customer_name": "Structured Intake",
        "customer_phone": "705-555-0133",
        "job_address": "133 Intake Rd",
        "description": "Small mixed load with optional structured facts",
        "service_type": "haul_away",
        "payment_method": "cash",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "garbage_bag_count": 0,
        "trailer_fill_estimate": "under_quarter",
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": "in_town",
        "access_difficulty": "normal",
        "has_dense_materials": False,
    }
    payload.update(overrides)
    return payload


def _structured_fields() -> dict[str, Any]:
    return {
        "stairs_count": 2,
        "floor_count": 1,
        "basement_or_inside_removal": True,
        "demolition_ripout": True,
        "construction_debris_type": "drywall",
        "dense_material_type": "concrete",
        "mixed_load": True,
        "contains_scrap": True,
        "contains_garbage": True,
        "has_refrigerant_appliance": True,
        "appliance_type": "fridge",
        "weather_protection_required": True,
    }


@pytest.fixture()
def temp_quote_db(monkeypatch: pytest.MonkeyPatch):
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    main_module._admin_failed_attempts.clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "structured-intake.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()
        yield

    main_module._admin_failed_attempts.clear()
    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)


@pytest.fixture()
def client(temp_quote_db: None):
    with TestClient(app) as test_client:
        yield test_client


def test_old_quote_payload_still_returns_quote(client: TestClient) -> None:
    response = client.post("/quote/calculate", json=_base_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["lead_source"] == "unknown"
    assert body["response"]["cash_total_cad"] > 0
    assert body["response"]["emt_total_cad"] > body["response"]["cash_total_cad"]


def test_structured_intake_fields_are_accepted_and_returned(client: TestClient) -> None:
    response = client.post("/quote/calculate", json=_base_payload(**_structured_fields()))

    assert response.status_code == 200
    request = response.json()["request"]
    for field, expected in _structured_fields().items():
        assert request[field] == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("construction_debris_type", "unknown_debris"),
        ("dense_material_type", "lead"),
        ("appliance_type", "tv"),
    ],
)
def test_structured_intake_invalid_enums_are_rejected(client: TestClient, field: str, value: str) -> None:
    response = client.post("/quote/calculate", json=_base_payload(**{field: value}))

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["stairs_count", "floor_count"])
def test_structured_intake_negative_counts_are_rejected(client: TestClient, field: str) -> None:
    response = client.post("/quote/calculate", json=_base_payload(**{field: -1}))

    assert response.status_code == 422


def test_structured_intake_blank_optional_selects_normalize_to_none(client: TestClient) -> None:
    response = client.post(
        "/quote/calculate",
        json=_base_payload(
            construction_debris_type="",
            dense_material_type="   ",
            appliance_type="",
        ),
    )

    assert response.status_code == 200
    request = response.json()["request"]
    assert request["construction_debris_type"] is None
    assert request["dense_material_type"] is None
    assert request["appliance_type"] is None


@pytest.mark.parametrize(
    "lead_source",
    [
        "facebook",
        "google",
        "referral",
        "marketplace",
        "repeat_customer",
        "other",
        "unknown",
    ],
)
def test_lead_source_values_are_accepted(client: TestClient, lead_source: str) -> None:
    response = client.post("/quote/calculate", json=_base_payload(lead_source=lead_source))

    assert response.status_code == 200
    assert response.json()["request"]["lead_source"] == lead_source


@pytest.mark.parametrize("lead_source", ["", "   ", None])
def test_blank_or_missing_lead_source_stores_unknown(client: TestClient, lead_source: Any) -> None:
    response = client.post("/quote/calculate", json=_base_payload(lead_source=lead_source))

    assert response.status_code == 200
    assert response.json()["request"]["lead_source"] == "unknown"


def test_invalid_nonblank_lead_source_is_rejected(client: TestClient) -> None:
    response = client.post("/quote/calculate", json=_base_payload(lead_source="flyer"))

    assert response.status_code == 422


def test_non_access_structured_intake_fields_do_not_change_quote_totals(client: TestClient) -> None:
    non_access_fields = {
        key: value
        for key, value in _structured_fields().items()
        if key not in {"stairs_count", "basement_or_inside_removal"}
    }

    baseline = client.post("/quote/calculate", json=_base_payload()).json()["response"]
    enriched = client.post("/quote/calculate", json=_base_payload(**non_access_fields)).json()["response"]

    assert enriched["cash_total_cad"] == baseline["cash_total_cad"]
    assert enriched["emt_total_cad"] == baseline["emt_total_cad"]


def test_structured_access_fields_raise_public_quote_to_difficult_access(client: TestClient) -> None:
    baseline_response = client.post(
        "/quote/calculate",
        json=_base_payload(
            garbage_bag_count=5,
            stairs_count=0,
            basement_or_inside_removal=False,
        ),
    )
    structured_response = client.post(
        "/quote/calculate",
        json=_base_payload(
            garbage_bag_count=5,
            access_difficulty="normal",
            stairs_count=1,
            basement_or_inside_removal=False,
        ),
    )
    explicit_difficult_response = client.post(
        "/quote/calculate",
        json=_base_payload(
            garbage_bag_count=5,
            access_difficulty="difficult",
        ),
    )

    assert baseline_response.status_code == 200
    assert structured_response.status_code == 200
    assert explicit_difficult_response.status_code == 200

    baseline = baseline_response.json()["response"]
    structured = structured_response.json()["response"]
    explicit_difficult = explicit_difficult_response.json()["response"]

    assert structured_response.json()["request"]["stairs_count"] == 1
    assert structured["cash_total_cad"] == explicit_difficult["cash_total_cad"]
    assert structured["emt_total_cad"] == explicit_difficult["emt_total_cad"]
    assert structured["cash_total_cad"] > baseline["cash_total_cad"]


def test_lead_source_does_not_change_quote_totals(client: TestClient) -> None:
    baseline = client.post("/quote/calculate", json=_base_payload()).json()["response"]
    sourced = client.post("/quote/calculate", json=_base_payload(lead_source="facebook")).json()["response"]

    assert sourced["cash_total_cad"] == baseline["cash_total_cad"]
    assert sourced["emt_total_cad"] == baseline["emt_total_cad"]


def test_only_structured_access_fields_reach_non_demolition_quote_engine_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_calculate_quote = quote_service.calculate_quote
    seen_kwargs: list[dict[str, Any]] = []

    def capture_calculate_quote(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(dict(kwargs))
        return original_calculate_quote(**kwargs)

    monkeypatch.setattr(quote_service, "calculate_quote", capture_calculate_quote)

    artifacts = quote_service.build_quote_artifacts(_base_payload(**_structured_fields()))

    assert artifacts["response"]["cash_total_cad"] > 0
    assert len(seen_kwargs) == 2
    pricing_fields = {"stairs_count", "basement_or_inside_removal"}
    non_pricing_fields = set(_structured_fields()) - pricing_fields
    for kwargs in seen_kwargs:
        for field in pricing_fields:
            assert field in kwargs
        for field in non_pricing_fields:
            assert field not in kwargs
        assert "lead_source" not in kwargs


def test_demolition_structured_risk_fields_reach_quote_engine_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    original_calculate_quote = quote_service.calculate_quote
    seen_kwargs: list[dict[str, Any]] = []

    def capture_calculate_quote(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(dict(kwargs))
        return original_calculate_quote(**kwargs)

    monkeypatch.setattr(quote_service, "calculate_quote", capture_calculate_quote)

    artifacts = quote_service.build_quote_artifacts(
        _base_payload(
            service_type="demolition",
            description="Brick demolition from basement with tight access.",
            **_structured_fields(),
        )
    )

    assert artifacts["response"]["cash_total_cad"] >= 1500.0
    assert len(seen_kwargs) == 2
    pricing_fields = {
        "stairs_count",
        "floor_count",
        "basement_or_inside_removal",
        "demolition_ripout",
        "construction_debris_type",
        "dense_material_type",
    }
    non_pricing_fields = set(_structured_fields()) - pricing_fields
    for kwargs in seen_kwargs:
        for field in pricing_fields:
            assert field in kwargs
        for field in non_pricing_fields:
            assert field not in kwargs
        assert "lead_source" not in kwargs


def test_structured_intake_fields_are_stored_in_quote_request_json(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_base_payload(**_structured_fields()))
    assert quote_response.status_code == 200
    quote_id = quote_response.json()["quote_id"]

    saved_quote = storage.get_quote_record(quote_id)
    assert saved_quote is not None
    for field, expected in _structured_fields().items():
        assert saved_quote["request"][field] == expected


def test_lead_source_persists_through_request_and_job_json(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_base_payload(lead_source="referral"))
    assert quote_response.status_code == 200
    quote_body = quote_response.json()
    quote_id = quote_body["quote_id"]
    accept_token = quote_body["accept_token"]

    saved_quote = storage.get_quote_record(quote_id)
    assert saved_quote is not None
    assert saved_quote["request"]["lead_source"] == "referral"

    accept_response = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "accept", "accept_token": accept_token},
    )
    assert accept_response.status_code == 200
    request_id = accept_response.json()["request_id"]

    saved_request = storage.get_quote_request_record(request_id)
    assert saved_request is not None
    assert saved_request["request_json"]["lead_source"] == "referral"

    approval_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=_admin_headers(),
        json={"action": "approve"},
    )
    assert approval_response.status_code == 200

    saved_job = storage.get_job_by_quote_id(quote_id)
    assert saved_job is not None
    assert saved_job["request_json"]["lead_source"] == "referral"


def test_structured_intake_fields_persist_through_request_and_job_json(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_base_payload(**_structured_fields()))
    assert quote_response.status_code == 200
    quote_body = quote_response.json()
    quote_id = quote_body["quote_id"]
    accept_token = quote_body["accept_token"]

    accept_response = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "accept", "accept_token": accept_token},
    )
    assert accept_response.status_code == 200
    request_id = accept_response.json()["request_id"]

    saved_request = storage.get_quote_request_record(request_id)
    assert saved_request is not None
    for field, expected in _structured_fields().items():
        assert saved_request["request_json"][field] == expected

    approval_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=_admin_headers(),
        json={"action": "approve"},
    )
    assert approval_response.status_code == 200

    saved_job = storage.get_job_by_quote_id(quote_id)
    assert saved_job is not None
    for field, expected in _structured_fields().items():
        assert saved_job["request_json"][field] == expected
