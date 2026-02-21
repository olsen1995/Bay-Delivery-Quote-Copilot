from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from app.quote_engine import calculate_quote
from app.storage import (
    init_db,
    save_quote,
    list_quotes,
    get_quote_record,
    save_quote_request,
    list_quote_requests,
    get_quote_request,
    update_quote_request,
)

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


APP_VERSION = "0.9.0"
CAD = "CAD"
LOCAL_TZ_NAME = "America/Toronto"

# Optional admin token (recommended for public Render deploy)
# If set, admin endpoints require header: X-Admin-Token: <token>  (or ?token=<token>)
ADMIN_TOKEN_ENV = "BAYDELIVERY_ADMIN_TOKEN"


app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version=APP_VERSION,
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + admin workflow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
INDEX_HTML_PATH = STATIC_DIR / "index.html"
ADMIN_HTML_PATH = STATIC_DIR / "admin.html"

# Serve /static/* (admin.css, future assets, etc.)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _now_local_iso() -> str:
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    if ZoneInfo is not None:
        tz = ZoneInfo(LOCAL_TZ_NAME)
        return now_utc.astimezone(tz).replace(microsecond=0).isoformat()
    return datetime.now().replace(microsecond=0).isoformat()


def _require_admin(request: Request) -> None:
    token_required = os.getenv(ADMIN_TOKEN_ENV)
    if not token_required:
        # No token configured -> admin endpoints are open.
        # Recommended: set BAYDELIVERY_ADMIN_TOKEN on Render.
        return

    token = request.headers.get("X-Admin-Token") or request.query_params.get("token")
    if token != token_required:
        raise HTTPException(status_code=401, detail="Admin token required")


@app.get("/")
def root():
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing frontend file: {INDEX_HTML_PATH.as_posix()}")
    return FileResponse(INDEX_HTML_PATH)


@app.get("/admin")
def admin_page(request: Request):
    _require_admin(request)
    if not ADMIN_HTML_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing admin file: {ADMIN_HTML_PATH.as_posix()}")
    return FileResponse(ADMIN_HTML_PATH)


class ServiceType(str, Enum):
    haul_away = "haul_away"
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"
    item_delivery = "item_delivery"
    demolition = "demolition"

    @classmethod
    def normalize(cls, value: str) -> "ServiceType":
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


NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
PosInt = Annotated[int, Field(ge=1)]


class QuoteRequest(BaseModel):
    service_type: ServiceType = ServiceType.haul_away

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    # Required for ALL quotes (prevents no-info estimates)
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=7, max_length=40)
    job_address: str = Field(..., min_length=5, max_length=240)

    # Required for moving + item delivery
    pickup_address: Optional[str] = Field(None, max_length=240)
    dropoff_address: Optional[str] = Field(None, max_length=240)

    description: str = Field(..., min_length=8, max_length=2000)

    estimated_hours: NonNegFloat = 0.0
    crew_size: Optional[PosInt] = None

    garbage_bag_count: NonNegInt = 0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    scrap_pickup_location: str = "curbside"

    stairs: bool = False
    elevator: bool = False
    difficult_corner: bool = False

    @field_validator(
        "customer_name",
        "customer_phone",
        "job_address",
        "pickup_address",
        "dropoff_address",
        "description",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def enforce_routes(self):
        if self.service_type in {ServiceType.small_move, ServiceType.item_delivery}:
            if not (self.pickup_address or "").strip():
                raise ValueError("pickup_address is required for moving / item delivery")
            if not (self.dropoff_address or "").strip():
                raise ValueError("dropoff_address is required for moving / item delivery")
        return self


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD
    service_type: ServiceType
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat
    disclaimer: str


@app.get("/health")
def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "local_timezone": LOCAL_TZ_NAME,
        "admin_token_configured": bool(os.getenv(ADMIN_TOKEN_ENV)),
    }


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest):
    crew = int(req.crew_size) if req.crew_size is not None else 1

    try:
        result = calculate_quote(
            service_type=req.service_type.value,
            hours=float(req.estimated_hours),
            crew_size=crew,
            garbage_bag_count=int(req.garbage_bag_count),
            mattresses_count=int(req.mattresses_count),
            box_springs_count=int(req.box_springs_count),
            scrap_pickup_location=str(req.scrap_pickup_location or "curbside"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    quote_id = str(uuid4())
    created_at_local = _now_local_iso()

    internal = result.get("_internal", {})
    normalized_job_type = str(result.get("service_type", req.service_type.value))

    save_quote(
        quote_id=quote_id,
        created_at=created_at_local,
        job_type=normalized_job_type,
        total_cad=float(result["total_cash_cad"]),
        request_obj=req.model_dump(),
        response_obj={
            "quote_id": quote_id,
            "created_at": created_at_local,
            "currency": CAD,
            "service_type": normalized_job_type,
            "total_cash_cad": float(result["total_cash_cad"]),
            "total_emt_cad": float(result["total_emt_cad"]),
            "disclaimer": str(result["disclaimer"]),
            "internal": internal,
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at_local,
        service_type=req.service_type,
        total_cash_cad=float(result["total_cash_cad"]),
        total_emt_cad=float(result["total_emt_cad"]),
        disclaimer=str(result["disclaimer"]),
    )


# =========================
# Customer: accept estimate + request booking (admin must approve)
# =========================

class BookingRequest(BaseModel):
    quote_id: str = Field(..., min_length=10, max_length=80)
    requested_job_date: str = Field(..., min_length=4, max_length=40)
    requested_time_window: str = Field(..., min_length=2, max_length=80)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("quote_id", "requested_job_date", "requested_time_window", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


@app.post("/quote/request-booking")
def quote_request_booking(body: BookingRequest):
    record = get_quote_record(body.quote_id)
    if not record:
        raise HTTPException(status_code=404, detail="Quote not found")

    req_obj = record["request_obj"]
    resp_obj = record["response_obj"]

    request_id = str(uuid4())
    created_at = _now_local_iso()

    save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": "customer_requested",
            "quote_id": body.quote_id,
            "customer_name": req_obj.get("customer_name"),
            "customer_phone": req_obj.get("customer_phone"),
            "job_address": req_obj.get("job_address"),
            "job_description_customer": req_obj.get("description"),
            "job_description_internal": None,
            "service_type": str(resp_obj.get("service_type") or req_obj.get("service_type") or "unknown"),
            "cash_total_cad": float(resp_obj.get("total_cash_cad", 0.0)),
            "emt_total_cad": float(resp_obj.get("total_emt_cad", 0.0)),
            "request_json": {
                "quote_request_type": "booking_request",
                "quote_id": body.quote_id,
                "requested_job_date": body.requested_job_date,
                "requested_time_window": body.requested_time_window,
                "notes": body.notes,
                "quote_request_created_at": created_at,
            },
            "notes": body.notes,
            "requested_job_date": body.requested_job_date,
            "requested_time_window": body.requested_time_window,
            "customer_accepted_at": created_at,
            "admin_approved_at": None,
        }
    )

    return {
        "ok": True,
        "request_id": request_id,
        "status": "customer_requested",
        "message": "Booking request received. We will review and confirm availability.",
    }


# =========================
# Admin APIs
# =========================

@app.get("/admin/api/quotes")
def admin_list_quotes(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_quotes(limit=int(limit))}


@app.get("/admin/api/quote-requests")
def admin_list_quote_requests(request: Request, limit: int = 50, status: Optional[str] = None):
    _require_admin(request)
    return {"items": list_quote_requests(limit=int(limit), status=status)}


@app.get("/admin/api/quote-requests/{request_id}")
def admin_get_quote_request(request: Request, request_id: str):
    _require_admin(request)
    data = get_quote_request(request_id)
    if not data:
        raise HTTPException(status_code=404, detail="Request not found")
    return data


class AdminDecision(BaseModel):
    action: str = Field(..., description="approve|reject")
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("action", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


@app.post("/admin/api/quote-requests/{request_id}/decision")
def admin_decide_quote_request(request: Request, request_id: str, body: AdminDecision):
    _require_admin(request)

    existing = get_quote_request(request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Request not found")

    now = _now_local_iso()
    action = (body.action or "").lower()

    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Invalid action (use approve|reject)")

    if action == "approve":
        updated = update_quote_request(
            request_id,
            status="admin_approved",
            notes=body.notes,
            admin_approved_at=now,
        )
    else:
        updated = update_quote_request(
            request_id,
            status="rejected",
            notes=body.notes,
            admin_approved_at=None,
        )

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update request")

    return {"ok": True, "request": updated}