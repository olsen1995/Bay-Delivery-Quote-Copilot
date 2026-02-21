from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.quote_engine import calculate_quote
from app.storage import init_db, save_quote

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

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML_PATH = BASE_DIR / "static" / "index.html"


@app.get("/")
def root():
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing frontend file: {INDEX_HTML_PATH.as_posix()}")
    return FileResponse(INDEX_HTML_PATH)


HST_RATE_EMT = 0.13


class ServiceType(str, Enum):
    haul_away = "haul_away"         # junk + dump are the same
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

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    job_address: Optional[str] = None

    description: Optional[str] = Field(
        None,
        description="Customer description of items / job details. Stored for admin review.",
    )

    estimated_hours: NonNegFloat = 0.0
    crew_size: Optional[PosInt] = None

    garbage_bag_count: NonNegInt = 0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    scrap_pickup_location: str = "curbside"

    stairs: bool = False
    elevator: bool = False
    difficult_corner: bool = False


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
        "base_address": os.getenv("BAYDELIVERY_BASE_ADDRESS"),
        "distance_autocalc_enabled": bool(os.getenv("GOOGLE_MAPS_API_KEY")),
    }


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest):
    # Default crew if missing
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
            # internal stays stored for admin, not displayed in UI
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