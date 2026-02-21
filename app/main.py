# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Annotated
from uuid import uuid4

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

APP_VERSION = "0.9.0"

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
    """Serve the quote page."""
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Missing frontend file: {INDEX_HTML_PATH.as_posix()}",
        )
    return FileResponse(INDEX_HTML_PATH)


# =========================
# Business Rules
# =========================

HST_RATE_EMT = 0.13

# Minimums per service
MINIMUM_HAUL_AWAY_CAD = 50.0
MINIMUM_MOVING_CAD = 60.0
MINIMUM_DEMOLITION_CAD = 75.0
MINIMUM_OTHER_CAD = 50.0

# Travel minimum always (gas + wear)
MIN_GAS_CAD = 20.0
MIN_WEAR_CAD = 20.0

# Labour rates (internal defaults — tune later)
DEFAULT_PRIMARY_RATE_CAD = 20.0
DEFAULT_HELPER_RATE_CAD = 16.0

# Mattress/boxspring (internal only: included in total; customer sees note, not itemized $)
MATTRESS_FEE_EACH_CAD = 50.0
BOXSPRING_FEE_EACH_CAD = 50.0

# Haul-away disposal allowance (bag tiers; includes dump travel + margin)
BAG_TIER_SMALL_MAX = 5
BAG_TIER_MEDIUM_MAX = 15
BAG_TIER_SMALL_PRICE = 50.0
BAG_TIER_MEDIUM_PRICE = 80.0
BAG_TIER_LARGE_PRICE = 120.0

# Scrap pickup (flat rate)
SCRAP_CURBSIDE_PRICE = 0.0
SCRAP_INSIDE_PRICE = 30.0


def round_cash_to_nearest_5(x: float) -> float:
    """Cash: nearest $5."""
    return float(int((x + 2.5) // 5) * 5)


# =========================
# Service Types
# =========================

class ServiceType(str, Enum):
    haul_away = "haul_away"  # junk removal / dump run (same)
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"  # canonical internal value
    item_delivery = "item_delivery"
    demolition = "demolition"

    @classmethod
    def normalize(cls, value: str) -> "ServiceType":
        # Back-compat aliases
        aliases = {
            "dump_run": cls.haul_away,
            "junk_removal": cls.haul_away,
            "junk": cls.haul_away,
            "haulaway": cls.haul_away,
            "small_moving": cls.small_move,
        }
        if value in aliases:
            return aliases[value]
        return cls(value)


def normalize_service_type(value: Any) -> Any:
    if isinstance(value, str):
        return ServiceType.normalize(value)
    return value


class ScrapPickupLocation(str, Enum):
    curbside = "curbside"
    inside = "inside"


NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
PosInt = Annotated[int, Field(ge=1)]


# =========================
# Schemas
# =========================

class QuoteRequest(BaseModel):
    service_type: ServiceType = ServiceType.haul_away

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    # Customer/job info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    # Description (stored for admin review)
    description: Optional[str] = Field(
        None,
        description="Customer description of items / job details. Stored for admin review.",
    )

    # Core pricing inputs
    estimated_hours: NonNegFloat = 0.0

    # Crew: customer can set, but we enforce minimums by service
    crew_size: Optional[PosInt] = Field(
        None,
        description="Optional crew size. We clamp to service minimums.",
    )

    # Haul-away specific (optional)
    garbage_bag_count: NonNegInt = 0

    # Mattress / box spring (customer indicates quantity; we include in total, show note only)
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    # Scrap pickup specific
    scrap_pickup_location: ScrapPickupLocation = ScrapPickupLocation.curbside

    # Access flags (stored now, used later for smarter bumping)
    stairs: bool = False
    elevator: bool = False
    difficult_corner: bool = False


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD
    service_type: ServiceType

    # Customer-facing totals only
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat

    disclaimer: str


# =========================
# Quote Logic
# =========================


def _service_minimum(service_type: ServiceType) -> float:
    if service_type == ServiceType.haul_away:
        return MINIMUM_HAUL_AWAY_CAD
    if service_type == ServiceType.small_move:
        return MINIMUM_MOVING_CAD
    if service_type == ServiceType.demolition:
        return MINIMUM_DEMOLITION_CAD
    return MINIMUM_OTHER_CAD


def _service_min_crew(service_type: ServiceType) -> int:
    # Your guidance:
    # - haul_away: can be 1 (sometimes 2)
    # - moving: never below 2; default 3
    # - demolition: usually 2+
    if service_type == ServiceType.small_move:
        return 2
    if service_type == ServiceType.demolition:
        return 2
    return 1


def _service_default_crew(service_type: ServiceType) -> int:
    if service_type == ServiceType.small_move:
        return 3
    if service_type == ServiceType.demolition:
        return 4
    return 1


def _calc_travel_min() -> float:
    return float(MIN_GAS_CAD + MIN_WEAR_CAD)


def _calc_labor(estimated_hours: float, crew_size: int) -> float:
    """primary + (crew-1)*helper"""
    if estimated_hours <= 0:
        return 0.0
    hourly_total = DEFAULT_PRIMARY_RATE_CAD + max(0, crew_size - 1) * DEFAULT_HELPER_RATE_CAD
    return float(estimated_hours * hourly_total)


def _calc_haul_away_disposal(garbage_bag_count: int) -> float:
    # This is an internal allowance (dump is by yards, varies; we keep simple tiers).
    if garbage_bag_count <= 0:
        return 0.0
    if garbage_bag_count <= BAG_TIER_SMALL_MAX:
        return float(BAG_TIER_SMALL_PRICE)
    if garbage_bag_count <= BAG_TIER_MEDIUM_MAX:
        return float(BAG_TIER_MEDIUM_PRICE)
    return float(BAG_TIER_LARGE_PRICE)


def _calc_mattress_boxspring(m: int, b: int) -> float:
    return float(m * MATTRESS_FEE_EACH_CAD + b * BOXSPRING_FEE_EACH_CAD)


def _calc_scrap(location: ScrapPickupLocation) -> float:
    if location == ScrapPickupLocation.curbside:
        return float(SCRAP_CURBSIDE_PRICE)
    return float(SCRAP_INSIDE_PRICE)


def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    # -----------------------------
    # 1) Scrap pickup: hard lock
    # -----------------------------
    if req.service_type == ServiceType.scrap_pickup:
        cash_total = float(_calc_scrap(req.scrap_pickup_location))
        emt_total = round(cash_total * (1.0 + HST_RATE_EMT), 2)

        disclaimer = (
            "Scrap pickup is flat-rate: curbside is free (picked up next time we’re in the area); "
            "inside removal is $30. Cash is tax-free; EMT/e-transfer adds 13% HST."
        )

        return {
            "total_cash_cad": round(cash_total, 2),
            "total_emt_cad": round(emt_total, 2),
            "disclaimer": disclaimer,
            # Internal breakdown (stored only; not returned to customer)
            "_internal": {
                "crew_size": 1,
                "travel_min_cad": 0.0,
                "labor_cad": 0.0,
                "disposal_cad": 0.0,
                "mattress_boxspring_cad": 0.0,
                "scrap_cad": cash_total,
            },
        }

    # -----------------------------
    # 2) All other services
    # -----------------------------
    service_min = _service_minimum(req.service_type)

    min_crew = _service_min_crew(req.service_type)
    default_crew = _service_default_crew(req.service_type)

    crew = int(req.crew_size) if req.crew_size is not None else default_crew
    if crew < min_crew:
        crew = min_crew

    travel = _calc_travel_min()
    labor = _calc_labor(float(req.estimated_hours), crew)

    disposal = 0.0
    if req.service_type == ServiceType.haul_away:
        disposal = _calc_haul_away_disposal(int(req.garbage_bag_count))

    mattress_boxspring = _calc_mattress_boxspring(int(req.mattresses_count), int(req.box_springs_count))

    raw_cash = travel + labor + disposal + mattress_boxspring

    # enforce minimum per service
    cash_before_round = max(service_min, raw_cash)

    # cash: round to nearest $5
    cash_total = round_cash_to_nearest_5(cash_before_round)

    # EMT: cents are fine
    emt_total = round(cash_total * (1.0 + HST_RATE_EMT), 2)

    # Customer-facing disclaimer
    # (No dump fee line items. Mattress note allowed.)
    disclaimer = (
        "This estimate is based on the information provided and may change after an in-person view "
        "(stairs, heavy items, access, actual load size, multiple trips, etc.). "
        "Removal & disposal included (if required). "
        "Mattresses/box springs may have an additional disposal cost if included. "
        "Cash is tax-free; EMT/e-transfer adds 13% HST."
    )

    return {
        "total_cash_cad": round(cash_total, 2),
        "total_emt_cad": round(emt_total, 2),
        "disclaimer": disclaimer,
        # Internal breakdown (stored only; not returned to customer)
        "_internal": {
            "crew_size": int(crew),
            "travel_min_cad": round(travel, 2),
            "labor_cad": round(labor, 2),
            "disposal_cad": round(disposal, 2),
            "mattress_boxspring_cad": round(mattress_boxspring, 2),
            "scrap_cad": 0.0,
        },
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

    internal = result.get("_internal", {})

    # Store full request + internal breakdown for admin review later
    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=float(result["total_cash_cad"]),
        request_obj=req.model_dump(),
        response_obj={
            "quote_id": quote_id,
            "created_at": created_at,
            "currency": CAD,
            "service_type": req.service_type.value,
            "total_cash_cad": float(result["total_cash_cad"]),
            "total_emt_cad": float(result["total_emt_cad"]),
            "disclaimer": str(result["disclaimer"]),
            # keep internal breakdown stored, not returned
            "internal": internal,
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=float(result["total_cash_cad"]),
        total_emt_cad=float(result["total_emt_cad"]),
        disclaimer=str(result["disclaimer"]),
    )