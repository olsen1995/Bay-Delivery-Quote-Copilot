from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.quote_engine import calculate_quote
from app.services.quote_risk_scoring import build_quote_risk_assessment
from app.storage import get_quote_record, save_quote

logger = logging.getLogger(__name__)

_PHONE_ALLOWED = re.compile(r"^[0-9().+\-\s]+$")
_PHONE_VALIDATION_MSG = (
    "Please enter a valid 10-digit phone number. "
    "You can include spaces, dashes, parentheses, or +1."
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


def build_quote_artifacts(request_payload: dict[str, Any]) -> dict[str, Any]:
    requested_service_type = str(request_payload.get("service_type", "")).strip()
    normalized_load_mode = _normalize_load_mode(request_payload.get("load_mode"))

    engine_quote = calculate_quote(
        service_type=requested_service_type,
        hours=float(request_payload.get("estimated_hours", 0.0)),
        crew_size=int(request_payload.get("crew_size", 1)),
        garbage_bag_count=int(request_payload.get("garbage_bag_count", 0)),
        bag_type=request_payload.get("bag_type"),
        trailer_fill_estimate=request_payload.get("trailer_fill_estimate"),
        trailer_class=request_payload.get("trailer_class"),
        mattresses_count=int(request_payload.get("mattresses_count", 0)),
        box_springs_count=int(request_payload.get("box_springs_count", 0)),
        scrap_pickup_location=str(request_payload.get("scrap_pickup_location", "curbside")),
        travel_zone=str(request_payload.get("travel_zone", "in_town")),
        access_difficulty=str(request_payload.get("access_difficulty", "normal")),
        has_dense_materials=bool(request_payload.get("has_dense_materials", False)),
        load_mode=normalized_load_mode,
    )

    # Validate required route fields using normalized service type returned by the engine.
    engine_service_type = str(engine_quote.get("service_type", "")).strip().lower()
    if engine_service_type in {"small_move", "item_delivery"}:
        if not request_payload.get("pickup_address") or not request_payload.get("dropoff_address"):
            raise HTTPException(status_code=400, detail="pickup_address and dropoff_address are required")

    normalized_request = {
        "customer_name": request_payload.get("customer_name"),
        "customer_phone": request_payload.get("customer_phone"),
        "job_address": request_payload.get("job_address"),
        "job_description_customer": request_payload.get("job_description_customer") or request_payload.get("description"),
        "service_type": engine_quote["service_type"],
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

    response = {
        "cash_total_cad": float(engine_quote["total_cash_cad"]),
        "emt_total_cad": float(engine_quote["total_emt_cad"]),
        "disclaimer": str(engine_quote["disclaimer"]),
    }
    internal_risk_assessment = build_quote_risk_assessment(
        normalized_request=normalized_request,
        engine_quote=engine_quote,
    )

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
