# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Annotated
from uuid import uuid4

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.storage import (
    init_db,
    save_quote,
)

# =========================
# VERSION
# =========================

APP_VERSION = "0.8.2"

app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version=APP_VERSION,
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + job tracking.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

CAD = "CAD"

# =========================
# Frontend (serve static/index.html at root)
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (one level above /app)
INDEX_HTML_PATH = BASE_DIR / "static" / "index.html"


@app.get("/")
def root():
    """
    Serve the customer/internal quote page.
    Keeps API routes like /health working normally.
    """
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Missing frontend file: {INDEX_HTML_PATH.as_posix()}",
        )
    return FileResponse(INDEX_HTML_PATH)


# =========================
# Service Types
# =========================

class ServiceType(str, Enum):
    dump_run = "dump_run"
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"
    item_delivery = "item_delivery"
    demolition = "demolition"

    @classmethod
    def normalize(cls, value: str) -> "ServiceType":
        # allow legacy alias
        if value == "small_moving":
            return cls.small_move
        return cls(value)


def normalize_service_type(value: Any) -> Any:
    if isinstance(value, str):
        return ServiceType.normalize(value)
    return value


# =========================
# Schemas
# =========================

NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]


class QuoteRequest(BaseModel):
    service_type: ServiceType = ServiceType.dump_run

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    # description captured from the form (customer-facing)
    job_description_customer: Optional[str] = None

    # (kept for future internal/admin tools)
    job_description_internal: Optional[str] = None

    # core inputs
    distance_km: Optional[NonNegFloat] = None
    estimated_hours: NonNegFloat = 0.0
    requires_two_workers: bool = False

    # disposal
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    # dump run addon
    garbage_bags_count: NonNegInt = 0

    # access/difficulty toggles
    has_stairs: bool = False
    has_tight_corners: bool = False
    has_long_carry: bool = False
    is_apartment_condo: bool = False
    has_elevator: bool = False


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD
    service_type: ServiceType
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat


# =========================
# Pricing / Rules
# =========================

MINIMUM_CASH_CAD = 50.0
EMT_HST_RATE = 0.13

# Labour baseline: simple for now
DEFAULT_RATE_PER_HOUR_CAD = 60.0

# Disposal pricing (your rule)
DISPOSAL_EACH_CAD = 50.0  # mattress or box spring

# Dump run garbage bag pricing
GARBAGE_BAG_EACH_CAD = 7.50

# Access/difficulty surcharges (tunable)
STAIRS_CAD = 20.0
TIGHT_CORNERS_CAD = 15.0
LONG_CARRY_CAD = 10.0
APARTMENT_CONDO_CAD = 10.0
ELEVATOR_OFFSET_CAD = -15.0  # reduces difficulty when apt+elevator


def _round_cash_to_nearest_5(x: float) -> float:
    # nearest $5 (not always up)
    return round(x / 5.0) * 5.0


def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    """
    Simple estimator:
      - base minimum
      - hourly labour (flat for now)
      - dump run: garbage bag add-on
      - disposal: mattresses/box springs @ $50 each
      - access/difficulty surcharges
      - cash rounded to nearest $5
      - EMT = cash + 13% HST (to cents)
    """
    # labour estimate
    hours_cost = float(req.estimated_hours) * DEFAULT_RATE_PER_HOUR_CAD

    # dump run bags add-on (only for dump_run)
    bags_cost = 0.0
    if req.service_type == ServiceType.dump_run and int(req.garbage_bags_count) > 0:
        bags_cost = int(req.garbage_bags_count) * GARBAGE_BAG_EACH_CAD

    # disposal (mattress + box spring)
    disposal_count = int(req.mattresses_count) + int(req.box_springs_count)
    disposal_cost = disposal_count * DISPOSAL_EACH_CAD

    # access/difficulty
    access_cost = 0.0
    if req.has_stairs:
        access_cost += STAIRS_CAD
    if req.has_tight_corners:
        access_cost += TIGHT_CORNERS_CAD
    if req.has_long_carry:
        access_cost += LONG_CARRY_CAD
    if req.is_apartment_condo:
        access_cost += APARTMENT_CONDO_CAD

    # elevator helps only when apartment/condo is true
    if req.is_apartment_condo and req.has_elevator:
        access_cost += ELEVATOR_OFFSET_CAD

    raw_cash = hours_cost + bags_cost + disposal_cost + access_cost

    # minimum charge
    cash = max(MINIMUM_CASH_CAD, raw_cash)

    # round cash to nearest $5 (Bay Delivery style)
    cash = _round_cash_to_nearest_5(cash)

    # EMT total (cents normal)
    emt = round(cash * (1.0 + EMT_HST_RATE), 2)

    return {
        "total_cash_cad": round(cash, 2),
        "total_emt_cad": emt,
    }


# =========================
# Routes
# =========================

@app.get("/health")
def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "base_address": os.getenv("BAYDELIVERY_BASE_ADDRESS"),
        "distance_autocalc_enabled": bool(os.getenv("GOOGLE_MAPS_API_KEY")),
    }


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest):
    result = calculate_quote(req)

    quote_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    # store full request (including description + access flags) so you can review later
    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=result["total_cash_cad"],
        request_obj=req.model_dump(),
        response_obj={
            "quote_id": quote_id,
            "created_at": created_at,
            "service_type": req.service_type.value,
            "total_cash_cad": result["total_cash_cad"],
            "total_emt_cad": result["total_emt_cad"],
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=result["total_cash_cad"],
        total_emt_cad=result["total_emt_cad"],
    )