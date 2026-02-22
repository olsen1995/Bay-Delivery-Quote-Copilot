from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Annotated
from uuid import uuid4
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError, HTTPError

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
    save_job,
    list_jobs,
    get_job_by_quote_id,
    export_db_to_json,
    import_db_from_json,
)

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


APP_VERSION = "0.9.0"
CAD = "CAD"
LOCAL_TZ_NAME = "America/Toronto"

# Admin auth options (either works):
# 1) Token auth (simple)
ADMIN_TOKEN_ENV = "BAYDELIVERY_ADMIN_TOKEN"
# 2) Basic auth (username/password)
ADMIN_USERNAME_ENV = "ADMIN_USERNAME"
ADMIN_PASSWORD_ENV = "ADMIN_PASSWORD"

# Optional (for image analysis)
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_VISION_MODEL_ENV = "OPENAI_VISION_MODEL"  # default below


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

HOME_HTML_PATH = STATIC_DIR / "home.html"
QUOTE_HTML_PATH = STATIC_DIR / "quote.html"
LEGACY_INDEX_HTML_PATH = STATIC_DIR / "index.html"
ADMIN_HTML_PATH = STATIC_DIR / "admin.html"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _now_local_iso() -> str:
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    if ZoneInfo is not None:
        tz = ZoneInfo(LOCAL_TZ_NAME)
        return now_utc.astimezone(tz).replace(microsecond=0).isoformat()
    return datetime.now().replace(microsecond=0).isoformat()


def _unauthorized_basic() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Admin authentication required",
        headers={"WWW-Authenticate": 'Basic realm="Bay Delivery Admin"'},
    )


def _require_admin(request: Request) -> None:
    token_required = os.getenv(ADMIN_TOKEN_ENV)
    if token_required:
        token = request.headers.get("X-Admin-Token") or request.query_params.get("token")
        if token != token_required:
            raise HTTPException(status_code=401, detail="Admin token required")
        return

    user_required = os.getenv(ADMIN_USERNAME_ENV)
    pass_required = os.getenv(ADMIN_PASSWORD_ENV)
    if user_required and pass_required:
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Basic "):
            raise _unauthorized_basic()

        b64 = auth.split(" ", 1)[1].strip()
        try:
            decoded = base64.b64decode(b64).decode("utf-8")
        except Exception:
            raise _unauthorized_basic()

        if ":" not in decoded:
            raise _unauthorized_basic()

        username, password = decoded.split(":", 1)
        if not (
            secrets.compare_digest(username, user_required)
            and secrets.compare_digest(password, pass_required)
        ):
            raise _unauthorized_basic()
        return

    return


# =========================
# Pages
# =========================

@app.get("/")
def home():
    if HOME_HTML_PATH.exists():
        return FileResponse(HOME_HTML_PATH)
    if QUOTE_HTML_PATH.exists():
        return FileResponse(QUOTE_HTML_PATH)
    if LEGACY_INDEX_HTML_PATH.exists():
        return FileResponse(LEGACY_INDEX_HTML_PATH)
    raise HTTPException(status_code=500, detail=f"Missing frontend files under: {STATIC_DIR.as_posix()}")


@app.get("/quote")
def quote_page():
    if QUOTE_HTML_PATH.exists():
        return FileResponse(QUOTE_HTML_PATH)
    if LEGACY_INDEX_HTML_PATH.exists():
        return FileResponse(LEGACY_INDEX_HTML_PATH)
    raise HTTPException(status_code=500, detail=f"Missing quote page: {QUOTE_HTML_PATH.as_posix()}")


@app.get("/admin")
def admin_page(request: Request):
    _require_admin(request)
    if not ADMIN_HTML_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing admin file: {ADMIN_HTML_PATH.as_posix()}")
    return FileResponse(ADMIN_HTML_PATH)


# =========================
# Models
# =========================

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

    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=7, max_length=40)
    job_address: str = Field(..., min_length=5, max_length=240)

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
        "admin_basic_configured": bool(os.getenv(ADMIN_USERNAME_ENV) and os.getenv(ADMIN_PASSWORD_ENV)),
        "openai_key_configured": bool(os.getenv(OPENAI_API_KEY_ENV)),
    }


# =========================
# Quote API
# =========================

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
            travel_zone="in_town",  # customer side always in_town; admin can adjust later
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


class ImageAnalysisResponse(BaseModel):
    ok: bool = True
    suggestions: dict
    message: str


def _call_openai_vision_json(prompt: str, images_data_urls: list[str]) -> dict:
    api_key = os.getenv(OPENAI_API_KEY_ENV)
    if not api_key:
        raise HTTPException(status_code=501, detail="Image analysis is not configured (missing OPENAI_API_KEY).")

    model = os.getenv(OPENAI_VISION_MODEL_ENV) or "gpt-4o-mini"

    input_content = [{"type": "input_text", "text": prompt}]
    for url in images_data_urls:
        input_content.append({"type": "input_image", "image_url": url})

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": input_content,
            }
        ],
        # Force JSON output style (we still validate/parse safely)
        "text": {"format": {"type": "json_object"}},
    }

    req = UrlRequest(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = str(e)
        raise HTTPException(status_code=502, detail=f"OpenAI error: {detail}")
    except URLError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI unreachable: {e}")

    raw = json.loads(body)

    # Responses API returns output items; easiest: collect any output_text blocks
    # but to keep dependencies zero, we handle a couple common shapes safely.
    text_out = None
    if isinstance(raw, dict):
        # SDK convenience property sometimes exists in docs; but not guaranteed.
        if isinstance(raw.get("output_text"), str):
            text_out = raw.get("output_text")
        elif isinstance(raw.get("output"), list):
            for item in raw["output"]:
                if isinstance(item, dict) and item.get("type") in ("output_text", "message"):
                    # Some items have content array with output_text blocks
                    content = item.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                                if isinstance(c.get("text"), str):
                                    text_out = c["text"]
                                    break
                if text_out:
                    break

    if not text_out:
        raise HTTPException(status_code=502, detail="OpenAI response parsing failed (no text output).")

    # We asked for json_object, so parse it
    try:
        return json.loads(text_out)
    except Exception:
        # If model returns raw text, try to salvage by stripping
        try:
            return json.loads(text_out.strip())
        except Exception:
            raise HTTPException(status_code=502, detail="OpenAI returned non-JSON output.")


@app.post("/quote/analyze-images", response_model=ImageAnalysisResponse)
async def quote_analyze_images(files: list[UploadFile] = File(...)):
    """
    Customer-facing image analysis (suggestions only).
    - No storage; in-memory only.
    - Requires OPENAI_API_KEY on the server to work.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files received.")

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Too many images (max 5).")

    images_data_urls: list[str] = []
    total_bytes = 0

    for f in files:
        content_type = (f.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image uploads are allowed.")

        b = await f.read()
        if not b:
            raise HTTPException(status_code=400, detail="One of the images was empty.")

        total_bytes += len(b)
        if total_bytes > 8_000_000:  # ~8MB total cap for safety
            raise HTTPException(status_code=400, detail="Images too large (max ~8MB total).")

        b64 = base64.b64encode(b).decode("utf-8")
        # data URL format for input_image
        images_data_urls.append(f"data:{content_type};base64,{b64}")

    prompt = (
        "You are estimating a hauling/junk removal job from photos. "
        "Return ONLY JSON with these keys:\n"
        "- estimated_hours (number, e.g. 1.5)\n"
        "- recommended_crew_size (integer 1 or 2)\n"
        "- estimated_garbage_bag_count (integer 0-30) (bag-equivalent)\n"
        "- estimated_mattresses_count (integer 0-10)\n"
        "- estimated_box_springs_count (integer 0-10)\n"
        "- confidence (number 0-1)\n"
        "- notes (string)\n"
        "Be conservative: if unsure, lower confidence and put assumptions in notes."
    )

    suggestions = _call_openai_vision_json(prompt, images_data_urls)

    # Defensive normalization
    def _num(x, default=0.0):
        try:
            return float(x)
        except Exception:
            return float(default)

    def _int(x, default=0):
        try:
            return int(float(x))
        except Exception:
            return int(default)

    cleaned = {
        "estimated_hours": max(0.0, _num(suggestions.get("estimated_hours", 0.0))),
        "recommended_crew_size": max(1, min(2, _int(suggestions.get("recommended_crew_size", 1)))),
        "estimated_garbage_bag_count": max(0, min(30, _int(suggestions.get("estimated_garbage_bag_count", 0)))),
        "estimated_mattresses_count": max(0, min(10, _int(suggestions.get("estimated_mattresses_count", 0)))),
        "estimated_box_springs_count": max(0, min(10, _int(suggestions.get("estimated_box_springs_count", 0)))),
        "confidence": max(0.0, min(1.0, _num(suggestions.get("confidence", 0.5)))),
        "notes": str(suggestions.get("notes", "") or "").strip(),
    }

    return {
        "ok": True,
        "suggestions": cleaned,
        "message": "Photo analysis complete. These are suggestions only — you can adjust before calculating.",
    }


# =========================
# Customer: request booking
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


@app.get("/admin/api/jobs")
def admin_list_jobs(request: Request, limit: int = 50, status: Optional[str] = None):
    _require_admin(request)
    return {"items": list_jobs(limit=int(limit), status=status)}


@app.get("/admin/api/db/export")
def admin_export_db(request: Request):
    _require_admin(request)

    payload = export_db_to_json()
    payload["meta"]["exported_at"] = _now_local_iso()
    payload["meta"]["db_path"] = str(Path("app/data/bay_delivery.sqlite3"))

    filename = f"bay_delivery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class AdminDBImport(BaseModel):
    payload: dict


@app.post("/admin/api/db/import")
def admin_import_db(request: Request, body: AdminDBImport):
    _require_admin(request)

    try:
        result = import_db_from_json(body.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return result


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


def _create_job_from_request(request_row: dict, admin_notes: Optional[str]) -> dict:
    existing = get_job_by_quote_id(request_row["quote_id"])
    if existing:
        return existing

    now = _now_local_iso()
    job_id = str(uuid4())

    requested_date = request_row.get("requested_job_date") or ""
    requested_window = request_row.get("requested_time_window") or ""

    notes_parts = []
    if requested_date or requested_window:
        notes_parts.append(f"Requested: {requested_date} {requested_window}".strip())
    if admin_notes:
        notes_parts.append(f"Admin notes: {admin_notes}".strip())
    notes = " | ".join([p for p in notes_parts if p])

    total = float(request_row.get("cash_total_cad", 0.0))

    job_obj = {
        "job_id": job_id,
        "created_at": now,
        "quote_id": request_row["quote_id"],
        "status": "approved_pending_schedule",
        "customer_name": request_row.get("customer_name"),
        "customer_phone": request_row.get("customer_phone"),
        "job_address": request_row.get("job_address"),
        "job_description_customer": request_row.get("job_description_customer"),
        "job_description_internal": request_row.get("job_description_internal"),
        "scheduled_start": None,
        "scheduled_end": None,
        "payment_method": None,
        "total_cad": total,
        "paid_cad": 0.0,
        "owing_cad": total,
        "notes": notes or None,
        "job_json": {
            "source": "quote_request_approved",
            "quote_request": request_row,
            "admin_notes": admin_notes,
        },
    }

    save_job(job_obj)
    return {
        "job_id": job_id,
        "created_at": now,
        "quote_id": request_row["quote_id"],
        "status": "approved_pending_schedule",
        "customer_name": request_row.get("customer_name"),
        "customer_phone": request_row.get("customer_phone"),
        "job_address": request_row.get("job_address"),
        "scheduled_start": None,
        "scheduled_end": None,
        "payment_method": None,
        "total_cad": total,
        "paid_cad": 0.0,
        "owing_cad": total,
        "notes": notes or None,
    }


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
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update request")

        job_summary = _create_job_from_request(updated, body.notes)
        return {"ok": True, "request": updated, "job": job_summary}

    updated = update_quote_request(
        request_id,
        status="rejected",
        notes=body.notes,
        admin_approved_at=None,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update request")

    return {"ok": True, "request": updated}