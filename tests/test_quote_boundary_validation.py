from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.quote_service import build_quote_artifacts


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _base_payload(service_type: str = "haul_away") -> dict:
    payload = {
        "customer_name": "Boundary Tester",
        "customer_phone": "705-555-0100",
        "job_address": "123 Main St",
        "job_description_customer": "Boundary validation check",
        "description": "Boundary validation check",
        "service_type": service_type,
        "payment_method": "cash",
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


def _post_quote(client: TestClient, payload: dict):
    return client.post("/quote/calculate", json=payload)


def test_invalid_service_type_returns_400(client: TestClient) -> None:
    payload = _base_payload(service_type="mystery_service")

    response = _post_quote(client, payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid service_type."}


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("access_difficulty", "stairs??"),
        ("travel_zone", "mars"),
        ("scrap_pickup_location", "backyard"),
    ],
)
def test_invalid_enum_inputs_return_400(client: TestClient, field_name: str, value: str) -> None:
    payload = _base_payload()
    payload[field_name] = value

    response = _post_quote(client, payload)

    assert response.status_code == 400
    assert response.json() == {"detail": f"Invalid {field_name}."}


@pytest.mark.parametrize(
    ("service_type", "field_name", "value", "expected"),
    [
        ("haul_away", "access_difficulty", "Normal", "normal"),
        ("haul_away", "travel_zone", "IN_TOWN", "in_town"),
        ("scrap_pickup", "scrap_pickup_location", "Inside", "inside"),
    ],
)
def test_mixed_case_valid_enum_inputs_still_return_200(
    client: TestClient,
    service_type: str,
    field_name: str,
    value: str,
    expected: str,
) -> None:
    payload = _base_payload(service_type=service_type)
    payload[field_name] = value

    response = _post_quote(client, payload)

    assert response.status_code == 200
    assert response.json()["request"][field_name] == expected


def test_empty_haul_away_returns_400(client: TestClient) -> None:
    payload = _base_payload()
    payload["trailer_fill_estimate"] = None

    response = _post_quote(client, payload)

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Please add at least one load detail so we can estimate your junk removal properly. "
            "Examples: bags, trailer space used, mattresses, box springs, or dense materials."
        )
    }


def test_valid_known_trailer_fill_estimate_satisfies_haul_away_load_detail(client: TestClient) -> None:
    response = _post_quote(client, _base_payload())

    assert response.status_code == 200


def test_invalid_trailer_fill_text_does_not_satisfy_haul_away_load_detail_boundary() -> None:
    payload = _base_payload()
    payload["trailer_fill_estimate"] = "almost_full"

    with pytest.raises(HTTPException, match="Please add at least one load detail") as exc_info:
        build_quote_artifacts(payload)

    assert exc_info.value.status_code == 400


def test_valid_haul_away_bulky_signal_only_still_succeeds(client: TestClient) -> None:
    payload = _base_payload()
    payload["trailer_fill_estimate"] = None
    payload["description"] = "Single mattress at curbside outside."
    payload["job_description_customer"] = "Single mattress at curbside outside."

    response = _post_quote(client, payload)

    assert response.status_code == 200


def test_valid_alias_service_type_still_succeeds(client: TestClient) -> None:
    response = _post_quote(client, _base_payload(service_type="moving"))

    assert response.status_code == 200
    assert response.json()["request"]["service_type"] == "small_move"
