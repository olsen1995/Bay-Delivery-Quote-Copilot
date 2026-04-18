from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.quote_engine import (
    ACCESS_DIFFICULTY_ADDERS,
    TRAVEL_ZONE_ADDERS,
    _has_fixed_bulky_item_signal,
    _normalize_service_type,
    calculate_quote,
    load_config,
)
from app.services.quote_risk_scoring import build_quote_risk_assessment
from app.storage import get_quote_record, save_quote

logger = logging.getLogger(__name__)

_PHONE_ALLOWED = re.compile(r"^[0-9().+\-\s]+$")
_PHONE_VALIDATION_MSG = (
    "Please enter a valid 10-digit phone number. "
    "You can include spaces, dashes, parentheses, or +1."
)
_HAUL_AWAY_LOAD_DETAIL_MSG = (
    "Please add at least one load detail so we can estimate your junk removal properly. "
    "Examples: bags, trailer space used, mattresses, box springs, or dense materials."
)


def _normalize_customer_phone(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not _PHONE_ALLOWED.fullmatch(trimmed):
        return None
    digits = re.sub(r"\D", "", trimmed)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def _normalize_load_mode(load_mode: Any) -> str:
    mode = str(load_mode or "").strip().lower()
    if mode == "space_fill":
        return "space_fill"
    return "standard"


def _normalized_service_type_or_400(config: dict[str, Any], request_payload: dict[str, Any]) -> str:
    requested_service_type = str(request_payload.get("service_type", "") or "").strip()
    normalized_service_type = _normalize_service_type(config, requested_service_type)
    services = config.get("services") or {}
    if normalized_service_type not in services:
        raise HTTPException(status_code=400, detail="Invalid service_type.")
    return normalized_service_type


def _validate_enum_input(
    request_payload: dict[str, Any],
    *,
    field_name: str,
    allowed_values: set[str],
    default_value: str,
) -> str:
    raw_value = request_payload.get(field_name, default_value)
    if raw_value is None and field_name not in request_payload:
        raw_value = default_value
    elif raw_value is None:
        raw_value = default_value
    value = str(raw_value).strip().lower()
    if value not in allowed_values:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}.")
    request_payload[field_name] = value
    return value


def _allowed_haul_away_trailer_fill_values(config: dict[str, Any]) -> set[str]:
    service_conf = ((config.get("services") or {}).get("haul_away") or {})
    allowed_values = {
        str(key).strip().lower()
        for key in ((service_conf.get("trailer_fill_floor_anchors_cad") or {}).keys())
        if str(key).strip()
    }
    trailer_class_anchors = service_conf.get("trailer_class_fill_floor_anchors_cad") or {}
    if isinstance(trailer_class_anchors, dict):
        for fill_map in trailer_class_anchors.values():
            if not isinstance(fill_map, dict):
                continue
            allowed_values.update(
                str(key).strip().lower()
                for key in fill_map.keys()
                if str(key).strip()
            )
    return allowed_values


def _validate_haul_away_structure(request_payload: dict[str, Any], *, config: dict[str, Any]) -> None:
    signal_text = " ".join(
        part.strip()
        for part in (
            str(request_payload.get("job_description_customer", "") or ""),
            str(request_payload.get("description", "") or ""),
        )
        if part and str(part).strip()
    )
    has_bulky_signal = _has_fixed_bulky_item_signal(
        signal_text,
        int(request_payload.get("mattresses_count", 0)),
        int(request_payload.get("box_springs_count", 0)),
    )
    trailer_fill_value = str(request_payload.get("trailer_fill_estimate", "") or "").strip().lower()
    has_valid_trailer_fill_signal = trailer_fill_value in _allowed_haul_away_trailer_fill_values(config)
    has_load_detail = any(
        (
            int(request_payload.get("garbage_bag_count", 0)) > 0,
            has_valid_trailer_fill_signal,
            bool(request_payload.get("has_dense_materials", False)),
            has_bulky_signal,
        )
    )
    if not has_load_detail:
        raise HTTPException(status_code=400, detail=_HAUL_AWAY_LOAD_DETAIL_MSG)


def _validate_quote_boundary(request_payload: dict[str, Any]) -> None:
    config = load_config()
    normalized_service_type = _normalized_service_type_or_400(config, request_payload)
    _validate_enum_input(
        request_payload,
        field_name="access_difficulty",
        allowed_values=set(ACCESS_DIFFICULTY_ADDERS),
        default_value="normal",
    )
    _validate_enum_input(
        request_payload,
        field_name="travel_zone",
        allowed_values=set(TRAVEL_ZONE_ADDERS),
        default_value="in_town",
    )
    scrap_pickup_rates = ((config.get("services") or {}).get("scrap_pickup", {}).get("flat_rates") or {})
    _validate_enum_input(
        request_payload,
        field_name="scrap_pickup_location",
        allowed_values=set(scrap_pickup_rates),
        default_value="curbside",
    )
    if normalized_service_type == "haul_away":
        _validate_haul_away_structure(request_payload, config=config)


def _quote_engine_inputs(
    request_payload: dict[str, Any],
    *,
    service_type: str,
    load_mode: str,
) -> dict[str, Any]:
    return {
        "service_type": service_type,
        "hours": float(request_payload.get("estimated_hours", 0.0)),
        "crew_size": int(request_payload.get("crew_size", 1)),
        "garbage_bag_count": int(request_payload.get("garbage_bag_count", 0)),
        "bag_type": request_payload.get("bag_type"),
        "trailer_fill_estimate": request_payload.get("trailer_fill_estimate"),
        "trailer_class": request_payload.get("trailer_class"),
        "mattresses_count": int(request_payload.get("mattresses_count", 0)),
        "box_springs_count": int(request_payload.get("box_springs_count", 0)),
        "scrap_pickup_location": str(request_payload.get("scrap_pickup_location", "curbside")),
        "travel_zone": str(request_payload.get("travel_zone", "in_town")),
        "access_difficulty": str(request_payload.get("access_difficulty", "normal")),
        "has_dense_materials": bool(request_payload.get("has_dense_materials", False)),
        "load_mode": load_mode,
        "description": request_payload.get("description"),
        "job_description_customer": request_payload.get("job_description_customer"),
        "pickup_address": request_payload.get("pickup_address"),
        "dropoff_address": request_payload.get("dropoff_address"),
    }


def build_quote_artifacts(request_payload: dict[str, Any]) -> dict[str, Any]:
    _validate_quote_boundary(request_payload)
    requested_service_type = str(request_payload.get("service_type", "")).strip()
    normalized_load_mode = _normalize_load_mode(request_payload.get("load_mode"))
    baseline_engine_quote = calculate_quote(
        **_quote_engine_inputs(
            request_payload,
            service_type=requested_service_type,
            load_mode=normalized_load_mode,
        )
    )

    # Validate required route fields using normalized service type returned by the engine.
    engine_service_type = str(baseline_engine_quote.get("service_type", "")).strip().lower()
    if engine_service_type in {"small_move", "item_delivery"}:
        if not request_payload.get("pickup_address") or not request_payload.get("dropoff_address"):
            raise HTTPException(status_code=400, detail="pickup_address and dropoff_address are required")

    normalized_request = {
        "customer_name": request_payload.get("customer_name"),
        "customer_phone": request_payload.get("customer_phone"),
        "job_address": request_payload.get("job_address"),
        "job_description_customer": request_payload.get("job_description_customer") or request_payload.get("description"),
        "description": request_payload.get("description") or request_payload.get("job_description_customer"),
        "service_type": baseline_engine_quote["service_type"],
        "payment_method": request_payload.get("payment_method"),
        "pickup_address": request_payload.get("pickup_address"),
        "dropoff_address": request_payload.get("dropoff_address"),
        "estimated_hours": float(request_payload.get("estimated_hours", 0.0)),
        "crew_size": int(request_payload.get("crew_size", 1)),
        "garbage_bag_count": int(request_payload.get("garbage_bag_count", 0)),
        "bag_type": request_payload.get("bag_type"),
        "trailer_fill_estimate": request_payload.get("trailer_fill_estimate"),
        "trailer_class": request_payload.get("trailer_class"),
        "mattresses_count": int(request_payload.get("mattresses_count", 0)),
        "box_springs_count": int(request_payload.get("box_springs_count", 0)),
        "scrap_pickup_location": request_payload.get("scrap_pickup_location", "curbside"),
        "travel_zone": request_payload.get("travel_zone", "in_town"),
        "access_difficulty": request_payload.get("access_difficulty", "normal"),
        "has_dense_materials": bool(request_payload.get("has_dense_materials", False)),
        "load_mode": normalized_load_mode,
    }

    internal_risk_assessment = build_quote_risk_assessment(
        normalized_request=normalized_request,
        engine_quote=baseline_engine_quote,
    )
    engine_quote = calculate_quote(
        **_quote_engine_inputs(
            normalized_request,
            service_type=normalized_request["service_type"],
            load_mode=normalized_request["load_mode"],
        ),
        internal_risk_assessment=internal_risk_assessment,
    )
    response = {
        "cash_total_cad": float(engine_quote["total_cash_cad"]),
        "emt_total_cad": float(engine_quote["total_emt_cad"]),
        "disclaimer": str(engine_quote["disclaimer"]),
    }

    return {
        "normalized_request": normalized_request,
        "response": response,
        "engine_quote": engine_quote,
        "internal_risk_assessment": internal_risk_assessment,
    }


def build_and_save_quote(request_payload: dict[str, Any], now_iso: str) -> dict[str, Any]:
    normalized_customer_phone = _normalize_customer_phone(request_payload.get("customer_phone"))
    if normalized_customer_phone is None:
        raise HTTPException(status_code=400, detail=_PHONE_VALIDATION_MSG)

    normalized_payload = dict(request_payload)
    normalized_payload["customer_phone"] = normalized_customer_phone

    quote_artifacts = build_quote_artifacts(normalized_payload)

    # Generate accept_token for this quote (before saving)
    accept_token = str(uuid4())

    quote = {
        "quote_id": str(uuid4()),
        "created_at": now_iso,
        "request": quote_artifacts["normalized_request"],
        "response": quote_artifacts["response"],
    }

    save_quote(
        {
            "quote_id": quote["quote_id"],
            "created_at": quote["created_at"],
            "request": quote["request"],
            "response": quote["response"],
            "accept_token": accept_token,
        }
    )

    return {
        **quote,
        "accept_token": accept_token,
    }


def load_admin_quote_detail(quote_id: str) -> dict[str, Any]:
    quote = get_quote_record(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")

    internal_risk_assessment: dict[str, Any] | None = None
    try:
        request_payload = quote.get("request")
        if not isinstance(request_payload, dict):
            raise TypeError("Saved quote request is not a structured object.")
        artifacts = build_quote_artifacts(dict(request_payload))
        assessment = artifacts.get("internal_risk_assessment")
        if isinstance(assessment, dict):
            internal_risk_assessment = assessment
    except Exception:
        logger.warning(
            "Failed to re-derive internal risk assessment for admin quote detail %s",
            quote_id,
            exc_info=True,
        )

    return {
        **quote,
        "internal_risk_assessment": internal_risk_assessment,
    }
