# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Annotated
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

APP_VERSION = "0.8.1"

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
        # Clear error so you immediately know what's wrong on deploy
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

    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=result["total_cash_cad"],
        request_obj=req.model_dump(),
        response_obj=result,
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=result["total_cash_cad"],
        total_emt_cad=result["total_emt_cad"],
    )