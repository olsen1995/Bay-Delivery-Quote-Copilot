# Fix: __future__ import must be first
from __future__ import annotations
# (moved below app = FastAPI)
import base64
import hmac
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import uuid4

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Fallback if not available

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.abuse_controls import (
    RateLimitMiddleware,
    RateLimitRule,
    RequestSizeLimitMiddleware,
    SizeLimitRule,
    extract_client_ip,
)
from app import gcalendar, gdrive
from app.services import booking_service, job_scheduling_service, quote_service
from app.storage import (
    export_db_to_json,
    get_job,
    get_quote_record,
    import_db_from_json,
    init_db,
    Job,
    list_attachments,
    list_admin_audit_log,
    list_jobs,
    list_quote_requests,
    list_quotes,
    save_attachment,
    update_job,
)
from app.update_fields import InvalidQuoteRequestTransition
from app.audit_log import init_audit_table, log_admin_audit

APP_VERSION = (Path("VERSION").read_text(encoding="utf-8").strip() if Path("VERSION").exists() else "0.0.0")
logger = logging.getLogger(__name__)

# Initialize audit table at startup
init_audit_table()

# Admin brute-force protection (in-memory tracking)
_admin_failed_attempts: dict[str, list[float]] = {}
_admin_lockout_threshold = 5
_admin_lockout_window = 300  # seconds
_admin_list_limit_cap = 500


def _check_admin_lockout(client_ip: str) -> bool:
    """Check if client IP is locked out from too many failed attempts."""
    now = time.time()
    if client_ip in _admin_failed_attempts:
        recent_attempts = [t for t in _admin_failed_attempts[client_ip] if now - t < _admin_lockout_window]
        if not recent_attempts:
            del _admin_failed_attempts[client_ip]
            return False
        _admin_failed_attempts[client_ip] = recent_attempts
        return len(recent_attempts) >= _admin_lockout_threshold
    return False


def _record_admin_failure(client_ip: str) -> None:
    """Record a failed admin authentication attempt."""
    if client_ip not in _admin_failed_attempts:
        _admin_failed_attempts[client_ip] = []
    _admin_failed_attempts[client_ip].append(time.time())


def _reset_admin_attempts(client_ip: str) -> None:
    """Reset failed admin attempts after successful login."""
    if client_ip in _admin_failed_attempts:
        del _admin_failed_attempts[client_ip]


def _cap_admin_list_limit(limit: int) -> int:
    return min(int(limit), _admin_list_limit_cap)


def _local_iso_to_utc_iso(local_iso: str) -> str:
    """Convert local ISO datetime string to UTC ISO string.

    Assumes input is naive local time. Converts to UTC for storage.
    Uses LOCAL_TIMEZONE env var or defaults to UTC if not set.
    """
    local_dt = datetime.fromisoformat(local_iso)
    if local_dt.tzinfo is not None:
        raise ValueError("Datetime should be naive (local time)")

    # Get timezone from environment or default to UTC
    tz_name = os.getenv("LOCAL_TIMEZONE", "UTC")

    try:
        if ZoneInfo:
            local_tz = ZoneInfo(tz_name)
        else:
            # Fallback if zoneinfo not available
            local_tz = timezone.utc
    except Exception:
        # If invalid timezone name, fall back to UTC
        local_tz = timezone.utc

    local_dt = local_dt.replace(tzinfo=local_tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    return utc_dt.isoformat()


def ensure_schedulable(job: Job) -> None:
    if job.get("status") not in {"approved", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Job must be approved or scheduled before scheduling operations.",
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version=APP_VERSION,
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + job tracking.",
    lifespan=lifespan,
)

JSON_SIZE_CAP_BYTES = 256 * 1024
DB_IMPORT_SIZE_CAP_BYTES = 20 * 1024 * 1024

SIZE_LIMIT_RULES = [
    SizeLimitRule(method="POST", exact_path="/quote/upload-photos", max_bytes=12 * 1024 * 1024),
    SizeLimitRule(method="POST", exact_path="/quote/calculate", max_bytes=JSON_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", exact_path="/admin/api/db/import", max_bytes=DB_IMPORT_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", prefix_path="/admin/api/", max_bytes=JSON_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", prefix_path="/quote/", max_bytes=JSON_SIZE_CAP_BYTES),
]

RATE_LIMIT_RULES = [
    RateLimitRule(rule_id="quote_calculate", method="POST", exact_path="/quote/calculate", limit=10),
    RateLimitRule(rule_id="quote_upload_photos", method="POST", exact_path="/quote/upload-photos", limit=6),
    RateLimitRule(rule_id="quote_quote", method="POST", prefix_path="/quote/", limit=20),
    RateLimitRule(rule_id="admin_api", prefix_path="/admin/api/", limit=120),
]

# configure CORS origins via environment variable; allowlist is required in prod.
# fall back to the old CORS_ORIGINS name for backwards compatibility.
cors_env = os.getenv("BAYDELIVERY_CORS_ORIGINS")
if cors_env is None:
    cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
allow_list = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
if "*" in allow_list:
    raise ValueError("CORS wildcard origin '*' is not allowed when credentials authentication is enabled.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestSizeLimitMiddleware, rules=SIZE_LIMIT_RULES)
app.add_middleware(RateLimitMiddleware, rules=RATE_LIMIT_RULES)


# Static file cache middleware
class StaticFileCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response


app.add_middleware(StaticFileCacheMiddleware)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =========================
# Utilities
# =========================

def _now_local_iso() -> str:
    # Keep timestamps as ISO strings (local time) for admin readability.
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _drive_enabled() -> bool:
    return gdrive.is_configured()


def _require_admin(request: Request) -> None:
    """
    Admin auth: Basic Auth using ADMIN_USERNAME / ADMIN_PASSWORD.
    Includes brute-force protection with lockout after 5 failed attempts.

    IMPORTANT (CI + smoke tests):
    - If creds are not configured, we must NOT return 503 (dependency failure).
      Smoke tests expect 200/401/403.
    - Therefore: missing creds => 401.
    """
    client_ip = extract_client_ip(request)

    # Check if client is locked out
    if _check_admin_lockout(client_ip):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")

    expected_user = os.getenv("ADMIN_USERNAME", "").strip()
    expected_pass = os.getenv("ADMIN_PASSWORD", "").strip()

    if not expected_user or not expected_pass:
        raise HTTPException(status_code=401, detail="Admin credentials are not configured.")

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("basic "):
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Missing Basic auth.")

    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        user, pw = decoded.split(":", 1)
    except Exception:
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid Basic auth header.")

    user_ok = hmac.compare_digest(user, expected_user)
    pass_ok = hmac.compare_digest(pw, expected_pass)
    if not user_ok or not pass_ok:
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Success - reset attempts
    _reset_admin_attempts(client_ip)


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
        # Log detailed error server-side; return generic message to client
        logging.error(f"Google Drive error during {desc}: {e}")
        # 502 = upstream dependency failure
        raise HTTPException(status_code=502, detail="Google Drive service unavailable.")


def _invalid_status_transition_response(e: InvalidQuoteRequestTransition) -> JSONResponse:
    allowed_text = ", ".join(e.allowed) if e.allowed else "(none)"
    detail = f"Invalid status transition from {e.from_status} to {e.to_status}. Allowed: {allowed_text}"
    return JSONResponse(
        status_code=409,
        content={
            "error": "invalid_status_transition",
            "from": e.from_status,
            "to": e.to_status,
            "allowed": e.allowed,
            "detail": detail,
        },
    )


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
    # historically the snapshot toggle was AUTO_SNAPSHOT but the README
    # advertised GDRIVE_AUTO_SNAPSHOT.  Support either variable (GDRIVE_ wins)
    val = os.getenv("GDRIVE_AUTO_SNAPSHOT")
    if val is None:
        val = os.getenv("AUTO_SNAPSHOT", "1")
    if val.strip() != "1":
        return
    background_tasks.add_task(_drive_snapshot_db)


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
    return {"ok": True, "version": APP_VERSION, "drive_configured": _drive_enabled()}


# =========================
# Quote APIs
# =========================

class QuoteRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=1, max_length=50)
    job_address: str = Field(..., min_length=1, max_length=250)
    job_description_customer: Optional[str] = Field(None, max_length=1000)
    description: str = Field(..., min_length=1, max_length=1000)
    service_type: str = Field(..., max_length=50)
    payment_method: Optional[str] = Field(None, max_length=20)
    pickup_address: Optional[str] = Field(None, max_length=250)
    dropoff_address: Optional[str] = Field(None, max_length=250)
    estimated_hours: float = Field(0.0, ge=0)
    crew_size: int = Field(1, ge=1)
    garbage_bag_count: int = Field(0, ge=0)
    bag_type: Optional[Literal["light", "heavy_mixed", "construction_debris"]] = Field(None)
    trailer_fill_estimate: Optional[Literal["under_quarter", "quarter", "half", "three_quarter", "full"]] = Field(None)
    trailer_class: Optional[Literal["single_axle_open_aluminum", "double_axle_open_aluminum", "older_enclosed", "newer_enclosed"]] = Field(None)
    mattresses_count: int = Field(0, ge=0)
    box_springs_count: int = Field(0, ge=0)
    scrap_pickup_location: str = Field("curbside", max_length=50)
    travel_zone: str = Field("in_town", max_length=50)
    access_difficulty: str = Field("normal", max_length=50)
    has_dense_materials: bool = Field(False)

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
        "bag_type",
        "trailer_fill_estimate",
        "trailer_class",
        "scrap_pickup_location",
        "travel_zone",
        "access_difficulty",
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
async def quote_calculate(payload: QuoteRequestPayload):
    request_payload = payload.model_dump()
    return quote_service.build_and_save_quote(request_payload, now_iso=_now_local_iso())


class CustomerDecision(BaseModel):
    action: str = Field(..., description="accept|decline")
    accept_token: str = Field(..., description="Token from quote response")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("action", "accept_token", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


class AdminDecision(BaseModel):
    action: str = Field(..., description="approve|reject")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("action", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


class BookingDetails(BaseModel):
    booking_token: str = Field(..., description="Token from accept decision response")
    requested_job_date: str = Field(..., max_length=10, description="YYYY-MM-DD format")
    requested_time_window: str = Field(..., max_length=20, description="morning|afternoon|evening|flexible")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("booking_token", "requested_job_date", "requested_time_window", "notes", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("requested_job_date")
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("Date must be in YYYY-MM-DD format")
            raise

    @field_validator("requested_time_window")
    @classmethod
    def validate_window(cls, v):
        valid_windows = {"morning", "afternoon", "evening", "flexible"}
        if v not in valid_windows:
            raise ValueError(f"Time window must be one of: {', '.join(sorted(valid_windows))}")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v):
        if v:
            # Reject all HTML tags for defense-in-depth (frontend uses textContent)
            if '<' in v or '>' in v:
                raise ValueError("Notes cannot contain HTML tags")
        return v


class ScheduleJobPayload(BaseModel):
    scheduled_start: str = Field(..., description="Local ISO datetime (YYYY-MM-DDTHH:MM:SS)")
    scheduled_end: str = Field(..., description="Local ISO datetime (YYYY-MM-DDTHH:MM:SS)")

    @field_validator("scheduled_start", "scheduled_end", mode="before")
    @classmethod
    def strip(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("scheduled_start", "scheduled_end")
    @classmethod
    def validate_datetime(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Datetime must be in ISO format (YYYY-MM-DDTHH:MM:SS)")


@app.post("/quote/{quote_id}/decision")
def quote_decision(quote_id: str, body: CustomerDecision, background_tasks: BackgroundTasks):
    provided_fields = getattr(body, "model_fields_set", None)
    if provided_fields is None:
        provided_fields = getattr(body, "__fields_set__", set())
    notes_provided = "notes" in provided_fields
    try:
        result = booking_service.process_customer_decision(
            quote_id,
            action=body.action,
            accept_token=body.accept_token,
            notes=body.notes,
            notes_provided=notes_provided,
            now_iso=_now_local_iso(),
        )
    except InvalidQuoteRequestTransition as e:
        return _invalid_status_transition_response(e)

    _maybe_auto_snapshot(background_tasks)
    return result


@app.post("/quote/{quote_id}/booking")
async def submit_booking(quote_id: str, body: BookingDetails):
    return booking_service.submit_booking_details(
        quote_id,
        booking_token=body.booking_token,
        requested_job_date=body.requested_job_date,
        requested_time_window=body.requested_time_window,
        notes=body.notes,
    )


@app.post("/quote/upload-photos")
async def quote_upload_photos(
    background_tasks: BackgroundTasks,
    quote_id: str = Form(...),
    accept_token: str = Form(...),
    files: list[UploadFile] = File(...),
):
    record = get_quote_record(quote_id)
    if not record:
        raise HTTPException(status_code=404, detail="Quote not found (invalid quote_id).")

    server_token = record.get("accept_token")
    if not server_token or not hmac.compare_digest(accept_token, str(server_token)):
        raise HTTPException(status_code=401, detail="Invalid or expired accept token.")

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

@app.get("/admin/api/smoke_uploads")
def admin_smoke_uploads(request: Request):
    """
    Used by CI smoke tests.
    Must return:
      - 200 if authorized
      - 401/403 if unauthorized
    (Never 503 just because env vars aren't set.)
    """
    _require_admin(request)
    return {"ok": True}


@app.get("/admin/api/quotes")
def admin_list_quotes(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_quotes(limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/quote-requests")
def admin_list_quote_requests(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_quote_requests(limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/jobs")
def admin_list_jobs(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_jobs(limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/uploads")
def admin_list_uploads(request: Request, quote_id: Optional[str] = None, limit: int = 50):
    _require_admin(request)
    return {"items": list_attachments(quote_id=quote_id, limit=_cap_admin_list_limit(limit))}


@app.post("/admin/api/quote-requests/{request_id}/decision")
def admin_decide_quote_request(
    request: Request,
    request_id: str,
    body: AdminDecision,
    background_tasks: BackgroundTasks,
):
        _require_admin(request)

        # Extract admin username from Basic Auth header (same as _require_admin logic)
        header = request.headers.get("authorization") or ""
        operator_username = "unknown"
        if header.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
                user, pw = decoded.split(":", 1)
                operator_username = user or "unknown"
            except Exception:
                operator_username = "unknown"

        provided_fields = getattr(body, "model_fields_set", None)
        if provided_fields is None:
            provided_fields = getattr(body, "__fields_set__", set())
        notes_provided = "notes" in provided_fields
        try:
            result = booking_service.process_admin_decision(
                request_id,
                action=body.action,
                notes=body.notes,
                notes_provided=notes_provided,
                now_iso=_now_local_iso(),
            )
            log_admin_audit(
                operator_username=operator_username,
                action_type=body.action,
                entity_type="quote_request",
                record_id=request_id,
                success=True,
            )
            _maybe_auto_snapshot(background_tasks)
            return result
        except InvalidQuoteRequestTransition as e:
            log_admin_audit(
                operator_username=operator_username,
                action_type=body.action,
                entity_type="quote_request",
                record_id=request_id,
                success=False,
                error_summary=str(e),
            )
            return _invalid_status_transition_response(e)


@app.post("/admin/api/jobs/{job_id}/schedule")
def admin_schedule_job(request: Request, job_id: str, body: ScheduleJobPayload):
    _require_admin(request)

    # Convert local to UTC
    try:
        start_utc = _local_iso_to_utc_iso(body.scheduled_start)
        end_utc = _local_iso_to_utc_iso(body.scheduled_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {e}")

    # Delegate to service layer
    try:
        job = job_scheduling_service.schedule_job(job_id, start_utc, end_utc)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="schedule_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "must be after" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        if "not schedulable" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="schedule_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/admin/api/jobs/{job_id}/reschedule")
def admin_reschedule_job(request: Request, job_id: str, body: ScheduleJobPayload):
    _require_admin(request)

    # Convert local to UTC
    try:
        start_utc = _local_iso_to_utc_iso(body.scheduled_start)
        end_utc = _local_iso_to_utc_iso(body.scheduled_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {e}")

    # Delegate to service layer
    try:
        job = job_scheduling_service.reschedule_job(job_id, start_utc, end_utc)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="reschedule_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "must be after" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        if "not schedulable" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        if "not scheduled" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="reschedule_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/admin/api/jobs/{job_id}/cancel")
def admin_cancel_job(request: Request, job_id: str):
    _require_admin(request)

    # Delegate to service layer
    try:
        job = job_scheduling_service.cancel_job(job_id)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="cancel_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        log_admin_audit(
            operator_username=os.getenv("ADMIN_USERNAME", "").strip(),
            action_type="cancel_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        raise HTTPException(status_code=400, detail=error_msg)


# =========================
# Admin DB Backup/Restore (JSON)
# =========================

@app.get("/admin/api/db/export")
def admin_db_export(request: Request):
    _require_admin(request)

    payload = export_db_to_json()
    payload["meta"]["exported_at"] = _now_local_iso()
    payload["meta"]["db_path"] = "app/data/bay_delivery.sqlite3"

    filename = f"bay_delivery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/json; charset=utf-8",
    }
    return Response(content=body, headers=headers, media_type="application/json")


class ImportPayload(BaseModel):
    payload: dict = Field(...)


class DriveRestorePayload(BaseModel):
    file_id: str = Field(...)

    @field_validator("file_id")
    @classmethod
    def validate_file_id(cls, v: str) -> str:
        value = v.strip() if isinstance(v, str) else ""
        if not value:
            raise ValueError("file_id is required")
        try:
            return gdrive.validate_drive_file_id(value)
        except ValueError as exc:
            raise ValueError(str(exc))


@app.post("/admin/api/db/import")
def admin_db_import(request: Request, body: ImportPayload, background_tasks: BackgroundTasks):
    _require_admin(request)
    result = import_db_from_json(body.payload)
    _maybe_auto_snapshot(background_tasks)
    return result


# =========================
# Admin Drive Vault
# =========================

@app.get("/admin/api/drive/status")
def admin_drive_status(request: Request):
    _require_admin(request)
    return {"ok": True, "drive_configured": _drive_enabled()}


@app.post("/admin/api/drive/snapshot")
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

    vault = _drive_call("vault setup", lambda: gdrive.ensure_vault_subfolders())
    backups = _drive_call("list backups", lambda: gdrive.list_files(vault["db_backups"], limit=_cap_admin_list_limit(limit)))

    items = []
    for f in backups:
        items.append(
            {
                "file_id": f.file_id,
                "name": f.name,
                "created_time": getattr(f, "created_time", None) or getattr(f, "createdTime", None) or "",
                "size": getattr(f, "size", None) or "",
                "web_view_link": f.web_view_link,
            }
        )

    return {"items": items}


@app.post("/admin/api/drive/restore")
def admin_drive_restore(request: Request, body: DriveRestorePayload, background_tasks: BackgroundTasks):
    _require_admin(request)
    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Google Drive not configured.")

    logger.info("Starting Drive DB restore from file_id=%s", body.file_id)

    backup_bytes = _drive_call("download backup", lambda: gdrive.download_file(body.file_id))
    try:
        payload = json.loads(backup_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid backup JSON.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Backup payload must be a JSON object.")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise HTTPException(status_code=400, detail="Backup payload missing 'tables' object.")

    meta = payload.get("meta")
    if isinstance(meta, dict):
        backup_format = meta.get("format")
        if backup_format is not None and backup_format != "bay-delivery-sqlite-backup":
            raise HTTPException(status_code=400, detail="Unsupported backup format.")

    try:
        result = import_db_from_json(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _maybe_auto_snapshot(background_tasks)
    logger.info("Drive DB restore completed for file_id=%s", body.file_id)
    return {
        "ok": bool(result.get("ok", True)),
        "restored": result.get("restored", {}),
        "restored_from_file_id": body.file_id,
    }


# =========================
# Admin Audit Log API
# =========================

@app.get("/admin/api/audit-log")
def admin_audit_log(request: Request):
    """
    Returns the latest 50 admin audit log entries as JSON.
    Requires admin authentication.
    """
    _require_admin(request)
    return {"items": list_admin_audit_log(limit=50)}
