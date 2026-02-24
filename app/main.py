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
    get_quote_request_by_quote_id,
    update_quote_request,
    save_job,
    list_jobs,
    get_job_by_quote_id,
    export_db_to_json,
    import_db_from_json,
    save_attachment,
    list_attachments,
)
from app import gdrive

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


APP_VERSION = "0.9.0"
CAD = "CAD"
LOCAL_TZ_NAME = "America/Toronto"

ADMIN_TOKEN_ENV = "BAYDELIVERY_ADMIN_TOKEN"
ADMIN_USERNAME_ENV = "ADMIN_USERNAME"
ADMIN_PASSWORD_ENV = "ADMIN_PASSWORD"

GDRIVE_AUTO_SNAPSHOT_ENV = "GDRIVE_AUTO_SNAPSHOT"


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
ADMIN_UPLOADS_HTML_PATH = STATIC_DIR / "admin_uploads.html"

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

    raise HTTPException(
        status_code=401,
        detail="Admin authentication is not configured",
    )


def _drive_enabled() -> bool:
    return gdrive.is_configured()


def _drive_snapshot_db() -> dict:
    if not _drive_enabled():
        return {"ok": False, "message": "Google Drive not configured."}

    vault = gdrive.ensure_vault_subfolders()
    payload = export_db_to_json()
    payload["meta"]["exported_at"] = _now_local_iso()
    payload["meta"]["db_path"] = "app/data/bay_delivery.sqlite3"

    filename = f"bay_delivery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    uploaded = gdrive.upload_bytes(
        parent_id=vault["db_backups"],
        filename=filename,
        mime_type="application/json",
        content=body,
    )

    keep = gdrive.backup_keep_count()
    backups = gdrive.list_files(vault["db_backups"], limit=200)
    if len(backups) > keep:
        for f in backups[keep:]:
            try:
                gdrive.delete_file(f.file_id)
            except Exception:
                pass

    return {"ok": True, "file_id": uploaded.file_id, "web_view_link": uploaded.web_view_link, "name": uploaded.name}


def _maybe_auto_snapshot(background_tasks: BackgroundTasks) -> None:
    if os.getenv(GDRIVE_AUTO_SNAPSHOT_ENV, "").strip() == "1" and _drive_enabled():
        background_tasks.add_task(_drive_snapshot_db)


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


@app.get("/admin/uploads")
def admin_uploads_page(request: Request):
    _require_admin(request)
    if not ADMIN_UPLOADS_HTML_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing admin uploads file: {ADMIN_UPLOADS_HTML_PATH.as_posix()}")
    return FileResponse(ADMIN_UPLOADS_HTML_PATH)


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




class QuoteDecisionRequest(BaseModel):
    action: str = Field(..., description="accept|decline")
    requested_job_date: Optional[str] = Field(None, max_length=40)
    requested_time_window: Optional[str] = Field(None, max_length=80)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("action", "requested_job_date", "requested_time_window", "notes", mode="before")
    @classmethod
    def strip_values(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned or None
        return v


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
        "admin_basic_configured": bool(os.getenv(ADMIN_USERNAME_ENV) and os.getenv(ADMIN_PASSWORD_ENV)),
        "drive_configured": _drive_enabled(),
    }


# =========================
# Quote API
# =========================

@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest, background_tasks: BackgroundTasks):
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

    _maybe_auto_snapshot(background_tasks)

    return QuoteResponse(
        quote_id=quote_id,
        created_at=created_at_local,
        service_type=req.service_type,
        total_cash_cad=float(result["total_cash_cad"]),
        total_emt_cad=float(result["total_emt_cad"]),
        disclaimer=str(result["disclaimer"]),
    )




@app.post("/quote/{quote_id}/decision")
def quote_decision(quote_id: str, body: QuoteDecisionRequest, background_tasks: BackgroundTasks):
    quote = get_quote_record(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found (invalid quote_id).")

    action = (body.action or "").lower()
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Invalid action (use accept|decline)")

    status = "customer_accepted_pending_admin" if action == "accept" else "customer_declined"
    customer_accepted_at = _now_local_iso() if action == "accept" else None

    existing = get_quote_request_by_quote_id(quote_id)
    if existing:
        updated = update_quote_request(
            existing["request_id"],
            status=status,
            notes=body.notes,
            requested_job_date=body.requested_job_date,
            requested_time_window=body.requested_time_window,
            customer_accepted_at=customer_accepted_at,
            admin_approved_at=None,
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update quote request")
        _maybe_auto_snapshot(background_tasks)
        return {"ok": True, "request_id": updated["request_id"], "status": updated["status"]}

    request_id = str(uuid4())
    created_at = _now_local_iso()
    request_payload = quote.get("request") or {}
    response_payload = quote.get("response") or {}

    save_quote_request(
        {
            "request_id": request_id,
            "created_at": created_at,
            "status": status,
            "quote_id": quote_id,
            "customer_name": request_payload.get("customer_name"),
            "customer_phone": request_payload.get("customer_phone"),
            "job_address": request_payload.get("job_address"),
            "job_description_customer": request_payload.get("description"),
            "job_description_internal": request_payload.get("description"),
            "service_type": str(response_payload.get("service_type") or request_payload.get("service_type") or "haul_away"),
            "cash_total_cad": float(response_payload.get("total_cash_cad") or 0.0),
            "emt_total_cad": float(response_payload.get("total_emt_cad") or 0.0),
            "request_json": {
                "quote_request": request_payload,
                "decision_action": action,
            },
            "notes": body.notes,
            "requested_job_date": body.requested_job_date,
            "requested_time_window": body.requested_time_window,
            "customer_accepted_at": customer_accepted_at,
            "admin_approved_at": None,
        }
    )

    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "request_id": request_id, "status": status}


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

    total_bytes = 0
    vault = gdrive.ensure_vault_subfolders()
    uploads_root = vault["uploads"]

    quote_folder = gdrive.ensure_folder(f"quote_{quote_id}", uploads_root)

    uploaded_items = []
    for f in files:
        ct = (f.content_type or "").lower()
        if not ct.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image uploads are allowed.")

        b = await f.read()
        if not b:
            continue

        total_bytes += len(b)
        if total_bytes > 10_000_000:
            raise HTTPException(status_code=400, detail="Images too large (max ~10MB total).")

        safe_name = (f.filename or "upload.jpg").replace("/", "_").replace("\\", "_")
        df = gdrive.upload_bytes(
            parent_id=quote_folder.file_id,
            filename=safe_name,
            mime_type=ct or "image/jpeg",
            content=b,
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
                "mime_type": ct or "image/jpeg",
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
def admin_list_quote_requests(request: Request, limit: int = 50, status: Optional[str] = None):
    _require_admin(request)
    return {"items": list_quote_requests(limit=int(limit), status=status)}


@app.get("/admin/api/jobs")
def admin_list_jobs(request: Request, limit: int = 50, status: Optional[str] = None):
    _require_admin(request)
    return {"items": list_jobs(limit=int(limit), status=status)}


@app.get("/admin/api/uploads")
def admin_list_uploads(request: Request, quote_id: Optional[str] = None, limit: int = 50):
    _require_admin(request)
    return {"items": list_attachments(quote_id=quote_id, limit=int(limit))}


@app.api_route("/admin/api/drive/snapshot", methods=["GET", "POST"])
def admin_drive_snapshot(request: Request):
    _require_admin(request)
    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Google Drive not configured.")
    return _drive_snapshot_db()


@app.get("/admin/api/drive/backups")
def admin_drive_backups(request: Request, limit: int = 20):
    _require_admin(request)
    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Google Drive not configured.")
    vault = gdrive.ensure_vault_subfolders()
    files = gdrive.list_files(vault["db_backups"], limit=int(limit))
    return {
        "items": [
            {
                "file_id": f.file_id,
                "name": f.name,
                "created_time": f.created_time,
                "web_view_link": f.web_view_link,
                "size": f.size,
            }
            for f in files
        ]
    }


class AdminDriveRestore(BaseModel):
    file_id: str


@app.post("/admin/api/drive/restore")
def admin_drive_restore(request: Request, body: AdminDriveRestore):
    _require_admin(request)
    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Google Drive not configured.")
    raw = gdrive.download_file(body.file_id)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Backup file was not valid JSON.")
    return import_db_from_json(payload)


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
        "job_json": {"source": "quote_request_approved", "quote_request": request_row, "admin_notes": admin_notes},
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
def admin_decide_quote_request(request: Request, request_id: str, body: AdminDecision, background_tasks: BackgroundTasks):
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
        _maybe_auto_snapshot(background_tasks)
        return {"ok": True, "request": updated, "job": job_summary}

    updated = update_quote_request(
        request_id,
        status="rejected",
        notes=body.notes,
        admin_approved_at=None,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update request")

    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "request": updated}