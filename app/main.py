# =========================
# BAY DELIVERY MAIN API
# =========================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Annotated
from uuid import uuid4

import os
import secrets

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator

from app.storage import (
    init_db,
    save_quote,
    get_quote,
    list_quotes,
    search_quotes,
    save_quote_request,
    get_quote_request,
    list_quote_requests,
    update_quote_request,
)

# =========================
# VERSION
# =========================

APP_VERSION = "0.8.0"

app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version=APP_VERSION,
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
security = HTTPBasic()

# =========================
# ADMIN AUTH
# =========================

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_pass = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# =========================
# Service Types
# =========================

class ServiceType(str, Enum):
    dump_run = "dump_run"
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"
    item_delivery = "item_delivery"
    demolition = "demolition"


# =========================
# Schemas
# =========================

NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]


class QuoteRequest(BaseModel):
    service_type: ServiceType = ServiceType.dump_run

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    estimated_hours: NonNegFloat = 0.0

    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD
    service_type: ServiceType
    total_cash_cad: NonNegFloat
    total_emt_cad: NonNegFloat


class AcceptRequest(BaseModel):
    requested_job_date: str
    requested_time_window: Optional[str] = None


# =========================
# Quote Logic
# =========================

def calculate_quote(req: QuoteRequest) -> Dict[str, Any]:
    base = 50.0
    hours_cost = req.estimated_hours * 60.0
    mattress_fee = (req.mattresses_count + req.box_springs_count) * 50.0

    total_cash = max(base, hours_cost) + mattress_fee
    total_cash = round(total_cash, 2)

    total_emt = round(total_cash * 1.13, 2)

    return {
        "total_cash_cad": total_cash,
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

    # create request record
    request_id = str(uuid4())

    save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": "new",
            "quote_id": quote_id,
            "customer_name": req.customer_name,
            "customer_phone": req.customer_phone,
            "job_address": req.job_address,
            "service_type": req.service_type.value,
            "cash_total_cad": result["total_cash_cad"],
            "emt_total_cad": result["total_emt_cad"],
            "request_json": req.model_dump(),
        }
    )

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        service_type=req.service_type,
        total_cash_cad=result["total_cash_cad"],
        total_emt_cad=result["total_emt_cad"],
    )


# =========================
# CUSTOMER ACCEPTS ESTIMATE
# =========================

@app.post("/request/{request_id}/accept")
def customer_accept(request_id: str, payload: AcceptRequest):
    req = get_quote_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Validate date (must be tomorrow or later)
    try:
        requested_date = datetime.fromisoformat(payload.requested_job_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()

    if requested_date < tomorrow:
        raise HTTPException(
            status_code=400,
            detail="Requested date must be at least tomorrow",
        )

    update_quote_request(
        request_id,
        status="customer_requested",
        requested_job_date=str(requested_date),
        requested_time_window=payload.requested_time_window,
        customer_accepted_at=datetime.utcnow().isoformat() + "Z",
    )

    return {"status": "customer_requested"}


# =========================
# ADMIN ENDPOINTS
# =========================

@app.get("/admin/request", dependencies=[Depends(require_admin)])
def admin_list_requests():
    return list_quote_requests()


@app.post("/admin/request/{request_id}/approve", dependencies=[Depends(require_admin)])
def admin_approve_request(request_id: str):
    req = get_quote_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req["status"] != "customer_requested":
        raise HTTPException(status_code=400, detail="Customer has not accepted yet")

    update_quote_request(
        request_id,
        status="approved",
        admin_approved_at=datetime.utcnow().isoformat() + "Z",
    )

    return {"status": "approved"}
