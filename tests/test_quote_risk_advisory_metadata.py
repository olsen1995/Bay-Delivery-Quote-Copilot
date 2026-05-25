from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app import storage
from app.main import app
from app.services import quote_service
from app.services.quote_risk_scoring import build_quote_risk_advisory, build_quote_risk_summary


def _admin_headers() -> dict[str, str]:
    token = base64.b64encode(b"admin:secret").decode("utf-8")
    return {"Authorization": f"Basic {token}", "Sec-Fetch-Site": "same-origin"}


def _base_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "customer_name": "Risk Advisory",
        "customer_phone": "705-555-0177",
        "job_address": "177 Advisory Rd",
        "job_description_customer": "Small load with optional advisory facts",
        "description": "Small load with optional advisory facts",
        "service_type": "haul_away",
        "payment_method": "cash",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "garbage_bag_count": 0,
        "trailer_fill_estimate": "under_quarter",
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": "in_town",
        "access_difficulty": "normal",
        "has_dense_materials": False,
    }
    payload.update(overrides)
    return payload


def _advisory_payload(**overrides: Any) -> dict[str, Any]:
    return _base_payload(
        dense_material_type="concrete",
        mixed_load=True,
        contains_scrap=True,
        contains_garbage=True,
        has_refrigerant_appliance=True,
        appliance_type="fridge",
        stairs_count=3,
        basement_or_inside_removal=True,
        demolition_ripout=True,
        weather_protection_required=True,
        **overrides,
    )


def _codes(advisory: dict[str, Any] | None) -> set[str]:
    assert advisory is not None
    return {str(flag["code"]) for flag in advisory["risk_flags"]}


@pytest.fixture()
def temp_quote_db(monkeypatch: pytest.MonkeyPatch):
    original_db_path = storage.DB_PATH
    original_cache = dict(storage._TABLE_COL_CACHE)
    main_module._admin_failed_attempts.clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage.DB_PATH = Path(tmp_dir) / "quote-risk-advisory.sqlite3"
        storage._TABLE_COL_CACHE.clear()
        storage.init_db()
        yield

    main_module._admin_failed_attempts.clear()
    storage.DB_PATH = original_db_path
    storage._TABLE_COL_CACHE.clear()
    storage._TABLE_COL_CACHE.update(original_cache)


@pytest.fixture()
def client(temp_quote_db: None):
    with TestClient(app) as test_client:
        yield test_client


def test_old_quote_payload_still_returns_quote(client: TestClient) -> None:
    response = client.post("/quote/calculate", json=_base_payload())

    assert response.status_code == 200
    assert response.json()["response"]["cash_total_cad"] > 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("disposal_manual_review_required", True),
        ("recommended_trailer", "double_axle_open_aluminum"),
        ("manual_review_recommended", True),
        ("quote_risk_advisory", {"manual_review_recommended": True}),
    ],
)
def test_public_callers_cannot_submit_internal_advisory_fields(
    client: TestClient,
    field: str,
    value: Any,
) -> None:
    response = client.post("/quote/calculate", json=_base_payload(**{field: value}))

    assert response.status_code == 422


def test_advisory_metadata_has_no_pricing_effect(client: TestClient) -> None:
    baseline = client.post("/quote/calculate", json=_base_payload()).json()["response"]
    enriched = client.post("/quote/calculate", json=_advisory_payload()).json()["response"]

    assert enriched["cash_total_cad"] == baseline["cash_total_cad"]
    assert enriched["emt_total_cad"] == baseline["emt_total_cad"]


def test_advisory_metadata_is_not_passed_to_quote_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    original_calculate_quote = quote_service.calculate_quote
    seen_kwargs: list[dict[str, Any]] = []

    def capture_calculate_quote(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(dict(kwargs))
        return original_calculate_quote(**kwargs)

    monkeypatch.setattr(quote_service, "calculate_quote", capture_calculate_quote)

    artifacts = quote_service.build_quote_artifacts(_advisory_payload())

    assert artifacts["quote_risk_advisory"] is not None
    assert len(seen_kwargs) == 2
    for kwargs in seen_kwargs:
        assert "quote_risk_advisory" not in kwargs
        assert "manual_review_recommended" not in kwargs
        assert "recommended_trailer" not in kwargs


def test_advisory_metadata_is_not_persisted_into_request_json(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_advisory_payload())
    quote_body = quote_response.json()
    quote_id = quote_body["quote_id"]
    accept_token = quote_body["accept_token"]

    saved_quote = storage.get_quote_record(quote_id)
    assert saved_quote is not None
    assert "quote_risk_advisory" not in saved_quote["request"]
    assert "manual_review_recommended" not in saved_quote["request"]
    assert "recommended_trailer" not in saved_quote["request"]

    accept_response = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "accept", "accept_token": accept_token},
    )
    assert accept_response.status_code == 200
    request_id = accept_response.json()["request_id"]
    saved_request = storage.get_quote_request_record(request_id)
    assert saved_request is not None
    assert "quote_risk_advisory" not in saved_request["request_json"]
    assert "manual_review_recommended" not in saved_request["request_json"]
    assert "recommended_trailer" not in saved_request["request_json"]

    approval_response = client.post(
        f"/admin/api/quote-requests/{request_id}/decision",
        headers=_admin_headers(),
        json={"action": "approve"},
    )
    assert approval_response.status_code == 200
    saved_job = storage.get_job_by_quote_id(quote_id)
    assert saved_job is not None
    assert "quote_risk_advisory" not in saved_job["request_json"]
    assert "manual_review_recommended" not in saved_job["request_json"]
    assert "recommended_trailer" not in saved_job["request_json"]


@pytest.mark.parametrize(
    ("request_fields", "expected_code"),
    [
        ({"dense_material_type": "concrete"}, "DENSE_MATERIAL_RISK"),
        ({"mixed_load": True, "contains_scrap": True, "contains_garbage": True}, "MIXED_LOAD_SORTING_RISK"),
        ({"has_refrigerant_appliance": True, "appliance_type": "fridge"}, "REFRIGERANT_APPLIANCE_RISK"),
        ({"stairs_count": 3, "basement_or_inside_removal": True}, "ACCESS_LABOUR_RISK"),
        ({"demolition_ripout": True}, "DEMOLITION_SCOPE_RISK"),
        ({"weather_protection_required": True}, "WEATHER_PROTECTION_RISK"),
    ],
)
def test_structured_intake_rules_generate_expected_advisory_flags(
    request_fields: dict[str, Any],
    expected_code: str,
) -> None:
    advisory = build_quote_risk_advisory({"service_type": "haul_away", **request_fields})

    assert expected_code in _codes(advisory)
    assert advisory["pricing_effect"] == "none"
    assert advisory["customer_visible"] is False


def test_high_risk_advisory_sets_manual_review_and_conservative_trailer() -> None:
    advisory = build_quote_risk_advisory({"service_type": "haul_away", "dense_material_type": "concrete"})

    assert advisory is not None
    assert advisory["manual_review_recommended"] is True
    assert advisory["risk_level"] == "high"
    assert advisory["recommended_trailer"] == "double_axle_open_aluminum"


def test_weather_move_advisory_sets_enclosed_trailer_without_manual_review() -> None:
    advisory = build_quote_risk_advisory({"service_type": "small_move", "weather_protection_required": True})

    assert advisory is not None
    assert advisory["manual_review_recommended"] is False
    assert advisory["risk_level"] == "low"
    assert advisory["recommended_trailer"] == "newer_enclosed"


@pytest.mark.parametrize(
    ("request_fields", "advisory", "assessment", "expected"),
    [
        (
            {
                "service_type": "haul_away",
                "garbage_bag_count": 4,
                "trailer_fill_estimate": "quarter",
                "access_difficulty": "normal",
                "crew_size": 1,
                "requested_job_date": "2026-05-20",
                "requested_time_window": "morning",
                "photos_uploaded": True,
            },
            None,
            {"confidence_level": "high", "risk_flags": []},
            {
                "risk_level": "low",
                "suggested_action": "approve",
                "crew_suggestion": "one_worker_likely",
                "trailer_suggestion": "single_axle",
            },
        ),
        (
            {
                "service_type": "haul_away",
                "dense_material_type": "tile",
                "garbage_bag_count": 2,
                "access_difficulty": "normal",
            },
            build_quote_risk_advisory({"service_type": "haul_away", "dense_material_type": "tile"}),
            {"confidence_level": "medium", "risk_flags": ["dense_material_risk"]},
            {
                "risk_level": "medium",
                "suggested_action": "request_photos",
                "crew_suggestion": "one_worker_likely",
                "trailer_suggestion": "single_axle",
            },
        ),
        (
            {
                "service_type": "haul_away",
                "stairs_count": 2,
                "basement_or_inside_removal": False,
                "mixed_load": True,
                "contains_scrap": True,
                "contains_garbage": False,
                "access_difficulty": "difficult",
            },
            build_quote_risk_advisory(
                {
                    "service_type": "haul_away",
                    "stairs_count": 2,
                    "basement_or_inside_removal": False,
                    "mixed_load": True,
                    "contains_scrap": True,
                    "contains_garbage": False,
                }
            ),
            {"confidence_level": "low", "risk_flags": ["access_volume_risk", "mixed_bulky_load_risk"]},
            {
                "risk_level": "high",
                "suggested_action": "ask_followup",
                "crew_suggestion": "two_workers_likely",
                "trailer_suggestion": "unknown",
            },
        ),
        (
            {
                "service_type": "haul_away",
                "dense_material_type": "concrete",
                "demolition_ripout": True,
                "stairs_count": 3,
            },
            build_quote_risk_advisory(
                {
                    "service_type": "haul_away",
                    "dense_material_type": "concrete",
                    "demolition_ripout": True,
                    "stairs_count": 3,
                }
            ),
            {"confidence_level": "low", "risk_flags": ["dense_material_risk", "access_volume_risk"]},
            {
                "risk_level": "owner_review",
                "suggested_action": "owner_review_before_approving",
                "crew_suggestion": "owner_review",
                "trailer_suggestion": "double_axle",
            },
        ),
    ],
)
def test_quote_risk_summary_builder_returns_stable_admin_shape(
    request_fields: dict[str, Any],
    advisory: dict[str, Any] | None,
    assessment: dict[str, Any],
    expected: dict[str, str],
) -> None:
    summary = build_quote_risk_summary(request_fields, advisory, assessment)

    assert set(summary) == {
        "risk_level",
        "reasons",
        "missing_info",
        "suggested_action",
        "crew_suggestion",
        "trailer_suggestion",
        "pricing_caution",
        "customer_visible",
        "pricing_effect",
    }
    assert summary["risk_level"] == expected["risk_level"]
    assert summary["suggested_action"] == expected["suggested_action"]
    assert summary["crew_suggestion"] == expected["crew_suggestion"]
    assert summary["trailer_suggestion"] == expected["trailer_suggestion"]
    assert isinstance(summary["reasons"], list)
    assert isinstance(summary["missing_info"], list)
    assert summary["pricing_caution"] == "internal_advisory_only_no_price_change"
    assert summary["customer_visible"] is False
    assert summary["pricing_effect"] == "none"


def test_quote_risk_summary_detects_missing_info_and_practical_reasons() -> None:
    advisory = build_quote_risk_advisory(
        {
            "service_type": "haul_away",
            "dense_material_type": "concrete",
            "stairs_count": 3,
            "basement_or_inside_removal": True,
            "has_refrigerant_appliance": True,
            "appliance_type": "fridge",
        }
    )
    summary = build_quote_risk_summary(
        {
            "service_type": "haul_away",
            "description": "stuff",
            "garbage_bag_count": 0,
            "trailer_fill_estimate": "",
            "dense_material_type": "concrete",
            "stairs_count": 3,
            "basement_or_inside_removal": True,
            "has_refrigerant_appliance": True,
            "appliance_type": "fridge",
        },
        advisory,
        {"confidence_level": "low", "risk_flags": ["missing_structured_scope", "dense_material_risk"]},
    )

    assert summary["risk_level"] == "owner_review"
    assert summary["suggested_action"] == "owner_review_before_approving"
    assert set(summary["missing_info"]).issuperset(
        {
            "photos",
            "item_count",
            "access_details",
            "disposal_type",
            "preferred_date",
            "preferred_time_window",
        }
    )
    assert set(summary["reasons"]).issuperset(
        {
            "heavy_material_risk",
            "access_or_stairs_risk",
            "refrigerant_appliance_check",
            "low_confidence_or_missing_scope",
            "owner_review_recommended",
        }
    )


def test_quote_risk_summary_does_not_request_photos_when_photo_context_exists() -> None:
    advisory = build_quote_risk_advisory({"service_type": "haul_away", "dense_material_type": "tile"})
    assert advisory is not None
    assert any("photo" in action.lower() for action in advisory["suggested_actions"])

    summary = build_quote_risk_summary(
        {
            "service_type": "haul_away",
            "dense_material_type": "tile",
            "garbage_bag_count": 4,
            "bag_type": "light",
            "trailer_fill_estimate": "quarter",
            "access_difficulty": "normal",
            "requested_job_date": "2026-05-20",
            "requested_time_window": "morning",
            "attachment_count": 2,
        },
        advisory,
        {"confidence_level": "medium", "risk_flags": ["dense_material_risk"]},
    )

    assert "photos" not in summary["missing_info"]
    assert summary["suggested_action"] == "ask_followup"


def test_quote_risk_summary_still_requests_photos_when_photos_are_missing() -> None:
    advisory = build_quote_risk_advisory({"service_type": "haul_away", "dense_material_type": "tile"})

    summary = build_quote_risk_summary(
        {
            "service_type": "haul_away",
            "dense_material_type": "tile",
            "garbage_bag_count": 4,
            "bag_type": "light",
            "trailer_fill_estimate": "quarter",
            "access_difficulty": "normal",
            "requested_job_date": "2026-05-20",
            "requested_time_window": "morning",
        },
        advisory,
        {"confidence_level": "medium", "risk_flags": ["dense_material_risk"]},
    )

    assert "photos" in summary["missing_info"]
    assert summary["suggested_action"] == "request_photos"


def test_quote_risk_summary_owner_review_still_outranks_missing_photos() -> None:
    advisory = build_quote_risk_advisory({"service_type": "haul_away", "dense_material_type": "concrete"})

    summary = build_quote_risk_summary(
        {
            "service_type": "haul_away",
            "dense_material_type": "concrete",
            "garbage_bag_count": 4,
            "bag_type": "heavy_mixed",
            "trailer_fill_estimate": "quarter",
            "access_difficulty": "normal",
            "requested_job_date": "2026-05-20",
            "requested_time_window": "morning",
        },
        advisory,
        {"confidence_level": "medium", "risk_flags": ["dense_material_risk"]},
    )

    assert "photos" in summary["missing_info"]
    assert summary["risk_level"] == "owner_review"
    assert summary["suggested_action"] == "owner_review_before_approving"


def test_quote_risk_summary_other_missing_info_asks_followup_when_photos_present() -> None:
    summary = build_quote_risk_summary(
        {
            "service_type": "haul_away",
            "description": "stuff",
            "access_difficulty": "normal",
            "requested_job_date": "2026-05-20",
            "requested_time_window": "morning",
            "photos_uploaded": True,
        },
        None,
        {"confidence_level": "high", "risk_flags": []},
    )

    assert "photos" not in summary["missing_info"]
    assert "item_count" in summary["missing_info"]
    assert summary["suggested_action"] == "ask_followup"


def test_quote_risk_summary_builder_does_not_mutate_inputs() -> None:
    request = {"service_type": "haul_away", "dense_material_type": "concrete"}
    advisory = build_quote_risk_advisory(request)
    assessment = {"confidence_level": "medium", "risk_flags": ["dense_material_risk"]}
    request_before = dict(request)
    advisory_before = dict(advisory or {})
    assessment_before = dict(assessment)

    build_quote_risk_summary(request, advisory, assessment)

    assert request == request_before
    assert advisory == advisory_before
    assert assessment == assessment_before


def test_public_quote_and_customer_review_exclude_advisory_metadata(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_advisory_payload())

    assert quote_response.status_code == 200
    quote_body = quote_response.json()
    assert "quote_risk_advisory" not in quote_body
    assert "quote_risk_summary" not in quote_body
    assert "quote_risk_advisory" not in quote_body["request"]
    assert "quote_risk_summary" not in quote_body["request"]
    assert "quote_risk_advisory" not in quote_body["response"]
    assert "quote_risk_summary" not in quote_body["response"]

    review_response = client.get(
        f"/quote/{quote_body['quote_id']}/view",
        headers={"Authorization": f"Bearer {quote_body['accept_token']}"},
    )

    assert review_response.status_code == 200
    review_body = review_response.json()
    assert "quote_risk_advisory" not in review_body
    assert "quote_risk_summary" not in review_body
    assert "quote_risk_advisory" not in review_body["request"]
    assert "quote_risk_summary" not in review_body["request"]
    assert "quote_risk_advisory" not in review_body["response"]
    assert "quote_risk_summary" not in review_body["response"]


def test_admin_quote_detail_includes_recomputed_advisory_metadata(client: TestClient) -> None:
    quote_response = client.post("/quote/calculate", json=_advisory_payload())
    quote_id = quote_response.json()["quote_id"]

    admin_response = client.get(f"/admin/api/quotes/{quote_id}", headers=_admin_headers())

    assert admin_response.status_code == 200
    advisory = admin_response.json()["quote_risk_advisory"]
    summary = admin_response.json()["quote_risk_summary"]
    assert advisory["customer_visible"] is False
    assert advisory["pricing_effect"] == "none"
    assert advisory["manual_review_recommended"] is True
    assert summary["customer_visible"] is False
    assert summary["pricing_effect"] == "none"
    assert summary["risk_level"] == "owner_review"
    assert summary["suggested_action"] == "owner_review_before_approving"
    assert summary["crew_suggestion"] == "owner_review"
    assert summary["trailer_suggestion"] == "double_axle"
    assert {
        "DENSE_MATERIAL_RISK",
        "MIXED_LOAD_SORTING_RISK",
        "REFRIGERANT_APPLIANCE_RISK",
        "ACCESS_LABOUR_RISK",
        "DEMOLITION_SCOPE_RISK",
        "WEATHER_PROTECTION_RISK",
    }.issubset(_codes(advisory))


def test_gpt_quote_response_excludes_advisory_metadata() -> None:
    response = quote_service.build_gpt_quote_response(_base_payload())

    assert "quote_risk_advisory" not in response
    assert "quote_risk_summary" not in response
