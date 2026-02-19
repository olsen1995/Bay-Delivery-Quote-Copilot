# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Annotated
from uuid import uuid4

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator

from app.storage import (
    init_db,
    save_quote,
    get_quote,
    list_quotes,
    search_quotes,
    save_job,
    get_job,
    list_jobs,
    update_job_fields,
    save_quote_request,
    get_quote_request,
    list_quote_requests,
    update_quote_request,
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
# Admin Auth (HTTP Basic)
# =========================

security = HTTPBasic()


def _require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    HTTP Basic auth for admin routes.
    Uses env vars:
      - ADMIN_USERNAME
      - ADMIN_PASSWORD
    """
    expected_user = (os.getenv("ADMIN_USERNAME") or "").strip()
    expected_pass = (os.getenv("ADMIN_PASSWORD") or "").strip()

    if not expected_user or not expected_pass:
        # Misconfiguration should be loud during setup.
        raise HTTPException(
            status_code=500,
            detail="Admin auth not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.",
        )

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Bay Delivery Admin"'},
        )

    return credentials.username


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
        """
        Allow both 'small_move' and 'small_moving' externally.
        Everything normalizes to 'small_move' internally.
        """
        if value == "small_moving":
            return cls.small_move
        return cls(value)


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


class QuoteRequest(BaseModel):
    service_type: ServiceType = ServiceType.dump_run

    @field_validator("service_type", mode="before")
    @classmethod
    def validate_service_type(cls, v):
        return normalize_service_type(v)

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None
    job_description_customer: Optional[str] = None
    job_description_internal: Optional[str] = None

    distance_km: Optional[NonNegFloat] = None
    estimated_hours: NonNegFloat = 0.0
    requires_two_workers: bool = False

    dump_fees_cad: NonNegFloat = 0.0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD
    service_type: ServiceType
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat


# =========================
# Minimal Quote Logic (unchanged)
# =========================

def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    # NOTE: This is the simple estimator you’re currently running.
    # We’ll upgrade per-service rules next (bags, scrap curbside, moving crew, demo minimums, etc.)
    base = 50.0
    hours_cost = req.estimated_hours * 60.0
    total_cash = max(base, hours_cost)

    total_emt = round(total_cash * 1.13, 2)

    return {
        "total_cash_cad": round(total_cash, 2),
        "total_emt_cad": total_emt,
    }


# =========================
# Routes
# =========================

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": APP_VERSION,
        "base_address": os.getenv("BAYDELIVERY_BASE_ADDRESS"),
        "distance_autocalc_enabled": bool(os.getenv("GOOGLE_MAPS_API_KEY")),
    }


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest) -> QuoteResponse:
    result = calculate_quote(req)

    quote_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=result["total_cash_cad"],
        request_obj=req.model_dump(),
        response_obj={
            "quote_id": quote_id,
            "created_at": created_at,
            "currency": CAD,
            "service_type": req.service_type.value,
            "total_cash_cad": result["total_cash_cad"],
            "total_emt_cad": result["total_emt_cad"],
            # Echo back useful fields so the stored quote is self-contained
            "customer_name": req.customer_name,
            "customer_phone": req.customer_phone,
            "job_address": req.job_address,
            "job_description_customer": req.job_description_customer,
            "job_description_internal": req.job_description_internal,
            "estimated_hours": float(req.estimated_hours),
            "requires_two_workers": bool(req.requires_two_workers),
            "mattresses_count": int(req.mattresses_count),
            "box_springs_count": int(req.box_springs_count),
        },
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=result["total_cash_cad"],
        total_emt_cad=result["total_emt_cad"],
    )


# =========================
# Admin JSON Dashboard (Phase 1)
# =========================

@app.get("/admin/health")
def admin_health(admin_user: str = Depends(_require_admin)) -> Dict[str, Any]:
    return {
        "ok": True,
        "admin_user": admin_user,
        "time": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
    }


@app.get("/admin/quotes")
def admin_list_quotes(
    limit: int = 50,
    admin_user: str = Depends(_require_admin),
) -> Dict[str, Any]:
    rows = list_quotes(limit=limit)
    return {"count": len(rows), "items": rows}


@app.get("/admin/quotes/{quote_id}")
def admin_get_quote(
    quote_id: str,
    admin_user: str = Depends(_require_admin),
) -> Dict[str, Any]:
    data = get_quote(quote_id)
    if not data:
        raise HTTPException(status_code=404, detail="Quote not found")
    return data


@app.get("/admin/quote-requests")
def admin_list_quote_requests(
    limit: int = 50,
    status: Optional[str] = None,
    admin_user: str = Depends(_require_admin),
) -> Dict[str, Any]:
    rows = list_quote_requests(limit=limit, status=status)
    return {"count": len(rows), "items": rows}


@app.get("/admin/quote-requests/{request_id}")
def admin_get_quote_request(
    request_id: str,
    admin_user: str = Depends(_require_admin),
) -> Dict[str, Any]:
    r = get_quote_request(request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Quote request not found")
    return r