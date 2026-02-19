# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.storage import init_db, save_quote

# =========================
# VERSION
# =========================

APP_VERSION = "0.9.0"

app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version=APP_VERSION,
    description="Backend for Bay Delivery Quotes: customer estimate + internal logging.",
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

UPLOAD_DIR = BASE_DIR / "app" / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
# Business rules (current)
# =========================

HST_RATE_EMT = 0.13

# Rates requested
RATE_DUMP_RUN_PER_WORKER_HR = 50.0
RATE_MOVING_PER_WORKER_HR = 60.0
RATE_DEMO_PER_WORKER_HR = 75.0

# Minimums / constants
MINIMUM_CHARGE_CAD = 50.0

BAG_FEE_CAD = 7.50
MATTRESS_FEE_EACH_CAD = 50.0
BOXS_FEE_EACH_CAD = 50.0

SCRAP_CURBSIDE_FEE_CAD = 0.0
SCRAP_INSIDE_FEE_CAD = 30.0


# =========================
# Enums
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


class PropertyType(str, Enum):
    house = "house"
    apartment = "apartment"
    apartment_building = "apartment_building"
    storage_locker = "storage_locker"
    commercial = "commercial"


class DemoType(str, Enum):
    small = "small"              # small interior demo, light tear-out
    shed_deck = "shed_deck"      # sheds/decks/backyard demo
    brick_masonry = "brick_masonry"  # brick walls / masonry removal


# =========================
# Validation helpers
# =========================

def normalize_service_type(value: Any) -> Any:
    if isinstance(value, str):
        return ServiceType.normalize(value)
    return value


# =========================
# Schemas
# =========================

NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
PosInt = Annotated[int, Field(ge=1)]


class QuoteRequest(BaseModel):
    # Core
    service_type: ServiceType = ServiceType.dump_run

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    # Basic customer info (stored)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    # Description that helps pricing (stored)
    job_description_customer: Optional[str] = Field(
        None,
        description="Customer description (we use keywords for a smarter estimate).",
    )

    # General flags (stored)
    stairs: bool = False
    elevator: bool = False
    difficult_corner: bool = False
    long_carry: bool = False

    # Optional uploads (store file refs returned by /upload)
    photo_refs: Optional[List[str]] = None

    # Inputs
    estimated_hours: Optional[NonNegFloat] = None  # customer can enter anything; we may bump if too low

    # Crew
    workers: Optional[PosInt] = None

    # Dump run specifics
    garbage_bags_count: NonNegInt = 0
    dump_fees_cad: NonNegFloat = 0.0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    # Scrap pickup specifics
    scrap_curbside: bool = True  # curbside = free, inside = $30

    # Moving specifics
    pickup_property_type: Optional[PropertyType] = None
    dropoff_property_type: Optional[PropertyType] = None

    # Demolition specifics
    demo_type: Optional[DemoType] = None
    remove_materials: bool = False


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD

    service_type: ServiceType

    # What the system actually used
    workers_used: int
    hours_entered: float
    hours_used: float
    hours_suggested: float

    # Totals
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat

    # Optional range for services that are often variable
    cash_range_low_cad: Optional[NonNegFloat] = None
    cash_range_high_cad: Optional[NonNegFloat] = None

    # Customer summary (no $ amounts except disposal)
    summary_labels: List[str]
    disposal_line_items: List[Dict[str, Any]]

    disclaimer: str


# =========================
# Money helpers
# =========================

def _round2(x: float) -> float:
    return float(f"{x:.2f}")


def _round_cash_pretty(x: float) -> float:
    """
    Cash totals: you prefer clean numbers.
    - Default: round to nearest $5
    - For bigger totals (>= $200): round to nearest $10
    """
    x = float(x)
    if x <= 0:
        return 0.0

    step = 10.0 if x >= 200.0 else 5.0
    return float(step * round(x / step))


# =========================
# Estimation heuristics
# =========================

def _keyword_score(desc: str) -> int:
    d = (desc or "").lower()
    score = 0
    # Light signals
    for w in ["couch", "sofa", "mattress", "boxspring", "dresser", "bed", "fridge", "washer", "dryer"]:
        if w in d:
            score += 1
    # Heavy / complex signals
    for w in ["stairs", "basement", "tight", "narrow", "corner", "elevator", "carry", "long", "many", "lot"]:
        if w in d:
            score += 1
    # Demo / heavy signals
    for w in ["brick", "masonry", "wall", "drywall", "concrete", "shed", "deck", "tear out", "demo"]:
        if w in d:
            score += 2
    return score


def _suggest_hours(req: QuoteRequest) -> float:
    desc_score = _keyword_score(req.job_description_customer or "")

    if req.service_type == ServiceType.dump_run:
        # Base 1hr, add per bag & disposal items
        base = 1.0
        base += (float(req.garbage_bags_count) / 20.0)  # 20 bags ≈ +1hr rough
        base += 0.5 * float(req.mattresses_count + req.box_springs_count)
        base += 0.25 * min(desc_score, 6)
        # Flags
        if req.stairs:
            base += 0.5
        if req.difficult_corner:
            base += 0.25
        if req.long_carry:
            base += 0.25
        return max(0.5, base)

    if req.service_type == ServiceType.scrap_pickup:
        base = 0.5 if req.scrap_curbside else 1.0
        base += 0.25 * min(desc_score, 6)
        if req.stairs:
            base += 0.5
        if req.long_carry:
            base += 0.25
        return max(0.5, base)

    if req.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
        # Moving is rarely under 4hrs in practice
        base = 4.0
        # Property types add friction
        prop_types = [req.pickup_property_type, req.dropoff_property_type]
        for p in prop_types:
            if p in {PropertyType.apartment, PropertyType.apartment_building}:
                base += 1.0
            if p == PropertyType.storage_locker:
                base += 0.5
            if p == PropertyType.commercial:
                base += 0.75
        # Flags
        if req.stairs:
            base += 1.0
        if req.elevator:
            base += 0.25  # elevators still take time
        if req.difficult_corner:
            base += 0.5
        if req.long_carry:
            base += 0.5
        base += 0.25 * min(desc_score, 10)
        return max(4.0, base)

    if req.service_type == ServiceType.demolition:
        dt = req.demo_type or DemoType.small
        if dt == DemoType.small:
            base = 4.0
        elif dt == DemoType.shed_deck:
            base = 8.0
        else:
            base = 12.0  # brick/masonry
        if req.remove_materials:
            base += 2.0
        if req.stairs:
            base += 0.5
        if req.difficult_corner or req.long_carry:
            base += 0.5
        base += 0.25 * min(desc_score, 12)
        return max(4.0, base)

    return 1.0


def _default_workers(req: QuoteRequest) -> int:
    if req.service_type == ServiceType.dump_run:
        # Default 1, but can increase if description suggests big items
        return 1

    if req.service_type == ServiceType.scrap_pickup:
        return 1

    if req.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
        # Your rule: never below 2, default 3
        return 3

    if req.service_type == ServiceType.demolition:
        # Demo usually 2+, brick often 4+
        dt = req.demo_type or DemoType.small
        if dt == DemoType.brick_masonry:
            return 4
        if dt == DemoType.shed_deck:
            return 3
        return 2

    return 1


# =========================
# Hybrid Quote Logic
# =========================

def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    # Workers
    workers_default = _default_workers(req)
    workers = int(req.workers) if req.workers is not None else workers_default

    # Enforce minimum workers per service
    if req.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
        workers = max(2, workers)
    if req.service_type == ServiceType.demolition:
        workers = max(2, workers)

    # Hours
    hours_entered = float(req.estimated_hours or 0.0)
    hours_suggested = _suggest_hours(req)

    # Billable hours rule:
    # - You allow any hours input
    # - If input is unreasonably low vs suggested, we bump up (prevents lowball quoting)
    if hours_entered <= 0:
        hours_used = hours_suggested
    else:
        # if user entered less than 75% of suggested, we use suggested
        if hours_entered < (0.75 * hours_suggested):
            hours_used = hours_suggested
        else:
            hours_used = hours_entered

    # Service pricing
    raw_cash = 0.0
    summary_labels: List[str] = []
    disposal_items: List[Dict[str, Any]] = []

    # Always show this style (customer-facing)
    summary_labels.append("Estimate based on info provided")
    if req.stairs:
        summary_labels.append("Stairs")
    if req.elevator:
        summary_labels.append("Elevator")
    if req.difficult_corner:
        summary_labels.append("Difficult access/corners")
    if req.long_carry:
        summary_labels.append("Long carry")

    if req.service_type == ServiceType.dump_run:
        summary_labels.append("Labour included")
        summary_labels.append("Local base pricing (North Bay)")

        labour = workers * RATE_DUMP_RUN_PER_WORKER_HR * hours_used
        bags_fee = float(req.garbage_bags_count) * BAG_FEE_CAD
        dump_fee = float(req.dump_fees_cad)

        m_cost = int(req.mattresses_count) * MATTRESS_FEE_EACH_CAD
        b_cost = int(req.box_springs_count) * BOXS_FEE_EACH_CAD

        if int(req.mattresses_count) > 0:
            disposal_items.append({"label": "Mattress disposal", "count": int(req.mattresses_count), "each_cad": MATTRESS_FEE_EACH_CAD, "total_cad": _round2(m_cost)})
        if int(req.box_springs_count) > 0:
            disposal_items.append({"label": "Box spring disposal", "count": int(req.box_springs_count), "each_cad": BOXS_FEE_EACH_CAD, "total_cad": _round2(b_cost)})

        raw_cash = labour + bags_fee + dump_fee + m_cost + b_cost
        raw_cash = max(MINIMUM_CHARGE_CAD, raw_cash)

    elif req.service_type == ServiceType.scrap_pickup:
        summary_labels.append("Scrap pickup")

        # Curbside free, inside $30
        pickup_fee = SCRAP_CURBSIDE_FEE_CAD if req.scrap_curbside else SCRAP_INSIDE_FEE_CAD

        # If curbside-only and truly free, allow $0 (no minimum)
        if req.scrap_curbside and pickup_fee == 0.0:
            raw_cash = 0.0
            summary_labels.append("Curbside only (free)")
        else:
            summary_labels.append("Inside pickup fee may apply")
            raw_cash = pickup_fee
            raw_cash = max(MINIMUM_CHARGE_CAD, raw_cash)

    elif req.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
        summary_labels.append("Moving labour included")
        summary_labels.append("Crew sized for job (min 2, default 3)")
        summary_labels.append("Estimate shown as a range")

        labour = workers * RATE_MOVING_PER_WORKER_HR * max(4.0, hours_used)
        raw_cash = labour
        raw_cash = max(MINIMUM_CHARGE_CAD, raw_cash)

    elif req.service_type == ServiceType.demolition:
        summary_labels.append("Demolition labour included")
        if req.remove_materials:
            summary_labels.append("Material removal included (estimate)")
        summary_labels.append("Estimate shown as a range")

        labour = workers * RATE_DEMO_PER_WORKER_HR * hours_used
        raw_cash = labour

        # Floors by demo type
        dt = req.demo_type or DemoType.small
        if dt == DemoType.small:
            raw_cash = max(500.0, raw_cash)
        elif dt == DemoType.shed_deck:
            raw_cash = max(1200.0, raw_cash)
        else:
            raw_cash = max(2500.0, raw_cash)

    else:
        raw_cash = max(MINIMUM_CHARGE_CAD, raw_cash)

    # Cash rounding preference (EMT stays exact cents)
    cash_total = _round_cash_pretty(raw_cash)

    # EMT: exact cents + HST
    emt_total = _round2(cash_total * (1.0 + HST_RATE_EMT))

    # Ranges (only for moving/demo right now)
    cash_low: Optional[float] = None
    cash_high: Optional[float] = None

    if req.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
        # moving variability smaller
        low = cash_total * 0.95
        high = cash_total * 1.20
        cash_low = _round_cash_pretty(low)
        cash_high = _round_cash_pretty(high)

    if req.service_type == ServiceType.demolition:
        # demo variability wider
        low = cash_total * 0.90
        high = cash_total * 1.35
        cash_low = _round_cash_pretty(low)
        cash_high = _round_cash_pretty(high)

    disclaimer = (
        "This estimate is solely based on the information provided. "
        "Final pricing may change after an in-person view if details differ "
        "(stairs, heavy items, access, actual dump/landfill fees, multiple trips, etc.). "
        "Cash is rounded to clean totals; EMT/e-transfer adds 13% HST."
    )

    return {
        "workers_used": workers,
        "hours_entered": _round2(hours_entered),
        "hours_used": _round2(hours_used),
        "hours_suggested": _round2(hours_suggested),
        "total_cash_cad": _round2(cash_total),
        "total_emt_cad": _round2(emt_total),
        "cash_range_low_cad": _round2(cash_low) if cash_low is not None else None,
        "cash_range_high_cad": _round2(cash_high) if cash_high is not None else None,
        "summary_labels": summary_labels,
        "disposal_line_items": disposal_items,
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


@app.post("/upload")
async def upload_photos(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Basic photo upload (no paid services).
    Note: Render free instances can have ephemeral disk; this is a starter feature.
    Returns file refs you can store with a quote.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    refs: List[str] = []
    for f in files:
        # Simple safe filename
        ext = Path(f.filename or "").suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            # allow HEIC from iPhone
            pass

        ref = f"{uuid4().hex}{ext if ext else ''}"
        out_path = UPLOAD_DIR / ref
        content = await f.read()
        out_path.write_bytes(content)
        refs.append(ref)

    return {"ok": True, "photo_refs": refs}


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest):
    result = calculate_quote(req)

    quote_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    # Persist full request + response for your admin review later
    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=float(result["total_cash_cad"]),
        request_obj=req.model_dump(),
        response_obj={
            "quote_id": quote_id,
            "created_at": created_at,
            "service_type": req.service_type.value,
            **result,
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        workers_used=int(result["workers_used"]),
        hours_entered=float(result["hours_entered"]),
        hours_used=float(result["hours_used"]),
        hours_suggested=float(result["hours_suggested"]),
        total_cash_cad=float(result["total_cash_cad"]),
        total_emt_cad=float(result["total_emt_cad"]),
        cash_range_low_cad=float(result["cash_range_low_cad"]) if result["cash_range_low_cad"] is not None else None,
        cash_range_high_cad=float(result["cash_range_high_cad"]) if result["cash_range_high_cad"] is not None else None,
        summary_labels=list(result["summary_labels"]),
        disposal_line_items=list(result["disposal_line_items"]),
        disclaimer=str(result["disclaimer"]),
    )