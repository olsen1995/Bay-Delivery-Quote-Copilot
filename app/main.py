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
    """
    Serve the quote page.
    Keeps API routes like /health working normally.
    """
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

# Minimums per service (your call)
MINIMUM_DUMP_RUN_CAD = 50.0
MINIMUM_MOVING_CAD = 60.0
MINIMUM_DEMOLITION_CAD = 75.0
MINIMUM_OTHER_CAD = 50.0

# Travel minimum always (gas + wear)
MIN_GAS_CAD = 20.0
MIN_WEAR_CAD = 20.0

# Labour rates (internal defaults — you can tune later)
DEFAULT_PRIMARY_RATE_CAD = 20.0
DEFAULT_HELPER_RATE_CAD = 16.0

# Disposal
MATTRESS_FEE_EACH_CAD = 50.0
BOXSPRING_FEE_EACH_CAD = 50.0

# Dump run: bag tiers (includes dump travel + margin)
BAG_TIER_SMALL_MAX = 5
BAG_TIER_MEDIUM_MAX = 15
BAG_TIER_SMALL_PRICE = 50.0
BAG_TIER_MEDIUM_PRICE = 80.0
BAG_TIER_LARGE_PRICE = 120.0

# Scrap pickup
SCRAP_CURBSIDE_PRICE = 0.0
SCRAP_INSIDE_PRICE = 30.0

# Cash rounding (you don’t like $22.50 etc)
def round_cash_to_nearest_5(x: float) -> float:
    # nearest $5
    return float(int((x + 2.5) // 5) * 5)


# =========================
# Service Types
# =========================

class ServiceType(str, Enum):
    dump_run = "dump_run"
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"  # canonical internal value
    item_delivery = "item_delivery"
    demolition = "demolition"

    @classmethod
    def normalize(cls, value: str) -> "ServiceType":
        # Allow both 'small_move' and 'small_moving' externally.
        if value == "small_moving":
            return cls.small_move
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
    service_type: ServiceType = ServiceType.dump_run

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    # Customer/job info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    # Description (this is what we will eventually "scan" / refine with)
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

    # Dump run specific
    garbage_bag_count: NonNegInt = 0

    # Mattresses / boxsprings (shown explicitly to customer only if >0)
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

    # Minimal customer-facing totals
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat

    # helpful metadata for admin + debugging
    crew_size: int
    travel_min_cad: NonNegFloat
    labor_cad: NonNegFloat
    disposal_cad: NonNegFloat
    mattress_boxspring_cad: NonNegFloat
    scrap_cad: NonNegFloat

    disclaimer: str


# =========================
# Quote Logic
# =========================

def _service_minimum(service_type: ServiceType) -> float:
    if service_type == ServiceType.dump_run:
        return MINIMUM_DUMP_RUN_CAD
    if service_type == ServiceType.small_move:
        return MINIMUM_MOVING_CAD
    if service_type == ServiceType.demolition:
        return MINIMUM_DEMOLITION_CAD
    return MINIMUM_OTHER_CAD


def _service_min_crew(service_type: ServiceType) -> int:
    # Your guidance:
    # - dump_run: can be 1 (sometimes 2)
    # - moving: never below 2; default 3
    # - demolition: usually 2+; common 4 on big jobs (we set minimum 2, default 4)
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
    # Simple but realistic:
    # primary + (crew-1)*helper
    if estimated_hours <= 0:
        return 0.0
    hourly_total = DEFAULT_PRIMARY_RATE_CAD + max(0, crew_size - 1) * DEFAULT_HELPER_RATE_CAD
    return float(estimated_hours * hourly_total)


def _calc_dump_run_disposal(garbage_bag_count: int) -> float:
    if garbage_bag_count <= 0:
        # if it's a dump run, even 0 bags could be "junk items" — but we only apply this bag-tier
        # when they give us bags. Minimums + labour/travel cover the rest.
        return 0.0

    if garbage_bag_count <= BAG_TIER_SMALL_MAX:
        return float(BAG_TIER_SMALL_PRICE)
    if garbage_bag_count <= BAG_TIER_MEDIUM_MAX:
        return float(BAG_TIER_MEDIUM_PRICE)
    return float(BAG_TIER_LARGE_PRICE)


def _calc_mattress_boxspring(m: int, b: int) -> float:
    return float(m * MATTRESS_FEE_EACH_CAD + b * BOXSPRING_FEE_EACH_CAD)


def _calc_scrap(req: QuoteRequest) -> float:
    if req.service_type != ServiceType.scrap_pickup:
        return 0.0
    if req.scrap_pickup_location == ScrapPickupLocation.curbside:
        return float(SCRAP_CURBSIDE_PRICE)
    return float(SCRAP_INSIDE_PRICE)


def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    service_min = _service_minimum(req.service_type)

    min_crew = _service_min_crew(req.service_type)
    default_crew = _service_default_crew(req.service_type)

    crew = int(req.crew_size) if req.crew_size is not None else default_crew
    if crew < min_crew:
        crew = min_crew

    travel = _calc_travel_min()
    labor = _calc_labor(float(req.estimated_hours), crew)

    disposal = 0.0
    if req.service_type == ServiceType.dump_run:
        disposal = _calc_dump_run_disposal(int(req.garbage_bag_count))

    mattress_boxspring = _calc_mattress_boxspring(int(req.mattresses_count), int(req.box_springs_count))
    scrap = _calc_scrap(req)

    raw_cash = travel + labor + disposal + mattress_boxspring + scrap

    # enforce minimum per service
    cash_before_round = max(service_min, raw_cash)

    # cash: round to nearest $5
    cash_total = round_cash_to_nearest_5(cash_before_round)

    # EMT: cents are fine (don’t “round to 5”)
    emt_total = round(cash_total * (1.0 + HST_RATE_EMT), 2)

    disclaimer = (
        "This estimate is solely based on the information provided and may change after an in-person view "
        "(stairs, heavy items, access, actual load size, multiple trips, etc.). "
        "Cash is tax-free; EMT/e-transfer adds 13% HST."
    )

    return {
        "total_cash_cad": round(cash_total, 2),
        "total_emt_cad": round(emt_total, 2),
        "crew_size": crew,
        "travel_min_cad": round(travel, 2),
        "labor_cad": round(labor, 2),
        "disposal_cad": round(disposal, 2),
        "mattress_boxspring_cad": round(mattress_boxspring, 2),
        "scrap_cad": round(scrap, 2),
        "disclaimer": disclaimer,
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

    # Store full request + response for admin review later
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
            **result,
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=float(result["total_cash_cad"]),
        total_emt_cad=float(result["total_emt_cad"]),
        crew_size=int(result["crew_size"]),
        travel_min_cad=float(result["travel_min_cad"]),
        labor_cad=float(result["labor_cad"]),
        disposal_cad=float(result["disposal_cad"]),
        mattress_boxspring_cad=float(result["mattress_boxspring_cad"]),
        scrap_cad=float(result["scrap_cad"]),
        disclaimer=str(result["disclaimer"]),
    )