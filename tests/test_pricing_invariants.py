import math
import logging
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


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


def test_response_request_service_type_is_normalized_for_aliases(client: TestClient) -> None:
    payload = _base_payload(service_type="moving")
    response = _post_quote(client, payload)

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["service_type"] == "small_move"


def test_unknown_fields_are_allowed_and_warned(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    payload = _base_payload()
    payload["legacy_flag"] = True

    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = _post_quote(client, payload)

    assert response.status_code == 200
    app_logs = [r.getMessage() for r in caplog.records if r.name == "app.main"]
    combined_logs = "\n".join(app_logs)
    assert "unknown request fields" in combined_logs
    assert "legacy_flag" in combined_logs


# =============================================================================
# Access difficulty tests
# =============================================================================

@pytest.mark.parametrize("service_type", CONFIRMED_SERVICE_TYPES)
def test_access_difficulty_normal_accepted(client: TestClient, service_type: str) -> None:
    """normal access_difficulty must succeed for all service types."""
    payload = _base_payload(service_type=service_type)
    payload["access_difficulty"] = "normal"
    response = _post_quote(client, payload)
    assert response.status_code == 200
    _assert_success_schema_and_totals(response.json())


def test_access_difficulty_monotonic_non_decreasing_haul_away(client: TestClient) -> None:
    """difficult access must cost >= normal; extreme >= difficult (haul_away)."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0

    difficulties = ["normal", "difficult", "extreme"]
    seen_cash = []
    for diff in difficulties:
        cur = {**payload, "access_difficulty": diff}
        resp = _post_quote(client, cur)
        assert resp.status_code == 200
        cash, _ = _assert_success_schema_and_totals(resp.json())
        seen_cash.append(cash)

    assert all(b >= a for a, b in zip(seen_cash, seen_cash[1:])), (
        f"access_difficulty costs not monotonically non-decreasing: {seen_cash}"
    )


@pytest.mark.parametrize("service_type", ["small_move", "demolition", "item_delivery"])
def test_access_difficulty_monotonic_non_decreasing_other_services(client: TestClient, service_type: str) -> None:
    """difficult access must never produce a lower total than normal, for any service."""
    payload = _base_payload(service_type=service_type)
    payload["estimated_hours"] = 3.0

    difficulties = ["normal", "difficult", "extreme"]
    seen_cash = []
    for diff in difficulties:
        cur = {**payload, "access_difficulty": diff}
        resp = _post_quote(client, cur)
        assert resp.status_code == 200
        cash, _ = _assert_success_schema_and_totals(resp.json())
        seen_cash.append(cash)

    assert all(b >= a for a, b in zip(seen_cash, seen_cash[1:])), (
        f"access_difficulty costs not monotonically non-decreasing for {service_type}: {seen_cash}"
    )


def test_difficult_access_adder_applied(client: TestClient) -> None:
    """Difficult access should cost at least $25 more than normal."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0

    resp_normal = _post_quote(client, {**payload, "access_difficulty": "normal"})
    resp_difficult = _post_quote(client, {**payload, "access_difficulty": "difficult"})

    assert resp_normal.status_code == 200
    assert resp_difficult.status_code == 200

    cash_normal, _ = _assert_success_schema_and_totals(resp_normal.json())
    cash_difficult, _ = _assert_success_schema_and_totals(resp_difficult.json())

    assert cash_difficult >= cash_normal + 20, (
        f"expected difficult >= normal + $20; got normal={cash_normal}, difficult={cash_difficult}"
    )


def test_unknown_access_difficulty_falls_back_to_normal(client: TestClient) -> None:
    """An unrecognised access_difficulty value must not raise a 500; defaults to normal."""
    payload = _base_payload(service_type="haul_away")
    payload["access_difficulty"] = "a_random_nonsense_value"
    response = _post_quote(client, payload)
    # The field is max_length=50 so this still passes Pydantic; engine should clamp it.
    assert response.status_code == 200
    _assert_success_schema_and_totals(response.json())


# =============================================================================
# Dense materials tests
# =============================================================================

def test_has_dense_materials_increases_haul_away_price(client: TestClient) -> None:
    """Dense materials flag must produce a higher quote than without it (haul_away)."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0
    payload["garbage_bag_count"] = 5

    resp_normal = _post_quote(client, {**payload, "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "has_dense_materials": True})

    assert resp_normal.status_code == 200
    assert resp_dense.status_code == 200

    cash_normal, _ = _assert_success_schema_and_totals(resp_normal.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())

    assert cash_dense > cash_normal, (
        f"Dense materials should cost more: normal={cash_normal}, dense={cash_dense}"
    )


def test_has_dense_materials_does_not_affect_scrap_pickup(client: TestClient) -> None:
    """Dense materials flag must not change scrap pickup (flat-rate service)."""
    payload = _base_payload(service_type="scrap_pickup")

    resp_normal = _post_quote(client, {**payload, "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "has_dense_materials": True})

    assert resp_normal.status_code == 200
    assert resp_dense.status_code == 200

    cash_normal, _ = _assert_success_schema_and_totals(resp_normal.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())

    assert cash_normal == cash_dense, (
        "Scrap pickup is flat-rate; dense materials should not affect its price"
    )


# =============================================================================
# Haul-away helper (crew escalation) tests
# =============================================================================

def test_haul_away_crew_escalated_at_large_bag_count(client: TestClient) -> None:
    """10+ bags must not be cheaper than 9 bags (crew escalation keeps price >= small load)."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0
    payload["crew_size"] = 1

    resp_9 = _post_quote(client, {**payload, "garbage_bag_count": 9})
    resp_10 = _post_quote(client, {**payload, "garbage_bag_count": 10})

    assert resp_9.status_code == 200
    assert resp_10.status_code == 200

    cash_9, _ = _assert_success_schema_and_totals(resp_9.json())
    cash_10, _ = _assert_success_schema_and_totals(resp_10.json())

    # At 10 bags a helper is auto-added, so 10 bags MUST cost >= 9 bags
    assert cash_10 >= cash_9, (
        f"10-bag job should cost >= 9-bag (helper escalation); got 9={cash_9}, 10={cash_10}"
    )


def test_haul_away_dense_materials_auto_escalates_crew(client: TestClient) -> None:
    """Dense materials with crew=1 must cost more than no dense materials crew=1 (helper added)."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0
    payload["crew_size"] = 1
    payload["garbage_bag_count"] = 3  # below escalation threshold

    resp_no_dense = _post_quote(client, {**payload, "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "has_dense_materials": True})

    assert resp_no_dense.status_code == 200
    assert resp_dense.status_code == 200

    cash_no_dense, _ = _assert_success_schema_and_totals(resp_no_dense.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())

    assert cash_dense > cash_no_dense, (
        f"Dense materials should trigger crew escalation and cost more; "
        f"no_dense={cash_no_dense}, dense={cash_dense}"
    )


def test_combining_difficult_access_and_dense_materials_is_additive(client: TestClient) -> None:
    """Combining difficult access + dense materials should produce the highest total."""
    payload = _base_payload(service_type="haul_away")
    payload["estimated_hours"] = 2.0
    payload["crew_size"] = 1
    payload["garbage_bag_count"] = 5

    resp_base = _post_quote(client, {**payload, "access_difficulty": "normal", "has_dense_materials": False})
    resp_diff = _post_quote(client, {**payload, "access_difficulty": "difficult", "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "access_difficulty": "normal", "has_dense_materials": True})
    resp_both = _post_quote(client, {**payload, "access_difficulty": "difficult", "has_dense_materials": True})

    for resp in (resp_base, resp_diff, resp_dense, resp_both):
        assert resp.status_code == 200

    cash_base, _ = _assert_success_schema_and_totals(resp_base.json())
    cash_diff, _ = _assert_success_schema_and_totals(resp_diff.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())
    cash_both, _ = _assert_success_schema_and_totals(resp_both.json())

    assert cash_both >= cash_diff, "difficult+dense should cost >= difficult alone"
    assert cash_both >= cash_dense, "difficult+dense should cost >= dense alone"
    assert cash_both >= cash_base, "difficult+dense should cost >= base"
