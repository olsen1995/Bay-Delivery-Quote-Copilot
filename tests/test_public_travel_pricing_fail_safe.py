from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, clear_gpt_quote_rate_limit_state
from app.services import quote_service
from app.storage import get_quote_record


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _payload(
    *,
    service_type: str = "small_move",
    pickup_address: str | None = "123 Main Street, North Bay, ON P1A 1A1",
    dropoff_address: str | None = "456 Oak Avenue, North Bay, Ontario, P1B 2B2, Canada",
    travel_zone: str = "in_town",
) -> dict:
    return {
        "customer_name": "Route Safety Tester",
        "customer_phone": "705-555-0144",
        "job_address": "123 Main Street, North Bay, ON",
        "job_description_customer": "Move a couch and table",
        "description": "Move a couch and table",
        "service_type": service_type,
        "payment_method": "cash",
        "pickup_address": pickup_address,
        "dropoff_address": dropoff_address,
        "estimated_hours": 4.0 if service_type == "small_move" else 1.0,
        "crew_size": 2 if service_type == "small_move" else 1,
        "garbage_bag_count": 0,
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
        "travel_zone": travel_zone,
    }


def _haul_payload(*, travel_zone: str = "in_town") -> dict:
    return {
        "customer_name": "Legacy Quote Tester",
        "customer_phone": "705-555-0188",
        "job_address": "88 Legacy Road, North Bay, ON",
        "description": "Remove a small local load",
        "service_type": "haul_away",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "trailer_fill_estimate": "under_quarter",
        "travel_zone": travel_zone,
    }


def _assert_authoritative(
    client: TestClient,
    service_type: str,
    *,
    pickup_address: str = "123 Main Street, North Bay, ON P1A 1A1",
    dropoff_address: str = "456 Oak Avenue, North Bay, Ontario, P1B 2B2, Canada",
) -> dict:
    response = client.post(
        "/quote/calculate",
        json=_payload(
            service_type=service_type,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authoritative"
    assert body["authoritative"] is True
    assert body["response"]["authoritative"] is True
    assert body["request"]["travel_zone"] == "in_town"
    assert body["request"]["route_classification"] == {
        "status": "authoritative",
        "source": "backend_address_locality_v1",
        "reason": "both_locations_north_bay",
        "travel_zone": "in_town",
    }
    assert body["accept_token"]
    return body


def _assert_review_required(
    client: TestClient,
    service_type: str,
    pickup_address: str,
    dropoff_address: str,
    expected_reason: str,
) -> dict:
    response = client.post(
        "/quote/calculate",
        json=_payload(
            service_type=service_type,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
        ),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "review_required"
    assert body["authoritative"] is False
    assert "accept_token" not in body
    assert "cash_total_cad" not in body["response"]
    assert "emt_total_cad" not in body["response"]
    assert body["request"]["route_classification"]["reason"] == expected_reason
    assert body["request"]["route_classification"]["travel_zone"] is None

    stored = get_quote_record(body["quote_id"])
    assert stored is not None
    assert stored["accept_token"] is None
    assert stored["request"]["pickup_address"] == pickup_address
    assert stored["request"]["dropoff_address"] == dropoff_address
    assert stored["response"]["authoritative"] is False
    return body


def test_small_move_strict_north_bay_route_is_authoritative(client: TestClient) -> None:
    _assert_authoritative(client, "small_move")


@pytest.mark.parametrize("service_type", ["small_move", "item_delivery"])
@pytest.mark.parametrize(
    ("pickup_address", "dropoff_address"),
    [
        ("123 Main Street North Bay ON", "123 Main St North Bay Ontario"),
        ("123 Main Street North Bay", "123 Main St North Bay ON P1A 1A1"),
        ("123 Main St North Bay P1A 1A1", "456 Oak Ave North Bay Canada"),
        (
            "123 Main St North Bay Ontario P1A 1A1 Canada",
            "456 Oak Avenue North Bay ON P1B 2B2 Canada",
        ),
    ],
)
def test_no_comma_terminal_north_bay_routes_are_authoritative(
    client: TestClient,
    service_type: str,
    pickup_address: str,
    dropoff_address: str,
) -> None:
    _assert_authoritative(
        client,
        service_type,
        pickup_address=pickup_address,
        dropoff_address=dropoff_address,
    )


@pytest.mark.parametrize("service_type", ["small_move", "item_delivery"])
@pytest.mark.parametrize(
    ("pickup_address", "dropoff_address", "expected_reason"),
    [
        (
            "123 Main Street near North Bay ON",
            "456 Oak Avenue North Bay ON",
            "conflicting_locality",
        ),
        (
            "123 Main Street North Bay to Sudbury",
            "456 Oak Avenue North Bay ON",
            "conflicting_locality",
        ),
        ("near North Bay", "outside North Bay", "unclassified_locality"),
        (
            "123 Main Street North Bay ON",
            "456 Elm Street Sudbury ON",
            "conflicting_locality",
        ),
    ],
)
def test_ambiguous_or_out_of_area_no_comma_routes_require_review(
    client: TestClient,
    service_type: str,
    pickup_address: str,
    dropoff_address: str,
    expected_reason: str,
) -> None:
    _assert_review_required(
        client,
        service_type,
        pickup_address,
        dropoff_address,
        expected_reason,
    )


def test_small_move_surrounding_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "small_move", "North Bay", "Callander", "conflicting_locality")


def test_small_move_out_of_town_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "small_move", "North Bay", "Sudbury", "conflicting_locality")


def test_small_move_unknown_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "small_move", "10 Road", "20 Avenue", "unclassified_locality")


def test_small_move_conflicting_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "small_move", "North Bay", "20 Avenue", "conflicting_locality")


def test_item_delivery_strict_north_bay_route_is_authoritative(client: TestClient) -> None:
    _assert_authoritative(client, "item_delivery")


def test_item_delivery_surrounding_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "item_delivery", "North Bay", "Callander", "conflicting_locality")


def test_item_delivery_out_of_town_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "item_delivery", "North Bay", "Sudbury", "conflicting_locality")


def test_item_delivery_unknown_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "item_delivery", "Sudbury", "Ottawa", "unclassified_locality")


def test_item_delivery_conflicting_route_requires_review(client: TestClient) -> None:
    _assert_review_required(client, "item_delivery", "10 Road", "North Bay", "conflicting_locality")


def test_public_route_travel_zone_is_ignored(client: TestClient) -> None:
    response = client.post(
        "/quote/calculate",
        json=_payload(service_type="small_move", travel_zone="out_of_town"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["travel_zone"] == "in_town"
    assert body["request"]["route_classification"]["source"] == "backend_address_locality_v1"


def test_direct_api_in_town_override_cannot_change_review_result(client: TestClient) -> None:
    response = client.post(
        "/quote/calculate",
        json=_payload(
            pickup_address="123 Main Street, North Bay, ON",
            dropoff_address="456 Elm Street, Sudbury, ON",
            travel_zone="in_town",
        ),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "review_required"
    assert body["request"]["route_classification"]["travel_zone"] is None
    assert "accept_token" not in body


def test_public_route_calibration_fields_are_forbidden(client: TestClient) -> None:
    payload = _payload()
    payload["route_distance_km"] = 1
    payload["route_duration_minutes"] = 1

    response = client.post("/quote/calculate", json=payload)

    assert response.status_code == 422
    assert "quote_id" not in response.json()


def test_authoritative_route_passes_only_in_town_to_quote_engine(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_calculate_quote = quote_service.calculate_quote
    travel_zones: list[str] = []

    def capture_travel_zone(**kwargs):
        travel_zones.append(str(kwargs.get("travel_zone")))
        return original_calculate_quote(**kwargs)

    monkeypatch.setattr(quote_service, "calculate_quote", capture_travel_zone)
    response = client.post(
        "/quote/calculate",
        json=_payload(travel_zone="surrounding"),
    )

    assert response.status_code == 200
    assert travel_zones
    assert set(travel_zones) == {"in_town"}


def test_review_route_never_calls_quote_engine(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(**_kwargs):
        raise AssertionError("review-required routes must not call calculate_quote")

    monkeypatch.setattr(quote_service, "calculate_quote", fail_if_called)

    response = client.post(
        "/quote/calculate",
        json=_payload(pickup_address="North Bay", dropoff_address="Sudbury"),
    )

    assert response.status_code == 202
    assert response.json()["status"] == "review_required"


def test_classifier_failure_requires_review_without_engine_call(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_classifier(_payload):
        raise RuntimeError("classifier unavailable")

    def fail_if_called(**_kwargs):
        raise AssertionError("classifier failures must not call calculate_quote")

    monkeypatch.setattr(quote_service, "_classify_public_route", fail_classifier)
    monkeypatch.setattr(quote_service, "calculate_quote", fail_if_called)

    response = client.post("/quote/calculate", json=_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["request"]["route_classification"]["reason"] == "classification_error"
    assert "accept_token" not in body


def test_review_request_and_classification_are_persisted(client: TestClient) -> None:
    body = _assert_review_required(
        client,
        "small_move",
        "123 Main Street, North Bay, ON",
        "456 Elm Street, Sudbury, ON",
        "conflicting_locality",
    )

    stored = get_quote_record(body["quote_id"])
    assert stored is not None
    assert stored["request"]["service_type"] == "small_move"
    assert stored["request"]["route_classification"] == {
        "status": "review_required",
        "source": "backend_address_locality_v1",
        "reason": "conflicting_locality",
        "travel_zone": None,
    }


def test_review_response_has_no_total_or_accept_token(client: TestClient) -> None:
    body = _assert_review_required(
        client,
        "item_delivery",
        "10 Unknown Road",
        "20 Unknown Avenue",
        "unclassified_locality",
    )

    assert "accept_token" not in body
    for total_field in ("cash_total_cad", "emt_total_cad", "total_cad", "total"):
        assert total_field not in body
        assert total_field not in body["response"]


def test_admin_review_detail_surfaces_route_without_repricing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = client.post(
        "/quote/calculate",
        json=_payload(pickup_address="North Bay", dropoff_address="Sudbury"),
    )
    assert response.status_code == 202

    def fail_if_called(**_kwargs):
        raise AssertionError("admin detail must not reprice a review-required route")

    monkeypatch.setattr(quote_service, "calculate_quote", fail_if_called)
    detail = quote_service.load_admin_quote_detail(response.json()["quote_id"])

    summary = detail["quote_risk_summary"]
    assert summary["risk_level"] == "high"
    assert summary["suggested_action"] == "owner_review_before_approving"
    assert "Pickup: North Bay" in summary["reasons"]
    assert "Drop-off: Sudbury" in summary["reasons"]
    assert summary["pricing_caution"] == "no_authoritative_total_until_route_is_confirmed"


def test_review_quote_cannot_be_reviewed_accepted_or_booked(client: TestClient) -> None:
    response = client.post(
        "/quote/calculate",
        json=_payload(pickup_address="North Bay", dropoff_address="Sudbury"),
    )
    assert response.status_code == 202
    quote_id = response.json()["quote_id"]

    review = client.get(
        f"/quote/{quote_id}/view",
        headers={"Authorization": "Bearer not-issued"},
    )
    assert review.status_code == 401

    decision = client.post(
        f"/quote/{quote_id}/decision",
        json={"action": "accept", "accept_token": "not-issued"},
    )
    assert decision.status_code == 401

    booking = client.post(
        f"/quote/{quote_id}/booking",
        json={
            "booking_token": "not-issued",
            "requested_job_date": "2099-01-01",
            "requested_time_window": "flexible",
        },
    )
    assert booking.status_code == 404
    assert booking.json()["detail"] == "Quote request not found. Accept the quote first."


def _assert_missing_route_address_rejected(client: TestClient, missing_field: str) -> None:
    payload = _payload()
    payload[missing_field] = None

    response = client.post("/quote/calculate", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "pickup_address and dropoff_address are required"


def test_route_missing_pickup_is_rejected_without_storage(client: TestClient) -> None:
    _assert_missing_route_address_rejected(client, "pickup_address")


def test_route_missing_dropoff_is_rejected_without_storage(client: TestClient) -> None:
    _assert_missing_route_address_rejected(client, "dropoff_address")


def test_legacy_saved_quote_review_and_acceptance_still_work(client: TestClient) -> None:
    calculate = client.post("/quote/calculate", json=_haul_payload())

    assert calculate.status_code == 200
    quote = calculate.json()
    assert "authoritative" not in quote
    review = client.get(
        f"/quote/{quote['quote_id']}/view",
        headers={"Authorization": f"Bearer {quote['accept_token']}"},
    )
    assert review.status_code == 200
    assert review.json()["quote_id"] == quote["quote_id"]

    decision = client.post(
        f"/quote/{quote['quote_id']}/decision",
        json={"action": "accept", "accept_token": quote["accept_token"]},
    )
    assert decision.status_code == 200
    assert decision.json()["ok"] is True
    assert decision.json()["booking_token"]


def test_existing_accepted_quote_remains_unchanged(client: TestClient) -> None:
    calculate = client.post("/quote/calculate", json=_haul_payload())
    assert calculate.status_code == 200
    quote = calculate.json()
    decision = client.post(
        f"/quote/{quote['quote_id']}/decision",
        json={"action": "accept", "accept_token": quote["accept_token"]},
    )
    assert decision.status_code == 200
    before = get_quote_record(quote["quote_id"])

    review = client.post(
        "/quote/calculate",
        json=_payload(pickup_address="North Bay", dropoff_address="Sudbury"),
    )
    assert review.status_code == 202

    after = get_quote_record(quote["quote_id"])
    assert after == before


def test_authenticated_gpt_explicit_zone_remains_compatible(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_calculate_quote = quote_service.calculate_quote
    travel_zones: list[str] = []

    def capture_travel_zone(**kwargs):
        travel_zones.append(str(kwargs.get("travel_zone")))
        return original_calculate_quote(**kwargs)

    monkeypatch.setenv("GPT_INTERNAL_API_TOKEN", "route-test-gpt-token")
    monkeypatch.setattr(quote_service, "calculate_quote", capture_travel_zone)
    clear_gpt_quote_rate_limit_state()
    try:
        response = client.post(
            "/api/gpt/quote",
            headers={"Authorization": "Bearer route-test-gpt-token"},
            json={
                "service_type": "small_move",
                "description": "Internal route compatibility check",
                "pickup_address": "North Bay",
                "dropoff_address": "Sudbury",
                "estimated_hours": 2.0,
                "crew_size": 2,
                "travel_zone": "out_of_town",
            },
        )
    finally:
        clear_gpt_quote_rate_limit_state()

    assert response.status_code == 200
    assert response.json()["normalized_service_type"] == "small_move"
    assert travel_zones
    assert set(travel_zones) == {"out_of_town"}


def test_non_route_public_travel_zone_behavior_is_unchanged(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_calculate_quote = quote_service.calculate_quote
    travel_zones: list[str] = []

    def capture_travel_zone(**kwargs):
        travel_zones.append(str(kwargs.get("travel_zone")))
        return original_calculate_quote(**kwargs)

    monkeypatch.setattr(quote_service, "calculate_quote", capture_travel_zone)
    response = client.post(
        "/quote/calculate",
        json=_haul_payload(travel_zone="out_of_town"),
    )

    assert response.status_code == 200
    assert "authoritative" not in response.json()
    assert travel_zones
    assert set(travel_zones) == {"out_of_town"}
