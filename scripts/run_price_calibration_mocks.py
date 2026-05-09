from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.quote_service import build_quote_artifacts


@dataclass(frozen=True)
class MockCosts:
    labor: float = 0.0
    disposal: float = 0.0
    fuel_wear: float = 0.0
    other: float = 0.0
    scrap_recovery: float = 0.0


@dataclass(frozen=True)
class OperatingCostAssumptions:
    calibration_only: bool
    helper_fully_loaded_hourly_range: tuple[float, float]
    owner_operator_hourly_range: tuple[float, float]
    truck_operating_reserve_per_hour: float
    admin_overhead_pct_of_revenue: float
    contribution_margin_floor_pct: float

    @property
    def helper_fully_loaded_midpoint(self) -> float:
        return round(sum(self.helper_fully_loaded_hourly_range) / 2.0, 2)

    @property
    def owner_operator_midpoint(self) -> float:
        return round(sum(self.owner_operator_hourly_range) / 2.0, 2)


@dataclass(frozen=True)
class CrewRateTarget:
    crew_size: int
    customer_facing_hourly_range: tuple[float, float]
    minimum_billable_hours: float


@dataclass(frozen=True)
class DisposalResearchAnchors:
    calibration_only: bool
    six_bags_or_less: float
    seven_plus_bags_half_ton_or_trailer: float
    residential_double_load_vehicle_plus_trailer: float
    mattress_box_spring_or_foam_top_each: float
    refrigerant_appliance_each: float
    weighed_dual_axle_mode: str
    ici_commercial_mode: str


@dataclass(frozen=True)
class MarketTarget:
    target_cash_floor: float
    target_cash_range: str


@dataclass(frozen=True)
class EquipmentGuidance:
    equipment_type: str
    trailer_type: str
    recommended_trailer: str
    trailer_reason: str
    load_weight_class: str
    disposal_fee_mode: str
    equipment_disposal_risk_note: str


@dataclass(frozen=True)
class CalibrationScenario:
    category: str
    name: str
    payload: dict[str, Any]
    costs: MockCosts
    market_target: MarketTarget | None
    equipment: EquipmentGuidance


@dataclass(frozen=True)
class Profitability:
    total_mock_cost: float
    estimated_gross_profit: float
    estimated_gross_margin_pct: float | None
    risk_flag: str


@dataclass(frozen=True)
class MarketPosition:
    target_cash_floor: float | None
    target_cash_range: str
    gap_to_target_floor: float | None
    market_price_flag: str


@dataclass(frozen=True)
class OperatingCostPosition:
    mock_internal_cost: float
    contribution_margin_pct: float | None
    operating_cost_target_floor: float | None
    operating_cost_target_gap: float | None
    labour_rate_risk: str
    mobilization_risk: str
    disposal_manual_review_risk: str
    moving_underpricing_risk: str
    demolition_premium_risk: str


@dataclass(frozen=True)
class CalibrationResult:
    category: str
    scenario_name: str
    cash_quote: float
    emt_quote: float
    costs: MockCosts
    total_mock_cost: float
    estimated_gross_profit: float
    estimated_gross_margin_pct: float | None
    risk_flag: str
    market_position: MarketPosition
    operating_cost_position: OperatingCostPosition
    equipment: EquipmentGuidance


@dataclass(frozen=True)
class CategorySummary:
    category: str
    scenario_count: int
    average_margin_pct: float | None
    lowest_margin_scenario: str
    highest_margin_scenario: str
    average_profit: float
    recommendation: str
    market_underpriced_count: int
    largest_gap_to_target_floor: float
    largest_gap_scenario: str
    risk_profile: str
    single_axle_count: int
    double_axle_count: int
    older_enclosed_count: int
    newer_enclosed_count: int
    weighed_tonnage_count: int
    mixed_tonnage_count: int
    manual_review_count: int
    under_operating_cost_target_count: int
    below_contribution_margin_count: int
    manual_review_disposal_risk_count: int
    demolition_premium_risk_count: int
    moving_underpricing_count: int


@dataclass(frozen=True)
class OwnerReviewEntry:
    result: CalibrationResult
    triggers: list[str]


QuoteFunc = Callable[[dict[str, Any]], dict[str, Any]]

PROFIT_RISK_FLAGS = {"LOSS", "BAD", "WATCH"}
DISPOSAL_RISK_MODES = {"weighed_tonnage", "mixed_tonnage", "manual_review"}
OPERATING_COST_ASSUMPTIONS = OperatingCostAssumptions(
    calibration_only=True,
    helper_fully_loaded_hourly_range=(21.0, 24.0),
    owner_operator_hourly_range=(25.0, 28.0),
    truck_operating_reserve_per_hour=12.0,
    admin_overhead_pct_of_revenue=12.0,
    contribution_margin_floor_pct=20.0,
)
CREW_RATE_TARGETS = {
    1: CrewRateTarget(crew_size=1, customer_facing_hourly_range=(95.0, 115.0), minimum_billable_hours=1.0),
    2: CrewRateTarget(crew_size=2, customer_facing_hourly_range=(165.0, 195.0), minimum_billable_hours=2.0),
    3: CrewRateTarget(crew_size=3, customer_facing_hourly_range=(220.0, 250.0), minimum_billable_hours=3.0),
}
EXTRA_HELPER_CUSTOMER_FACING_HOURLY_RANGE = (55.0, 70.0)
LOCAL_MOBILIZATION_TARGETS = {
    "one_person": (55.0, 65.0),
    "two_person": (75.0, 95.0),
}
LOW_END_MOVER_EXTERNAL_COMPARATOR_RANGE = (119.0, 129.0)
HARD_MOVE_CUSTOMER_FACING_HOURLY_RANGE = (175.0, 210.0)
DISPOSAL_RESEARCH_ANCHORS = DisposalResearchAnchors(
    calibration_only=True,
    six_bags_or_less=10.0,
    seven_plus_bags_half_ton_or_trailer=25.0,
    residential_double_load_vehicle_plus_trailer=35.0,
    mattress_box_spring_or_foam_top_each=30.0,
    refrigerant_appliance_each=25.0,
    weighed_dual_axle_mode="manual_confirmation_source_conflict",
    ici_commercial_mode="manual_confirmation_source_conflict",
)
TRAILER_REASON_REVIEW_PHRASES = (
    "escalate",
    "manual review",
    "weather",
    "capacity",
    "protected",
    "protection",
)


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "customer_name": "TEST / SIMULATED - Price Calibration",
        "customer_phone": "705-555-0100",
        "job_address": "TEST / SIMULATED - North Bay local calibration",
        "job_description_customer": "TEST / SIMULATED local-only price calibration scenario",
        "description": "TEST / SIMULATED local-only price calibration scenario",
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
        "load_mode": "standard",
    }
    payload.update(overrides)
    return payload


def _market(floor: float, target_range: str) -> MarketTarget:
    return MarketTarget(target_cash_floor=floor, target_cash_range=target_range)


def _equipment(
    *,
    equipment_type: str,
    trailer_type: str,
    recommended_trailer: str,
    trailer_reason: str,
    load_weight_class: str,
    disposal_fee_mode: str,
    equipment_disposal_risk_note: str,
) -> EquipmentGuidance:
    return EquipmentGuidance(
        equipment_type=equipment_type,
        trailer_type=trailer_type,
        recommended_trailer=recommended_trailer,
        trailer_reason=trailer_reason,
        load_weight_class=load_weight_class,
        disposal_fee_mode=disposal_fee_mode,
        equipment_disposal_risk_note=equipment_disposal_risk_note,
    )


SCENARIOS: tuple[CalibrationScenario, ...] = (
    CalibrationScenario(
        category="dump runs",
        name="3 light garbage bags curbside/in-town",
        payload=_payload(
            service_type="dump_run",
            description="Three light garbage bags curbside in town.",
            job_description_customer="Three light garbage bags curbside in town.",
            garbage_bag_count=3,
            bag_type="light",
        ),
        costs=MockCosts(labor=18.0, disposal=18.0, fuel_wear=12.0, other=0.0),
        market_target=_market(95.0, "95-115"),
        equipment=_equipment(
            equipment_type="truck_only",
            trailer_type="none",
            recommended_trailer="none",
            trailer_reason="Truck-only or no trailer needed for tiny curbside bag run.",
            load_weight_class="light",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low disposal/equipment risk.",
        ),
    ),
    CalibrationScenario(
        category="dump runs",
        name="couch or mattress simple pickup",
        payload=_payload(
            service_type="dump_run",
            description="One couch at curbside outside for simple pickup.",
            job_description_customer="One couch at curbside outside for simple pickup.",
            garbage_bag_count=1,
            bag_type="light",
        ),
        costs=MockCosts(labor=25.0, disposal=35.0, fuel_wear=15.0, other=0.0),
        market_target=_market(119.0, "119-149"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="older_enclosed",
            trailer_reason=(
                "Older enclosed is useful for mattresses/box springs or dirty bulky items; "
                "single axle is also acceptable for normal bulky junk."
            ),
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Watch mattress/box spring disposal fees and weather/containment needs.",
        ),
    ),
    CalibrationScenario(
        category="dump runs",
        name="quarter-trailer mixed junk",
        payload=_payload(
            service_type="dump_run",
            description="Quarter trailer mixed household junk.",
            job_description_customer="Quarter trailer mixed household junk.",
            garbage_bag_count=6,
            trailer_fill_estimate="quarter",
            trailer_class="single_axle",
        ),
        costs=MockCosts(labor=48.0, disposal=45.0, fuel_wear=22.0, other=5.0),
        market_target=_market(219.0, "219-279"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Default trailer for light/normal household junk.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low-medium risk unless dense/heavy material is present.",
        ),
    ),
    CalibrationScenario(
        category="dump runs",
        name="half-trailer mixed junk",
        payload=_payload(
            service_type="dump_run",
            description="Half trailer mixed junk with normal access.",
            job_description_customer="Half trailer mixed junk with normal access.",
            estimated_hours=2.0,
            crew_size=2,
            garbage_bag_count=12,
            trailer_fill_estimate="half",
        ),
        costs=MockCosts(labor=72.0, disposal=75.0, fuel_wear=28.0, other=5.0),
        market_target=_market(329.0, "329-399"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Single axle is suitable for normal household junk; escalate if heavy or near capacity.",
            load_weight_class="normal",
            disposal_fee_mode="double_load_flat_fee",
            equipment_disposal_risk_note="Watch capacity and mixed-load fees.",
        ),
    ),
    CalibrationScenario(
        category="dump runs",
        name="three-quarter/full trailer mixed junk",
        payload=_payload(
            service_type="dump_run",
            description="Three-quarter to full trailer mixed household junk.",
            job_description_customer="Three-quarter to full trailer mixed household junk.",
            estimated_hours=3.0,
            crew_size=2,
            garbage_bag_count=22,
            trailer_fill_estimate="full",
        ),
        costs=MockCosts(labor=108.0, disposal=125.0, fuel_wear=35.0, other=10.0),
        market_target=_market(549.0, "549-649"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Full light household volume can use single axle; heavy/full loads may need double axle.",
            load_weight_class="normal",
            disposal_fee_mode="double_load_flat_fee",
            equipment_disposal_risk_note="Volume is high; confirm density before dispatch.",
        ),
    ),
    CalibrationScenario(
        category="dump runs",
        name="heavy construction/demo bags",
        payload=_payload(
            service_type="dump_run",
            description="Heavy construction and demo bags with tile and drywall debris.",
            job_description_customer="Heavy construction and demo bags with tile and drywall debris.",
            estimated_hours=2.0,
            garbage_bag_count=9,
            bag_type="heavy_mixed",
            has_dense_materials=True,
        ),
        costs=MockCosts(labor=80.0, disposal=95.0, fuel_wear=25.0, other=10.0),
        market_target=_market(300.0, "300-450"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Heavy construction/demo material belongs on double axle.",
            load_weight_class="dense",
            disposal_fee_mode="weighed_tonnage",
            equipment_disposal_risk_note="High disposal risk; volume-based pricing may be unsafe.",
        ),
    ),
    CalibrationScenario(
        category="small moves",
        name="single-item local move",
        payload=_payload(
            service_type="small_move",
            description="Single dresser local move between two addresses.",
            job_description_customer="Single dresser local move between two addresses.",
            estimated_hours=1.0,
            crew_size=2,
            pickup_address="11 Pickup Rd",
            dropoff_address="22 Dropoff Ave",
        ),
        costs=MockCosts(labor=96.0, disposal=0.0, fuel_wear=18.0, other=0.0),
        market_target=_market(180.0, "180-300"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Customer-owned item should be protected from weather/damage.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low disposal risk; damage/weather risk matters.",
        ),
    ),
    CalibrationScenario(
        category="small moves",
        name="small apartment move, 2 workers",
        payload=_payload(
            service_type="small_move",
            description="Small apartment move with two workers and normal access.",
            job_description_customer="Small apartment move with two workers and normal access.",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="31 Apartment St",
            dropoff_address="42 Apartment Ave",
        ),
        costs=MockCosts(labor=192.0, disposal=0.0, fuel_wear=24.0, other=10.0),
        market_target=_market(500.0, "500-650"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Moving job with customer belongings needs newer enclosed trailer and scope review.",
            load_weight_class="normal",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Labour/access/scope risk; usually should not be priced like simple delivery.",
        ),
    ),
    CalibrationScenario(
        category="small moves",
        name="3-hour local move",
        payload=_payload(
            service_type="small_move",
            description="Three-hour local move with two workers.",
            job_description_customer="Three-hour local move with two workers.",
            estimated_hours=3.0,
            crew_size=2,
            pickup_address="51 Local Rd",
            dropoff_address="52 Local Rd",
        ),
        costs=MockCosts(labor=144.0, disposal=0.0, fuel_wear=22.0, other=8.0),
        market_target=_market(500.0, "500-600"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Standard moving work should use newer enclosed trailer.",
            load_weight_class="normal",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Labour-hour risk; compare against moving market minimums.",
        ),
    ),
    CalibrationScenario(
        category="small moves",
        name="stairs/access difficulty move",
        payload=_payload(
            service_type="small_move",
            description="Small move with stairs, tight hallway, and long carry.",
            job_description_customer="Small move with stairs, tight hallway, and long carry.",
            estimated_hours=4.0,
            crew_size=2,
            pickup_address="61 Stair Rd",
            dropoff_address="72 Stair Ave",
            access_difficulty="extreme",
        ),
        costs=MockCosts(labor=216.0, disposal=0.0, fuel_wear=28.0, other=12.0),
        market_target=_market(600.0, "600-750"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Difficult access moving job needs protected trailer and manual review.",
            load_weight_class="heavy",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="High labour/access risk.",
        ),
    ),
    CalibrationScenario(
        category="small moves",
        name="short-distance Marketplace move",
        payload=_payload(
            service_type="small_move",
            description="Short-distance Marketplace table move.",
            job_description_customer="Short-distance Marketplace table move.",
            estimated_hours=1.0,
            crew_size=2,
            pickup_address="81 Seller St",
            dropoff_address="82 Buyer Ave",
        ),
        costs=MockCosts(labor=90.0, disposal=0.0, fuel_wear=12.0, other=0.0),
        market_target=_market(180.0, "180-300"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Marketplace furniture usually benefits from newer enclosed trailer, especially in bad weather.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low disposal risk; watch damage/weather/access.",
        ),
    ),
    CalibrationScenario(
        category="demolition",
        name="small carpet/floor rip-out",
        payload=_payload(
            service_type="demolition",
            description="Small carpet and floor rip-out with bagged debris.",
            job_description_customer="Small carpet and floor rip-out with bagged debris.",
            estimated_hours=2.0,
            crew_size=2,
            garbage_bag_count=6,
        ),
        costs=MockCosts(labor=96.0, disposal=35.0, fuel_wear=18.0, other=10.0),
        market_target=_market(300.0, "300-500"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Small rip-out debris may fit single axle but still needs weight awareness.",
            load_weight_class="heavy",
            disposal_fee_mode="weighed_tonnage",
            equipment_disposal_risk_note="Flooring debris can be heavier than it looks.",
        ),
    ),
    CalibrationScenario(
        category="demolition",
        name="light demo debris cleanup",
        payload=_payload(
            service_type="demolition",
            description="Light demo debris cleanup from garage renovation.",
            job_description_customer="Light demo debris cleanup from garage renovation.",
            estimated_hours=2.0,
            crew_size=2,
            garbage_bag_count=8,
        ),
        costs=MockCosts(labor=100.0, disposal=50.0, fuel_wear=20.0, other=5.0),
        market_target=_market(300.0, "300-450"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Light demo debris can use single axle if not too dense.",
            load_weight_class="heavy",
            disposal_fee_mode="weighed_tonnage",
            equipment_disposal_risk_note="Escalate to double axle if dense or large.",
        ),
    ),
    CalibrationScenario(
        category="demolition",
        name="heavy demo debris cleanup",
        payload=_payload(
            service_type="demolition",
            description="Heavy demo debris cleanup with dense tile and drywall.",
            job_description_customer="Heavy demo debris cleanup with dense tile and drywall.",
            estimated_hours=3.0,
            crew_size=2,
            garbage_bag_count=12,
            has_dense_materials=True,
        ),
        costs=MockCosts(labor=150.0, disposal=110.0, fuel_wear=30.0, other=15.0),
        market_target=_market(500.0, "500-800"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Heavy demolition debris belongs on double axle.",
            load_weight_class="dense",
            disposal_fee_mode="weighed_tonnage",
            equipment_disposal_risk_note="High disposal and equipment risk.",
        ),
    ),
    CalibrationScenario(
        category="demolition",
        name="half-day demo labour job",
        payload=_payload(
            service_type="demolition",
            description="Half-day demo labour job with cleanup.",
            job_description_customer="Half-day demo labour job with cleanup.",
            estimated_hours=4.0,
            crew_size=2,
            garbage_bag_count=10,
        ),
        costs=MockCosts(labor=200.0, disposal=65.0, fuel_wear=28.0, other=20.0),
        market_target=_market(550.0, "550-750"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Demo labour with debris needs manual review and likely double axle.",
            load_weight_class="dense",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Labour + disposal risk; should not be auto-priced casually.",
        ),
    ),
    CalibrationScenario(
        category="demolition",
        name="awkward access demo job",
        payload=_payload(
            service_type="demolition",
            description="Awkward access demo job with basement stairs and tight carry.",
            job_description_customer="Awkward access demo job with basement stairs and tight carry.",
            estimated_hours=4.0,
            crew_size=2,
            garbage_bag_count=10,
            access_difficulty="extreme",
        ),
        costs=MockCosts(labor=230.0, disposal=70.0, fuel_wear=30.0, other=20.0),
        market_target=_market(650.0, "650-950"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Awkward/heavy demo is double-axle/manual-review work.",
            load_weight_class="dense",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="High access, labour, and disposal risk.",
        ),
    ),
    CalibrationScenario(
        category="item / appliance / material delivery",
        name="Marketplace couch delivery",
        payload=_payload(
            service_type="item_delivery",
            description="Marketplace couch delivery from seller to buyer.",
            job_description_customer="Marketplace couch delivery from seller to buyer.",
            estimated_hours=1.0,
            crew_size=1,
            pickup_address="101 Seller Lane",
            dropoff_address="202 Buyer Road",
        ),
        costs=MockCosts(labor=35.0, disposal=0.0, fuel_wear=18.0, other=0.0),
        market_target=_market(120.0, "120-180"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Couch delivery should be protected from weather/damage.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low disposal risk; damage/weather risk matters.",
        ),
    ),
    CalibrationScenario(
        category="item / appliance / material delivery",
        name="appliance delivery with 2 workers",
        payload=_payload(
            service_type="item_delivery",
            description="Appliance delivery with two workers and difficult access.",
            job_description_customer="Appliance delivery with two workers and difficult access.",
            estimated_hours=1.5,
            crew_size=2,
            pickup_address="303 Store St",
            dropoff_address="404 Home Ave",
            access_difficulty="difficult",
        ),
        costs=MockCosts(labor=70.0, disposal=0.0, fuel_wear=20.0, other=5.0),
        market_target=_market(160.0, "160-250"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Customer appliance delivery needs protection and 2-worker/access review.",
            load_weight_class="heavy",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Heavy item and access risk.",
        ),
    ),
    CalibrationScenario(
        category="item / appliance / material delivery",
        name="building material delivery",
        payload=_payload(
            service_type="item_delivery",
            description="Building material delivery with open trailer.",
            job_description_customer="Building material delivery with open trailer.",
            estimated_hours=1.5,
            crew_size=1,
            pickup_address="505 Supplier Rd",
            dropoff_address="606 Jobsite Ave",
            trailer_class="open_trailer",
        ),
        costs=MockCosts(labor=45.0, disposal=0.0, fuel_wear=24.0, other=5.0),
        market_target=_market(140.0, "140-220"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Building materials/heavy material delivery should use double axle.",
            load_weight_class="heavy",
            disposal_fee_mode="weighed_tonnage",
            equipment_disposal_risk_note="Weight/capacity risk.",
        ),
    ),
    CalibrationScenario(
        category="item / appliance / material delivery",
        name="short local delivery",
        payload=_payload(
            service_type="item_delivery",
            description="Short local item delivery.",
            job_description_customer="Short local item delivery.",
            estimated_hours=0.5,
            crew_size=1,
            pickup_address="707 Pickup St",
            dropoff_address="808 Dropoff Ave",
        ),
        costs=MockCosts(labor=25.0, disposal=0.0, fuel_wear=10.0, other=0.0),
        market_target=_market(100.0, "100-150"),
        equipment=_equipment(
            equipment_type="truck_only",
            trailer_type="none",
            recommended_trailer="none",
            trailer_reason="Truck-only is fine for small local delivery unless item needs protection.",
            load_weight_class="light",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low risk.",
        ),
    ),
    CalibrationScenario(
        category="item / appliance / material delivery",
        name="longer surrounding-area delivery",
        payload=_payload(
            service_type="item_delivery",
            description="Longer surrounding-area delivery.",
            job_description_customer="Longer surrounding-area delivery.",
            estimated_hours=2.0,
            crew_size=1,
            pickup_address="909 North Bay Rd",
            dropoff_address="1010 Surrounding Area Ave",
            travel_zone="surrounding",
        ),
        costs=MockCosts(labor=55.0, disposal=0.0, fuel_wear=38.0, other=5.0),
        market_target=_market(160.0, "160-250"),
        equipment=_equipment(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Longer delivery needs route/scope review and protected trailer for customer goods.",
            load_weight_class="normal",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Travel and scope risk.",
        ),
    ),
    CalibrationScenario(
        category="scrap pickups",
        name="curbside scrap pickup",
        payload=_payload(
            service_type="scrap_pickup",
            description="Curbside scrap pickup with easy access.",
            job_description_customer="Curbside scrap pickup with easy access.",
            estimated_hours=0.0,
            scrap_pickup_location="curbside",
        ),
        costs=MockCosts(labor=12.0, disposal=0.0, fuel_wear=10.0, other=0.0, scrap_recovery=8.0),
        market_target=_market(0.0, "0-free if pure/easy/route-compatible"),
        equipment=_equipment(
            equipment_type="truck_only",
            trailer_type="none",
            recommended_trailer="none",
            trailer_reason="Easy curbside scrap may not need trailer.",
            load_weight_class="light",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Only free/cheap if pure, easy, and route-compatible.",
        ),
    ),
    CalibrationScenario(
        category="scrap pickups",
        name="inside appliance removal",
        payload=_payload(
            service_type="scrap_pickup",
            description="Inside appliance removal for scrap.",
            job_description_customer="Inside appliance removal for scrap.",
            estimated_hours=0.0,
            scrap_pickup_location="inside",
        ),
        costs=MockCosts(labor=35.0, disposal=0.0, fuel_wear=14.0, other=0.0, scrap_recovery=15.0),
        market_target=_market(60.0, "60-100"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Inside appliance removal is heavy labour; single axle usually enough unless volume/heavy.",
            load_weight_class="heavy",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Labour/access risk; watch refrigerant appliance rules.",
        ),
    ),
    CalibrationScenario(
        category="scrap pickups",
        name="basement scrap removal",
        payload=_payload(
            service_type="scrap_pickup",
            description="Basement scrap removal with stairs.",
            job_description_customer="Basement scrap removal with stairs.",
            estimated_hours=0.0,
            scrap_pickup_location="inside",
            access_difficulty="difficult",
        ),
        costs=MockCosts(labor=50.0, disposal=0.0, fuel_wear=15.0, other=0.0, scrap_recovery=20.0),
        market_target=_market(100.0, "100-175"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Basement scrap requires labour/access review; trailer depends on volume.",
            load_weight_class="heavy",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Access risk.",
        ),
    ),
    CalibrationScenario(
        category="scrap pickups",
        name="mixed scrap plus small garbage",
        payload=_payload(
            service_type="scrap_pickup",
            description="Mixed scrap plus small garbage at curbside.",
            job_description_customer="Mixed scrap plus small garbage at curbside.",
            estimated_hours=0.0,
            scrap_pickup_location="curbside",
        ),
        costs=MockCosts(labor=24.0, disposal=20.0, fuel_wear=12.0, other=0.0, scrap_recovery=12.0),
        market_target=_market(100.0, "100-175"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="single_axle_aluminum",
            recommended_trailer="single_axle_aluminum",
            trailer_reason="Mixed scrap/garbage needs disposal awareness and normal open trailer.",
            load_weight_class="normal",
            disposal_fee_mode="double_load_flat_fee",
            equipment_disposal_risk_note="Mixed load risk; scrap recovery may not offset garbage disposal.",
        ),
    ),
    CalibrationScenario(
        category="scrap pickups",
        name="awkward/heavy scrap removal",
        payload=_payload(
            service_type="scrap_pickup",
            description="Awkward heavy scrap removal from inside.",
            job_description_customer="Awkward heavy scrap removal from inside.",
            estimated_hours=0.0,
            scrap_pickup_location="inside",
            access_difficulty="extreme",
        ),
        costs=MockCosts(labor=70.0, disposal=0.0, fuel_wear=18.0, other=5.0, scrap_recovery=25.0),
        market_target=_market(125.0, "125-200"),
        equipment=_equipment(
            equipment_type="truck_plus_trailer",
            trailer_type="double_axle_aluminum",
            recommended_trailer="double_axle_aluminum",
            trailer_reason="Big/heavy scrap loads belong on double axle.",
            load_weight_class="heavy",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Labour/access/equipment risk.",
        ),
    ),
)


def _calculate_profitability(*, cash_quote: float, costs: MockCosts) -> Profitability:
    total_mock_cost = round(
        costs.labor + costs.disposal + costs.fuel_wear + costs.other - costs.scrap_recovery,
        2,
    )
    estimated_gross_profit = round(cash_quote - total_mock_cost, 2)
    if cash_quote <= 0:
        margin_pct = None
    else:
        margin_pct = round((estimated_gross_profit / cash_quote) * 100.0, 1)

    if estimated_gross_profit < 0:
        risk_flag = "LOSS"
    elif margin_pct is None:
        risk_flag = "NO_REVENUE"
    elif margin_pct >= 40.0:
        risk_flag = "STRONG"
    elif margin_pct >= 30.0:
        risk_flag = "OK"
    elif margin_pct >= 20.0:
        risk_flag = "WATCH"
    else:
        risk_flag = "BAD"

    return Profitability(
        total_mock_cost=total_mock_cost,
        estimated_gross_profit=estimated_gross_profit,
        estimated_gross_margin_pct=margin_pct,
        risk_flag=risk_flag,
    )


def _calculate_market_position(
    *,
    cash_quote: float,
    market_target: MarketTarget | None,
) -> MarketPosition:
    if market_target is None:
        return MarketPosition(
            target_cash_floor=None,
            target_cash_range="N/A",
            gap_to_target_floor=None,
            market_price_flag="N/A",
        )

    gap = round(max(float(market_target.target_cash_floor) - float(cash_quote), 0.0), 2)
    flag = "MARKET_UNDERPRICED" if cash_quote < market_target.target_cash_floor else "TARGET_OK"
    return MarketPosition(
        target_cash_floor=float(market_target.target_cash_floor),
        target_cash_range=market_target.target_cash_range,
        gap_to_target_floor=gap,
        market_price_flag=flag,
    )


def _operating_cost_labour_total(
    payload: dict[str, Any],
    *,
    fallback_mock_labor_cost: float = 0.0,
) -> float:
    hours = max(float(payload.get("estimated_hours") or 0.0), 0.0)
    crew_size = max(int(payload.get("crew_size") or 0), 0)
    if hours <= 0.0 or crew_size <= 0:
        return round(max(float(fallback_mock_labor_cost), 0.0), 2)

    owner_cost = OPERATING_COST_ASSUMPTIONS.owner_operator_midpoint * hours
    helper_count = max(crew_size - 1, 0)
    helper_cost = helper_count * OPERATING_COST_ASSUMPTIONS.helper_fully_loaded_midpoint * hours
    return round(owner_cost + helper_cost, 2)


def _operating_cost_base_cost(
    *,
    labour_total: float,
    truck_reserve: float,
    costs: MockCosts,
) -> float:
    return round(
        max(
            labour_total
            + truck_reserve
            + costs.disposal
            + costs.fuel_wear
            + costs.other
            - costs.scrap_recovery,
            0.0,
        ),
        2,
    )


def _operating_cost_target_floor(base_cost: float) -> float | None:
    overhead_pct = OPERATING_COST_ASSUMPTIONS.admin_overhead_pct_of_revenue / 100.0
    contribution_margin_pct = OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct / 100.0
    denominator = 1.0 - overhead_pct - contribution_margin_pct
    if denominator <= 0.0:
        return None
    return round(base_cost / denominator, 2)


def _crew_rate_target_floor(payload: dict[str, Any]) -> float | None:
    hours = max(float(payload.get("estimated_hours") or 0.0), 0.0)
    crew_size = max(int(payload.get("crew_size") or 0), 0)
    if hours <= 0.0 or crew_size <= 0:
        return None

    base_target = CREW_RATE_TARGETS.get(min(crew_size, 3))
    if base_target is None:
        return None

    target_hours = max(hours, base_target.minimum_billable_hours)
    target_floor = base_target.customer_facing_hourly_range[0] * target_hours
    if crew_size > 3:
        extra_helpers = crew_size - 3
        target_floor += extra_helpers * EXTRA_HELPER_CUSTOMER_FACING_HOURLY_RANGE[0] * target_hours
    return round(target_floor, 2)


def _mobilization_target_floor(payload: dict[str, Any]) -> float | None:
    crew_rate_floor = _crew_rate_target_floor(payload)
    if crew_rate_floor is None:
        return None

    crew_size = max(int(payload.get("crew_size") or 0), 0)
    if crew_size <= 1:
        mobilization_floor = LOCAL_MOBILIZATION_TARGETS["one_person"][0]
    else:
        mobilization_floor = LOCAL_MOBILIZATION_TARGETS["two_person"][0]
    return round(crew_rate_floor + mobilization_floor, 2)


def _is_harder_move(scenario: CalibrationScenario) -> bool:
    payload = scenario.payload
    name = scenario.name.lower()
    access = str(payload.get("access_difficulty") or "").lower()
    return (
        access in {"difficult", "extreme"}
        or "apartment" in name
        or "stairs" in name
        or "surrounding" in name
    )


def _moving_underpricing_risk(*, scenario: CalibrationScenario, cash_quote: float) -> str:
    if scenario.category != "small moves" and scenario.payload.get("service_type") != "small_move":
        return "N/A"

    hours = max(float(scenario.payload.get("estimated_hours") or 0.0), 0.0)
    crew_size = max(int(scenario.payload.get("crew_size") or 0), 0)
    if hours <= 0.0 or crew_size <= 0:
        return "N/A"

    if _is_harder_move(scenario):
        target_floor = HARD_MOVE_CUSTOMER_FACING_HOURLY_RANGE[0] * max(hours, 3.0)
        return "HARD_MOVE_UNDERPRICED" if cash_quote < target_floor else "TARGET_OK"

    if crew_size == 2:
        target_floor = CREW_RATE_TARGETS[2].customer_facing_hourly_range[0] * max(hours, 2.0)
        return "MOVING_UNDERPRICED" if cash_quote < target_floor else "TARGET_OK"

    crew_floor = _crew_rate_target_floor(scenario.payload)
    if crew_floor is None:
        return "N/A"
    return "MOVING_UNDERPRICED" if cash_quote < crew_floor else "TARGET_OK"


def _disposal_manual_review_risk(scenario: CalibrationScenario) -> str:
    description = " ".join(
        str(scenario.payload.get(key) or "")
        for key in ("description", "job_description_customer")
    ).lower()
    if (
        scenario.equipment.disposal_fee_mode in DISPOSAL_RISK_MODES
        or scenario.equipment.load_weight_class in {"heavy", "dense"}
        or bool(scenario.payload.get("has_dense_materials"))
        or "mixed" in description
        or "construction" in description
        or "demo" in description
        or scenario.costs.scrap_recovery > 0.0
    ):
        return "MANUAL_REVIEW"
    return "LOW"


def _demolition_premium_risk(*, scenario: CalibrationScenario, cash_quote: float) -> str:
    if scenario.category != "demolition" and scenario.payload.get("service_type") != "demolition":
        return "N/A"
    if (
        cash_quote < 175.0
        or scenario.equipment.load_weight_class in {"heavy", "dense"}
        or scenario.equipment.disposal_fee_mode in DISPOSAL_RISK_MODES
        or bool(scenario.payload.get("has_dense_materials"))
    ):
        return "DEMO_PREMIUM_RISK"
    return "TARGET_OK"


def _calculate_operating_cost_position(
    *,
    scenario: CalibrationScenario,
    cash_quote: float,
) -> OperatingCostPosition:
    payload = scenario.payload
    hours = max(float(payload.get("estimated_hours") or 0.0), 0.0)
    labour_total = _operating_cost_labour_total(
        payload,
        fallback_mock_labor_cost=scenario.costs.labor,
    )
    truck_reserve = OPERATING_COST_ASSUMPTIONS.truck_operating_reserve_per_hour * hours
    overhead = cash_quote * (OPERATING_COST_ASSUMPTIONS.admin_overhead_pct_of_revenue / 100.0)
    base_cost = _operating_cost_base_cost(
        labour_total=labour_total,
        truck_reserve=truck_reserve,
        costs=scenario.costs,
    )
    mock_internal_cost = round(base_cost + overhead, 2)
    operating_cost_target_floor = _operating_cost_target_floor(base_cost)
    if operating_cost_target_floor is None:
        operating_cost_target_gap = None
    else:
        operating_cost_target_gap = round(max(operating_cost_target_floor - cash_quote, 0.0), 2)

    if cash_quote <= 0.0:
        contribution_margin_pct = None
        labour_rate_risk = "NO_REVENUE"
        mobilization_risk = "NO_REVENUE"
    else:
        contribution_margin_pct = round(((cash_quote - mock_internal_cost) / cash_quote) * 100.0, 1)

        crew_floor = _crew_rate_target_floor(payload)
        if crew_floor is None:
            labour_rate_risk = "N/A"
        elif cash_quote < crew_floor:
            labour_rate_risk = "UNDER_CREW_RATE_TARGET"
        else:
            labour_rate_risk = "TARGET_OK"

        mobilization_floor = _mobilization_target_floor(payload)
        if mobilization_floor is None:
            mobilization_risk = "N/A"
        elif cash_quote < mobilization_floor:
            mobilization_risk = "UNDER_LOCAL_MOBILIZATION_TARGET"
        else:
            mobilization_risk = "TARGET_OK"

    return OperatingCostPosition(
        mock_internal_cost=mock_internal_cost,
        contribution_margin_pct=contribution_margin_pct,
        operating_cost_target_floor=operating_cost_target_floor,
        operating_cost_target_gap=operating_cost_target_gap,
        labour_rate_risk=labour_rate_risk,
        mobilization_risk=mobilization_risk,
        disposal_manual_review_risk=_disposal_manual_review_risk(scenario),
        moving_underpricing_risk=_moving_underpricing_risk(scenario=scenario, cash_quote=cash_quote),
        demolition_premium_risk=_demolition_premium_risk(scenario=scenario, cash_quote=cash_quote),
    )


def _run_scenario(scenario: CalibrationScenario, quote_func: QuoteFunc | None = None) -> CalibrationResult:
    quote_builder = quote_func or build_quote_artifacts
    try:
        artifacts = quote_builder(dict(scenario.payload))
    except Exception as exc:
        raise RuntimeError(
            f"Quote API shape blocked scenario '{scenario.category} / {scenario.name}'. "
            f"Payload: {scenario.payload!r}. Error: {type(exc).__name__}: {exc}"
        ) from exc

    response = artifacts["response"]
    cash_quote = float(response["cash_total_cad"])
    emt_quote = float(response["emt_total_cad"])
    profitability = _calculate_profitability(cash_quote=cash_quote, costs=scenario.costs)
    market_position = _calculate_market_position(
        cash_quote=cash_quote,
        market_target=scenario.market_target,
    )
    operating_cost_position = _calculate_operating_cost_position(
        scenario=scenario,
        cash_quote=cash_quote,
    )
    return CalibrationResult(
        category=scenario.category,
        scenario_name=scenario.name,
        cash_quote=cash_quote,
        emt_quote=emt_quote,
        costs=scenario.costs,
        total_mock_cost=profitability.total_mock_cost,
        estimated_gross_profit=profitability.estimated_gross_profit,
        estimated_gross_margin_pct=profitability.estimated_gross_margin_pct,
        risk_flag=profitability.risk_flag,
        market_position=market_position,
        operating_cost_position=operating_cost_position,
        equipment=scenario.equipment,
    )


def _summary_risk_profile(results: list[CalibrationResult]) -> str:
    labels: list[str] = []
    if any(result.risk_flag in PROFIT_RISK_FLAGS for result in results):
        labels.append("profit")
    if any(
        (result.operating_cost_position.operating_cost_target_gap or 0.0) > 0.0
        or (
            result.operating_cost_position.contribution_margin_pct is not None
            and result.operating_cost_position.contribution_margin_pct
            < OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct
        )
        for result in results
    ):
        labels.append("operating-cost")
    if any(result.market_position.market_price_flag == "MARKET_UNDERPRICED" for result in results):
        labels.append("market")
    if any(
        result.equipment.disposal_fee_mode in DISPOSAL_RISK_MODES
        or result.equipment.load_weight_class in {"heavy", "dense"}
        or result.operating_cost_position.disposal_manual_review_risk == "MANUAL_REVIEW"
        for result in results
    ):
        labels.append("equipment/disposal")
    if any(result.operating_cost_position.moving_underpricing_risk not in {"N/A", "TARGET_OK"} for result in results):
        labels.append("moving")
    if any(result.operating_cost_position.demolition_premium_risk == "DEMO_PREMIUM_RISK" for result in results):
        labels.append("demo-premium")
    if any(
        result.equipment.recommended_trailer == "double_axle_aluminum"
        or (
            result.equipment.recommended_trailer != result.equipment.trailer_type
            and result.equipment.recommended_trailer != "none"
        )
        for result in results
    ):
        labels.append("recommended-trailer")
    return ", ".join(labels) if labels else "none"


def _summarize_category(category: str, results: list[CalibrationResult]) -> CategorySummary:
    numeric_margin_results = [result for result in results if result.estimated_gross_margin_pct is not None]
    if numeric_margin_results:
        average_margin = round(
            sum(float(result.estimated_gross_margin_pct) for result in numeric_margin_results)
            / len(numeric_margin_results),
            1,
        )
        lowest = min(numeric_margin_results, key=lambda result: float(result.estimated_gross_margin_pct))
        highest = max(numeric_margin_results, key=lambda result: float(result.estimated_gross_margin_pct))
        lowest_name = lowest.scenario_name
        highest_name = highest.scenario_name
    else:
        average_margin = None
        lowest_name = "N/A"
        highest_name = "N/A"

    average_profit = round(sum(result.estimated_gross_profit for result in results) / len(results), 2)
    has_loss_or_bad = any(result.risk_flag in {"LOSS", "BAD"} for result in results)
    has_watch = any(result.risk_flag == "WATCH" for result in results)
    if has_loss_or_bad or (average_margin is not None and average_margin < 20.0):
        recommendation = "recalibrate"
    elif has_watch or average_margin is None or average_margin < 30.0:
        recommendation = "watch"
    else:
        recommendation = "keep"

    market_underpriced_count = sum(
        1 for result in results if result.market_position.market_price_flag == "MARKET_UNDERPRICED"
    )
    gap_results = [result for result in results if result.market_position.gap_to_target_floor is not None]
    if gap_results:
        largest_gap_result = max(gap_results, key=lambda result: float(result.market_position.gap_to_target_floor))
        largest_gap = float(largest_gap_result.market_position.gap_to_target_floor or 0.0)
        largest_gap_scenario = largest_gap_result.scenario_name
    else:
        largest_gap = 0.0
        largest_gap_scenario = "N/A"

    return CategorySummary(
        category=category,
        scenario_count=len(results),
        average_margin_pct=average_margin,
        lowest_margin_scenario=lowest_name,
        highest_margin_scenario=highest_name,
        average_profit=average_profit,
        recommendation=recommendation,
        market_underpriced_count=market_underpriced_count,
        largest_gap_to_target_floor=largest_gap,
        largest_gap_scenario=largest_gap_scenario,
        risk_profile=_summary_risk_profile(results),
        single_axle_count=sum(
            1 for result in results if result.equipment.recommended_trailer == "single_axle_aluminum"
        ),
        double_axle_count=sum(
            1 for result in results if result.equipment.recommended_trailer == "double_axle_aluminum"
        ),
        older_enclosed_count=sum(
            1 for result in results if result.equipment.recommended_trailer == "older_enclosed"
        ),
        newer_enclosed_count=sum(
            1 for result in results if result.equipment.recommended_trailer == "newer_enclosed"
        ),
        weighed_tonnage_count=sum(1 for result in results if result.equipment.disposal_fee_mode == "weighed_tonnage"),
        mixed_tonnage_count=sum(1 for result in results if result.equipment.disposal_fee_mode == "mixed_tonnage"),
        manual_review_count=sum(1 for result in results if result.equipment.disposal_fee_mode == "manual_review"),
        under_operating_cost_target_count=sum(
            1 for result in results if (result.operating_cost_position.operating_cost_target_gap or 0.0) > 0.0
        ),
        below_contribution_margin_count=sum(
            1
            for result in results
            if result.operating_cost_position.contribution_margin_pct is not None
            and result.operating_cost_position.contribution_margin_pct
            < OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct
        ),
        manual_review_disposal_risk_count=sum(
            1 for result in results if result.operating_cost_position.disposal_manual_review_risk == "MANUAL_REVIEW"
        ),
        demolition_premium_risk_count=sum(
            1 for result in results if result.operating_cost_position.demolition_premium_risk == "DEMO_PREMIUM_RISK"
        ),
        moving_underpricing_count=sum(
            1
            for result in results
            if result.operating_cost_position.moving_underpricing_risk not in {"N/A", "TARGET_OK"}
        ),
    )


def _owner_review_entries(results: list[CalibrationResult]) -> list[OwnerReviewEntry]:
    entries: list[OwnerReviewEntry] = []
    for result in results:
        triggers: list[str] = []
        if result.risk_flag in PROFIT_RISK_FLAGS:
            triggers.append(result.risk_flag)
        if result.market_position.market_price_flag == "MARKET_UNDERPRICED":
            triggers.append("MARKET_UNDERPRICED")
        if (result.operating_cost_position.operating_cost_target_gap or 0.0) > 0.0:
            triggers.append("UNDER_OPERATING_COST_TARGET")
        if (
            result.operating_cost_position.contribution_margin_pct is not None
            and result.operating_cost_position.contribution_margin_pct
            < OPERATING_COST_ASSUMPTIONS.contribution_margin_floor_pct
        ):
            triggers.append("BELOW_CONTRIBUTION_MARGIN")
        if result.equipment.recommended_trailer == "double_axle_aluminum":
            triggers.append("double_axle_aluminum")
        if result.equipment.disposal_fee_mode in DISPOSAL_RISK_MODES:
            triggers.append(result.equipment.disposal_fee_mode)
        if result.operating_cost_position.disposal_manual_review_risk == "MANUAL_REVIEW":
            triggers.append("DISPOSAL_MANUAL_REVIEW")
        if result.operating_cost_position.moving_underpricing_risk not in {"N/A", "TARGET_OK"}:
            triggers.append(result.operating_cost_position.moving_underpricing_risk)
        if result.operating_cost_position.demolition_premium_risk == "DEMO_PREMIUM_RISK":
            triggers.append("DEMO_PREMIUM_RISK")
        if result.equipment.load_weight_class == "dense":
            triggers.append("dense")
        reason = result.equipment.trailer_reason.lower()
        if any(phrase in reason for phrase in TRAILER_REASON_REVIEW_PHRASES):
            triggers.append("trailer_reason")
        if triggers:
            entries.append(OwnerReviewEntry(result=result, triggers=triggers))
    return entries


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _money_or_na(value: float | None) -> str:
    if value is None:
        return "N/A"
    return _money(value)


def _margin(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _print_table(results: list[CalibrationResult]) -> None:
    headers = [
        "category",
        "scenario",
        "cash",
        "emt",
        "labor",
        "disposal",
        "fuel/wear",
        "other",
        "scrap",
        "cost",
        "profit",
        "margin",
        "risk",
        "mock internal cost",
        "contribution margin",
        "op cost target floor",
        "op cost gap",
        "labour risk",
        "mobilization risk",
        "disposal risk",
        "moving risk",
        "demo premium risk",
        "target cash floor",
        "target cash range",
        "gap to target floor",
        "market flag",
        "equipment type",
        "trailer type",
        "rec trailer",
        "load weight",
        "disposal mode",
    ]
    rows = [
        [
            result.category,
            result.scenario_name,
            _money(result.cash_quote),
            _money(result.emt_quote),
            _money(result.costs.labor),
            _money(result.costs.disposal),
            _money(result.costs.fuel_wear),
            _money(result.costs.other),
            _money(result.costs.scrap_recovery),
            _money(result.total_mock_cost),
            _money(result.estimated_gross_profit),
            _margin(result.estimated_gross_margin_pct),
            result.risk_flag,
            _money(result.operating_cost_position.mock_internal_cost),
            _margin(result.operating_cost_position.contribution_margin_pct),
            _money_or_na(result.operating_cost_position.operating_cost_target_floor),
            _money_or_na(result.operating_cost_position.operating_cost_target_gap),
            result.operating_cost_position.labour_rate_risk,
            result.operating_cost_position.mobilization_risk,
            result.operating_cost_position.disposal_manual_review_risk,
            result.operating_cost_position.moving_underpricing_risk,
            result.operating_cost_position.demolition_premium_risk,
            _money_or_na(result.market_position.target_cash_floor),
            result.market_position.target_cash_range,
            _money_or_na(result.market_position.gap_to_target_floor),
            result.market_position.market_price_flag,
            result.equipment.equipment_type,
            result.equipment.trailer_type,
            result.equipment.recommended_trailer,
            result.equipment.load_weight_class,
            result.equipment.disposal_fee_mode,
        ]
        for result in results
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]

    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def _print_summaries(results: list[CalibrationResult]) -> list[CategorySummary]:
    summaries: list[CategorySummary] = []
    print()
    print("Category summaries")
    print("------------------")
    for category in dict.fromkeys(result.category for result in results):
        category_results = [result for result in results if result.category == category]
        summary = _summarize_category(category, category_results)
        summaries.append(summary)
        print(
            f"{summary.category}: scenarios={summary.scenario_count}, "
            f"average margin={_margin(summary.average_margin_pct)}, "
            f"lowest margin scenario={summary.lowest_margin_scenario}, "
            f"highest margin scenario={summary.highest_margin_scenario}, "
            f"average profit={_money(summary.average_profit)}, "
            f"recommendation={summary.recommendation}, "
            f"market underpriced={summary.market_underpriced_count}, "
            f"under operating-cost target={summary.under_operating_cost_target_count}, "
            f"below contribution margin={summary.below_contribution_margin_count}, "
            f"manual-review disposal risk={summary.manual_review_disposal_risk_count}, "
            f"demo premium risk={summary.demolition_premium_risk_count}, "
            f"moving underpricing risk={summary.moving_underpricing_count}, "
            f"largest target gap={_money(summary.largest_gap_to_target_floor)} "
            f"({summary.largest_gap_scenario}), "
            f"risks={summary.risk_profile}, "
            "rec trailers="
            f"single:{summary.single_axle_count}/"
            f"double:{summary.double_axle_count}/"
            f"older:{summary.older_enclosed_count}/"
            f"newer:{summary.newer_enclosed_count}, "
            "disposal modes="
            f"weighed:{summary.weighed_tonnage_count}/"
            f"mixed:{summary.mixed_tonnage_count}/"
            f"manual:{summary.manual_review_count}"
        )
    return summaries


def _print_owner_review(results: list[CalibrationResult]) -> None:
    entries = _owner_review_entries(results)
    print()
    print("Owner review scenarios")
    print("----------------------")
    if not entries:
        print("No scenarios require owner review.")
        return

    headers = [
        "scenario",
        "triggers",
        "target gap",
        "op cost gap",
        "contribution margin",
        "rec trailer",
        "trailer reason",
        "equipment/disposal risk note",
    ]
    rows = [
        [
            entry.result.scenario_name,
            ", ".join(entry.triggers),
            _money_or_na(entry.result.market_position.gap_to_target_floor),
            _money_or_na(entry.result.operating_cost_position.operating_cost_target_gap),
            _margin(entry.result.operating_cost_position.contribution_margin_pct),
            entry.result.equipment.recommended_trailer,
            entry.result.equipment.trailer_reason,
            entry.result.equipment.equipment_disposal_risk_note,
        ]
        for entry in entries
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]

    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def main() -> int:
    print("Bay Delivery Price Calibration Mock Harness")
    print("Local-only TEST / SIMULATED analysis. Quote totals come from build_quote_artifacts().")
    print("Mock costs, market targets, trailer guidance, and scrap recovery are analysis-only.")
    print("Operating-cost assumptions are calibration-only and do not change production pricing.")
    print(
        "Lower $119-$129/hr mover rates are external comparators only; Bay targets use "
        "$165-$195/hr for normal 2-person truck work."
    )
    print(
        "Weighed dual-axle and ICI/commercial disposal rates are manual-confirmation "
        "source-conflict areas before automation."
    )
    print("Margin note: cash quote <= 0 displays as N/A and is never divided by.")
    print()

    results = [_run_scenario(scenario) for scenario in SCENARIOS]
    _print_table(results)
    _print_summaries(results)
    _print_owner_review(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
