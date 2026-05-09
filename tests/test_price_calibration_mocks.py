from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_price_calibration_mocks as calibration


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_SCENARIOS = {
    "dump runs": {
        "3 light garbage bags curbside/in-town",
        "couch or mattress simple pickup",
        "quarter-trailer mixed junk",
        "half-trailer mixed junk",
        "three-quarter/full trailer mixed junk",
        "heavy construction/demo bags",
    },
    "small moves": {
        "single-item local move",
        "small apartment move, 2 workers",
        "3-hour local move",
        "stairs/access difficulty move",
        "short-distance Marketplace move",
    },
    "demolition": {
        "small carpet/floor rip-out",
        "light demo debris cleanup",
        "heavy demo debris cleanup",
        "half-day demo labour job",
        "awkward access demo job",
    },
    "item / appliance / material delivery": {
        "Marketplace couch delivery",
        "appliance delivery with 2 workers",
        "building material delivery",
        "short local delivery",
        "longer surrounding-area delivery",
    },
    "scrap pickups": {
        "curbside scrap pickup",
        "inside appliance removal",
        "basement scrap removal",
        "mixed scrap plus small garbage",
        "awkward/heavy scrap removal",
    },
}

EXPECTED_TARGETS = {
    "3 light garbage bags curbside/in-town": (95.0, "95-115"),
    "couch or mattress simple pickup": (119.0, "119-149"),
    "quarter-trailer mixed junk": (219.0, "219-279"),
    "half-trailer mixed junk": (329.0, "329-399"),
    "three-quarter/full trailer mixed junk": (549.0, "549-649"),
    "heavy construction/demo bags": (300.0, "300-450"),
    "small apartment move, 2 workers": (500.0, "500-650"),
    "3-hour local move": (500.0, "500-600"),
    "awkward access demo job": (650.0, "650-950"),
    "curbside scrap pickup": (0.0, "0-free if pure/easy/route-compatible"),
}


def test_operating_cost_assumptions_are_research_backed_and_calibration_only() -> None:
    assumptions = calibration.OPERATING_COST_ASSUMPTIONS

    assert assumptions.calibration_only is True
    assert assumptions.helper_fully_loaded_hourly_range == (21.0, 24.0)
    assert assumptions.owner_operator_hourly_range == (25.0, 28.0)
    assert assumptions.truck_operating_reserve_per_hour == 12.0
    assert assumptions.admin_overhead_pct_of_revenue == 12.0
    assert assumptions.contribution_margin_floor_pct == 20.0

    assert calibration.CREW_RATE_TARGETS[1].customer_facing_hourly_range == (95.0, 115.0)
    assert calibration.CREW_RATE_TARGETS[2].customer_facing_hourly_range == (165.0, 195.0)
    assert calibration.CREW_RATE_TARGETS[3].customer_facing_hourly_range == (220.0, 250.0)
    assert calibration.EXTRA_HELPER_CUSTOMER_FACING_HOURLY_RANGE == (55.0, 70.0)
    assert calibration.LOCAL_MOBILIZATION_TARGETS["one_person"] == (55.0, 65.0)
    assert calibration.LOCAL_MOBILIZATION_TARGETS["two_person"] == (75.0, 95.0)


def test_old_helper_anchor_is_not_used_for_operating_cost_labour_model() -> None:
    assert calibration.OPERATING_COST_ASSUMPTIONS.helper_fully_loaded_midpoint != 16.0
    assert calibration.OPERATING_COST_ASSUMPTIONS.helper_fully_loaded_midpoint == 22.5
    assert calibration.OPERATING_COST_ASSUMPTIONS.owner_operator_midpoint == 26.5


def test_disposal_research_anchors_are_analysis_only_and_source_conflicts_manual() -> None:
    anchors = calibration.DISPOSAL_RESEARCH_ANCHORS

    assert anchors.six_bags_or_less == 10.0
    assert anchors.seven_plus_bags_half_ton_or_trailer == 25.0
    assert anchors.residential_double_load_vehicle_plus_trailer == 35.0
    assert anchors.mattress_box_spring_or_foam_top_each == 30.0
    assert anchors.refrigerant_appliance_each == 25.0
    assert anchors.weighed_dual_axle_mode == "manual_confirmation_source_conflict"
    assert anchors.ici_commercial_mode == "manual_confirmation_source_conflict"
    assert anchors.calibration_only is True


def test_required_categories_and_scenarios_are_represented() -> None:
    scenarios_by_category: dict[str, set[str]] = {}
    for scenario in calibration.SCENARIOS:
        scenarios_by_category.setdefault(scenario.category, set()).add(scenario.name)

    assert set(REQUIRED_SCENARIOS).issubset(scenarios_by_category)
    for category, required_names in REQUIRED_SCENARIOS.items():
        assert required_names.issubset(scenarios_by_category[category])


def test_required_market_target_bands_are_represented() -> None:
    scenarios_by_name = {scenario.name: scenario for scenario in calibration.SCENARIOS}

    for scenario_name, (expected_floor, expected_range) in EXPECTED_TARGETS.items():
        scenario = scenarios_by_name[scenario_name]
        assert scenario.market_target is not None
        assert scenario.market_target.target_cash_floor == expected_floor
        assert scenario.market_target.target_cash_range == expected_range


@pytest.mark.parametrize(
    ("cash_quote", "target", "expected_gap", "expected_flag"),
    [
        (100.0, calibration.MarketTarget(120.0, "120-180"), 20.0, "MARKET_UNDERPRICED"),
        (120.0, calibration.MarketTarget(120.0, "120-180"), 0.0, "TARGET_OK"),
        (140.0, calibration.MarketTarget(120.0, "120-180"), 0.0, "TARGET_OK"),
        (140.0, None, None, "N/A"),
    ],
)
def test_market_position_classifies_flags_and_gap(
    cash_quote: float,
    target: object,
    expected_gap: float | None,
    expected_flag: str,
) -> None:
    result = calibration._calculate_market_position(
        cash_quote=cash_quote,
        market_target=target,
    )

    assert result.gap_to_target_floor == expected_gap
    assert result.market_price_flag == expected_flag


def test_margin_math_handles_scrap_recovery_and_zero_revenue() -> None:
    costs = calibration.MockCosts(
        labor=20.0,
        disposal=5.0,
        fuel_wear=10.0,
        other=5.0,
        scrap_recovery=40.0,
    )

    result = calibration._calculate_profitability(cash_quote=0.0, costs=costs)

    assert result.total_mock_cost == 0.0
    assert result.estimated_gross_profit == 0.0
    assert result.estimated_gross_margin_pct is None
    assert result.risk_flag == "NO_REVENUE"


@pytest.mark.parametrize(
    ("cash_quote", "total_cost", "expected_flag"),
    [
        (100.0, 110.0, "LOSS"),
        (100.0, 85.0, "BAD"),
        (100.0, 75.0, "WATCH"),
        (100.0, 65.0, "OK"),
        (100.0, 60.0, "STRONG"),
        (0.0, 5.0, "LOSS"),
        (0.0, 0.0, "NO_REVENUE"),
    ],
)
def test_risk_flags_classify_thresholds(cash_quote: float, total_cost: float, expected_flag: str) -> None:
    result = calibration._calculate_profitability(
        cash_quote=cash_quote,
        costs=calibration.MockCosts(labor=total_cost),
    )

    assert result.risk_flag == expected_flag


def test_category_summary_skips_na_margins() -> None:
    results = [
        calibration.CalibrationResult(
            category="scrap pickups",
            scenario_name="curbside scrap pickup",
            cash_quote=0.0,
            emt_quote=0.0,
            costs=calibration.MockCosts(),
            total_mock_cost=0.0,
            estimated_gross_profit=0.0,
            estimated_gross_margin_pct=None,
            risk_flag="NO_REVENUE",
            market_position=calibration.MarketPosition(None, "N/A", None, "N/A"),
            operating_cost_position=calibration.OperatingCostPosition(
                mock_internal_cost=0.0,
                contribution_margin_pct=None,
                operating_cost_target_floor=None,
                operating_cost_target_gap=None,
                labour_rate_risk="NO_REVENUE",
                mobilization_risk="N/A",
                disposal_manual_review_risk="LOW",
                moving_underpricing_risk="N/A",
                demolition_premium_risk="N/A",
            ),
            equipment=calibration.EquipmentGuidance(
                equipment_type="truck_only",
                trailer_type="none",
                recommended_trailer="none",
                trailer_reason="Truck-only easy curbside scrap pickup.",
                load_weight_class="light",
                disposal_fee_mode="small_flat_fee",
                equipment_disposal_risk_note="Low risk.",
            ),
        ),
        calibration.CalibrationResult(
            category="scrap pickups",
            scenario_name="inside appliance removal",
            cash_quote=100.0,
            emt_quote=113.0,
            costs=calibration.MockCosts(labor=60.0),
            total_mock_cost=60.0,
            estimated_gross_profit=40.0,
            estimated_gross_margin_pct=40.0,
            risk_flag="STRONG",
            market_position=calibration.MarketPosition(60.0, "60-100", 0.0, "TARGET_OK"),
            operating_cost_position=calibration.OperatingCostPosition(
                mock_internal_cost=60.0,
                contribution_margin_pct=40.0,
                operating_cost_target_floor=75.0,
                operating_cost_target_gap=0.0,
                labour_rate_risk="TARGET_OK",
                mobilization_risk="TARGET_OK",
                disposal_manual_review_risk="LOW",
                moving_underpricing_risk="N/A",
                demolition_premium_risk="N/A",
            ),
            equipment=calibration.EquipmentGuidance(
                equipment_type="truck_plus_trailer",
                trailer_type="single_axle_aluminum",
                recommended_trailer="single_axle_aluminum",
                trailer_reason="Single axle usually enough unless volume/heavy.",
                load_weight_class="heavy",
                disposal_fee_mode="small_flat_fee",
                equipment_disposal_risk_note="Labour/access risk.",
            ),
        ),
    ]

    summary = calibration._summarize_category("scrap pickups", results)

    assert summary.average_margin_pct == 40.0
    assert summary.lowest_margin_scenario == "inside appliance removal"
    assert summary.highest_margin_scenario == "inside appliance removal"
    assert summary.market_underpriced_count == 0
    assert summary.manual_review_count == 0
    assert summary.under_operating_cost_target_count == 0
    assert summary.below_contribution_margin_count == 0


def test_trailer_and_disposal_guidance_represent_required_values() -> None:
    recommended_trailers = {scenario.equipment.recommended_trailer for scenario in calibration.SCENARIOS}
    disposal_modes = {scenario.equipment.disposal_fee_mode for scenario in calibration.SCENARIOS}

    assert {
        "single_axle_aluminum",
        "double_axle_aluminum",
        "older_enclosed",
        "newer_enclosed",
    }.issubset(recommended_trailers)
    assert "double_axle_aluminum" in recommended_trailers
    assert "weighed_tonnage" in disposal_modes
    assert "manual_review" in disposal_modes


def test_owner_review_summary_includes_market_and_equipment_risk_scenarios() -> None:
    results = [
        calibration._run_scenario(scenario)
        for scenario in calibration.SCENARIOS
    ]

    owner_review = calibration._owner_review_entries(results)
    scenarios = {entry.result.scenario_name: entry for entry in owner_review}

    assert "small apartment move, 2 workers" in scenarios
    assert "heavy construction/demo bags" in scenarios
    assert "awkward access demo job" in scenarios
    assert "couch or mattress simple pickup" in scenarios
    assert "MARKET_UNDERPRICED" in scenarios["small apartment move, 2 workers"].triggers
    assert "double_axle_aluminum" in scenarios["heavy construction/demo bags"].triggers
    assert "manual_review" in scenarios["awkward access demo job"].triggers
    assert scenarios["couch or mattress simple pickup"].result.equipment.recommended_trailer == "older_enclosed"


def test_operating_cost_position_flags_margin_and_target_gap() -> None:
    scenario = calibration.CalibrationScenario(
        category="small moves",
        name="low two-person move",
        payload=calibration._payload(
            service_type="small_move",
            estimated_hours=2.0,
            crew_size=2,
            access_difficulty="normal",
        ),
        costs=calibration.MockCosts(disposal=0.0, fuel_wear=0.0, other=0.0),
        market_target=calibration.MarketTarget(330.0, "165-195/hr"),
        equipment=calibration.EquipmentGuidance(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Moving job should use protected trailer.",
            load_weight_class="normal",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="Moving scope risk.",
        ),
    )

    result = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )

    assert result.operating_cost_position.mock_internal_cost == 134.0
    assert result.operating_cost_position.contribution_margin_pct == -34.0
    assert result.operating_cost_position.operating_cost_target_floor == 179.41
    assert result.operating_cost_position.operating_cost_target_gap == 79.41
    assert result.operating_cost_position.labour_rate_risk == "UNDER_CREW_RATE_TARGET"
    assert result.operating_cost_position.mobilization_risk == "UNDER_LOCAL_MOBILIZATION_TARGET"
    assert result.operating_cost_position.moving_underpricing_risk == "MOVING_UNDERPRICED"


def _operating_cost_base_cost_scenario() -> calibration.CalibrationScenario:
    return calibration.CalibrationScenario(
        category="target floor regression",
        name="100 dollar base cost",
        payload=calibration._payload(
            service_type="haul_away",
            estimated_hours=0.0,
            crew_size=1,
        ),
        costs=calibration.MockCosts(labor=70.0, disposal=20.0, fuel_wear=10.0, other=0.0),
        market_target=None,
        equipment=calibration.EquipmentGuidance(
            equipment_type="truck_only",
            trailer_type="none",
            recommended_trailer="none",
            trailer_reason="Synthetic calibration-only operating cost regression scenario.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Low risk.",
        ),
    )


def _scrap_recovery_operating_cost_scenario(*, scrap_recovery: float) -> calibration.CalibrationScenario:
    return calibration.CalibrationScenario(
        category="scrap recovery regression",
        name="scrap recovery net cost",
        payload=calibration._payload(
            service_type="scrap_pickup",
            estimated_hours=0.0,
            crew_size=1,
        ),
        costs=calibration.MockCosts(labor=80.0, fuel_wear=20.0, scrap_recovery=scrap_recovery),
        market_target=None,
        equipment=calibration.EquipmentGuidance(
            equipment_type="truck_only",
            trailer_type="none",
            recommended_trailer="none",
            trailer_reason="Synthetic calibration-only scrap recovery regression scenario.",
            load_weight_class="normal",
            disposal_fee_mode="small_flat_fee",
            equipment_disposal_risk_note="Scrap recovery remains manual-review analysis only.",
        ),
    )


def test_operating_cost_target_floor_solves_from_revenue_independent_base_cost() -> None:
    result = calibration._run_scenario(
        _operating_cost_base_cost_scenario(),
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )

    assert result.operating_cost_position.mock_internal_cost == 112.0
    assert result.operating_cost_position.operating_cost_target_floor == 147.06
    assert result.operating_cost_position.operating_cost_target_floor != 140.0
    assert result.operating_cost_position.operating_cost_target_gap == 47.06


def test_operating_cost_target_floor_stays_stable_when_cash_quote_changes() -> None:
    scenario = _operating_cost_base_cost_scenario()

    low_quote = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )
    high_quote = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 200.0,
                "emt_total_cad": 226.0,
            },
        },
    )

    assert low_quote.operating_cost_position.mock_internal_cost == 112.0
    assert high_quote.operating_cost_position.mock_internal_cost == 124.0
    assert low_quote.operating_cost_position.operating_cost_target_floor == 147.06
    assert high_quote.operating_cost_position.operating_cost_target_floor == 147.06
    assert low_quote.operating_cost_position.operating_cost_target_gap == 47.06
    assert high_quote.operating_cost_position.operating_cost_target_gap == 0.0


def test_scrap_recovery_reduces_mock_internal_cost_and_improves_margin() -> None:
    without_scrap = calibration._run_scenario(
        _scrap_recovery_operating_cost_scenario(scrap_recovery=0.0),
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )
    with_scrap = calibration._run_scenario(
        _scrap_recovery_operating_cost_scenario(scrap_recovery=30.0),
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )

    assert without_scrap.operating_cost_position.mock_internal_cost == 112.0
    assert without_scrap.operating_cost_position.contribution_margin_pct == -12.0
    assert with_scrap.operating_cost_position.mock_internal_cost == 82.0
    assert with_scrap.operating_cost_position.contribution_margin_pct == 18.0
    assert (
        without_scrap.operating_cost_position.mock_internal_cost
        - with_scrap.operating_cost_position.mock_internal_cost
        == 30.0
    )
    assert with_scrap.operating_cost_position.operating_cost_target_floor == 102.94
    assert with_scrap.operating_cost_position.operating_cost_target_gap == 2.94


def test_scrap_recovery_net_base_cost_clamps_before_overhead() -> None:
    scenario = _scrap_recovery_operating_cost_scenario(scrap_recovery=150.0)
    base_cost = calibration._operating_cost_base_cost(
        labour_total=80.0,
        truck_reserve=0.0,
        costs=scenario.costs,
    )

    result = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
            },
        },
    )

    assert base_cost == 0.0
    assert result.operating_cost_position.mock_internal_cost == 12.0
    assert result.operating_cost_position.contribution_margin_pct == 88.0
    assert result.operating_cost_position.operating_cost_target_floor == 0.0
    assert result.operating_cost_position.operating_cost_target_gap == 0.0


def test_zero_hour_operating_cost_labour_uses_positive_mock_labor_fallback() -> None:
    payload = calibration._payload(
        estimated_hours=0.0,
        crew_size=1,
    )

    result = calibration._operating_cost_labour_total(
        payload,
        fallback_mock_labor_cost=35.0,
    )

    assert result == 35.0


def test_zero_hour_operating_cost_labour_without_mock_labor_stays_zero() -> None:
    payload = calibration._payload(
        estimated_hours=0.0,
        crew_size=1,
    )

    result = calibration._operating_cost_labour_total(
        payload,
        fallback_mock_labor_cost=0.0,
    )

    assert result == 0.0


def test_positive_hour_operating_cost_labour_uses_calculated_assumption_not_fallback() -> None:
    payload = calibration._payload(
        estimated_hours=2.0,
        crew_size=2,
    )

    result = calibration._operating_cost_labour_total(
        payload,
        fallback_mock_labor_cost=999.0,
    )

    assert result == 98.0


def test_existing_zero_hour_scrap_scenario_uses_mock_labor_in_operating_cost() -> None:
    scenario = next(
        scenario
        for scenario in calibration.SCENARIOS
        if scenario.name == "inside appliance removal"
    )

    result = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 60.0,
                "emt_total_cad": 67.80,
            },
        },
    )

    assert scenario.payload["estimated_hours"] == 0.0
    assert scenario.costs.labor == 35.0
    assert result.operating_cost_position.mock_internal_cost == 41.2
    assert result.operating_cost_position.contribution_margin_pct == 31.3
    assert result.operating_cost_position.operating_cost_target_floor == 50.0
    assert result.operating_cost_position.operating_cost_target_gap == 0.0


def test_access_difficulty_move_uses_harder_moving_target() -> None:
    scenario = calibration.CalibrationScenario(
        category="small moves",
        name="stairs move",
        payload=calibration._payload(
            service_type="small_move",
            estimated_hours=3.0,
            crew_size=2,
            access_difficulty="extreme",
        ),
        costs=calibration.MockCosts(disposal=0.0, fuel_wear=0.0, other=0.0),
        market_target=calibration.MarketTarget(525.0, "175-210/hr"),
        equipment=calibration.EquipmentGuidance(
            equipment_type="enclosed_trailer",
            trailer_type="newer_enclosed",
            recommended_trailer="newer_enclosed",
            trailer_reason="Difficult access moving job needs manual review.",
            load_weight_class="heavy",
            disposal_fee_mode="manual_review",
            equipment_disposal_risk_note="High labour/access risk.",
        ),
    )

    result = calibration._run_scenario(
        scenario,
        quote_func=lambda payload: {
            "response": {
                "cash_total_cad": 500.0,
                "emt_total_cad": 565.0,
            },
        },
    )

    assert result.operating_cost_position.moving_underpricing_risk == "HARD_MOVE_UNDERPRICED"


def test_summary_counts_new_risk_categories() -> None:
    results = [
        calibration._run_scenario(scenario)
        for scenario in calibration.SCENARIOS
    ]

    summaries = {
        summary.category: summary
        for summary in (
            calibration._summarize_category(category, [result for result in results if result.category == category])
            for category in dict.fromkeys(result.category for result in results)
        )
    }

    assert summaries["small moves"].moving_underpricing_count >= 1
    assert summaries["demolition"].demolition_premium_risk_count >= 1
    assert summaries["dump runs"].manual_review_disposal_risk_count >= 1
    assert sum(summary.under_operating_cost_target_count for summary in summaries.values()) >= 1
    assert sum(summary.below_contribution_margin_count for summary in summaries.values()) >= 1


def test_quote_totals_are_sourced_from_build_quote_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_build_quote_artifacts(payload: dict) -> dict:
        calls.append(payload)
        return {
            "normalized_request": {"service_type": "haul_away"},
            "response": {
                "cash_total_cad": 125.0,
                "emt_total_cad": 141.25,
                "disclaimer": "mock",
            },
        }

    monkeypatch.setattr(calibration, "build_quote_artifacts", fake_build_quote_artifacts)

    result = calibration._run_scenario(calibration.SCENARIOS[0])

    assert calls == [calibration.SCENARIOS[0].payload]
    assert result.cash_quote == 125.0
    assert result.emt_quote == 141.25
    assert result.operating_cost_position.mock_internal_cost >= 0.0


def test_script_does_not_directly_import_storage_or_call_db_writes() -> None:
    script_path = REPO_ROOT / "scripts" / "run_price_calibration_mocks.py"
    tree = ast.parse(script_path.read_text(encoding="utf-8"))

    forbidden_imports = []
    forbidden_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            forbidden_imports.extend(alias.name for alias in node.names if alias.name == "app.storage")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "app" and any(alias.name == "storage" for alias in node.names):
                forbidden_imports.append("from app import storage")
            if node.module == "app.storage":
                forbidden_imports.append("from app.storage import ...")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "save_quote",
                "save_job",
                "update_job_costing",
                "init_db",
            }:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in {
                "save_quote",
                "save_job",
                "update_job_costing",
                "init_db",
            }:
                forbidden_calls.append(node.func.attr)

    assert forbidden_imports == []
    assert forbidden_calls == []


def test_script_runs_directly_without_creating_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / "calibration-should-not-exist.sqlite3"
    env = os.environ.copy()
    env["BAYDELIVERY_DB_PATH"] = str(db_path)

    result = subprocess.run(
        [sys.executable, "scripts/run_price_calibration_mocks.py"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Bay Delivery Price Calibration Mock Harness" in result.stdout
    assert "target floor" in result.stdout
    assert "market flag" in result.stdout
    assert "op cost target floor" in result.stdout
    assert "op cost gap" in result.stdout
    assert "contribution margin" in result.stdout
    assert "labour risk" in result.stdout
    assert "mobilization risk" in result.stdout
    assert "disposal risk" in result.stdout
    assert "moving risk" in result.stdout
    assert "equipment" in result.stdout
    assert "rec trailer" in result.stdout
    assert "Owner review scenarios" in result.stdout
    assert "MARKET_UNDERPRICED" in result.stdout
    assert "TARGET_OK" in result.stdout
    assert "double_axle_aluminum" in result.stdout
    assert "newer_enclosed" in result.stdout
    assert "older_enclosed" in result.stdout
    assert "weighed_tonnage" in result.stdout
    assert "manual_review" in result.stdout
    assert "MOVING_UNDERPRICED" in result.stdout
    assert "MANUAL_REVIEW" in result.stdout
    assert "demo premium risk" in result.stdout
    assert "under operating-cost target" in result.stdout
    assert "below contribution margin" in result.stdout
    assert "Category summaries" in result.stdout
    assert "N/A" in result.stdout
    assert not db_path.exists()
