from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import storage
from app.quote_engine import calculate_quote
from app.storage import get_quote_record
from app.services.quote_service import build_and_save_quote, build_quote_artifacts
from app.services.quote_risk_scoring import build_quote_risk_assessment


def _base_payload(service_type: str = "haul_away") -> dict:
    return {
        "customer_name": "Risk Tester",
        "customer_phone": "705-555-0111",
        "job_address": "123 Risk St",
        "job_description_customer": "Risk scoring regression",
        "description": "Risk scoring regression",
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
        "access_difficulty": "normal",
        "has_dense_materials": False,
    }


def _assessment_for(**overrides: object) -> dict[str, object]:
    payload = _base_payload()
    payload.update(overrides)
    artifacts = build_quote_artifacts(payload)
    return build_quote_risk_assessment(
        normalized_request=artifacts["normalized_request"],
        engine_quote=artifacts["engine_quote"],
    )


@pytest.fixture()
def temp_quote_db():
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "quote-risk.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()
        yield
    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)


def test_sparse_haul_away_inputs_score_low_confidence() -> None:
    with pytest.raises(HTTPException, match="Please add at least one load detail"):
        _assessment_for()


def test_dense_material_inputs_set_dense_material_risk() -> None:
    assessment = _assessment_for(
        garbage_bag_count=8,
        estimated_hours=1.5,
        has_dense_materials=True,
    )

    assert assessment["confidence_level"] == "medium"
    assert "dense_material_risk" in assessment["risk_flags"]


def test_access_volume_and_underestimated_volume_rules_are_structured() -> None:
    assessment = _assessment_for(
        garbage_bag_count=3,
        estimated_hours=2.0,
        crew_size=2,
        access_difficulty="difficult",
    )

    assert assessment["confidence_level"] == "low"
    assert "access_volume_risk" in assessment["risk_flags"]
    assert "likely_underestimated_volume" in assessment["risk_flags"]


def test_mixed_bulky_load_risk_uses_structured_load_signals() -> None:
    assessment = _assessment_for(
        garbage_bag_count=4,
        estimated_hours=2.0,
        crew_size=2,
    )

    assert assessment["confidence_level"] == "medium"
    assert "mixed_bulky_load_risk" in assessment["risk_flags"]


def test_invalid_access_and_travel_inputs_do_not_count_as_scope_signals() -> None:
    with pytest.raises(HTTPException, match="Invalid access_difficulty"):
        _assessment_for(
            service_type="demolition",
            access_difficulty="stairs",
            travel_zone="rural",
        )


def test_invalid_haul_away_scope_strings_do_not_count_as_structured_scope() -> None:
    with pytest.raises(HTTPException, match="Please add at least one load detail"):
        _assessment_for(
            bag_type="foo",
            trailer_fill_estimate="bar",
        )


def test_valid_haul_away_scope_values_still_count_as_structured_scope() -> None:
    assessment = _assessment_for(
        bag_type="light",
        trailer_fill_estimate="quarter",
    )

    assert assessment["confidence_level"] == "medium"
    assert "missing_structured_scope" not in assessment["risk_flags"]
    assert "low_input_signal" not in assessment["risk_flags"]


def test_low_risk_structured_quote_artifacts_do_not_add_margin_protection() -> None:
    payload = _base_payload()
    payload.update(
        {
            "garbage_bag_count": 2,
            "bag_type": "light",
        }
    )
    baseline = calculate_quote(
        "haul_away",
        1.0,
        crew_size=1,
        garbage_bag_count=2,
        bag_type="light",
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="standard",
    )

    artifacts = build_quote_artifacts(payload)

    assert artifacts["internal_risk_assessment"] == {"confidence_level": "high", "risk_flags": []}
    assert artifacts["response"] == {
        "cash_total_cad": float(baseline["total_cash_cad"]),
        "emt_total_cad": float(baseline["total_emt_cad"]),
        "disclaimer": str(baseline["disclaimer"]),
    }
    assert artifacts["engine_quote"]["_internal"]["risk_margin_protection_cad"] == 0.0
    assert artifacts["engine_quote"]["_internal"]["risk_margin_protection_flags"] == []


def test_quote_artifacts_apply_expected_margin_protection_for_strong_flags() -> None:
    payload = _base_payload()
    payload.update(
        {
            "garbage_bag_count": 4,
            "estimated_hours": 2.0,
            "crew_size": 2,
        }
    )
    baseline = calculate_quote(
        "haul_away",
        2.0,
        crew_size=2,
        garbage_bag_count=4,
        travel_zone="in_town",
        access_difficulty="normal",
        has_dense_materials=False,
        load_mode="standard",
    )

    artifacts = build_quote_artifacts(payload)

    assert artifacts["internal_risk_assessment"] == {
        "confidence_level": "medium",
        "risk_flags": ["mixed_bulky_load_risk", "likely_underestimated_volume"],
    }
    assert set(artifacts["response"].keys()) == {"cash_total_cad", "emt_total_cad", "disclaimer"}
    assert artifacts["response"]["disclaimer"] == baseline["disclaimer"]
    assert artifacts["engine_quote"]["_internal"]["risk_margin_protection_cad"] == 75.0
    assert artifacts["engine_quote"]["_internal"]["risk_margin_protection_flags"] == [
        "mixed_bulky_load_risk",
        "likely_underestimated_volume",
    ]
    assert artifacts["engine_quote"]["_internal"]["cash_before_round_cad"] == (
        baseline["_internal"]["cash_before_round_cad"] + 75.0
    )
    assert artifacts["response"]["cash_total_cad"] == 235.0
    assert artifacts["response"]["emt_total_cad"] == 265.55


def test_build_quote_artifacts_keeps_internal_assessment_out_of_public_quote(temp_quote_db) -> None:
    payload = _base_payload()
    payload["garbage_bag_count"] = 3
    artifacts = build_quote_artifacts(payload)

    assert artifacts["internal_risk_assessment"]["confidence_level"] in {"high", "medium", "low"}
    assert isinstance(artifacts["internal_risk_assessment"]["risk_flags"], list)
    assert set(artifacts["response"].keys()) == {"cash_total_cad", "emt_total_cad", "disclaimer"}
    assert "risk_margin_protection_cad" not in artifacts["response"]
    assert "risk_margin_protection_flags" not in artifacts["response"]

    saved = build_and_save_quote(payload, now_iso="2026-04-16T12:00:00-04:00")
    assert set(saved.keys()) == {"quote_id", "created_at", "request", "response", "accept_token"}
    assert "internal_risk_assessment" not in saved
    assert "internal_risk_assessment" not in saved["response"]

    record = get_quote_record(saved["quote_id"])
    assert record is not None
    assert "internal_risk_assessment" not in record["response"]


def test_build_quote_artifacts_preserves_description_for_second_engine_pass() -> None:
    payload = _base_payload(service_type="item_delivery")
    payload.update(
        {
            "job_description_customer": "Single delivery",
            "description": "Pickup sofa, dropoff to customer, then remove old couch.",
        }
    )

    artifacts = build_quote_artifacts(payload)

    assert artifacts["normalized_request"]["description"] == payload["description"]
    assert artifacts["engine_quote"]["_internal"]["multi_stop_complexity_adder_cad"] == 75.0
    assert artifacts["response"]["cash_total_cad"] == 175.0
