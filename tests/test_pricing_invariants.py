import math
from copy import deepcopy

import inspect

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


def _ensure_testclient_httpx_compat() -> None:
    """Compat for Starlette TestClient with newer httpx that removed `app=` kwarg."""
    params = inspect.signature(httpx.Client.__init__).parameters
    if "app" in params:
        return

    original_init = httpx.Client.__init__

    def patched_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return original_init(self, *args, **kwargs)

    httpx.Client.__init__ = patched_init


_ensure_testclient_httpx_compat()


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _base_payload(service_type: str = "haul_away") -> dict:
    return {
        "customer_name": "Invariant Tester",
        "customer_phone": "555-0100",
        "job_address": "123 Main St",
        "job_description_customer": "Regression invariant check",
        "description": "Regression invariant check",
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
    }


def _post_quote(client: TestClient, payload: dict):
    return client.post("/quote/calculate", json=payload)


def _assert_success_schema_and_totals(payload: dict) -> tuple[float, float]:
    assert isinstance(payload, dict)
    for key in ("quote_id", "created_at", "request", "response"):
        assert key in payload

    response = payload["response"]
    assert isinstance(response, dict)
    for key in ("cash_total_cad", "emt_total_cad", "disclaimer"):
        assert key in response

    cash = response["cash_total_cad"]
    emt = response["emt_total_cad"]

    assert isinstance(cash, (int, float))
    assert isinstance(emt, (int, float))
    assert math.isfinite(cash)
    assert math.isfinite(emt)
    assert cash >= 0
    assert emt >= 0
    assert isinstance(response["disclaimer"], str)

    return float(cash), float(emt)


# Confirmed service types from config/services and calculate_quote path.
CONFIRMED_SERVICE_TYPES = ["haul_away", "small_move", "item_delivery", "demolition", "scrap_pickup"]


@pytest.mark.parametrize("service_type", CONFIRMED_SERVICE_TYPES)
def test_emt_never_below_cash_and_totals_non_negative_finite(client: TestClient, service_type: str) -> None:
    payload = _base_payload(service_type=service_type)
    response = _post_quote(client, payload)

    assert response.status_code == 200
    cash, emt = _assert_success_schema_and_totals(response.json())
    assert emt >= cash


@pytest.mark.parametrize("service_type", ["haul_away", "small_move", "item_delivery", "demolition"])
def test_estimated_hours_monotonic_non_decreasing(client: TestClient, service_type: str) -> None:
    payload = _base_payload(service_type=service_type)

    hours_sequence = [0.0, 1.0, 2.0, 4.0, 8.0]
    seen_cash = []
    seen_emt = []

    for hours in hours_sequence:
        cur = deepcopy(payload)
        cur["estimated_hours"] = hours
        response = _post_quote(client, cur)
        assert response.status_code == 200
        cash, emt = _assert_success_schema_and_totals(response.json())
        seen_cash.append(cash)
        seen_emt.append(emt)

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


@pytest.mark.parametrize("service_type", ["haul_away", "small_move", "item_delivery", "demolition"])
def test_crew_size_monotonic_non_decreasing(client: TestClient, service_type: str) -> None:
    payload = _base_payload(service_type=service_type)
    payload["estimated_hours"] = 3.0

    crew_sequence = [1, 2, 3, 4]
    seen_cash = []
    seen_emt = []

    for crew in crew_sequence:
        cur = deepcopy(payload)
        cur["crew_size"] = crew
        response = _post_quote(client, cur)
        assert response.status_code == 200
        cash, emt = _assert_success_schema_and_totals(response.json())
        seen_cash.append(cash)
        seen_emt.append(emt)

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


def test_haul_away_garbage_bag_count_monotonic_non_decreasing(client: TestClient) -> None:
    payload = _base_payload(service_type="haul_away")

    bag_sequence = [0, 1, 5, 6, 15, 16, 30]
    seen_cash = []
    seen_emt = []

    for bags in bag_sequence:
        cur = deepcopy(payload)
        cur["garbage_bag_count"] = bags
        response = _post_quote(client, cur)
        assert response.status_code == 200
        cash, emt = _assert_success_schema_and_totals(response.json())
        seen_cash.append(cash)
        seen_emt.append(emt)

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


def test_haul_away_mattresses_count_monotonic_non_decreasing(client: TestClient) -> None:
    payload = _base_payload(service_type="haul_away")

    mattress_sequence = [0, 1, 2, 5]
    seen_cash = []
    seen_emt = []

    for mattresses in mattress_sequence:
        cur = deepcopy(payload)
        cur["mattresses_count"] = mattresses
        response = _post_quote(client, cur)
        assert response.status_code == 200
        cash, emt = _assert_success_schema_and_totals(response.json())
        seen_cash.append(cash)
        seen_emt.append(emt)

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


def test_haul_away_box_springs_count_monotonic_non_decreasing(client: TestClient) -> None:
    payload = _base_payload(service_type="haul_away")

    box_spring_sequence = [0, 1, 2, 5]
    seen_cash = []
    seen_emt = []

    for box_springs in box_spring_sequence:
        cur = deepcopy(payload)
        cur["box_springs_count"] = box_springs
        response = _post_quote(client, cur)
        assert response.status_code == 200
        cash, emt = _assert_success_schema_and_totals(response.json())
        seen_cash.append(cash)
        seen_emt.append(emt)

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


@pytest.mark.parametrize("service_type", ["small_move", "item_delivery", "moving", "delivery"])
@pytest.mark.parametrize("missing_fields", [("pickup_address",), ("dropoff_address",), ("pickup_address", "dropoff_address")])
def test_move_and_delivery_require_pickup_and_dropoff(
    client: TestClient,
    service_type: str,
    missing_fields: tuple[str, ...],
) -> None:
    payload = _base_payload(service_type=service_type)
    for field in missing_fields:
        payload[field] = None

    response = _post_quote(client, payload)
    assert response.status_code == 400
    body = response.json()
    assert body.get("detail") == "pickup_address and dropoff_address are required"


@pytest.mark.parametrize("service_type", ["small_move", "item_delivery", "moving", "delivery"])
def test_move_and_delivery_succeed_with_pickup_and_dropoff(client: TestClient, service_type: str) -> None:
    payload = _base_payload(service_type=service_type)
    response = _post_quote(client, payload)

    assert response.status_code == 200
    _assert_success_schema_and_totals(response.json())
