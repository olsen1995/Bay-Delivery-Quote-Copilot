from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from tests.quote_stress_scenarios import (
    ALL_QUOTE_STRESS_SCENARIOS,
    EDGE_MARGIN_RISK_COMPARISONS,
    SCENARIO_BY_ID,
    QuoteStressComparison,
    QuoteStressScenario,
)

SUCCESS_SCENARIOS = [
    scenario for scenario in ALL_QUOTE_STRESS_SCENARIOS
    if scenario["expected_status"] == 200
]

FAILURE_SCENARIOS = [
    scenario for scenario in ALL_QUOTE_STRESS_SCENARIOS
    if scenario["expected_status"] != 200
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    original_db_path = storage.DB_PATH
    scratch_dir = Path("tmp") / "quote-stress-harness"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    scratch_db_path = scratch_dir / "quote-stress-harness.sqlite3"
    if scratch_db_path.exists():
        scratch_db_path.unlink()

    storage.DB_PATH = scratch_db_path
    storage._TABLE_COL_CACHE.clear()
    storage.init_db()

    with TestClient(app) as test_client:
        yield test_client

    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()


def _post_quote(client: TestClient, scenario: QuoteStressScenario):
    return client.post("/quote/calculate", json=scenario["payload"])


def _assert_success_invariants(body: dict[str, Any], scenario: QuoteStressScenario) -> float:
    if scenario.get("check_shape"):
        assert isinstance(body.get("quote_id"), str)
        assert body["quote_id"]
        assert isinstance(body.get("created_at"), str)
        assert body["created_at"]
        assert isinstance(body.get("accept_token"), str)
        assert body["accept_token"]

    request = body.get("request")
    response = body.get("response")
    assert isinstance(request, dict)
    assert isinstance(response, dict)

    assert isinstance(request.get("customer_name"), str)
    assert request["customer_name"]
    assert isinstance(request.get("customer_phone"), str)
    assert request["customer_phone"]
    assert isinstance(request.get("job_address"), str)
    assert request["job_address"]

    cash = response.get("cash_total_cad")
    emt = response.get("emt_total_cad")
    disclaimer = response.get("disclaimer")

    assert isinstance(cash, (int, float))
    assert isinstance(emt, (int, float))
    assert math.isfinite(cash)
    assert math.isfinite(emt)
    assert cash >= 0
    assert emt >= 0
    assert emt >= cash
    assert isinstance(disclaimer, str)
    assert disclaimer

    normalized_service_type = request.get("service_type")
    expected_service_type = scenario.get("expected_service_type")
    if expected_service_type:
        assert normalized_service_type == expected_service_type

    if scenario.get("requires_pickup_dropoff"):
        assert isinstance(request.get("pickup_address"), str)
        assert request["pickup_address"]
        assert isinstance(request.get("dropoff_address"), str)
        assert request["dropoff_address"]

    cash_total = float(cash)
    if scenario.get("check_minimum_floor"):
        assert cash_total >= 60.0
        if normalized_service_type == "item_delivery":
            assert cash_total >= 100.0
        if normalized_service_type == "demolition":
            assert cash_total >= 75.0

    return cash_total


def _assert_failure_invariants(response, scenario: QuoteStressScenario) -> None:
    body = response.json()

    if response.status_code == 400:
        assert body == {"detail": scenario["expected_error_detail"]}
        return

    assert response.status_code == 422
    detail = body.get("detail")
    assert isinstance(detail, list)
    assert detail
    assert any(
        isinstance(item, dict) and item.get("loc") == scenario["expected_error_loc"]
        for item in detail
    )


@pytest.mark.parametrize(
    "scenario",
    SUCCESS_SCENARIOS,
    ids=[scenario["id"] for scenario in SUCCESS_SCENARIOS],
)
def test_quote_stress_success_scenarios(client: TestClient, scenario: QuoteStressScenario) -> None:
    response = _post_quote(client, scenario)

    assert response.status_code == 200
    _assert_success_invariants(response.json(), scenario)


@pytest.mark.parametrize(
    "scenario",
    FAILURE_SCENARIOS,
    ids=[scenario["id"] for scenario in FAILURE_SCENARIOS],
)
def test_quote_stress_failure_scenarios(client: TestClient, scenario: QuoteStressScenario) -> None:
    response = _post_quote(client, scenario)

    assert response.status_code == scenario["expected_status"]
    _assert_failure_invariants(response, scenario)


@pytest.mark.parametrize(
    "comparison",
    EDGE_MARGIN_RISK_COMPARISONS,
    ids=[comparison["id"] for comparison in EDGE_MARGIN_RISK_COMPARISONS],
)
def test_quote_stress_edge_margin_risk_comparisons(
    client: TestClient,
    comparison: QuoteStressComparison,
) -> None:
    lower_scenario = SCENARIO_BY_ID[comparison["lower_quote_scenario_id"]]
    higher_scenario = SCENARIO_BY_ID[comparison["higher_quote_scenario_id"]]

    lower_response = _post_quote(client, lower_scenario)
    higher_response = _post_quote(client, higher_scenario)

    assert lower_response.status_code == 200
    assert higher_response.status_code == 200

    lower_cash = _assert_success_invariants(lower_response.json(), lower_scenario)
    higher_cash = _assert_success_invariants(higher_response.json(), higher_scenario)

    assert higher_cash >= lower_cash, comparison["reason"]
