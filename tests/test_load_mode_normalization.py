import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _base_payload() -> dict:
    return {
        "customer_name": "Invariant Tester",
        "customer_phone": "705-555-0100",
        "job_address": "123 Main St",
        "job_description_customer": "Regression invariant check",
        "description": "Regression invariant check",
        "service_type": "haul_away",
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
    }


@pytest.mark.parametrize(
    ("load_mode", "expected"),
    [
        (None, "standard"),
        ("", "standard"),
        ("SPACEFILL_X", "standard"),
        ("space_fill", "space_fill"),
    ],
)
def test_quote_request_persists_normalized_load_mode(client: TestClient, load_mode: str | None, expected: str) -> None:
    payload = _base_payload()
    if load_mode is not None:
        payload["load_mode"] = load_mode

    response = client.post("/quote/calculate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["request"]["load_mode"] == expected
