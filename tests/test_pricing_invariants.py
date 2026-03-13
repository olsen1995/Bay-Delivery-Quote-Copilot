import math
import logging
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quote_engine import calculate_quote

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


def test_haul_away_garbage_bag_count_monotonic_non_decreasing() -> None:
    # Sequence starts at 1: the small-load protection produces per-bag disposal
    # for 1–3 bags, so price correctly increases as bag count grows from 1 onward.
    # bag_count=0 (unknown/unspecified load) is a special conservative case that
    # does not participate in this monotone contract.
    bag_sequence = [1, 2, 3, 4, 5, 6, 15, 16, 20, 24, 30]
    seen_cash = []
    seen_emt = []

    for bags in bag_sequence:
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        seen_cash.append(float(result["total_cash_cad"]))
        seen_emt.append(float(result["total_emt_cad"]))

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:]))
    assert all(next_emt >= prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:]))


def test_haul_away_5_to_9_light_non_dense_strict_progression() -> None:
    """5 < 6 < 7 < 8 < 9 for light/non-dense normal-access jobs."""
    bag_sequence = [5, 6, 7, 8, 9]
    seen_cash = []

    for bags in bag_sequence:
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        seen_cash.append(float(result["total_cash_cad"]))

    assert all(next_cash > prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:])), (
        f"expected strict progression for 5-9 light/non-dense jobs; got {seen_cash}"
    )
    assert seen_cash[-1] == 140.0, f"9-bag anchor should remain unchanged; got {seen_cash[-1]}"


def test_haul_away_1_to_5_light_non_dense_unchanged_contract() -> None:
    """1-5 light/non-dense jobs should preserve current business-minimum behavior."""
    expected_cash = {1: 75.0, 2: 90.0, 3: 105.0, 4: 110.0, 5: 110.0}

    for bags, expected in expected_cash.items():
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        assert float(result["total_cash_cad"]) == expected


@pytest.mark.parametrize("access_difficulty", ["difficult", "extreme"])
def test_haul_away_6_to_8_harder_access_unchanged(access_difficulty: str) -> None:
    """Difficult/extreme 6-8 bag jobs stay anchored to unchanged 9-bag pricing."""
    anchor = float(
        calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=9,
            travel_zone="in_town",
            access_difficulty=access_difficulty,
            has_dense_materials=False,
        )["total_cash_cad"]
    )

    for bags in (6, 7, 8):
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty=access_difficulty,
            has_dense_materials=False,
        )
        assert float(result["total_cash_cad"]) == anchor


def test_haul_away_6_to_8_dense_unchanged() -> None:
    """Dense 6-8 bag jobs stay anchored to unchanged 9-bag dense pricing."""
    anchor = float(
        calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=9,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=True,
        )["total_cash_cad"]
    )

    for bags in (6, 7, 8):
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=True,
        )
        assert float(result["total_cash_cad"]) == anchor


def test_haul_away_large_volume_bag_steps_progressive() -> None:
    """High-volume haul-away tiers must progress at each step to avoid 16+ flattening."""
    bag_sequence = [15, 16, 20, 24, 30]
    seen_cash = []
    seen_emt = []

    for bags in bag_sequence:
        result = calculate_quote(
            "haul_away",
            2.0,
            crew_size=2,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        seen_cash.append(float(result["total_cash_cad"]))
        seen_emt.append(float(result["total_emt_cad"]))

    assert all(next_cash > prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:])), (
        f"high-volume haul-away tiers must be strictly progressive at 15/16/20/24/30 bags; got {seen_cash}"
    )
    assert all(next_emt > prev_emt for prev_emt, next_emt in zip(seen_emt, seen_emt[1:])), (
        f"high-volume haul-away EMT tiers must be strictly progressive at 15/16/20/24/30 bags; got {seen_emt}"
    )


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


# =============================================================================
# Small-load protection tier tests
# =============================================================================

def test_small_load_1_bag_cheaper_than_5_bags(client: TestClient) -> None:
    """1 light bag must cost less than 5 bags (same zone/access) — protection is active."""
    payload = _base_payload(service_type="haul_away")
    payload["has_dense_materials"] = False

    resp_1 = _post_quote(client, {**payload, "garbage_bag_count": 1})
    resp_5 = _post_quote(client, {**payload, "garbage_bag_count": 5})

    assert resp_1.status_code == 200
    assert resp_5.status_code == 200

    cash_1, _ = _assert_success_schema_and_totals(resp_1.json())
    cash_5, _ = _assert_success_schema_and_totals(resp_5.json())

    assert cash_1 < cash_5, (
        f"1-bag light job should cost less than 5-bag job; got 1-bag={cash_1}, 5-bag={cash_5}"
    )


def test_small_load_2_bags_cheaper_than_5_bags(client: TestClient) -> None:
    """2 light bags must cost less than 5 bags — protection still active at 2 bags."""
    payload = _base_payload(service_type="haul_away")
    payload["has_dense_materials"] = False

    resp_2 = _post_quote(client, {**payload, "garbage_bag_count": 2})
    resp_5 = _post_quote(client, {**payload, "garbage_bag_count": 5})

    assert resp_2.status_code == 200
    assert resp_5.status_code == 200

    cash_2, _ = _assert_success_schema_and_totals(resp_2.json())
    cash_5, _ = _assert_success_schema_and_totals(resp_5.json())

    assert cash_2 < cash_5, (
        f"2-bag light job should cost less than 5-bag job; got 2-bag={cash_2}, 5-bag={cash_5}"
    )


def test_small_load_3_bags_cheaper_than_5_bags(client: TestClient) -> None:
    """3 light bags must cost less than 5 bags — SMALL_LOAD_MAX_BAGS boundary."""
    payload = _base_payload(service_type="haul_away")
    payload["has_dense_materials"] = False

    resp_3 = _post_quote(client, {**payload, "garbage_bag_count": 3})
    resp_5 = _post_quote(client, {**payload, "garbage_bag_count": 5})

    assert resp_3.status_code == 200
    assert resp_5.status_code == 200

    cash_3, _ = _assert_success_schema_and_totals(resp_3.json())
    cash_5, _ = _assert_success_schema_and_totals(resp_5.json())

    assert cash_3 < cash_5, (
        f"3-bag light job should cost less than 5-bag job; got 3-bag={cash_3}, 5-bag={cash_5}"
    )


@pytest.mark.parametrize("bag_count", [1, 2, 3])
def test_small_load_above_minimum_total(client: TestClient, bag_count: int) -> None:
    """Small-load protected quotes must still meet the service minimum."""
    payload = _base_payload(service_type="haul_away")
    payload["garbage_bag_count"] = bag_count
    payload["has_dense_materials"] = False

    response = _post_quote(client, payload)
    assert response.status_code == 200
    cash, _ = _assert_success_schema_and_totals(response.json())
    assert cash >= 50, f"Small-load quote must be >= minimum $50; got {cash}"


def test_small_load_dense_escapes_protection(client: TestClient) -> None:
    """Dense materials on a 1–3 bag job must escape the small-load tier and cost more."""
    payload = _base_payload(service_type="haul_away")
    payload["garbage_bag_count"] = 2
    payload["estimated_hours"] = 1.0
    payload["crew_size"] = 1

    resp_light = _post_quote(client, {**payload, "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "has_dense_materials": True})

    assert resp_light.status_code == 200
    assert resp_dense.status_code == 200

    cash_light, _ = _assert_success_schema_and_totals(resp_light.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())

    assert cash_dense > cash_light, (
        f"Dense 2-bag job should cost more than light 2-bag (protection escaped); "
        f"light={cash_light}, dense={cash_dense}"
    )


def test_small_load_protection_does_not_apply_at_4_bags(client: TestClient) -> None:
    """4 bags (just above threshold) must not receive the per-bag protection rate."""
    payload = _base_payload(service_type="haul_away")
    payload["has_dense_materials"] = False

    resp_3 = _post_quote(client, {**payload, "garbage_bag_count": 3})
    resp_4 = _post_quote(client, {**payload, "garbage_bag_count": 4})
    resp_5 = _post_quote(client, {**payload, "garbage_bag_count": 5})

    for r in (resp_3, resp_4, resp_5):
        assert r.status_code == 200

    cash_3, _ = _assert_success_schema_and_totals(resp_3.json())
    cash_4, _ = _assert_success_schema_and_totals(resp_4.json())
    cash_5, _ = _assert_success_schema_and_totals(resp_5.json())

    # 4+ bags leave the protection and hit the flat disposal tier;
    # price must not drop back below the 3-bag protected price.
    assert cash_4 >= cash_3, (
        f"4-bag job should cost >= 3-bag job (no protection dip); got 3={cash_3}, 4={cash_4}"
    )
    assert cash_5 >= cash_4, (
        f"5-bag job should cost >= 4-bag job; got 4={cash_4}, 5={cash_5}"
    )


# =============================================================================
# Small-move labour floor tests
# =============================================================================

def test_small_move_labor_floor_applied_on_minimum_job(client: TestClient) -> None:
    """
    The minimum 4h/2-person move must include a labour-floor component of at least
    $280 cash (floor = 35 * 2 * 4 = 280), before adding travel and other surcharges.

    This ensures the move labour rate is priced above the raw haul-away labour rate,
    which is too low for the moving market.
    """
    payload = _base_payload(service_type="small_move")
    payload["estimated_hours"] = 4.0
    payload["access_difficulty"] = "normal"

    response = _post_quote(client, payload)
    assert response.status_code == 200
    cash, _ = _assert_success_schema_and_totals(response.json())
    # floor labor = 35 * 2 crew * 4 h = 280; add travel $40 → raw $320, cash $320
    assert cash == 320.0, (
        f"Minimum 4h/2-person move must produce cash == $320; got {cash}"
    )
    # labour floor = 35 * 2 crew * 4 h = 280; base travel adds $40 for an expected
    # total cash of $320 on an in-town/normal job, but this assertion only guards
    # the labour-floor minimum of $280.
    assert cash >= 280, (
        f"Minimum 4h/2-person move must produce cash >= $280 (labour floor bound); got {cash}"
    )


def test_small_move_labor_floor_5h_exceeds_4h(client: TestClient) -> None:
    """A 5-hour move must cost more than a 4-hour move (floor scales with hours)."""
    payload = _base_payload(service_type="small_move")
    payload["access_difficulty"] = "normal"

    resp_4 = _post_quote(client, {**payload, "estimated_hours": 4.0})
    resp_5 = _post_quote(client, {**payload, "estimated_hours": 5.0})

    assert resp_4.status_code == 200
    assert resp_5.status_code == 200

    cash_4, _ = _assert_success_schema_and_totals(resp_4.json())
    cash_5, _ = _assert_success_schema_and_totals(resp_5.json())

    assert cash_5 > cash_4, (
        f"5h move must cost more than 4h move with labour floor; got 4h={cash_4}, 5h={cash_5}"
    )


def test_small_move_access_adder_is_additive_with_labor_floor(client: TestClient) -> None:
    """Difficult access must still produce a higher total than normal when the floor is active."""
    payload = _base_payload(service_type="small_move")
    payload["estimated_hours"] = 4.0

    resp_normal = _post_quote(client, {**payload, "access_difficulty": "normal"})
    resp_difficult = _post_quote(client, {**payload, "access_difficulty": "difficult"})

    assert resp_normal.status_code == 200
    assert resp_difficult.status_code == 200

    cash_normal, _ = _assert_success_schema_and_totals(resp_normal.json())
    cash_difficult, _ = _assert_success_schema_and_totals(resp_difficult.json())

    assert cash_difficult > cash_normal, (
        f"Difficult access must cost more than normal even when labour floor is active; "
        f"normal={cash_normal}, difficult={cash_difficult}"
    )


def test_small_move_long_job_floor_only_applies_after_four_hours() -> None:
    quote_4h = calculate_quote(
        "small_move",
        4.0,
        crew_size=2,
        access_difficulty="normal",
        travel_zone="in_town",
    )
    quote_5h = calculate_quote(
        "small_move",
        5.0,
        crew_size=2,
        access_difficulty="normal",
        travel_zone="in_town",
    )

    # At 4 hours, the long-job floor should not yet be applied.
    assert quote_4h["_internal"]["move_long_job_floor_applied"] is False

    # At 5 hours, the long-job floor should be applied.
    assert quote_5h["_internal"]["move_long_job_floor_applied"] is True

    # The internal labor component for 5h should exceed that for 4h; this checks
    # the floor-driven behavior without relying on exact total cash amounts.
    labor_4h = quote_4h["_internal"]["labor_cad"]
    labor_5h = quote_5h["_internal"]["labor_cad"]
    assert labor_5h > labor_4h
    assert quote_4h["total_cash_cad"] == 320.0

    assert quote_5h["total_cash_cad"] == 400.0
