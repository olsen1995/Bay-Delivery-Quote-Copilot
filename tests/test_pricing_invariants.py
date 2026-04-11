import math
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import quote_engine
from app.quote_engine import calculate_quote

@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _base_payload(service_type: str = "haul_away") -> dict:
    return {
        "customer_name": "Invariant Tester",
        "customer_phone": "705-555-0100",
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
    expected_cash = {1: 80.0, 2: 95.0, 3: 105.0, 4: 110.0, 5: 110.0}

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


def test_space_fill_default_unchanged_when_omitted_vs_standard() -> None:
    standard_omitted = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    explicit_standard = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="standard",
    )
    assert float(standard_omitted["total_cash_cad"]) == float(explicit_standard["total_cash_cad"])
    assert float(standard_omitted["total_emt_cad"]) == float(explicit_standard["total_emt_cad"])


@pytest.mark.parametrize("service_type", ["small_move", "item_delivery", "demolition", "scrap_pickup"])
def test_space_fill_ignored_for_non_haul_away(service_type: str) -> None:
    baseline = calculate_quote(
        service_type,
        2.0,
        crew_size=2,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    space_fill = calculate_quote(
        service_type,
        2.0,
        crew_size=2,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="space_fill",
    )
    assert float(space_fill["total_cash_cad"]) == float(baseline["total_cash_cad"])
    assert float(space_fill["total_emt_cad"]) == float(baseline["total_emt_cad"])


def test_space_fill_discount_then_floor_protection_half_load() -> None:
    standard = calculate_quote(
        "haul_away",
        3.0,
        crew_size=2,
        garbage_bag_count=8,
        trailer_fill_estimate="half",
        travel_zone="out_of_town",
        access_difficulty="extreme",
        has_dense_materials=False,
    )
    space_fill = calculate_quote(
        "haul_away",
        3.0,
        crew_size=2,
        garbage_bag_count=8,
        trailer_fill_estimate="half",
        travel_zone="out_of_town",
        access_difficulty="extreme",
        has_dense_materials=False,
        load_mode="space_fill",
    )
    assert float(space_fill["total_cash_cad"]) <= float(standard["total_cash_cad"])
    assert float(space_fill["total_cash_cad"]) >= 300.0


@pytest.mark.parametrize(
    ("trailer_fill_estimate", "bags", "expected_floor"),
    [
        ("under_quarter", 1, 225.0),
        ("quarter", 4, 300.0),
        ("half", 7, 300.0),
        ("three_quarter", 10, 375.0),
    ],
)
def test_space_fill_floor_by_inferred_load_band(trailer_fill_estimate: str, bags: int, expected_floor: float) -> None:
    result = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=bags,
        trailer_fill_estimate=trailer_fill_estimate,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="space_fill",
    )
    assert float(result["total_cash_cad"]) >= expected_floor


def test_space_fill_full_load_ignored() -> None:
    standard = calculate_quote(
        "haul_away",
        2.0,
        crew_size=2,
        garbage_bag_count=18,
        trailer_fill_estimate="full",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    space_fill = calculate_quote(
        "haul_away",
        2.0,
        crew_size=2,
        garbage_bag_count=18,
        trailer_fill_estimate="full",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="space_fill",
    )
    assert float(space_fill["total_cash_cad"]) == float(standard["total_cash_cad"])


def test_space_fill_conflicting_signals_choose_larger_class() -> None:
    under_quarter_signal = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=12,
        trailer_fill_estimate="under_quarter",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="space_fill",
    )
    assert float(under_quarter_signal["total_cash_cad"]) >= 375.0


def test_space_fill_unrecognized_or_blank_load_mode_treated_as_standard() -> None:
    standard = calculate_quote(
        "haul_away",
        1.5,
        crew_size=1,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    blank_mode = calculate_quote(
        "haul_away",
        1.5,
        crew_size=1,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="",
    )
    unknown_mode = calculate_quote(
        "haul_away",
        1.5,
        crew_size=1,
        garbage_bag_count=6,
        trailer_fill_estimate="half",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="SPACEFILL_X",
    )
    assert float(blank_mode["total_cash_cad"]) == float(standard["total_cash_cad"])
    assert float(unknown_mode["total_cash_cad"]) == float(standard["total_cash_cad"])


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


def test_unknown_fields_are_rejected(client: TestClient) -> None:
    payload = _base_payload()
    payload["legacy_flag"] = True

    response = _post_quote(client, payload)

    assert response.status_code == 422
    body = response.json()
    assert body["detail"][0]["type"] == "extra_forbidden"
    assert body["detail"][0]["loc"] == ["body", "legacy_flag"]


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
    """Dense materials flag must not change scrap pickup under the current minimum-floor path."""
    payload = _base_payload(service_type="scrap_pickup")

    resp_normal = _post_quote(client, {**payload, "has_dense_materials": False})
    resp_dense = _post_quote(client, {**payload, "has_dense_materials": True})

    assert resp_normal.status_code == 200
    assert resp_dense.status_code == 200

    cash_normal, _ = _assert_success_schema_and_totals(resp_normal.json())
    cash_dense, _ = _assert_success_schema_and_totals(resp_dense.json())

    assert cash_normal == cash_dense, (
        "Scrap pickup stays on the current minimum-service-charge path; dense materials should not affect its price"
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
    assert cash >= 60, f"Small-load quote must be >= minimum $60; got {cash}"


def test_global_minimum_floor_applies_to_small_job() -> None:
    """The curbside scrap path must still be hard-floored to $60 cash."""
    result = calculate_quote(
        "scrap_pickup",
        0.0,
        scrap_pickup_location="curbside",
    )
    assert float(result["total_cash_cad"]) == 60.0


def test_global_minimum_overrides_legacy_50_service_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if a service minimum is set to $50, final cash must floor to $60."""
    config = quote_engine.load_config()
    item_delivery = config["services"]["item_delivery"]
    item_delivery["minimum_total"] = 50
    item_delivery["item_delivery_protected_base_floor_cad"] = 0
    config["minimum_charges"] = {"gas": 0, "wear_and_tear": 0}
    monkeypatch.setattr(quote_engine, "load_config", lambda: config)

    result = calculate_quote(
        "item_delivery",
        0.0,
        crew_size=1,
        travel_zone="in_town",
        access_difficulty="normal",
    )
    assert float(result["total_cash_cad"]) == 60.0


def test_demolition_minimum_75_remains_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Higher service minimums must remain intact under the global floor."""
    config = quote_engine.load_config()
    demolition = config["services"]["demolition"]
    demolition["minimum_total"] = 75
    demolition["minimum_hours"] = 0
    demolition["hourly_rate_primary"] = 0
    demolition["hourly_rate_helper"] = 0
    config["minimum_charges"] = {"gas": 0, "wear_and_tear": 0}
    monkeypatch.setattr(quote_engine, "load_config", lambda: config)

    result = calculate_quote(
        "demolition",
        0.0,
        crew_size=1,
        travel_zone="in_town",
        access_difficulty="normal",
    )
    assert float(result["total_cash_cad"]) == 75.0


def test_emt_total_still_correct_when_global_floor_applies() -> None:
    """Inside scrap must still compute EMT from the same $60 floor-protected cash total."""
    result = calculate_quote(
        "scrap_pickup",
        0.0,
        scrap_pickup_location="inside",
    )
    assert float(result["total_cash_cad"]) == 60.0
    assert float(result["total_emt_cad"]) == 67.8


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
# Haul-away bag-type and trailer-fill floor tests
# =============================================================================

@pytest.mark.parametrize(
    ("bag_count", "bag_type", "expected_cash"),
    [
        (32, "light", 330.0),
        (27, "heavy_mixed", 305.0),
        (20, "construction_debris", 300.0),
    ],
)
def test_haul_away_bag_type_floor_does_not_decrease_quote(
    bag_count: int,
    bag_type: str,
    expected_cash: float,
) -> None:
    baseline = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=bag_count,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    floored = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=bag_count,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        bag_type=bag_type,
    )

    assert float(floored["total_cash_cad"]) == expected_cash
    assert float(floored["total_cash_cad"]) >= float(baseline["total_cash_cad"])


@pytest.mark.parametrize(
    ("trailer_fill_estimate", "expected_cash"),
    [
        ("quarter", 175.0),
        ("half", 300.0),
        ("three_quarter", 400.0),
        ("full", 500.0),
    ],
)
def test_haul_away_trailer_fill_floor_raises_quote(
    trailer_fill_estimate: str,
    expected_cash: float,
) -> None:
    baseline = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=5,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    floored = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=5,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate=trailer_fill_estimate,
    )

    assert float(floored["total_cash_cad"]) == expected_cash
    assert float(floored["total_cash_cad"]) > float(baseline["total_cash_cad"])


def test_haul_away_trailer_fill_under_quarter_is_noop() -> None:
    baseline = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=5,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    floored = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=5,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="under_quarter",
    )

    assert float(floored["total_cash_cad"]) == float(baseline["total_cash_cad"])


def test_haul_away_bag_type_floor_requires_positive_bag_count() -> None:
    baseline = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=0,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    floored = calculate_quote(
        "haul_away",
        0.0,
        crew_size=1,
        garbage_bag_count=0,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        bag_type="construction_debris",
    )

    assert float(floored["total_cash_cad"]) == float(baseline["total_cash_cad"])


def test_haul_away_floor_only_raises_never_lowers_existing_quote() -> None:
    baseline = calculate_quote(
        "haul_away",
        2.0,
        crew_size=2,
        garbage_bag_count=16,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    floored = calculate_quote(
        "haul_away",
        2.0,
        crew_size=2,
        garbage_bag_count=16,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        bag_type="heavy_mixed",
        trailer_fill_estimate="quarter",
    )

    assert float(floored["total_cash_cad"]) == float(baseline["total_cash_cad"])


def test_non_haul_away_services_ignore_new_floor_inputs() -> None:
    baseline = calculate_quote(
        "small_move",
        4.0,
        crew_size=2,
        travel_zone="in_town",
        access_difficulty="normal",
    )
    with_optional_fields = calculate_quote(
        "small_move",
        4.0,
        crew_size=2,
        travel_zone="in_town",
        access_difficulty="normal",
        bag_type="construction_debris",
        trailer_fill_estimate="full",
    )

    assert float(with_optional_fields["total_cash_cad"]) == float(baseline["total_cash_cad"])
    assert float(with_optional_fields["total_emt_cad"]) == float(baseline["total_emt_cad"])


def test_haul_away_omitted_new_fields_preserve_existing_anchor_values_through_24_bags() -> None:
    expected_cash = {
        1: 80.0,
        5: 110.0,
        9: 140.0,
        15: 170.0,
        16: 205.0,
        20: 250.0,
        24: 260.0,
    }

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


def test_haul_away_high_volume_disposal_progression_above_24_bags() -> None:
    expected_cash = {
        24: 260.0,
        30: 305.0,
        40: 330.0,
        50: 360.0,
    }

    seen_cash = []
    for bags in (24, 30, 40, 50):
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        cash = float(result["total_cash_cad"])
        seen_cash.append(cash)
        assert cash == expected_cash[bags]

    assert all(next_cash > prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:])), (
        f"expected strict high-volume progression for 24/30/40/50 bags; got {seen_cash}"
    )


def test_haul_away_dense_disposal_uplift_applies_only_above_24_bags() -> None:
    light_24 = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=24,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    dense_24 = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=24,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=True,
    )

    assert float(dense_24["_internal"]["disposal_allowance_cad"]) == float(light_24["_internal"]["disposal_allowance_cad"])

    light_30 = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    dense_30 = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=True,
    )

    light_disposal_30 = float(light_30["_internal"]["disposal_allowance_cad"])
    dense_disposal_30 = float(dense_30["_internal"]["disposal_allowance_cad"])

    assert dense_disposal_30 == pytest.approx(light_disposal_30 * 1.15, rel=0, abs=0.01)
    assert dense_disposal_30 > light_disposal_30


@pytest.mark.parametrize("raw_value", [None, "not-a-number", float("nan"), float("inf"), 0, -1])
def test_dense_disposal_multiplier_fallback_invalid_values_through_quote_behavior(monkeypatch: pytest.MonkeyPatch, raw_value) -> None:
    config = quote_engine.load_config()
    haul_away = config["services"]["haul_away"]
    if raw_value is None:
        haul_away.pop("dense_material_disposal_multiplier", None)
    else:
        haul_away["dense_material_disposal_multiplier"] = raw_value
    monkeypatch.setattr(quote_engine, "load_config", lambda: config)

    light = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    dense = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=True,
    )

    assert float(dense["_internal"]["disposal_allowance_cad"]) == float(light["_internal"]["disposal_allowance_cad"])


@pytest.mark.parametrize("raw_value", [1.15, "1.15", 2])
def test_dense_disposal_multiplier_accepts_valid_numeric_values_through_quote_behavior(monkeypatch: pytest.MonkeyPatch, raw_value) -> None:
    config = quote_engine.load_config()
    config["services"]["haul_away"]["dense_material_disposal_multiplier"] = raw_value
    monkeypatch.setattr(quote_engine, "load_config", lambda: config)

    light = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
    )
    dense = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=30,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=True,
    )

    expected_dense_disposal = float(light["_internal"]["disposal_allowance_cad"]) * float(raw_value)
    assert float(dense["_internal"]["disposal_allowance_cad"]) == pytest.approx(expected_dense_disposal, rel=0, abs=0.01)


def test_quote_api_accepts_valid_haul_away_floor_fields(client: TestClient) -> None:
    payload = _base_payload(service_type="haul_away")
    payload["garbage_bag_count"] = 20
    payload["bag_type"] = "construction_debris"
    payload["trailer_fill_estimate"] = "half"

    response = _post_quote(client, payload)
    assert response.status_code == 200
    body = response.json()
    assert body["request"]["bag_type"] == "construction_debris"
    assert body["request"]["trailer_fill_estimate"] == "half"
    assert isinstance(body.get("accept_token"), str)
    assert body["accept_token"]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("bag_type", "invalid_bag_type"),
        ("trailer_fill_estimate", "almost_full"),
    ],
)
def test_quote_api_rejects_invalid_haul_away_floor_fields(
    client: TestClient,
    field_name: str,
    value: str,
) -> None:
    payload = _base_payload(service_type="haul_away")
    payload[field_name] = value

    response = _post_quote(client, payload)
    assert response.status_code == 422


# =============================================================================
# Small-move labour floor tests
# =============================================================================

def test_small_move_labor_floor_applied_on_minimum_job(client: TestClient) -> None:
    """
    The minimum 4h/2-person move must include a labour-floor component of at least
    $288 pre-round labour (labour floor = 36 * 2 * 4 = 288), before adding travel and other surcharges.

    This ensures the move labour rate is priced above the raw haul-away labour rate,
    which is too low for the moving market.
    """
    payload = _base_payload(service_type="small_move")
    payload["estimated_hours"] = 4.0
    payload["access_difficulty"] = "normal"

    response = _post_quote(client, payload)
    assert response.status_code == 200
    cash, _ = _assert_success_schema_and_totals(response.json())
    # floor labor = 36 * 2 crew * 4 h = 288; add travel $40 → raw $328, cash $330
    assert cash == 330.0, (
        f"Minimum 4h/2-person move must produce cash == $330; got {cash}"
    )
    # labour floor = 36 * 2 crew * 4 h = 288; base travel adds $40 for a raw
    # pre-round total of $328 on an in-town/normal job.
    assert cash >= 288, (
        f"Minimum 4h/2-person move must produce cash >= $288 (labour floor bound); got {cash}"
    )


def test_item_delivery_floor_0h_1h_2h_non_decreasing_and_protected() -> None:
    """item_delivery should keep a protected floor for 0h-1h and remain non-decreasing."""
    seen_cash = []
    for hours in (0.0, 1.0, 2.0):
        quote = calculate_quote(
            "item_delivery",
            hours,
            crew_size=1,
            travel_zone="in_town",
            access_difficulty="normal",
        )
        seen_cash.append(float(quote["total_cash_cad"]))

    assert all(next_cash >= prev_cash for prev_cash, next_cash in zip(seen_cash, seen_cash[1:])), (
        f"item_delivery 0h/1h/2h should be non-decreasing; got {seen_cash}"
    )
    assert all(cash >= 100.0 for cash in seen_cash), (
        f"item_delivery 0h/1h/2h should each be >= $100 cash; got {seen_cash}"
    )


def test_item_delivery_access_adders_stack_on_top_of_protected_floor() -> None:
    """item_delivery access adders should stack over the protected base floor."""
    normal = calculate_quote(
        "item_delivery",
        0.0,
        crew_size=1,
        travel_zone="in_town",
        access_difficulty="normal",
    )
    difficult = calculate_quote(
        "item_delivery",
        0.0,
        crew_size=1,
        travel_zone="in_town",
        access_difficulty="difficult",
    )
    extreme = calculate_quote(
        "item_delivery",
        0.0,
        crew_size=1,
        travel_zone="in_town",
        access_difficulty="extreme",
    )

    normal_cash = float(normal["total_cash_cad"])
    difficult_cash = float(difficult["total_cash_cad"])
    extreme_cash = float(extreme["total_cash_cad"])

    assert normal_cash < difficult_cash < extreme_cash
    assert difficult_cash == normal_cash + 25.0
    assert extreme_cash == normal_cash + 60.0


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

    # The internal labor component for 5h should exceed that for 4h, confirming
    # the floor-driven behavior; we also assert exact total cash amounts here to
    # lock in the current pricing for this scenario.
    labor_4h = quote_4h["_internal"]["labor_cad"]
    labor_5h = quote_5h["_internal"]["labor_cad"]
    assert labor_5h > labor_4h
    assert quote_4h["total_cash_cad"] == 330.0

    assert quote_5h["total_cash_cad"] == 430.0


@pytest.mark.parametrize(
    ("hours", "access_difficulty", "expected_cash"),
    [
        (4.0, "normal", 330.0),
        (5.0, "normal", 430.0),
        (4.0, "difficult", 355.0),
        (5.0, "difficult", 455.0),
    ],
)
def test_small_move_two_person_selective_targets(hours: float, access_difficulty: str, expected_cash: float) -> None:
    quote = calculate_quote(
        "small_move",
        hours,
        crew_size=2,
        travel_zone="in_town",
        access_difficulty=access_difficulty,
    )

    assert float(quote["total_cash_cad"]) == expected_cash


# =============================================================================
# Trailer-class aware pricing tests
# =============================================================================

def test_haul_away_trailer_class_omitted_matches_baseline() -> None:
    """Omitting trailer_class must produce identical results to not passing it at all."""
    base = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
    )
    with_none = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
        trailer_class=None,
    )
    assert float(with_none["total_cash_cad"]) == float(base["total_cash_cad"])


def test_haul_away_double_axle_uses_default_anchors() -> None:
    """double_axle_open_aluminum has no class-specific table so falls through to default anchors."""
    default = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
    )
    double_axle = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
        trailer_class="double_axle_open_aluminum",
    )
    assert float(double_axle["total_cash_cad"]) == float(default["total_cash_cad"])


def test_haul_away_single_axle_quarter_uses_lower_floor() -> None:
    """single_axle_open_aluminum at quarter fill uses $150 floor, less than default $175."""
    default_quarter = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
    )
    single_axle_quarter = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate="quarter",
        trailer_class="single_axle_open_aluminum",
    )
    assert float(default_quarter["total_cash_cad"]) == 175.0
    assert float(single_axle_quarter["total_cash_cad"]) == 150.0
    assert float(single_axle_quarter["total_cash_cad"]) < float(default_quarter["total_cash_cad"])


@pytest.mark.parametrize("trailer_fill_estimate", ["half", "three_quarter", "full"])
def test_haul_away_single_axle_higher_fills_match_default(trailer_fill_estimate: str) -> None:
    """single_axle_open_aluminum at half/three_quarter/full anchors match the default lane."""
    default = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate=trailer_fill_estimate,
    )
    single_axle = calculate_quote(
        "haul_away", 0.0,
        crew_size=1, garbage_bag_count=5,
        travel_zone="in_town", access_difficulty="normal",
        has_dense_materials=False,
        trailer_fill_estimate=trailer_fill_estimate,
        trailer_class="single_axle_open_aluminum",
    )
    assert float(single_axle["total_cash_cad"]) == float(default["total_cash_cad"])


@pytest.mark.parametrize("trailer_class", ["older_enclosed", "newer_enclosed"])
def test_small_move_enclosed_trailer_adds_40_uplift(trailer_class: str) -> None:
    """small_move applies the enclosed-trailer adder only for enclosed trailer classes."""
    base = calculate_quote(
        "small_move", 4.0,
        crew_size=2,
        travel_zone="in_town", access_difficulty="normal",
    )
    with_tc = calculate_quote(
        "small_move", 4.0,
        crew_size=2,
        travel_zone="in_town", access_difficulty="normal",
        trailer_class=trailer_class,
    )
    assert float(with_tc["total_cash_cad"]) == float(base["total_cash_cad"]) + 40.0
    assert float(with_tc["_internal"]["small_move_enclosed_trailer_adder_cad"]) == 40.0


@pytest.mark.parametrize("trailer_class", [None, "single_axle_open_aluminum", "double_axle_open_aluminum"])
def test_small_move_open_or_missing_trailer_class_remains_unchanged(trailer_class: str | None) -> None:
    """small_move keeps open trailer classes and missing trailer_class neutral."""
    base = calculate_quote(
        "small_move", 4.0,
        crew_size=2,
        travel_zone="in_town", access_difficulty="normal",
    )
    with_tc = calculate_quote(
        "small_move", 4.0,
        crew_size=2,
        travel_zone="in_town", access_difficulty="normal",
        trailer_class=trailer_class,
    )
    assert float(with_tc["total_cash_cad"]) == float(base["total_cash_cad"])
    assert float(with_tc["_internal"]["small_move_enclosed_trailer_adder_cad"]) == 0.0


@pytest.mark.parametrize("trailer_class", ["older_enclosed", "newer_enclosed"])
def test_item_delivery_enclosed_trailer_adds_30_uplift(trailer_class: str) -> None:
    """item_delivery applies a +$30 adder only for enclosed trailer classes."""
    base = calculate_quote(
        "item_delivery", 0.0,
        crew_size=1,
        travel_zone="in_town", access_difficulty="normal",
    )
    with_tc = calculate_quote(
        "item_delivery", 0.0,
        crew_size=1,
        travel_zone="in_town", access_difficulty="normal",
        trailer_class=trailer_class,
    )
    assert float(with_tc["total_cash_cad"]) == float(base["total_cash_cad"]) + 30.0
    assert float(with_tc["_internal"]["item_delivery_enclosed_trailer_adder_cad"]) == 30.0


@pytest.mark.parametrize("trailer_class", [None, "single_axle_open_aluminum", "double_axle_open_aluminum"])
def test_item_delivery_open_or_missing_trailer_class_remains_unchanged(trailer_class: str | None) -> None:
    """item_delivery keeps open trailer classes and missing trailer_class neutral."""
    base = calculate_quote(
        "item_delivery", 0.0,
        crew_size=1,
        travel_zone="in_town", access_difficulty="normal",
    )
    with_tc = calculate_quote(
        "item_delivery", 0.0,
        crew_size=1,
        travel_zone="in_town", access_difficulty="normal",
        trailer_class=trailer_class,
    )
    assert float(with_tc["total_cash_cad"]) == float(base["total_cash_cad"])
    assert float(with_tc["_internal"]["item_delivery_enclosed_trailer_adder_cad"]) == 0.0


def test_invalid_trailer_class_rejected(client: TestClient) -> None:
    """An unrecognized trailer_class value must be rejected with HTTP 422."""
    payload = _base_payload(service_type="haul_away")
    payload["trailer_class"] = "giant_trailer"
    response = _post_quote(client, payload)
    assert response.status_code == 422


def test_valid_trailer_class_accepted_and_persisted(client: TestClient) -> None:
    """A valid trailer_class is accepted and saved in the request shape."""
    payload = _base_payload(service_type="haul_away")
    payload["garbage_bag_count"] = 5
    payload["trailer_fill_estimate"] = "quarter"
    payload["trailer_class"] = "single_axle_open_aluminum"

    response = _post_quote(client, payload)
    assert response.status_code == 200
    body = response.json()
    assert body["request"]["trailer_class"] == "single_axle_open_aluminum"
    assert isinstance(body.get("accept_token"), str)
    assert body["accept_token"]


# =============================================================================
# Awkward small-load floor tests
# (haul_away, difficult/extreme access, 1–3 light bags only)
# =============================================================================

@pytest.mark.parametrize("bags,access_difficulty,expected_cash", [
    (1, "difficult", 115.0),
    (2, "difficult", 120.0),
    (3, "difficult", 130.0),  # raw $130 already exceeds floor
    (1, "extreme",  145.0),
    (2, "extreme",  155.0),  # raw total is $155 here; $145 floor does not bind
    (3, "extreme",  165.0),  # raw $165 already exceeds floor
])
def test_haul_away_awkward_small_load_floor_exact_values(
    bags: int, access_difficulty: str, expected_cash: float
) -> None:
    """Verify exact totals for tiny awkward haul-away jobs (1h, in_town, light bags)."""
    result = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=bags,
        travel_zone="in_town",
        access_difficulty=access_difficulty,
        has_dense_materials=False,
    )
    assert float(result["total_cash_cad"]) == expected_cash, (
        f"bags={bags}, access={access_difficulty}: "
        f"expected {expected_cash}, got {result['total_cash_cad']}"
    )


def test_haul_away_awkward_small_load_floor_not_applied_for_normal_access() -> None:
    """The awkward small-load floor must NOT change normal-access pricing."""
    for bags in (1, 2, 3):
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=bags,
            travel_zone="in_town",
            access_difficulty="normal",
            has_dense_materials=False,
        )
        assert result["_internal"]["awkward_small_load_floor_cad"] == 0.0
    # Spot-check 1-bag to confirm normal-access tiny-load contract is stable.
    assert float(
        calculate_quote("haul_away", 1.0, crew_size=1, garbage_bag_count=1,
                        travel_zone="in_town", access_difficulty="normal")["total_cash_cad"]
    ) == 80.0


def test_haul_away_mid_band_12_to_15_progression_meaningful_at_fixed_hours() -> None:
    """12-15 light/non-dense difficult-access jobs should not flatten at fixed hours."""
    quote_12 = calculate_quote(
        "haul_away",
        1.5,
        crew_size=1,
        garbage_bag_count=12,
        travel_zone="in_town",
        access_difficulty="difficult",
        has_dense_materials=False,
    )
    quote_15 = calculate_quote(
        "haul_away",
        1.5,
        crew_size=1,
        garbage_bag_count=15,
        travel_zone="in_town",
        access_difficulty="difficult",
        has_dense_materials=False,
    )

    cash_12 = float(quote_12["total_cash_cad"])
    cash_15 = float(quote_15["total_cash_cad"])
    assert cash_15 >= cash_12 + 10.0, (
        f"expected meaningful 12->15 progression (>= +$10) at fixed hours; got 12={cash_12}, 15={cash_15}"
    )


def test_haul_away_awkward_small_load_floor_not_applied_for_4_bags() -> None:
    """The floor only targets small-load-protected jobs (1–3 bags); 4+ bags are excluded."""
    for access in ("difficult", "extreme"):
        result_4 = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=4,
            travel_zone="in_town",
            access_difficulty=access,
            has_dense_materials=False,
        )
        assert result_4["_internal"]["awkward_small_load_floor_cad"] == 0.0


def test_haul_away_awkward_small_load_floor_not_applied_for_dense_materials() -> None:
    """Dense materials bypass small-load protection, so the awkward floor must not apply."""
    for access in ("difficult", "extreme"):
        result = calculate_quote(
            "haul_away",
            1.0,
            crew_size=1,
            garbage_bag_count=1,
            travel_zone="in_town",
            access_difficulty=access,
            has_dense_materials=True,
        )
        assert result["_internal"]["awkward_small_load_floor_cad"] == 0.0


def test_haul_away_awkward_floor_raises_extreme_above_difficult() -> None:
    """Extreme floor must produce a higher total than difficult floor for the same bag count."""
    for bags in (1, 2):
        q_diff = calculate_quote(
            "haul_away", 1.0, crew_size=1, garbage_bag_count=bags,
            travel_zone="in_town", access_difficulty="difficult", has_dense_materials=False,
        )
        q_ext = calculate_quote(
            "haul_away", 1.0, crew_size=1, garbage_bag_count=bags,
            travel_zone="in_town", access_difficulty="extreme", has_dense_materials=False,
        )
        assert float(q_ext["total_cash_cad"]) > float(q_diff["total_cash_cad"]), (
            f"bags={bags}: extreme ({q_ext['total_cash_cad']}) must exceed "
            f"difficult ({q_diff['total_cash_cad']})"
        )
