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

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
    import_db_from_json,
)
from app.update_fields import include_optional_update_fields
from app import gdrive

APP_VERSION = (Path("VERSION").read_text(encoding="utf-8").strip() if Path("VERSION").exists() else "0.0.0")

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
    # Keep timestamps as ISO strings (local time) for admin readability.
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _require_admin(request: Request) -> None:
    expected_user = os.getenv("ADMIN_USERNAME", "").strip()
    expected_pass = os.getenv("ADMIN_PASSWORD", "").strip()

    # Fail-closed: if credentials aren't configured, admin endpoints should not be accessible.
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
# Reliability Helpers
# =========================

_ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


def _drive_call(desc: str, fn):
    """Wrap Google Drive calls so production endpoints don't throw raw 500s."""
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as e:
        # 502 = upstream dependency failure
        raise HTTPException(status_code=502, detail=f"Google Drive error during {desc}: {e}")


def _looks_like_supported_image(content: bytes) -> bool:
    """Cheap signature check to avoid trusting MIME alone."""
    if len(content) < 12:
        return False
    # JPEG: FF D8 FF
    if content[:3] == b"\xFF\xD8\xFF":
        return True
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # GIF87a / GIF89a
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return True
    # WEBP: RIFF....WEBP
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True
    return False


def _drive_snapshot_db() -> dict:
    if not _drive_enabled():
        return {"ok": False, "message": "Google Drive not configured."}

    vault = _drive_call("vault setup", lambda: gdrive.ensure_vault_subfolders())

    payload = export_db_to_json()
    payload["meta"]["exported_at"] = _now_local_iso()
    payload["meta"]["db_path"] = "app/data/bay_delivery.sqlite3"

    filename = f"bay_delivery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    uploaded = _drive_call(
        "snapshot upload",
        lambda: gdrive.upload_bytes(
            parent_id=vault["db_backups"],
            filename=filename,
            mime_type="application/json",
            content=body,
        ),
    )

    # Best-effort retention cleanup (never fail the snapshot because cleanup failed)
    try:
        keep = gdrive.backup_keep_count()
        backups = gdrive.list_files(vault["db_backups"], limit=200)
        if len(backups) > keep:
            for f in backups[keep:]:
                try:
                    gdrive.delete_file(f.file_id)
                except Exception:
                    pass
    except Exception:
        pass

    return {"ok": True, "file_id": uploaded.file_id, "web_view_link": uploaded.web_view_link, "name": uploaded.name}


def _maybe_auto_snapshot(background_tasks: BackgroundTasks) -> None:
    if not _drive_enabled():
        return
    if os.getenv("AUTO_SNAPSHOT", "1").strip() != "1":
        return
    background_tasks.add_task(_drive_snapshot_db)


# =========================
# App init
# =========================

init_db()


# =========================
# Pages
# =========================

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


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

    @field_validator(
        "customer_name",
        "customer_phone",
        "job_address",
        "job_description_customer",
        "description",
        "service_type",
        "payment_method",
        "pickup_address",
        "dropoff_address",
        "scrap_pickup_location",
        "travel_zone",
        mode="before",
    )
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


@app.post("/quote/calculate")
def quote_calculate(payload: QuoteRequestPayload):
    request_payload = payload.model_dump()

    engine_quote = calculate_quote(
        service_type=str(request_payload.get("service_type", "")),
        hours=float(request_payload.get("estimated_hours", 0.0)),
        crew_size=int(request_payload.get("crew_size", 1)),
        garbage_bag_count=int(request_payload.get("garbage_bag_count", 0)),
        mattresses_count=int(request_payload.get("mattresses_count", 0)),
        box_springs_count=int(request_payload.get("box_springs_count", 0)),
        scrap_pickup_location=str(request_payload.get("scrap_pickup_location", "curbside")),
        travel_zone=str(request_payload.get("travel_zone", "in_town")),
    )

    # IMPORTANT:
    # Validate required route fields using the *normalized* service type returned by the engine.
    # This prevents alias bypass (e.g., "moving" -> "small_move") from skipping pickup/dropoff validation.
    normalized_service_type = str(engine_quote.get("service_type", "")).strip().lower()
    if normalized_service_type in {"small_move", "item_delivery"}:
        if not request_payload.get("pickup_address") or not request_payload.get("dropoff_address"):
            raise HTTPException(status_code=400, detail="pickup_address and dropoff_address are required")

    normalized_request = {
        "customer_name": request_payload.get("customer_name"),
        "customer_phone": request_payload.get("customer_phone"),
        "job_address": request_payload.get("job_address"),
        "job_description_customer": request_payload.get("job_description_customer") or request_payload.get("description"),
        "service_type": engine_quote["service_type"],
        "payment_method": request_payload.get("payment_method"),
        "pickup_address": request_payload.get("pickup_address"),
        "dropoff_address": request_payload.get("dropoff_address"),
        "estimated_hours": float(request_payload.get("estimated_hours", 0.0)),
        "crew_size": int(request_payload.get("crew_size", 1)),
        "garbage_bag_count": int(request_payload.get("garbage_bag_count", 0)),
        "mattresses_count": int(request_payload.get("mattresses_count", 0)),
        "box_springs_count": int(request_payload.get("box_springs_count", 0)),
        "scrap_pickup_location": request_payload.get("scrap_pickup_location", "curbside"),
        "travel_zone": request_payload.get("travel_zone", "in_town"),
    }

    quote = {
        "quote_id": str(uuid4()),
        "created_at": _now_local_iso(),
        "request": normalized_request,
        "response": {
            "cash_total_cad": float(engine_quote["total_cash_cad"]),
            "emt_total_cad": float(engine_quote["total_emt_cad"]),
            "disclaimer": str(engine_quote["disclaimer"]),
        },
    }

    save_quote(
        {
            "quote_id": quote["quote_id"],
            "created_at": quote["created_at"],
            "request": quote["request"],
            "response": quote["response"],
        }
    )
    return quote


class CustomerDecision(BaseModel):
    action: str = Field(..., description="accept|decline")
    requested_job_date: Optional[str] = Field(None, max_length=50)
    requested_time_window: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("action", "requested_job_date", "requested_time_window", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


@app.post("/quote/{quote_id}/decision")
def quote_decision(quote_id: str, body: CustomerDecision, background_tasks: BackgroundTasks):
    quote = get_quote_record(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found.")

    existing = get_quote_request_by_quote_id(quote_id)
    now = _now_local_iso()
    action = (body.action or "").lower()

    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Invalid action (use accept|decline).")

    if not existing:
        request_id = str(uuid4())
        save_quote_request(
            {
                "request_id": request_id,
                "created_at": now,
                "status": "customer_pending",
                "quote_id": quote_id,
                "customer_name": quote["request"].get("customer_name"),
                "customer_phone": quote["request"].get("customer_phone"),
                "job_address": quote["request"].get("job_address"),
                "job_description_customer": quote["request"].get("job_description_customer"),
                "job_description_internal": quote["response"].get("job_description_internal"),
                "service_type": quote["request"].get("service_type"),
                "cash_total_cad": quote["response"].get("cash_total_cad"),
                "emt_total_cad": quote["response"].get("emt_total_cad"),
                "request_json": quote["request"],
                "notes": None,
                "requested_job_date": None,
                "requested_time_window": None,
                "customer_accepted_at": None,
                "admin_approved_at": None,
            }
        )
        existing = get_quote_request_by_quote_id(quote_id)

    if action == "accept":
        update_kwargs: dict[str, Any] = {
            "status": "customer_accepted",
            "customer_accepted_at": now,
            "admin_approved_at": None,
        }
        include_optional_update_fields(body, update_kwargs, ("notes", "requested_job_date", "requested_time_window"))

        updated = update_quote_request(existing["request_id"], **update_kwargs)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update quote request")
        _maybe_auto_snapshot(background_tasks)
        return {"ok": True, "request_id": updated["request_id"], "status": updated["status"]}

    # decline
    update_kwargs = {"status": "customer_declined", "customer_accepted_at": None, "admin_approved_at": None}
    include_optional_update_fields(body, update_kwargs, ("notes", "requested_job_date", "requested_time_window"))
    updated = update_quote_request(existing["request_id"], **update_kwargs)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update quote request")
    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "request_id": updated["request_id"], "status": updated["status"]}


@app.post("/quote/upload-photos")
async def quote_upload_photos(
    background_tasks: BackgroundTasks,
    quote_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    record = get_quote_record(quote_id)
    if not record:
        raise HTTPException(status_code=404, detail="Quote not found (invalid quote_id).")

    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Photo upload is not configured (Google Drive not set).")

    if not files:
        raise HTTPException(status_code=400, detail="No files received.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Too many images (max 5).")

    MAX_TOTAL_BYTES = 10_000_000  # ~10MB total
    MAX_PER_FILE_BYTES = 5_000_000  # ~5MB each

    total_bytes = 0

    vault = _drive_call("vault setup", lambda: gdrive.ensure_vault_subfolders())
    uploads_root = vault["uploads"]
    quote_folder = _drive_call("quote folder setup", lambda: gdrive.ensure_folder(f"quote_{quote_id}", uploads_root))

    uploaded_items = []
    for f in files:
        ct = (f.content_type or "").lower().strip()

        b = await f.read()
        if not b:
            continue

        if len(b) > MAX_PER_FILE_BYTES:
            raise HTTPException(status_code=400, detail="An image is too large (max ~5MB each).")

        total_bytes += len(b)
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(status_code=400, detail="Images too large (max ~10MB total).")

        if ct and ct not in _ALLOWED_IMAGE_MIMES:
            raise HTTPException(status_code=400, detail="Unsupported image type (use JPG/PNG/WEBP/GIF).")
        if not _looks_like_supported_image(b):
            raise HTTPException(status_code=400, detail="Unsupported or invalid image content.")

        safe_name = (f.filename or "upload.jpg").replace("/", "_").replace("\\", "_").strip()
        if not safe_name:
            safe_name = "upload.jpg"

        mime_type = ct or "image/jpeg"

        df = _drive_call(
            "upload",
            lambda: gdrive.upload_bytes(
                parent_id=quote_folder.file_id,
                filename=safe_name,
                mime_type=mime_type,
                content=b,
            ),
        )

        att_id = str(uuid4())
        created_at = _now_local_iso()
        save_attachment(
            {
                "attachment_id": att_id,
                "created_at": created_at,
                "quote_id": quote_id,
                "request_id": None,
                "job_id": None,
                "filename": safe_name,
                "mime_type": mime_type,
                "size_bytes": len(b),
                "drive_file_id": df.file_id,
                "drive_web_view_link": df.web_view_link,
            }
        )

        uploaded_items.append(
            {
                "attachment_id": att_id,
                "filename": safe_name,
                "drive_file_id": df.file_id,
                "drive_web_view_link": df.web_view_link,
            }
        )

    _maybe_auto_snapshot(background_tasks)

    return {"ok": True, "uploaded": uploaded_items}


# =========================
# Admin APIs
# =========================

@app.get("/admin/api/quotes")
def admin_list_quotes(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_quotes(limit=int(limit))}


@app.get("/admin/api/quote-requests")
def admin_list_quote_requests(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_quote_requests(limit=int(limit))}


@app.get("/admin/api/jobs")
def admin_list_jobs(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_jobs(limit=int(limit))}


@app.get("/admin/api/uploads")
def admin_list_uploads(request: Request, quote_id: Optional[str] = None, limit: int = 50):
    _require_admin(request)
    return {"items": list_attachments(quote_id=quote_id, limit=int(limit))}


@app.post("/admin/api/quote-requests/{request_id}/decision")
def admin_decide_quote_request(request: Request, request_id: str, body: CustomerDecision, background_tasks: BackgroundTasks):
    _require_admin(request)

    existing = get_quote_request(request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Request not found")

    now = _now_local_iso()
    action = (body.action or "").lower()

    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Invalid action (use approve|reject)")

    if action == "approve":
        update_kwargs: dict[str, Any] = {
            "status": "admin_approved",
            "admin_approved_at": now,
        }
        include_optional_update_fields(body, update_kwargs, ("notes",))

        updated = update_quote_request(request_id, **update_kwargs)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update request")

        if not get_job_by_quote_id(updated["quote_id"]):
            job = {
                "job_id": str(uuid4()),
                "created_at": now,
                "status": "in_progress",
                "quote_id": updated["quote_id"],
                "request_id": updated["request_id"],
                "customer_name": updated.get("customer_name"),
                "customer_phone": updated.get("customer_phone"),
                "job_address": updated.get("job_address"),
                "job_description_customer": updated.get("job_description_customer"),
                "job_description_internal": updated.get("job_description_internal"),
                "service_type": updated["service_type"],
                "cash_total_cad": float(updated["cash_total_cad"]),
                "emt_total_cad": float(updated["emt_total_cad"]),
                "request_json": updated["request_json"],
                "notes": updated.get("notes"),
            }
            save_job(job)

        _maybe_auto_snapshot(background_tasks)
        return {"ok": True, "request": updated}

    # reject
    reject_kwargs: dict[str, Any] = {"status": "rejected", "admin_approved_at": None}
    include_optional_update_fields(body, reject_kwargs, ("notes",))
    updated = update_quote_request(request_id, **reject_kwargs)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update request")
    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "request": updated}