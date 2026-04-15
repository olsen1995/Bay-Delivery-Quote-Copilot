from __future__ import annotations

from typing import Any, TypedDict


class QuoteStressScenario(TypedDict, total=False):
    id: str
    category: str
    payload: dict[str, Any]
    expected_status: int
    expected_service_type: str
    expected_error_detail_substrings: list[str]
    expected_error_loc: list[str]
    requires_pickup_dropoff: bool
    check_minimum_floor: bool
    check_shape: bool


class QuoteStressComparison(TypedDict):
    id: str
    lower_quote_scenario_id: str
    higher_quote_scenario_id: str
    reason: str


def _payload(*, remove: tuple[str, ...] = (), **overrides: Any) -> dict[str, Any]:
    payload = {
        "customer_name": "Stress Harness",
        "customer_phone": "705-555-0199",
        "job_address": "123 Stress Ave",
        "description": "Fixture-driven quote scenario",
        "service_type": "haul_away",
        "payment_method": "cash",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "garbage_bag_count": 0,
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": "in_town",
        "access_difficulty": "normal",
        "has_dense_materials": False,
    }
    payload.update(overrides)
    for key in remove:
        payload.pop(key, None)
    return payload


NORMAL_SCENARIOS: list[QuoteStressScenario] = [
    {
        "id": "normal_small_curbside_haul_away",
        "category": "normal",
        "payload": _payload(
            description="Two light curbside bags for haul-away",
            garbage_bag_count=2,
            bag_type="light",
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "normal_couch_disposal",
        "category": "normal",
        "payload": _payload(
            description="One couch at curbside for disposal",
            estimated_hours=1.5,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "normal_small_move_valid_route",
        "category": "normal",
        "payload": _payload(
            description="Small apartment move with valid pickup and dropoff",
            service_type="moving",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="45 Pickup Rd",
            dropoff_address="67 Dropoff Ave",
        ),
        "expected_status": 200,
        "expected_service_type": "small_move",
        "requires_pickup_dropoff": True,
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "normal_item_delivery_valid_route",
        "category": "normal",
        "payload": _payload(
            description="Single couch delivery with valid pickup and dropoff",
            service_type="delivery",
            estimated_hours=0.0,
            pickup_address="11 Warehouse Way",
            dropoff_address="22 Customer Crescent",
        ),
        "expected_status": 200,
        "expected_service_type": "item_delivery",
        "requires_pickup_dropoff": True,
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "normal_scrap_curbside",
        "category": "normal",
        "payload": _payload(
            description="Loose scrap metal at curbside",
            service_type="scrap_pickup",
            estimated_hours=0.0,
        ),
        "expected_status": 200,
        "expected_service_type": "scrap_pickup",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "normal_light_demolition_cleanup",
        "category": "normal",
        "payload": _payload(
            description="Light shed demolition cleanup",
            service_type="demolition",
            estimated_hours=2.0,
            crew_size=2,
        ),
        "expected_status": 200,
        "expected_service_type": "demolition",
        "check_shape": True,
        "check_minimum_floor": True,
    },
]


EDGE_MARGIN_RISK_SCENARIOS: list[QuoteStressScenario] = [
    {
        "id": "edge_low_volume_in_town_baseline",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Single light item haul-away in town",
            garbage_bag_count=1,
            bag_type="light",
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_low_volume_out_of_town",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Single light item haul-away out of town",
            garbage_bag_count=1,
            bag_type="light",
            travel_zone="out_of_town",
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_light_debris_baseline",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Mixed light renovation debris",
            garbage_bag_count=8,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_dense_heavy_debris",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Dense concrete and tile debris",
            garbage_bag_count=8,
            has_dense_materials=True,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_normal_access_move_baseline",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Main-floor small move with short carry",
            service_type="small_move",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="90 Main Floor Rd",
            dropoff_address="91 Main Floor Rd",
            access_difficulty="normal",
        ),
        "expected_status": 200,
        "expected_service_type": "small_move",
        "requires_pickup_dropoff": True,
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_stairs_long_carry_move",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Third-floor move with stairs and long carry",
            service_type="small_move",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="90 Stairwell Rd",
            dropoff_address="91 Stairwell Rd",
            access_difficulty="extreme",
        ),
        "expected_status": 200,
        "expected_service_type": "small_move",
        "requires_pickup_dropoff": True,
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_mattress_box_spring_mix",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Mattress and box spring haul-away",
            mattresses_count=1,
            box_springs_count=1,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_mixed_bulky_items",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Couch, loveseat, table, and four chairs",
            estimated_hours=2.0,
            crew_size=2,
            garbage_bag_count=4,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
    {
        "id": "edge_ambiguous_notes_valid_structure",
        "category": "edge_margin_risk",
        "payload": _payload(
            description="Maybe couch, maybe some bags, maybe garage stuff; final details on arrival",
            garbage_bag_count=3,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
]


BAD_INPUT_SCENARIOS: list[QuoteStressScenario] = [
    {
        "id": "bad_input_missing_customer_name",
        "category": "bad_input",
        "payload": _payload(remove=("customer_name",)),
        "expected_status": 422,
        "expected_error_loc": ["body", "customer_name"],
    },
    {
        "id": "bad_input_missing_job_address",
        "category": "bad_input",
        "payload": _payload(remove=("job_address",)),
        "expected_status": 422,
        "expected_error_loc": ["body", "job_address"],
    },
    {
        "id": "bad_input_move_missing_dropoff",
        "category": "bad_input",
        "payload": _payload(
            description="Small move missing dropoff",
            service_type="moving",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="10 Pickup Rd",
        ),
        "expected_status": 400,
        "expected_error_detail_substrings": ["pickup_address", "dropoff_address", "required"],
    },
    {
        "id": "bad_input_delivery_missing_pickup",
        "category": "bad_input",
        "payload": _payload(
            description="Delivery missing pickup",
            service_type="delivery",
            estimated_hours=0.0,
            dropoff_address="20 Delivery Lane",
        ),
        "expected_status": 400,
        "expected_error_detail_substrings": ["pickup_address", "dropoff_address", "required"],
    },
    {
        "id": "bad_input_negative_garbage_bag_count",
        "category": "bad_input",
        "payload": _payload(
            description="Negative bag count should fail validation",
            garbage_bag_count=-1,
        ),
        "expected_status": 422,
        "expected_error_loc": ["body", "garbage_bag_count"],
    },
    {
        "id": "bad_input_odd_text_but_valid_description",
        "category": "bad_input",
        "payload": _payload(
            description="Odd chars <> {} [] ### $$$ newline\nsecond line still valid",
            garbage_bag_count=3,
        ),
        "expected_status": 200,
        "expected_service_type": "haul_away",
        "check_shape": True,
        "check_minimum_floor": True,
    },
]


ALL_QUOTE_STRESS_SCENARIOS = (
    NORMAL_SCENARIOS + EDGE_MARGIN_RISK_SCENARIOS + BAD_INPUT_SCENARIOS
)

SCENARIO_BY_ID = {
    scenario["id"]: scenario
    for scenario in ALL_QUOTE_STRESS_SCENARIOS
}

EDGE_MARGIN_RISK_COMPARISONS: list[QuoteStressComparison] = [
    {
        "id": "edge_out_of_town_not_below_in_town",
        "lower_quote_scenario_id": "edge_low_volume_in_town_baseline",
        "higher_quote_scenario_id": "edge_low_volume_out_of_town",
        "reason": "Out-of-town low-volume haul-away should not underquote the equivalent in-town case.",
    },
    {
        "id": "edge_dense_not_below_light",
        "lower_quote_scenario_id": "edge_light_debris_baseline",
        "higher_quote_scenario_id": "edge_dense_heavy_debris",
        "reason": "Dense debris should not underquote the equivalent light-debris case.",
    },
    {
        "id": "edge_harder_access_move_not_below_normal_access",
        "lower_quote_scenario_id": "edge_normal_access_move_baseline",
        "higher_quote_scenario_id": "edge_stairs_long_carry_move",
        "reason": "A harder-access small move should not underquote the equivalent normal-access move.",
    },
]
