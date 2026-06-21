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
from app.services.quote_risk_scoring import (
    build_quote_risk_advisory,
    build_quote_risk_assessment,
    build_quote_risk_summary,
)
from app.storage import (
    get_quote_record,
    get_quote_request_by_quote_id,
    list_attachments,
    load_customer_history_context,
    save_quote,
)

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
_STRUCTURED_INTAKE_FIELDS = (
    "stairs_count",
    "floor_count",
    "basement_or_inside_removal",
    "demolition_ripout",
    "construction_debris_type",
    "dense_material_type",
    "mixed_load",
    "contains_scrap",
    "contains_garbage",
    "has_refrigerant_appliance",
    "appliance_type",
    "weather_protection_required",
)
_STRUCTURED_INTAKE_SUPPLIED_KEY = "_structured_intake_fields_supplied"
_DEMOLITION_PRICING_CONTEXT_FIELDS = (
    "stairs_count",
    "floor_count",
    "basement_or_inside_removal",
    "demolition_ripout",
    "construction_debris_type",
    "dense_material_type",
)
_STRUCTURED_ACCESS_PRICING_FIELDS = (
    "stairs_count",
    "floor_count",
    "basement_or_inside_removal",
)
_ROUTE_CALIBRATION_FIELDS = (
    "route_distance_km",
    "route_duration_minutes",
)
LEAD_SOURCE_LABELS = {
    "facebook": "Facebook",
    "google": "Google",
    "referral": "Referral",
    "marketplace": "Marketplace",
    "repeat_customer": "Repeat customer",
    "other": "Other",
    "unknown": "Unknown",
}


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


def normalize_lead_source(value: Any) -> str:
    if value is None:
        return "unknown"
    normalized = str(value).strip()
    if not normalized:
        return "unknown"
    if normalized not in LEAD_SOURCE_LABELS:
        raise HTTPException(status_code=400, detail="Invalid lead_source.")
    return normalized


def _lead_source_metadata(value: Any) -> dict[str, str]:
    try:
        normalized = normalize_lead_source(value)
    except HTTPException:
        normalized = "unknown"
    return {"value": normalized, "label": LEAD_SOURCE_LABELS[normalized]}


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
    inputs = {
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
    pricing_context_fields = (
        _DEMOLITION_PRICING_CONTEXT_FIELDS
        if str(service_type or "").strip().lower() == "demolition"
        else _STRUCTURED_ACCESS_PRICING_FIELDS
    )
    for field in pricing_context_fields:
        if field in request_payload:
            inputs[field] = request_payload.get(field)
    for field in _ROUTE_CALIBRATION_FIELDS:
        if field in request_payload:
            inputs[field] = request_payload.get(field)
    return inputs


def _structured_intake_values(request_payload: dict[str, Any]) -> dict[str, Any]:
    supplied = request_payload.get(_STRUCTURED_INTAKE_SUPPLIED_KEY)
    if isinstance(supplied, (list, tuple, set)):
        field_names = [field for field in _STRUCTURED_INTAKE_FIELDS if field in supplied]
    else:
        field_names = [field for field in _STRUCTURED_INTAKE_FIELDS if field in request_payload]
    return {field: request_payload.get(field) for field in field_names}


def build_quote_artifacts(request_payload: dict[str, Any]) -> dict[str, Any]:
    _validate_quote_boundary(request_payload)
    lead_source = normalize_lead_source(request_payload.get("lead_source"))
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
        "lead_source": lead_source,
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
    for field in _ROUTE_CALIBRATION_FIELDS:
        if field in request_payload:
            normalized_request[field] = request_payload.get(field)
    normalized_request.update(_structured_intake_values(request_payload))

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
    quote_risk_advisory = build_quote_risk_advisory(
        {
            **normalized_request,
            "_engine_internal": engine_quote.get("_internal"),
        }
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
        "quote_risk_advisory": quote_risk_advisory,
    }


def _gpt_request_to_quote_payload(request_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "service_type": request_payload.get("service_type"),
        "description": request_payload.get("description"),
        "job_description_customer": request_payload.get("description"),
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
        "load_mode": request_payload.get("load_mode", "standard"),
        "stairs_count": request_payload.get("stairs_count"),
        "floor_count": request_payload.get("floor_count"),
        "basement_or_inside_removal": request_payload.get("basement_or_inside_removal"),
        "demolition_ripout": request_payload.get("demolition_ripout"),
        "construction_debris_type": request_payload.get("construction_debris_type"),
        "dense_material_type": request_payload.get("dense_material_type"),
    }


def build_gpt_quote_response(request_payload: dict[str, Any]) -> dict[str, Any]:
    quote_artifacts = build_quote_artifacts(_gpt_request_to_quote_payload(request_payload))
    assessment = quote_artifacts.get("internal_risk_assessment") or {}
    advisory = quote_artifacts.get("quote_risk_advisory")
    summary = build_quote_risk_summary(
        quote_artifacts["normalized_request"],
        advisory if isinstance(advisory, dict) else None,
        assessment if isinstance(assessment, dict) else None,
    )
    response = quote_artifacts["response"]
    risk_flags_raw = assessment.get("risk_flags")
    risk_flags = [str(flag) for flag in risk_flags_raw] if isinstance(risk_flags_raw, list) else []

    return {
        "cash_total_cad": float(response["cash_total_cad"]),
        "emt_total_cad": float(response["emt_total_cad"]),
        "disclaimer": str(response["disclaimer"]),
        "normalized_service_type": str(quote_artifacts["normalized_request"]["service_type"]),
        "confidence_level": str(assessment.get("confidence_level") or ""),
        "risk_flags": risk_flags,
        "quote_risk_advisory": advisory,
        "quote_risk_summary": summary,
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


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _quote_risk_summary_request_context(
    *,
    quote_id: str,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    context = dict(request_payload)

    quote_request = get_quote_request_by_quote_id(quote_id)
    if quote_request:
        requested_job_date = quote_request.get("requested_job_date")
        requested_time_window = quote_request.get("requested_time_window")
        if _has_text(requested_job_date):
            context["requested_job_date"] = requested_job_date
        if _has_text(requested_time_window):
            context["requested_time_window"] = requested_time_window
        context["booking_submitted"] = bool(_has_text(requested_job_date) or _has_text(requested_time_window))

    attachments = list_attachments(quote_id=quote_id, limit=50)
    attachment_count = len(attachments)
    context["attachment_count"] = attachment_count
    context["photo_count"] = attachment_count
    context["photos_uploaded"] = attachment_count > 0

    return context


def load_admin_quote_detail(quote_id: str) -> dict[str, Any]:
    quote = get_quote_record(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")

    internal_risk_assessment: dict[str, Any] | None = None
    quote_risk_advisory: dict[str, Any] | None = None
    quote_risk_summary: dict[str, Any] | None = None
    request_payload = quote.get("request")
    safe_request_payload = request_payload if isinstance(request_payload, dict) else {}
    try:
        if not isinstance(request_payload, dict):
            raise TypeError("Saved quote request is not a structured object.")
        artifacts = build_quote_artifacts(dict(request_payload))
        assessment = artifacts.get("internal_risk_assessment")
        if isinstance(assessment, dict):
            internal_risk_assessment = assessment
        advisory = artifacts.get("quote_risk_advisory")
        if isinstance(advisory, dict):
            quote_risk_advisory = advisory
        quote_risk_summary_request = _quote_risk_summary_request_context(
            quote_id=quote_id,
            request_payload=request_payload,
        )
        quote_risk_summary = build_quote_risk_summary(
            quote_risk_summary_request,
            quote_risk_advisory,
            internal_risk_assessment,
        )
    except Exception:
        logger.warning(
            "Failed to re-derive internal risk assessment for admin quote detail %s",
            quote_id,
            exc_info=True,
        )

    return {
        **quote,
        "lead_source": _lead_source_metadata(safe_request_payload.get("lead_source")),
        "customer_history": load_customer_history_context(
            quote_id=quote_id,
            customer_phone=safe_request_payload.get("customer_phone"),
        ),
        "internal_risk_assessment": internal_risk_assessment,
        "quote_risk_advisory": quote_risk_advisory,
        "quote_risk_summary": quote_risk_summary,
    }
