from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.quote_engine import calculate_quote
from app.storage import save_quote


def build_and_save_quote(request_payload: dict[str, Any], now_iso: str) -> dict[str, Any]:
    requested_service_type = str(request_payload.get("service_type", "")).strip()

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
    }

    # Generate accept_token for this quote (before saving)
    accept_token = str(uuid4())

    quote = {
        "quote_id": str(uuid4()),
        "created_at": now_iso,
        "request": normalized_request,
        "response": {
            "cash_total_cad": float(engine_quote["total_cash_cad"]),
            "emt_total_cad": float(engine_quote["total_emt_cad"]),
            "disclaimer": str(engine_quote["disclaimer"]),
        },
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
