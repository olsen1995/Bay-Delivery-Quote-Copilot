from __future__ import annotations
from collections import deque
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal, Optional
from urllib.parse import urlsplit
from uuid import uuid4

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Fallback if not available

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.abuse_controls import (
    RateLimitMiddleware,
    RateLimitRule,
    RequestSizeLimitMiddleware,
    SizeLimitRule,
    extract_client_ip,
)
from app import gcalendar, gdrive, storage
from app.services import (
    admin_ops_queue,
    booking_notification_service,
    booking_service,
    completed_job_profit_report,
    job_scheduling_service,
    quote_service,
    screenshot_assistant_service,
    screenshot_ocr_service,
)
from app.storage import (
    export_db_to_json,
    get_completed_job_calibration_entry,
    get_gpt_admin_note_by_idempotency_key,
    get_job,
    GptAdminNoteDuplicatePayload,
    GptAdminNoteIdempotencyReplay,
    GptQuoteObservabilityRecord,
    get_quote_record,
    import_db_from_json,
    init_db,
    is_token_expired,
    Job,
    list_completed_job_calibration_entries,
    list_attachments,
    list_admin_audit_log,
    list_gpt_admin_notes,
    list_gpt_quote_observability,
    list_jobs,
    list_quote_requests,
    list_quotes,
    save_attachment,
    save_completed_job_calibration_entry,
    save_gpt_admin_note,
    save_gpt_quote_observability_event,
    update_job,
    update_job_costing,
    update_quote_admin_status,
    update_quote_request_followup_status,
)
from app.update_fields import InvalidJobTransition, InvalidQuoteRequestTransition
from app.audit_log import init_audit_table, log_admin_audit

APP_VERSION = (Path("VERSION").read_text(encoding="utf-8").strip() if Path("VERSION").exists() else "0.0.0")
logger = logging.getLogger(__name__)
_DEFAULT_LOCAL_TIMEZONE = "UTC"
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:8000"
_DEPLOY_COMMIT_ENV_VARS = ("BAYDELIVERY_COMMIT_SHA", "RENDER_GIT_COMMIT")
_DEPLOY_COMMIT_HEX_RE = re.compile(r"^[0-9a-fA-F]{12,64}$")

# Initialize audit table at startup
init_audit_table()

# Admin brute-force protection (in-memory tracking)
_admin_failed_attempts: dict[str, list[float]] = {}
_admin_lockout_threshold = 5
_admin_lockout_window = 300  # seconds
_admin_list_limit_cap = 500
_gpt_quote_rate_limit = 10
_gpt_quote_rate_limit_window = 60
_gpt_quote_rate_limit_buckets: dict[str, deque[float]] = {}
_gpt_quote_rate_limit_lock = Lock()
_gpt_admin_notes_rate_limit = 5
_gpt_admin_notes_rate_limit_window = 60
_gpt_admin_notes_rate_limit_buckets: dict[str, deque[float]] = {}
_gpt_admin_notes_rate_limit_lock = Lock()
_ADMIN_VALIDATION_AUDIT_MAX_SUMMARY_LENGTH = 240
_GPT_QUOTE_ROUTE_NAME = "/api/gpt/quote"
_GPT_ADMIN_NOTES_ROUTE_NAME = "/api/gpt/admin-notes"
_GPT_QUOTE_OBSERVABILITY_STATE_KEY = "gpt_quote_observability"
_GPT_GROUNDING_REVISION_HEADER = "x-gpt-grounding-revision"
_MAX_GROUNDING_REVISION_LENGTH = 120
_GPT_ADMIN_NOTE_DUPLICATE_WINDOW_SECONDS = 300
_ADMIN_VALIDATION_AUDIT_ROUTES: dict[tuple[str, str], dict[str, str]] = {
    ("POST", "/admin/api/db/import"): {
        "action_type": "import_db",
        "entity_type": "database",
        "record_id": "primary",
    },
    ("POST", "/admin/api/manual-completed-jobs"): {
        "action_type": "create_manual_completed_job_calibration_entry",
        "entity_type": "completed_job_calibration_entry",
        "record_id": "draft",
    },
    ("POST", "/admin/api/drive/restore"): {
        "action_type": "drive_restore",
        "entity_type": "drive_backup",
        "record_id": "pending",
    },
}


def _init_gpt_quote_observability(request: Request) -> dict[str, Any]:
    payload = getattr(request.state, _GPT_QUOTE_OBSERVABILITY_STATE_KEY, None)
    if isinstance(payload, dict):
        return payload

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route_name": _GPT_QUOTE_ROUTE_NAME,
        "success": False,
        "normalized_service_type": None,
        "cash_total_cad": None,
        "emt_total_cad": None,
        "confidence_level": None,
        "risk_flags": [],
        "failure_reason": None,
        "latency_ms": None,
        "server_grounding_revision": None,
        "caller_grounding_revision": None,
        "started_at": time.perf_counter(),
        "logged": False,
    }
    setattr(request.state, _GPT_QUOTE_OBSERVABILITY_STATE_KEY, payload)
    return payload


def _finalize_gpt_quote_observability(
    request: Request,
    *,
    success: bool,
    normalized_service_type: str | None = None,
    cash_total_cad: float | None = None,
    emt_total_cad: float | None = None,
    confidence_level: str | None = None,
    risk_flags: list[str] | None = None,
    failure_reason: str | None = None,
    server_grounding_revision: str | None = None,
    caller_grounding_revision: str | None = None,
) -> None:
    payload = _init_gpt_quote_observability(request)
    if payload.get("logged"):
        return

    started_at = payload.get("started_at")
    latency_ms: int | None = None
    if isinstance(started_at, (int, float)):
        latency_ms = int((time.perf_counter() - started_at) * 1000)

    payload.update(
        {
            "success": success,
            "normalized_service_type": normalized_service_type,
            "cash_total_cad": cash_total_cad,
            "emt_total_cad": emt_total_cad,
            "confidence_level": confidence_level,
            "risk_flags": [str(flag) for flag in (risk_flags or [])],
            "failure_reason": failure_reason,
            "latency_ms": latency_ms,
            "server_grounding_revision": server_grounding_revision,
            "caller_grounding_revision": caller_grounding_revision,
            "logged": True,
        }
    )

    record: GptQuoteObservabilityRecord = {
        "timestamp": str(payload["timestamp"]),
        "route_name": str(payload["route_name"]),
        "success": bool(payload["success"]),
        "normalized_service_type": (
            str(payload["normalized_service_type"])
            if payload.get("normalized_service_type") is not None
            else None
        ),
        "cash_total_cad": float(payload["cash_total_cad"]) if payload.get("cash_total_cad") is not None else None,
        "emt_total_cad": float(payload["emt_total_cad"]) if payload.get("emt_total_cad") is not None else None,
        "confidence_level": str(payload["confidence_level"]) if payload.get("confidence_level") is not None else None,
        "risk_flags": [str(flag) for flag in payload.get("risk_flags") or []],
        "failure_reason": str(payload["failure_reason"]) if payload.get("failure_reason") is not None else None,
        "latency_ms": int(payload["latency_ms"]) if payload.get("latency_ms") is not None else None,
        "server_grounding_revision": (
            str(payload["server_grounding_revision"])
            if payload.get("server_grounding_revision") is not None
            else None
        ),
        "caller_grounding_revision": (
            str(payload["caller_grounding_revision"])
            if payload.get("caller_grounding_revision") is not None
            else None
        ),
    }
    try:
        save_gpt_quote_observability_event(record)
    except Exception:
        logger.exception(
            "Best-effort GPT quote observability logging failed for route=%s failure_reason=%s",
            record["route_name"],
            record["failure_reason"],
        )


def _gpt_failure_reason_from_status_code(status_code: int) -> str:
    if status_code == 400:
        return "invalid_request"
    if status_code == 401:
        return "auth_failed"
    if status_code == 404:
        return "endpoint_disabled"
    if status_code == 429:
        return "rate_limited"
    return "http_error"


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


def _operator_safe_notification_error(status: Any, last_error: Any) -> Optional[str]:
    if last_error is None:
        return None
    text = str(last_error).strip()
    if not text:
        return None

    normalized_status = str(status or "").lower()
    if normalized_status == "failed":
        return "send failed"

    sensitive_patterns = (
        r"bearer\s+",
        r"password",
        r"secret",
        r"token",
        r"sk-[A-Za-z0-9_-]+",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in sensitive_patterns):
        return "notification details unavailable"

    return text[:160]


def _booking_notification_summary(request_id: Any) -> dict[str, Any]:
    if not request_id:
        return {
            "status": "unavailable",
            "channel": None,
            "attempt_count": 0,
            "updated_at": None,
            "sent_at": None,
            "last_error": None,
        }

    attempt = storage.get_notification_attempt(
        str(request_id),
        booking_notification_service.BOOKING_SUBMITTED_EVENT_TYPE,
    )
    if not attempt:
        return {
            "status": "unavailable",
            "channel": None,
            "attempt_count": 0,
            "updated_at": None,
            "sent_at": None,
            "last_error": None,
        }

    status = attempt.get("status") or "unavailable"
    return {
        "status": status,
        "channel": attempt.get("channel"),
        "attempt_count": int(attempt.get("attempt_count") or 0),
        "updated_at": attempt.get("updated_at"),
        "sent_at": attempt.get("sent_at"),
        "last_error": _operator_safe_notification_error(status, attempt.get("last_error")),
    }


def _parse_basic_auth_credentials(header: str) -> tuple[str, str] | None:
    if not header.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        user, pw = decoded.split(":", 1)
    except Exception:
        return None
    return user, pw


def _configured_admin_credentials() -> tuple[str, str] | None:
    expected_user = os.getenv("ADMIN_USERNAME", "").strip()
    expected_pass = os.getenv("ADMIN_PASSWORD", "").strip()
    if not expected_user or not expected_pass:
        return None
    return expected_user, expected_pass


def _configured_gpt_internal_token() -> str | None:
    token = os.getenv("GPT_INTERNAL_API_TOKEN", "").strip()
    return token or None


def _configured_gpt_grounding_revision() -> str | None:
    revision = os.getenv("GPT_GROUNDING_REVISION", "").strip()
    if not revision:
        return None
    return revision[:_MAX_GROUNDING_REVISION_LENGTH]


def _caller_declared_gpt_grounding_revision(request: Request) -> str | None:
    revision = (request.headers.get(_GPT_GROUNDING_REVISION_HEADER) or "").strip()
    if not revision:
        return None
    return revision[:_MAX_GROUNDING_REVISION_LENGTH]


def _admin_operator_username(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    credentials = _parse_basic_auth_credentials(header)
    if credentials is not None:
        user, _pw = credentials
        if user:
            return user
    configured_credentials = _configured_admin_credentials()
    if configured_credentials is not None:
        return configured_credentials[0]
    return "unknown"


def _local_iso_to_utc_iso(local_iso: str) -> str:
    """Convert local ISO datetime string to UTC ISO string.

    Assumes input is naive local time. Converts to UTC for storage.
    Uses LOCAL_TIMEZONE env var or defaults to UTC if not set.
    """
    local_dt = datetime.fromisoformat(local_iso)
    if local_dt.tzinfo is not None:
        raise ValueError("Datetime should be naive (local time)")

    # Get timezone from environment or default to UTC
    tz_name = os.getenv("LOCAL_TIMEZONE", _DEFAULT_LOCAL_TIMEZONE)

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


def _warn_on_env_fallbacks() -> None:
    tz_name = os.getenv("LOCAL_TIMEZONE")
    if not tz_name:
        logger.warning("LOCAL_TIMEZONE is unset; falling back to UTC.")
    elif ZoneInfo is not None:
        try:
            ZoneInfo(tz_name)
        except Exception:
            logger.warning("LOCAL_TIMEZONE=%r is invalid; falling back to UTC.", tz_name)

    cors_env = os.getenv("BAYDELIVERY_CORS_ORIGINS")
    if cors_env is not None:
        return

    legacy_cors_env = os.getenv("CORS_ORIGINS")
    if legacy_cors_env is not None:
        logger.warning("BAYDELIVERY_CORS_ORIGINS is unset; using legacy CORS_ORIGINS.")
        return

    logger.warning("BAYDELIVERY_CORS_ORIGINS is unset; falling back to localhost CORS defaults.")


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
    SizeLimitRule(
        method="POST",
        path_regex=re.compile(r"^/admin/api/screenshot-assistant/analyses/[^/]+/attachments$"),
        max_bytes=12 * 1024 * 1024,
    ),
    SizeLimitRule(method="POST", exact_path="/quote/calculate", max_bytes=JSON_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", exact_path="/api/gpt/quote", max_bytes=JSON_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", exact_path="/api/gpt/admin-notes", max_bytes=16 * 1024),
    SizeLimitRule(method="POST", exact_path="/admin/api/db/import", max_bytes=DB_IMPORT_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", prefix_path="/admin/api/", max_bytes=JSON_SIZE_CAP_BYTES),
    SizeLimitRule(method="POST", prefix_path="/quote/", max_bytes=JSON_SIZE_CAP_BYTES),
]

RATE_LIMIT_RULES = [
    RateLimitRule(rule_id="quote_calculate", method="POST", exact_path="/quote/calculate", limit=10),
    RateLimitRule(rule_id="quote_upload_photos", method="POST", exact_path="/quote/upload-photos", limit=6),
    RateLimitRule(
        rule_id="assistant_upload_photos",
        method="POST",
        path_regex=re.compile(r"^/admin/api/screenshot-assistant/analyses/[^/]+/attachments$"),
        limit=6,
    ),
    RateLimitRule(rule_id="quote_quote", method="POST", prefix_path="/quote/", limit=20),
    RateLimitRule(rule_id="admin_api", prefix_path="/admin/api/", limit=120),
]

_warn_on_env_fallbacks()

# configure CORS origins via environment variable; allowlist is required in prod.
# fall back to the old CORS_ORIGINS name for backwards compatibility.
cors_env = os.getenv("BAYDELIVERY_CORS_ORIGINS")
if cors_env is None:
    cors_env = os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
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


def _now_local_iso_microseconds() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _drive_enabled() -> bool:
    return gdrive.is_configured()


def _health_commit_fingerprint() -> str | None:
    for env_name in _DEPLOY_COMMIT_ENV_VARS:
        commit = os.getenv(env_name, "").strip()
        if commit and _DEPLOY_COMMIT_HEX_RE.fullmatch(commit):
            return commit[:12].lower()
    return None


def _enforce_admin_post_origin(request: Request) -> None:
    if request.method != "POST" or not request.url.path.startswith("/admin/api/"):
        return

    origin = (request.headers.get("origin") or "").strip()
    referer = (request.headers.get("referer") or "").strip()
    sec_fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()

    if origin:
        if origin not in allow_list:
            raise HTTPException(status_code=403, detail="Origin not allowed for admin POST request.")
        return

    if sec_fetch_site and sec_fetch_site != "same-origin":
        raise HTTPException(status_code=403, detail="Origin not allowed for admin POST request.")

    if referer:
        referer_origin = _origin_from_referer(referer)
        if referer_origin not in allow_list:
            raise HTTPException(status_code=403, detail="Origin not allowed for admin POST request.")
        return


def _origin_from_referer(referer: str) -> str | None:
    try:
        parsed = urlsplit(referer)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _resolve_authenticated_admin_username(request: Request) -> str | None:
    configured_credentials = _configured_admin_credentials()
    if configured_credentials is None:
        return None

    if _check_admin_lockout(extract_client_ip(request)):
        return None

    credentials = _parse_basic_auth_credentials(request.headers.get("authorization") or "")
    if credentials is None:
        return None

    user, pw = credentials
    expected_user, expected_pass = configured_credentials
    if not hmac.compare_digest(user, expected_user) or not hmac.compare_digest(pw, expected_pass):
        return None

    try:
        _enforce_admin_post_origin(request)
    except HTTPException:
        return None

    return user


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

    configured_credentials = _configured_admin_credentials()
    if configured_credentials is None:
        raise HTTPException(status_code=401, detail="Admin credentials are not configured.")

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("basic "):
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Missing Basic auth.")

    credentials = _parse_basic_auth_credentials(header)
    if credentials is None:
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid Basic auth header.")

    user, pw = credentials
    expected_user, expected_pass = configured_credentials
    user_ok = hmac.compare_digest(user, expected_user)
    pass_ok = hmac.compare_digest(pw, expected_pass)
    if not user_ok or not pass_ok:
        _record_admin_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Success - reset attempts
    _reset_admin_attempts(client_ip)
    _enforce_admin_post_origin(request)


def _require_gpt_internal_token(request: Request) -> None:
    _init_gpt_quote_observability(request)
    server_grounding_revision = _configured_gpt_grounding_revision()
    caller_grounding_revision = _caller_declared_gpt_grounding_revision(request)
    expected_token = _configured_gpt_internal_token()
    if expected_token is None:
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="endpoint_disabled",
            server_grounding_revision=server_grounding_revision,
            caller_grounding_revision=caller_grounding_revision,
        )
        raise HTTPException(status_code=404, detail="Not found.")

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="auth_failed",
            server_grounding_revision=server_grounding_revision,
            caller_grounding_revision=caller_grounding_revision,
        )
        raise HTTPException(status_code=401, detail="Invalid internal API token.")

    provided_token = header.split(" ", 1)[1].strip()
    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="auth_failed",
            server_grounding_revision=server_grounding_revision,
            caller_grounding_revision=caller_grounding_revision,
        )
        raise HTTPException(status_code=401, detail="Invalid internal API token.")

    _enforce_gpt_quote_rate_limit(request)


def _request_has_valid_gpt_internal_token(request: Request) -> bool:
    expected_token = _configured_gpt_internal_token()
    if expected_token is None:
        return False

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return False

    provided_token = header.split(" ", 1)[1].strip()
    return bool(provided_token) and hmac.compare_digest(provided_token, expected_token)


def _require_gpt_admin_notes_token(request: Request) -> None:
    expected_token = _configured_gpt_internal_token()
    if expected_token is None:
        raise HTTPException(status_code=404, detail="Not found.")

    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid internal API token.")

    provided_token = header.split(" ", 1)[1].strip()
    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid internal API token.")


def _enforce_gpt_quote_rate_limit(request: Request) -> None:
    ip = extract_client_ip(request)
    now = time.time()
    window_start = now - _gpt_quote_rate_limit_window
    is_rate_limited = False

    with _gpt_quote_rate_limit_lock:
        bucket = _gpt_quote_rate_limit_buckets.setdefault(ip, deque())

        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if not bucket:
            _gpt_quote_rate_limit_buckets.pop(ip, None)
            bucket = _gpt_quote_rate_limit_buckets.setdefault(ip, deque())

        if len(bucket) >= _gpt_quote_rate_limit:
            is_rate_limited = True
        else:
            bucket.append(now)

    if is_rate_limited:
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="rate_limited",
            server_grounding_revision=_configured_gpt_grounding_revision(),
            caller_grounding_revision=_caller_declared_gpt_grounding_revision(request),
        )
        raise HTTPException(status_code=429, detail="rate limit exceeded")


def clear_gpt_quote_rate_limit_state() -> None:
    with _gpt_quote_rate_limit_lock:
        _gpt_quote_rate_limit_buckets.clear()


def _enforce_gpt_admin_notes_rate_limit(request: Request) -> None:
    ip = extract_client_ip(request)
    now = time.time()
    window_start = now - _gpt_admin_notes_rate_limit_window
    is_rate_limited = False

    with _gpt_admin_notes_rate_limit_lock:
        bucket = _gpt_admin_notes_rate_limit_buckets.setdefault(ip, deque())

        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if not bucket:
            _gpt_admin_notes_rate_limit_buckets.pop(ip, None)
            bucket = _gpt_admin_notes_rate_limit_buckets.setdefault(ip, deque())

        if len(bucket) >= _gpt_admin_notes_rate_limit:
            is_rate_limited = True
        else:
            bucket.append(now)

    if is_rate_limited:
        raise HTTPException(status_code=429, detail="rate limit exceeded")


def clear_gpt_admin_notes_rate_limit_state() -> None:
    with _gpt_admin_notes_rate_limit_lock:
        _gpt_admin_notes_rate_limit_buckets.clear()


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


def _try_log_admin_audit(**kwargs: Any) -> None:
    try:
        log_admin_audit(**kwargs)
    except Exception:
        logger.exception(
            "Best-effort admin audit logging failed for action_type=%s entity_type=%s record_id=%s",
            kwargs.get("action_type"),
            kwargs.get("entity_type"),
            kwargs.get("record_id"),
        )


def _summarize_validation_error(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Validation failed."

    first_error = errors[0]
    location = ".".join(str(part) for part in first_error.get("loc") or () if part is not None)
    message = str(first_error.get("msg") or "Validation failed.")
    summary = f"{location}: {message}" if location else message
    summary = " ".join(summary.split())
    if len(summary) <= _ADMIN_VALIDATION_AUDIT_MAX_SUMMARY_LENGTH:
        return summary
    return summary[: _ADMIN_VALIDATION_AUDIT_MAX_SUMMARY_LENGTH - 3].rstrip() + "..."


@app.exception_handler(RequestValidationError)
async def request_validation_audit_handler(request: Request, exc: RequestValidationError):
    audit_metadata = _ADMIN_VALIDATION_AUDIT_ROUTES.get((request.method.upper(), request.url.path))
    if audit_metadata is not None:
        operator_username = _resolve_authenticated_admin_username(request)
        if operator_username is not None:
            _try_log_admin_audit(
                operator_username=operator_username,
                success=False,
                error_summary=_summarize_validation_error(exc),
                **audit_metadata,
            )
    if request.method.upper() == "POST" and request.url.path == _GPT_QUOTE_ROUTE_NAME:
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="validation_error",
            server_grounding_revision=_configured_gpt_grounding_revision(),
            caller_grounding_revision=_caller_declared_gpt_grounding_revision(request),
        )
    if request.method.upper() == "POST" and request.url.path == _GPT_ADMIN_NOTES_ROUTE_NAME:
        if _request_has_valid_gpt_internal_token(request):
            _try_log_admin_audit(
                operator_username="internal_gpt",
                action_type="create_gpt_admin_note",
                entity_type="gpt_admin_note",
                record_id="validation_error",
                success=False,
                error_summary=_summarize_validation_error(exc),
            )
    return await request_validation_exception_handler(request, exc)


def _safe_upload_filename(filename: str | None) -> str:
    safe_name = (filename or "upload.jpg").replace("/", "_").replace("\\", "_").strip()
    return safe_name or "upload.jpg"


async def _store_image_attachments(
    *,
    files: list[UploadFile],
    folder_name: str,
    quote_id: str | None = None,
    analysis_id: str | None = None,
) -> list[dict[str, Any]]:
    if not _drive_enabled():
        raise HTTPException(status_code=501, detail="Photo upload is not configured (Google Drive not set).")

    if not files:
        raise HTTPException(status_code=400, detail="No files received.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Too many images (max 5).")

    max_total_bytes = 10_000_000  # ~10MB total
    max_per_file_bytes = 5_000_000  # ~5MB each
    total_bytes = 0

    vault = _drive_call("vault setup", lambda: gdrive.ensure_vault_subfolders())
    target_folder = _drive_call(
        "attachment folder setup",
        lambda: gdrive.ensure_folder(folder_name, vault["uploads"]),
    )

    uploaded_items: list[dict[str, Any]] = []
    for upload in files:
        mime_type = (upload.content_type or "").lower().strip()
        content = await upload.read()
        if not content:
            continue

        if len(content) > max_per_file_bytes:
            raise HTTPException(status_code=400, detail="An image is too large (max ~5MB each).")

        total_bytes += len(content)
        if total_bytes > max_total_bytes:
            raise HTTPException(status_code=400, detail="Images too large (max ~10MB total).")

        if mime_type and mime_type not in _ALLOWED_IMAGE_MIMES:
            raise HTTPException(status_code=400, detail="Unsupported image type (use JPG/PNG/WEBP/GIF).")
        if not _looks_like_supported_image(content):
            raise HTTPException(status_code=400, detail="Unsupported or invalid image content.")

        safe_name = _safe_upload_filename(upload.filename)
        normalized_mime_type = mime_type or "image/jpeg"
        drive_file = _drive_call(
            "upload",
            lambda: gdrive.upload_bytes(
                parent_id=target_folder.file_id,
                filename=safe_name,
                mime_type=normalized_mime_type,
                content=content,
            ),
        )

        attachment_id = str(uuid4())
        created_at = _now_local_iso()
        ocr_payload = screenshot_ocr_service.extract_attachment_ocr(
            filename=safe_name,
            content=content,
        )
        save_attachment(
            {
                "attachment_id": attachment_id,
                "created_at": created_at,
                "quote_id": quote_id,
                "request_id": None,
                "job_id": None,
                "analysis_id": analysis_id,
                "filename": safe_name,
                "mime_type": normalized_mime_type,
                "size_bytes": len(content),
                "drive_file_id": drive_file.file_id,
                "drive_web_view_link": drive_file.web_view_link,
                "ocr_json": ocr_payload,
            }
        )
        uploaded_items.append(
            {
                "attachment_id": attachment_id,
                "created_at": created_at,
                "quote_id": quote_id,
                "analysis_id": analysis_id,
                "filename": safe_name,
                "mime_type": normalized_mime_type,
                "size_bytes": len(content),
                "drive_file_id": drive_file.file_id,
                "drive_web_view_link": drive_file.web_view_link,
                "ocr_json": ocr_payload,
            }
        )

    return uploaded_items


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


def _invalid_job_transition_response(e: InvalidJobTransition) -> JSONResponse:
    allowed_text = ", ".join(e.allowed) if e.allowed else "(none)"
    detail = f"Invalid job status transition from {e.from_status} to {e.to_status}. Allowed: {allowed_text}"
    return JSONResponse(
        status_code=409,
        content={
            "error": "invalid_job_status_transition",
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
    payload["meta"].pop("db_path", None)

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


@app.get("/admin/mobile")
def admin_mobile_page():
    return FileResponse(str(STATIC_DIR / "admin_mobile.html"))


@app.get("/admin/uploads")
def admin_uploads_page():
    return FileResponse(str(STATIC_DIR / "admin_uploads.html"))


# =========================
# Health
# =========================

@app.get("/health")
def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "drive_configured": _drive_enabled(),
        "commit": _health_commit_fingerprint(),
    }


# =========================
# Quote APIs
# =========================

STRUCTURED_INTAKE_FIELD_NAMES = (
    "stairs_count",
    "floor_count",
    "basement_or_inside_removal",
    "demolition_ripout",
    "construction_debris_type",
    "dense_material_type",
    "mixed_load",
    "contains_scrap",
    "contains_garbage",
    "has_refrigerant_appliance",
    "appliance_type",
    "weather_protection_required",
)


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
    load_mode: Optional[str] = Field("standard", max_length=20)
    lead_source: Optional[Literal["facebook", "google", "referral", "marketplace", "repeat_customer", "other", "unknown"]] = Field("unknown")
    stairs_count: Optional[int] = Field(None, ge=0)
    floor_count: Optional[int] = Field(None, ge=0)
    basement_or_inside_removal: Optional[bool] = Field(None)
    demolition_ripout: Optional[bool] = Field(None)
    construction_debris_type: Optional[Literal["drywall", "wood", "tile", "concrete", "shingles", "mixed", "other"]] = Field(None)
    dense_material_type: Optional[Literal["drywall", "tile", "concrete", "shingles", "soil", "brick", "stone", "mixed", "other"]] = Field(None)
    mixed_load: Optional[bool] = Field(None)
    contains_scrap: Optional[bool] = Field(None)
    contains_garbage: Optional[bool] = Field(None)
    has_refrigerant_appliance: Optional[bool] = Field(None)
    appliance_type: Optional[Literal["fridge", "freezer", "air_conditioner", "dehumidifier", "washer", "dryer", "stove", "dishwasher", "water_heater", "other"]] = Field(None)
    weather_protection_required: Optional[bool] = Field(None)

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
        "load_mode",
        mode="before",
    )
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "construction_debris_type",
        "dense_material_type",
        "appliance_type",
        mode="before",
    )
    @classmethod
    def normalize_optional_select(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            value = v.strip().lower()
            return value or None
        return v

    @field_validator("lead_source", mode="before")
    @classmethod
    def normalize_lead_source(cls, v):
        if v is None:
            return "unknown"
        if isinstance(v, str):
            value = v.strip()
            return value or "unknown"
        return v


class GptQuoteRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_type: str = Field(..., max_length=50)
    description: str = Field(..., min_length=1, max_length=1000)
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
    load_mode: Optional[str] = Field("standard", max_length=20)

    @field_validator(
        "service_type",
        "description",
        "pickup_address",
        "dropoff_address",
        "bag_type",
        "trailer_fill_estimate",
        "trailer_class",
        "scrap_pickup_location",
        "travel_zone",
        "access_difficulty",
        "load_mode",
        mode="before",
    )
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v


class GptAdminNotePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    related_entity_type: Literal[
        "quote",
        "quote_request",
        "job",
        "completed_job_calibration_entry",
        "general",
    ]
    related_entity_id: Optional[str] = Field(None, max_length=160)
    note_type: Literal[
        "job_observation",
        "quote_caution",
        "missing_info",
        "follow_up_recommendation",
        "completed_job_calibration_observation",
        "customer_message_draft",
        "photo_access_density_risk",
        "owner_review_context",
    ]
    title: str = Field(..., min_length=1, max_length=120)
    summary: str = Field(..., min_length=1, max_length=1200)
    recommendation: Optional[str] = Field(None, max_length=1000)
    customer_message_draft: Optional[str] = Field(None, max_length=1000)
    risk_flags: list[str] = Field(default_factory=list, max_length=10)
    follow_up_needed: bool = False
    idempotency_key: Optional[str] = Field(None, max_length=160)

    @field_validator(
        "related_entity_id",
        "title",
        "summary",
        "recommendation",
        "customer_message_draft",
        "idempotency_key",
        mode="before",
    )
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None
        return v

    @field_validator("risk_flags", mode="before")
    @classmethod
    def normalize_risk_flags(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("risk_flags must be a list")
        normalized: list[str] = []
        for item in v:
            text = str(item).strip().lower()
            text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
            if len(text) > 40:
                raise ValueError("risk flag values must be 40 characters or fewer")
            if text and text not in normalized:
                normalized.append(text)
            if len(normalized) > 10:
                raise ValueError("risk_flags may include at most 10 items")
        return normalized

    @model_validator(mode="after")
    def require_related_entity_id(self):
        if self.related_entity_type != "general" and not self.related_entity_id:
            raise ValueError("related_entity_id is required unless related_entity_type is general")
        return self


def _gpt_admin_note_payload_hash(payload: GptAdminNotePayload) -> str:
    payload_data = payload.model_dump(exclude_none=True)
    payload_data.pop("idempotency_key", None)
    canonical = json.dumps(payload_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _gpt_admin_note_related_entity_exists(
    related_entity_type: str,
    related_entity_id: str | None,
) -> bool:
    if related_entity_type == "general":
        return True
    if not related_entity_id:
        return False
    if related_entity_type == "quote":
        return get_quote_record(related_entity_id) is not None
    if related_entity_type == "quote_request":
        return storage.get_quote_request_record(related_entity_id) is not None
    if related_entity_type == "job":
        return get_job(related_entity_id) is not None
    if related_entity_type == "completed_job_calibration_entry":
        return get_completed_job_calibration_entry(related_entity_id) is not None
    return False


def _audit_gpt_admin_note_failure(record_id: str, error_summary: str) -> None:
    _try_log_admin_audit(
        operator_username="internal_gpt",
        action_type="create_gpt_admin_note",
        entity_type="gpt_admin_note",
        record_id=record_id,
        success=False,
        error_summary=error_summary,
    )


def _gpt_admin_note_response(note: dict[str, Any], *, created: bool) -> dict[str, Any]:
    return {"note_id": note["note_id"], "created": created}


@app.post("/quote/calculate")
async def quote_calculate(payload: QuoteRequestPayload):
    request_payload = payload.model_dump()
    provided_fields = getattr(payload, "model_fields_set", None)
    if provided_fields is None:
        provided_fields = getattr(payload, "__fields_set__", set())
    request_payload["_structured_intake_fields_supplied"] = [
        field for field in STRUCTURED_INTAKE_FIELD_NAMES if field in provided_fields
    ]
    return quote_service.build_and_save_quote(request_payload, now_iso=_now_local_iso())


@app.post(_GPT_QUOTE_ROUTE_NAME, include_in_schema=False, dependencies=[Depends(_require_gpt_internal_token)])
async def gpt_quote(request: Request, payload: GptQuoteRequestPayload):
    _init_gpt_quote_observability(request)
    server_grounding_revision = _configured_gpt_grounding_revision()
    caller_grounding_revision = _caller_declared_gpt_grounding_revision(request)
    try:
        response = quote_service.build_gpt_quote_response(payload.model_dump())
    except HTTPException as exc:
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason=_gpt_failure_reason_from_status_code(exc.status_code),
            server_grounding_revision=server_grounding_revision,
            caller_grounding_revision=caller_grounding_revision,
        )
        raise
    except Exception:
        _finalize_gpt_quote_observability(
            request,
            success=False,
            failure_reason="internal_error",
            server_grounding_revision=server_grounding_revision,
            caller_grounding_revision=caller_grounding_revision,
        )
        raise

    _finalize_gpt_quote_observability(
        request,
        success=True,
        normalized_service_type=str(response.get("normalized_service_type") or ""),
        cash_total_cad=float(response["cash_total_cad"]),
        emt_total_cad=float(response["emt_total_cad"]),
        confidence_level=str(response.get("confidence_level") or ""),
        risk_flags=[str(flag) for flag in response.get("risk_flags") or []],
        failure_reason=None,
        server_grounding_revision=server_grounding_revision,
        caller_grounding_revision=caller_grounding_revision,
    )
    return response


@app.post(_GPT_ADMIN_NOTES_ROUTE_NAME, include_in_schema=False, dependencies=[Depends(_require_gpt_admin_notes_token)])
async def gpt_admin_notes(request: Request, payload: GptAdminNotePayload):
    note_id = str(uuid4())
    idempotency_key = payload.idempotency_key
    if idempotency_key:
        existing = get_gpt_admin_note_by_idempotency_key(idempotency_key)
        if existing is not None:
            return _gpt_admin_note_response(existing, created=False)

    if not _gpt_admin_note_related_entity_exists(
        payload.related_entity_type,
        payload.related_entity_id,
    ):
        _audit_gpt_admin_note_failure("pending", "related entity not found")
        raise HTTPException(status_code=404, detail="related entity not found")

    duplicate_since = (
        datetime.now().astimezone() - timedelta(seconds=_GPT_ADMIN_NOTE_DUPLICATE_WINDOW_SECONDS)
    ).isoformat(timespec="seconds")
    payload_hash = _gpt_admin_note_payload_hash(payload)

    try:
        _enforce_gpt_admin_notes_rate_limit(request)
    except HTTPException as exc:
        _audit_gpt_admin_note_failure("rate_limited", str(exc.detail))
        raise

    record = payload.model_dump()
    record.update(
        {
            "note_id": note_id,
            "created_at": _now_local_iso_microseconds(),
            "updated_at": None,
            "source": "internal_gpt",
            "customer_visible": False,
            "pricing_effect": "none",
            "review_status": "open",
            "payload_hash": payload_hash,
            "server_grounding_revision": _configured_gpt_grounding_revision(),
            "caller_grounding_revision": _caller_declared_gpt_grounding_revision(request),
        }
    )

    try:
        note = save_gpt_admin_note(record, duplicate_since_created_at=duplicate_since)
    except GptAdminNoteIdempotencyReplay as exc:
        return _gpt_admin_note_response(exc.note, created=False)
    except GptAdminNoteDuplicatePayload as exc:
        _audit_gpt_admin_note_failure(exc.note["note_id"], "duplicate_note")
        raise HTTPException(status_code=409, detail="duplicate_note")
    except ValueError as exc:
        _audit_gpt_admin_note_failure(note_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except sqlite3.IntegrityError:
        _audit_gpt_admin_note_failure(note_id, "integrity_error")
        raise HTTPException(status_code=409, detail="conflicting_note")

    _try_log_admin_audit(
        operator_username="internal_gpt",
        action_type="create_gpt_admin_note",
        entity_type="gpt_admin_note",
        record_id=note["note_id"],
        success=True,
    )
    return _gpt_admin_note_response(note, created=True)


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


class AdminFollowupStatusPayload(BaseModel):
    followup_status: Optional[
        Literal["needs_followup", "contacted", "waiting_on_customer", "not_ready", "closed_no_followup"]
    ] = None

    @field_validator("followup_status", mode="before")
    @classmethod
    def normalize_followup_status(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            normalized = v.strip().lower()
            return normalized or None
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


class ScreenshotAssistantCandidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: Optional[str] = Field(None, max_length=120)
    customer_phone: Optional[str] = Field(None, max_length=50)
    job_address: Optional[str] = Field(None, max_length=250)
    job_description_customer: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=1000)
    service_type: Optional[str] = Field(None, max_length=50)
    payment_method: Optional[str] = Field(None, max_length=20)
    pickup_address: Optional[str] = Field(None, max_length=250)
    dropoff_address: Optional[str] = Field(None, max_length=250)
    estimated_hours: Optional[float] = Field(None, ge=0)
    crew_size: Optional[int] = Field(None, ge=1)
    garbage_bag_count: Optional[int] = Field(None, ge=0)
    bag_type: Optional[Literal["light", "heavy_mixed", "construction_debris"]] = Field(None)
    trailer_fill_estimate: Optional[Literal["under_quarter", "quarter", "half", "three_quarter", "full"]] = Field(None)
    trailer_class: Optional[Literal["single_axle_open_aluminum", "double_axle_open_aluminum", "older_enclosed", "newer_enclosed"]] = Field(None)
    mattresses_count: Optional[int] = Field(None, ge=0)
    box_springs_count: Optional[int] = Field(None, ge=0)
    scrap_pickup_location: Optional[str] = Field(None, max_length=50)
    travel_zone: Optional[str] = Field(None, max_length=50)
    access_difficulty: Optional[str] = Field(None, max_length=50)
    has_dense_materials: Optional[bool] = None

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


class ScreenshotAssistantIntakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: Optional[str] = Field(None, max_length=120)
    message: Optional[str] = Field(None, max_length=4000)
    requested_job_date: Optional[str] = Field(None, max_length=10, description="YYYY-MM-DD format")
    requested_time_window: Optional[str] = Field(None, max_length=20, description="morning|afternoon|evening|flexible")
    screenshot_attachment_ids: list[str] = Field(default_factory=list, max_length=10)
    candidate_inputs: ScreenshotAssistantCandidatePayload = Field(default_factory=ScreenshotAssistantCandidatePayload)
    operator_overrides: ScreenshotAssistantCandidatePayload = Field(default_factory=ScreenshotAssistantCandidatePayload)

    @field_validator("analysis_id", "message", "requested_job_date", "requested_time_window", mode="before")
    @classmethod
    def strip(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("requested_job_date")
    @classmethod
    def validate_requested_job_date(cls, v):
        if v in {None, ""}:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("Date must be in YYYY-MM-DD format")
            raise

    @field_validator("requested_time_window")
    @classmethod
    def validate_requested_time_window(cls, v):
        if v in {None, ""}:
            return None
        valid_windows = {"morning", "afternoon", "evening", "flexible"}
        if v not in valid_windows:
            raise ValueError(f"Time window must be one of: {', '.join(sorted(valid_windows))}")
        return v

    @field_validator("screenshot_attachment_ids", mode="before")
    @classmethod
    def normalize_attachment_ids(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("screenshot_attachment_ids must be a list")
        return [str(item).strip() for item in v if str(item).strip()]


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


class JobCloseoutPayload(BaseModel):
    closeout_notes: Optional[str] = Field(None, max_length=500)

    @field_validator("closeout_notes", mode="before")
    @classmethod
    def strip(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class JobCostingPayload(BaseModel):
    actual_hours: Optional[float] = Field(None, ge=0)
    actual_crew_size: Optional[int] = Field(None, ge=1)
    actual_labor_cost_cad: Optional[float] = Field(None, ge=0)
    actual_disposal_cost_cad: Optional[float] = Field(None, ge=0)
    actual_fuel_cost_cad: Optional[float] = Field(None, ge=0)
    actual_other_costs_cad: Optional[float] = Field(None, ge=0)
    final_amount_collected_cad: Optional[float] = Field(None, ge=0)
    payment_method: Optional[Literal["cash", "emt", "other"]] = None
    payment_status: Optional[Literal["not_paid_yet", "partial_payment", "paid_in_full"]] = None
    job_profit_status: Optional[Literal["underquoted", "fair", "profitable", "painful"]] = None
    quote_accuracy_note: Optional[str] = Field(None, max_length=500)
    disposal_receipt_note: Optional[str] = Field(None, max_length=500)

    @field_validator("payment_method", "payment_status", "job_profit_status", mode="before")
    @classmethod
    def normalize_vocab(cls, v):
        if isinstance(v, str):
            stripped = v.strip().lower()
            return stripped or None
        return v

    @field_validator("quote_accuracy_note", "disposal_receipt_note", mode="before")
    @classmethod
    def strip_optional_text(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None
        return v


class ManualCompletedJobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str = Field(..., min_length=1, max_length=120)
    service_type: str = Field(..., min_length=1, max_length=120)
    secondary_category: Optional[str] = Field(None, max_length=120)
    quoted_price_cad: Optional[float] = Field(None, ge=0)
    actual_collected_cad: float = Field(..., gt=0)
    crew_size: int = Field(..., ge=1)
    duration_hours: float = Field(..., gt=0)
    labour_hours: Optional[float] = Field(None, ge=0)
    disposal_cost_cad: Optional[float] = Field(None, ge=0)
    fuel_cost_cad: Optional[float] = Field(None, ge=0)
    other_costs_cad: Optional[float] = Field(None, ge=0)
    difficulty: Optional[Literal["easy", "normal", "hard", "very_hard"]] = None
    access_difficulty: Optional[Literal["normal", "awkward", "difficult"]] = None
    disassembly_required: bool = False
    dense_materials: bool = False
    underquoted: bool = False
    painful_job: bool = False
    pricing_result: Literal["underquoted", "fair", "profitable", "painful"]
    notes: Optional[str] = Field(None, max_length=1000)
    calibration_note: Optional[str] = Field(None, max_length=1000)

    @field_validator("job_title", "service_type", mode="before")
    @classmethod
    def strip_required_text(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field is required")
            return stripped
        return v

    @field_validator("secondary_category", "notes", "calibration_note", mode="before")
    @classmethod
    def strip_optional_manual_text(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None
        return v

    @field_validator("difficulty", "access_difficulty", "pricing_result", mode="before")
    @classmethod
    def normalize_manual_vocab(cls, v):
        if isinstance(v, str):
            stripped = v.strip().lower()
            return stripped or None
        return v


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


@app.get("/quote/{quote_id}/view")
def quote_review_view(quote_id: str, request: Request):
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid or expired accept token.")

    accept_token = header.split(" ", 1)[1].strip()
    if not accept_token:
        raise HTTPException(status_code=401, detail="Invalid or expired accept token.")

    return booking_service.load_quote_for_customer_review(quote_id, accept_token=accept_token)


@app.post("/quote/{quote_id}/booking")
async def submit_booking(quote_id: str, body: BookingDetails, background_tasks: BackgroundTasks):
    result = booking_service.submit_booking_details(
        quote_id,
        booking_token=body.booking_token,
        requested_job_date=body.requested_job_date,
        requested_time_window=body.requested_time_window,
        notes=body.notes,
    )
    request_id = str(result.get("request_id") or "")
    if result.get("ok") is True and request_id:
        background_tasks.add_task(booking_notification_service.notify_customer_booking_submitted, request_id)
    return result


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
    if is_token_expired(record.get("created_at")):
        raise HTTPException(status_code=401, detail="Invalid or expired accept token.")

    uploaded_items = await _store_image_attachments(
        files=files,
        folder_name=f"quote_{quote_id}",
        quote_id=quote_id,
    )

    _maybe_auto_snapshot(background_tasks)

    return {
        "ok": True,
        "uploaded": [
            {
                "attachment_id": item["attachment_id"],
                "filename": item["filename"],
                "drive_file_id": item["drive_file_id"],
                "drive_web_view_link": item["drive_web_view_link"],
            }
            for item in uploaded_items
        ],
    }


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


@app.get("/admin/api/quotes/{quote_id}")
def admin_get_quote_detail(request: Request, quote_id: str):
    _require_admin(request)
    return quote_service.load_admin_quote_detail(quote_id)


@app.post("/admin/api/quotes/{quote_id}/expire")
def admin_expire_quote(request: Request, quote_id: str, background_tasks: BackgroundTasks):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    existing_quote = get_quote_record(quote_id)
    if not existing_quote:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="expire_quote",
            entity_type="quote",
            record_id=quote_id,
            success=False,
            error_summary="Quote not found",
        )
        raise HTTPException(status_code=404, detail="Quote not found.")

    linked_request = storage.get_quote_request_by_quote_id(quote_id)
    linked_status = str(linked_request.get("status") or "") if linked_request else ""
    if linked_status in {"customer_accepted", "admin_approved"}:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="expire_quote",
            entity_type="quote",
            record_id=quote_id,
            success=False,
            error_summary=f"Quote has active request status: {linked_status}",
        )
        raise HTTPException(
            status_code=409,
            detail="Quote has an active accepted or approved request and cannot be marked expired from Recent Estimates.",
        )

    updated_quote = update_quote_admin_status(quote_id, "expired")
    if not updated_quote:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="expire_quote",
            entity_type="quote",
            record_id=quote_id,
            success=False,
            error_summary="Failed to update quote",
        )
        raise HTTPException(status_code=500, detail="Failed to update quote.")

    _try_log_admin_audit(
        operator_username=operator_username,
        action_type="expire_quote",
        entity_type="quote",
        record_id=quote_id,
        success=True,
    )
    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "quote": updated_quote}


@app.get("/admin/api/quote-requests")
def admin_list_quote_requests(request: Request, limit: int = 50):
    _require_admin(request)
    items = []
    for item in list_quote_requests(limit=_cap_admin_list_limit(limit), include_followup_status=True):
        enriched = dict(item)
        enriched["booking_notification"] = _booking_notification_summary(enriched.get("request_id"))
        items.append(enriched)
    return {"items": items}


@app.get("/admin/api/ops-queue")
def admin_ops_queue_summary(request: Request):
    _require_admin(request)
    return admin_ops_queue.build_admin_ops_queue()


@app.get("/admin/api/completed-job-profit-report")
def admin_completed_job_profit_report(request: Request):
    _require_admin(request)
    return completed_job_profit_report.build_completed_job_profit_report()


@app.get("/admin/api/manual-completed-jobs")
def admin_list_manual_completed_jobs(request: Request, limit: int = 10):
    _require_admin(request)
    return {"items": list_completed_job_calibration_entries(limit=limit)}


@app.post("/admin/api/manual-completed-jobs")
def admin_create_manual_completed_job(
    request: Request,
    body: ManualCompletedJobPayload,
    background_tasks: BackgroundTasks,
):
    _require_admin(request)
    operator_username = _admin_operator_username(request)
    entry_id = str(uuid4())
    record = body.model_dump(exclude_unset=True)
    record.update(
        {
            "entry_id": entry_id,
            "created_at": _now_local_iso(),
            "updated_at": None,
            "operator_username": operator_username,
        }
    )

    try:
        entry = save_completed_job_calibration_entry(record)
    except ValueError as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="create_manual_completed_job_calibration_entry",
            entity_type="completed_job_calibration_entry",
            record_id=entry_id,
            success=False,
            error_summary=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))

    _try_log_admin_audit(
        operator_username=operator_username,
        action_type="create_manual_completed_job_calibration_entry",
        entity_type="completed_job_calibration_entry",
        record_id=entry["entry_id"],
        success=True,
    )
    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "entry": entry}


@app.post("/admin/api/quote-requests/{request_id}/followup-status")
def admin_update_quote_request_followup_status(
    request: Request,
    request_id: str,
    body: AdminFollowupStatusPayload,
    background_tasks: BackgroundTasks,
):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        updated = update_quote_request_followup_status(request_id, body.followup_status)
    except ValueError as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="update_followup_status",
            entity_type="quote_request",
            record_id=request_id,
            success=False,
            error_summary=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))

    if not updated:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="update_followup_status",
            entity_type="quote_request",
            record_id=request_id,
            success=False,
            error_summary="Request not found",
        )
        raise HTTPException(status_code=404, detail="Request not found.")

    _try_log_admin_audit(
        operator_username=operator_username,
        action_type="update_followup_status",
        entity_type="quote_request",
        record_id=request_id,
        success=True,
    )
    _maybe_auto_snapshot(background_tasks)
    return {"ok": True, "request": updated}


@app.get("/admin/api/jobs")
def admin_list_jobs(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": list_jobs(limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/uploads")
def admin_list_uploads(request: Request, quote_id: Optional[str] = None, limit: int = 50):
    _require_admin(request)
    return {"items": list_attachments(quote_id=quote_id, limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/screenshot-assistant/analyses")
def admin_list_screenshot_assistant_analyses(request: Request, limit: int = 50):
    _require_admin(request)
    return {"items": screenshot_assistant_service.list_analyses(limit=_cap_admin_list_limit(limit))}


@app.get("/admin/api/screenshot-assistant/analyses/{analysis_id}")
def admin_get_screenshot_assistant_analysis(request: Request, analysis_id: str):
    _require_admin(request)
    analysis = screenshot_assistant_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Screenshot assistant analysis not found.")
    return analysis


@app.post("/admin/api/screenshot-assistant/analyses/intake")
def admin_create_screenshot_assistant_analysis(
    request: Request,
    body: ScreenshotAssistantIntakePayload,
    background_tasks: BackgroundTasks,
):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        result = screenshot_assistant_service.create_analysis(
            analysis_id=body.analysis_id,
            operator_username=operator_username,
            message=body.message,
            requested_job_date=body.requested_job_date,
            requested_time_window=body.requested_time_window,
            candidate_inputs=body.candidate_inputs.model_dump(exclude_none=True),
            operator_overrides=body.operator_overrides.model_dump(exclude_none=True),
            screenshot_attachment_ids=body.screenshot_attachment_ids,
            now_iso=_now_local_iso(),
        )
        log_admin_audit(
            operator_username=operator_username,
            action_type="create_screenshot_analysis",
            entity_type="screenshot_assistant_analysis",
            record_id=result["analysis_id"],
            success=True,
        )
        _maybe_auto_snapshot(background_tasks)
        return result
    except HTTPException as exc:
        log_admin_audit(
            operator_username=operator_username,
            action_type="create_screenshot_analysis",
            entity_type="screenshot_assistant_analysis",
            record_id="draft",
            success=False,
            error_summary=str(exc.detail),
        )
        raise


@app.post("/admin/api/screenshot-assistant/analyses/{analysis_id}/attachments")
async def admin_upload_screenshot_assistant_attachments(
    request: Request,
    analysis_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        analysis = screenshot_assistant_service.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Screenshot assistant analysis not found.")
        if str(analysis.get("quote_id") or "").strip():
            raise HTTPException(status_code=409, detail="Screenshot assistant analysis is locked after quote draft creation.")

        uploaded_items = await _store_image_attachments(
            files=files,
            folder_name=f"analysis_{analysis_id}",
            analysis_id=analysis_id,
        )
        refreshed = screenshot_assistant_service.get_analysis(analysis_id)
        log_admin_audit(
            operator_username=operator_username,
            action_type="upload_screenshot_analysis_attachments",
            entity_type="screenshot_assistant_analysis",
            record_id=analysis_id,
            success=True,
        )
        _maybe_auto_snapshot(background_tasks)
        return {
            "ok": True,
            "analysis_id": analysis_id,
            "uploaded": uploaded_items,
            "attachments": refreshed["attachments"] if refreshed else list_attachments(analysis_id=analysis_id, limit=25),
        }
    except HTTPException as exc:
        log_admin_audit(
            operator_username=operator_username,
            action_type="upload_screenshot_analysis_attachments",
            entity_type="screenshot_assistant_analysis",
            record_id=analysis_id,
            success=False,
            error_summary=str(exc.detail),
        )
        raise


@app.post("/admin/api/quote-requests/{request_id}/decision")
def admin_decide_quote_request(
    request: Request,
    request_id: str,
    body: AdminDecision,
    background_tasks: BackgroundTasks,
):
        _require_admin(request)

        operator_username = _admin_operator_username(request)

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
    operator_username = _admin_operator_username(request)

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
            operator_username=operator_username,
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
            operator_username=operator_username,
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
    operator_username = _admin_operator_username(request)

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
            operator_username=operator_username,
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
            operator_username=operator_username,
            action_type="reschedule_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/admin/api/jobs/{job_id}/start")
def admin_start_job(request: Request, job_id: str):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        job = job_scheduling_service.start_job(job_id, _now_local_iso())
        log_admin_audit(
            operator_username=operator_username,
            action_type="start_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except InvalidJobTransition as e:
        log_admin_audit(
            operator_username=operator_username,
            action_type="start_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=str(e),
        )
        return _invalid_job_transition_response(e)
    except ValueError as e:
        error_msg = str(e)
        log_admin_audit(
            operator_username=operator_username,
            action_type="start_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/admin/api/jobs/{job_id}/complete")
def admin_complete_job(request: Request, job_id: str, body: Optional[JobCloseoutPayload] = None):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        job = job_scheduling_service.complete_job(
            job_id,
            _now_local_iso(),
            body.closeout_notes if body else None,
        )
        log_admin_audit(
            operator_username=operator_username,
            action_type="complete_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except InvalidJobTransition as e:
        log_admin_audit(
            operator_username=operator_username,
            action_type="complete_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=str(e),
        )
        return _invalid_job_transition_response(e)
    except ValueError as e:
        error_msg = str(e)
        log_admin_audit(
            operator_username=operator_username,
            action_type="complete_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/admin/api/jobs/{job_id}/costing")
def admin_update_job_costing(request: Request, job_id: str, body: JobCostingPayload):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    existing = get_job(job_id)
    if not existing:
        log_admin_audit(
            operator_username=operator_username,
            action_type="update_job_costing",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary="Job not found",
        )
        raise HTTPException(status_code=404, detail="Job not found")

    if existing.get("status") != "completed":
        log_admin_audit(
            operator_username=operator_username,
            action_type="update_job_costing",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary="Job costing is only editable for completed jobs",
        )
        raise HTTPException(status_code=409, detail="Job costing is only editable for completed jobs.")

    fields = body.model_dump(exclude_unset=True)
    try:
        job = update_job_costing(job_id, **fields)
    except ValueError as exc:
        log_admin_audit(
            operator_username=operator_username,
            action_type="update_job_costing",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    log_admin_audit(
        operator_username=operator_username,
        action_type="update_job_costing",
        entity_type="job",
        record_id=job_id,
        success=True,
    )
    return {"ok": True, "job": job}


@app.post("/admin/api/jobs/{job_id}/cancel")
def admin_cancel_job(request: Request, job_id: str, body: Optional[JobCloseoutPayload] = None):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    # Delegate to service layer
    try:
        job = job_scheduling_service.cancel_job(
            job_id,
            _now_local_iso(),
            body.closeout_notes if body else None,
        )
        log_admin_audit(
            operator_username=operator_username,
            action_type="cancel_job",
            entity_type="job",
            record_id=job_id,
            success=True,
        )
        return {"ok": True, "job": job}
    except InvalidJobTransition as e:
        log_admin_audit(
            operator_username=operator_username,
            action_type="cancel_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=str(e),
        )
        return _invalid_job_transition_response(e)
    except ValueError as e:
        error_msg = str(e)
        log_admin_audit(
            operator_username=operator_username,
            action_type="cancel_job",
            entity_type="job",
            record_id=job_id,
            success=False,
            error_summary=error_msg,
        )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


# =========================
# Admin DB Backup/Restore (JSON)
# =========================

@app.get("/admin/api/db/export")
def admin_db_export(request: Request):
    _require_admin(request)
    operator_username = _admin_operator_username(request)

    try:
        payload = export_db_to_json()
        payload["meta"]["exported_at"] = _now_local_iso()
        payload["meta"].pop("db_path", None)

        filename = f"bay_delivery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/json; charset=utf-8",
        }
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="export_db",
            entity_type="database",
            record_id="primary",
            success=True,
        )
        return Response(content=body, headers=headers, media_type="application/json")
    except Exception as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="export_db",
            entity_type="database",
            record_id="primary",
            success=False,
            error_summary=str(exc.detail) if isinstance(exc, HTTPException) else str(exc),
        )
        raise


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
    operator_username = _admin_operator_username(request)
    try:
        result = import_db_from_json(body.payload)
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="import_db",
            entity_type="database",
            record_id="primary",
            success=True,
        )
        _maybe_auto_snapshot(background_tasks)
        return result
    except Exception as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="import_db",
            entity_type="database",
            record_id="primary",
            success=False,
            error_summary=str(exc.detail) if isinstance(exc, HTTPException) else str(exc),
        )
        raise


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
    operator_username = _admin_operator_username(request)
    try:
        if not _drive_enabled():
            raise HTTPException(status_code=501, detail="Google Drive not configured.")
        result = _drive_snapshot_db()
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="drive_snapshot",
            entity_type="drive_backup",
            record_id=str(result.get("file_id") or "pending"),
            success=True,
        )
        return result
    except Exception as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="drive_snapshot",
            entity_type="drive_backup",
            record_id="pending",
            success=False,
            error_summary=str(exc.detail) if isinstance(exc, HTTPException) else str(exc),
        )
        raise


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
    operator_username = _admin_operator_username(request)
    try:
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

        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="drive_restore",
            entity_type="drive_backup",
            record_id=body.file_id,
            success=True,
        )
        _maybe_auto_snapshot(background_tasks)
        logger.info("Drive DB restore completed for file_id=%s", body.file_id)
        return {
            "ok": bool(result.get("ok", True)),
            "restored": result.get("restored", {}),
            "restored_from_file_id": body.file_id,
        }
    except Exception as exc:
        _try_log_admin_audit(
            operator_username=operator_username,
            action_type="drive_restore",
            entity_type="drive_backup",
            record_id=body.file_id,
            success=False,
            error_summary=str(exc.detail) if isinstance(exc, HTTPException) else str(exc),
        )
        raise


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


@app.get("/admin/api/gpt-quote-observability")
def admin_gpt_quote_observability(request: Request):
    """
    Returns the latest 50 GPT quote observability entries as JSON.
    Requires admin authentication.
    """
    _require_admin(request)
    return {"items": list_gpt_quote_observability(limit=50)}


@app.get("/admin/api/gpt-notes")
def admin_gpt_notes(
    request: Request,
    limit: int = 50,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    review_status: Optional[str] = None,
):
    """
    Returns internal GPT admin notes as JSON. Requires admin authentication.
    """
    _require_admin(request)
    try:
        items = list_gpt_admin_notes(
            limit=limit,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            review_status=review_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"items": items}
