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
class CalibrationScenario:
    category: str
    name: str
    payload: dict[str, Any]
    costs: MockCosts


@dataclass(frozen=True)
class Profitability:
    total_mock_cost: float
    estimated_gross_profit: float
    estimated_gross_margin_pct: float | None
    risk_flag: str


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


@dataclass(frozen=True)
class CategorySummary:
    category: str
    scenario_count: int
    average_margin_pct: float | None
    lowest_margin_scenario: str
    highest_margin_scenario: str
    average_profit: float
    recommendation: str


QuoteFunc = Callable[[dict[str, Any]], dict[str, Any]]


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
    )


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

    return CategorySummary(
        category=category,
        scenario_count=len(results),
        average_margin_pct=average_margin,
        lowest_margin_scenario=lowest_name,
        highest_margin_scenario=highest_name,
        average_profit=average_profit,
        recommendation=recommendation,
    )


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _margin(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _print_table(results: list[CalibrationResult]) -> None:
    headers = [
        "category",
        "scenario name",
        "customer cash quote",
        "customer EMT/e-transfer quote",
        "mock labor cost",
        "mock disposal cost",
        "mock fuel/wear cost",
        "mock other cost",
        "mock scrap recovery",
        "total mock cost",
        "estimated gross profit",
        "estimated gross margin %",
        "risk flag",
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
            f"recommendation={summary.recommendation}"
        )
    return summaries


def main() -> int:
    print("Bay Delivery Price Calibration Mock Harness")
    print("Local-only TEST / SIMULATED analysis. Quote totals come from build_quote_artifacts().")
    print("Mock costs and scrap recovery are analysis-only and do not feed pricing.")
    print("Margin note: cash quote <= 0 displays as N/A and is never divided by.")
    print()

    results = [_run_scenario(scenario) for scenario in SCENARIOS]
    _print_table(results)
    _print_summaries(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
