from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.quote_engine import calculate_quote
from app.storage import (
    init_db,
    save_quote,
    list_quotes,
    get_quote_record,
    save_quote_request,
    list_quote_requests,
    get_quote_request,
    get_quote_request_by_quote_id,
    update_quote_request,
    save_job,
    list_jobs,
    get_job_by_quote_id,
    save_attachment,
    list_attachments,
    export_db_to_json,
)
from app.update_fields import include_optional_update_fields
from app import gdrive

APP_VERSION = (
    Path("VERSION").read_text(encoding="utf-8").strip()
    if Path("VERSION").exists()
    else "0.0.0"
)

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

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =========================
# Utilities
# =========================

def _now_local_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _require_admin(request: Request) -> None:
    expected_user = os.getenv("ADMIN_USERNAME", "").strip()
    expected_pass = os.getenv("ADMIN_PASSWORD", "").strip()

    if not expected_user or not expected_pass:
        raise HTTPException(status_code=503, detail="Admin credentials are not configured.")

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("basic "):
        raise HTTPException(status_code=401, detail="Missing Basic auth.")

    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        user, pw = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Basic auth header.")

    if user != expected_user or pw != expected_pass:
        raise HTTPException(status_code=401, detail="Invalid credentials.")


def _drive_enabled() -> bool:
    return gdrive.is_configured()


# =========================
# App init
# =========================

init_db()


# =========================
# Pages
# =========================

@app.get("/")
def index():
    # FIX: Serve quote.html as homepage to avoid broken index.html
    return FileResponse(str(STATIC_DIR / "quote.html"))


@app.get("/quote")
def quote_page():
    return FileResponse(str(STATIC_DIR / "quote.html"))


@app.get("/admin")
def admin_page():
    return FileResponse(str(STATIC_DIR / "admin.html"))


@app.get("/admin/uploads")
def admin_uploads_page():
    return FileResponse(str(STATIC_DIR / "admin_uploads.html"))


# =========================
# Health
# =========================

@app.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}


# =========================
# Quote APIs
# =========================

class QuoteRequestPayload(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=120)
    customer_phone: Optional[str] = Field(None, max_length=50)
    job_address: Optional[str] = Field(None, max_length=250)
    job_description_customer: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=1000)
    service_type: str = Field(..., max_length=50)
    payment_method: Optional[str] = Field(None, max_length=20)
    pickup_address: Optional[str] = Field(None, max_length=250)
    dropoff_address: Optional[str] = Field(None, max_length=250)
    estimated_hours: float = Field(0.0, ge=0)
    crew_size: int = Field(1, ge=1)
    garbage_bag_count: int = Field(0, ge=0)
    mattresses_count: int = Field(0, ge=0)
    box_springs_count: int = Field(0, ge=0)
    scrap_pickup_location: str = Field("curbside", max_length=50)
    travel_zone: str = Field("in_town", max_length=50)

    @field_validator("*", mode="before")
    @classmethod
    def strip(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


@app.post("/quote/calculate")
def quote_calculate(payload: QuoteRequestPayload):
    request_payload = payload.model_dump()

    engine_quote = calculate_quote(
        service_type=request_payload["service_type"],
        hours=float(request_payload.get("estimated_hours", 0.0)),
        crew_size=int(request_payload.get("crew_size", 1)),
        garbage_bag_count=int(request_payload.get("garbage_bag_count", 0)),
        mattresses_count=int(request_payload.get("mattresses_count", 0)),
        box_springs_count=int(request_payload.get("box_springs_count", 0)),
        scrap_pickup_location=str(request_payload.get("scrap_pickup_location", "curbside")),
        travel_zone=str(request_payload.get("travel_zone", "in_town")),
    )

    # Normalized validation (prevents alias bypass)
    normalized_service = engine_quote["service_type"]
    if normalized_service in {"small_move", "item_delivery"}:
        if not request_payload.get("pickup_address") or not request_payload.get("dropoff_address"):
            raise HTTPException(status_code=400, detail="pickup_address and dropoff_address are required")

    quote = {
        "quote_id": str(uuid4()),
        "created_at": _now_local_iso(),
        "request": request_payload,
        "response": {
            "cash_total_cad": float(engine_quote["total_cash_cad"]),
            "emt_total_cad": float(engine_quote["total_emt_cad"]),
            "disclaimer": str(engine_quote["disclaimer"]),
        },
    }

    save_quote(quote)
    return quote