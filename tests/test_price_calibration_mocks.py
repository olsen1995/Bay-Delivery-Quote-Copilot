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
    assert "Category summaries" in result.stdout
    assert "N/A" in result.stdout
    assert not db_path.exists()
