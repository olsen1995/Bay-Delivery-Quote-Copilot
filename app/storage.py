from __future__ import annotations

from itertools import product
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, NotRequired, Optional, Tuple, TypedDict, cast
from uuid import uuid4

from app.update_fields import validate_quote_request_transition

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("app/data/bay_delivery.sqlite3")
DB_PATH = DEFAULT_DB_PATH  # overridable by tests
UNSET = object()

# Token validity in days
TOKEN_VALIDITY_DAYS = 30
BACKUP_TOKEN_ROTATION_PLACEHOLDER = "__bay_delivery_token_rotated_on_import__"

ALLOWED_DEPOSIT_STATUSES = (
    "not_required",
    "required",
    "pending",
    "paid",
    "failed",
)
ALLOWED_PAYMENT_ATTEMPT_STATUSES = (
    "created",
    "pending",
    "succeeded",
    "failed",
    "expired",
)
ALLOWED_NOTIFICATION_ATTEMPT_STATUSES = (
    "pending",
    "sent",
    "failed",
    "skipped",
)
NOTIFICATION_PENDING_STALE_THRESHOLD_MINUTES = 15
ALLOWED_QUOTE_ADMIN_STATUSES = ("pending", "expired")
ALLOWED_QUOTE_REQUEST_FOLLOWUP_STATUSES = (
    "needs_followup",
    "contacted",
    "waiting_on_customer",
    "not_ready",
    "closed_no_followup",
)
DEPOSIT_STATUS_CHECK_SQL = (
    "deposit_status IS NULL OR deposit_status IN "
    "('not_required', 'required', 'pending', 'paid', 'failed')"
)
PAYMENT_ATTEMPT_STATUS_CHECK_SQL = (
    "status IN ('created', 'pending', 'succeeded', 'failed', 'expired')"
)
NOTIFICATION_ATTEMPT_STATUS_CHECK_SQL = (
    "status IN ('pending', 'sent', 'failed', 'skipped')"
)
QUOTE_ADMIN_STATUS_CHECK_SQL = "admin_status IN ('pending', 'expired')"
QUOTE_REQUEST_FOLLOWUP_STATUS_CHECK_SQL = (
    "followup_status IS NULL OR followup_status IN "
    "('needs_followup', 'contacted', 'waiting_on_customer', 'not_ready', 'closed_no_followup')"
)
ALLOWED_JOB_COSTING_PAYMENT_METHODS = ("cash", "emt", "other")
ALLOWED_JOB_PAYMENT_STATUSES = ("not_paid_yet", "partial_payment", "paid_in_full")
ALLOWED_JOB_PROFIT_STATUSES = ("underquoted", "fair", "profitable", "painful")
ALLOWED_MANUAL_CALIBRATION_PRICING_RESULTS = ("underquoted", "fair", "profitable", "painful")
ALLOWED_MANUAL_CALIBRATION_DIFFICULTIES = ("easy", "normal", "hard", "very_hard")
ALLOWED_MANUAL_CALIBRATION_ACCESS_DIFFICULTIES = ("normal", "awkward", "difficult")
ALLOWED_GPT_ADMIN_NOTE_RELATED_ENTITY_TYPES = (
    "quote",
    "quote_request",
    "job",
    "completed_job_calibration_entry",
    "general",
)
ALLOWED_GPT_ADMIN_NOTE_TYPES = (
    "job_observation",
    "quote_caution",
    "missing_info",
    "follow_up_recommendation",
    "completed_job_calibration_observation",
    "customer_message_draft",
    "photo_access_density_risk",
    "owner_review_context",
)
ALLOWED_GPT_ADMIN_NOTE_REVIEW_STATUSES = ("open", "reviewed", "archived")
JOB_COSTING_PAYMENT_METHOD_CHECK_SQL = (
    "payment_method IS NULL OR payment_method IN ('cash', 'emt', 'other')"
)
JOB_PAYMENT_STATUS_CHECK_SQL = (
    "payment_status IS NULL OR payment_status IN "
    "('not_paid_yet', 'partial_payment', 'paid_in_full')"
)
JOB_PROFIT_STATUS_CHECK_SQL = (
    "job_profit_status IS NULL OR job_profit_status IN "
    "('underquoted', 'fair', 'profitable', 'painful')"
)
MANUAL_CALIBRATION_PRICING_RESULT_CHECK_SQL = (
    "pricing_result IN ('underquoted', 'fair', 'profitable', 'painful')"
)
MANUAL_CALIBRATION_DIFFICULTY_CHECK_SQL = (
    "difficulty IS NULL OR difficulty IN ('easy', 'normal', 'hard', 'very_hard')"
)
MANUAL_CALIBRATION_ACCESS_DIFFICULTY_CHECK_SQL = (
    "access_difficulty IS NULL OR access_difficulty IN ('normal', 'awkward', 'difficult')"
)
GPT_ADMIN_NOTE_RELATED_ENTITY_TYPE_CHECK_SQL = (
    "related_entity_type IN "
    "('quote', 'quote_request', 'job', 'completed_job_calibration_entry', 'general')"
)
GPT_ADMIN_NOTE_TYPE_CHECK_SQL = (
    "note_type IN "
    "('job_observation', 'quote_caution', 'missing_info', 'follow_up_recommendation', "
    "'completed_job_calibration_observation', 'customer_message_draft', "
    "'photo_access_density_risk', 'owner_review_context')"
)
GPT_ADMIN_NOTE_REVIEW_STATUS_CHECK_SQL = "review_status IN ('open', 'reviewed', 'archived')"


class Job(TypedDict):
    job_id: str
    created_at: str
    status: str
    quote_id: str
    request_id: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    job_address: Optional[str]
    job_description_customer: Optional[str]
    job_description_internal: Optional[str]
    service_type: str
    cash_total_cad: float
    emt_total_cad: float
    request_json: Any
    notes: Optional[str]
    scheduled_start: Optional[str]
    scheduled_end: Optional[str]
    google_calendar_event_id: Optional[str]
    calendar_sync_status: Optional[str]
    calendar_last_error: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    cancelled_at: Optional[str]
    closeout_notes: Optional[str]
    actual_hours: Optional[float]
    actual_crew_size: Optional[int]
    actual_labor_cost_cad: Optional[float]
    actual_disposal_cost_cad: Optional[float]
    actual_fuel_cost_cad: Optional[float]
    actual_other_costs_cad: Optional[float]
    final_amount_collected_cad: Optional[float]
    payment_method: Optional[str]
    payment_status: Optional[str]
    job_profit_status: Optional[str]
    quote_accuracy_note: Optional[str]
    disposal_receipt_note: Optional[str]
    scheduling_context: NotRequired[Dict[str, Any]]


class CompletedJobCalibrationEntry(TypedDict):
    entry_id: str
    created_at: str
    updated_at: Optional[str]
    operator_username: str
    job_title: str
    service_type: str
    secondary_category: Optional[str]
    quoted_price_cad: Optional[float]
    actual_collected_cad: float
    crew_size: int
    duration_hours: float
    labour_hours: Optional[float]
    disposal_cost_cad: Optional[float]
    fuel_cost_cad: Optional[float]
    other_costs_cad: Optional[float]
    difficulty: Optional[str]
    access_difficulty: Optional[str]
    disassembly_required: int
    dense_materials: int
    underquoted: int
    painful_job: int
    pricing_result: str
    notes: Optional[str]
    calibration_note: Optional[str]


class GptAdminNoteRecord(TypedDict):
    note_id: str
    created_at: str
    updated_at: Optional[str]
    source: str
    related_entity_type: str
    related_entity_id: Optional[str]
    note_type: str
    title: str
    summary: str
    recommendation: Optional[str]
    customer_message_draft: Optional[str]
    risk_flags: List[str]
    follow_up_needed: bool
    customer_visible: bool
    pricing_effect: str
    review_status: str
    idempotency_key: Optional[str]
    payload_hash: str
    server_grounding_revision: Optional[str]
    caller_grounding_revision: Optional[str]


class GptAdminNoteConflictError(Exception):
    def __init__(self, note: GptAdminNoteRecord) -> None:
        self.note = note


class GptAdminNoteIdempotencyReplay(GptAdminNoteConflictError):
    pass


class GptAdminNoteDuplicatePayload(GptAdminNoteConflictError):
    pass


class QuoteRecord(TypedDict):
    quote_id: str
    created_at: str
    request: Any
    response: Any
    accept_token: Optional[str]
    admin_status: NotRequired[str]
    job_type: NotRequired[str]
    total_cad: NotRequired[float]


class QuoteRequest(TypedDict):
    request_id: str
    created_at: str
    status: str
    quote_id: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    job_address: Optional[str]
    job_description_customer: Optional[str]
    job_description_internal: Optional[str]
    service_type: str
    cash_total_cad: float
    emt_total_cad: float
    request_json: Any
    notes: Optional[str]
    requested_job_date: Optional[str]
    requested_time_window: Optional[str]
    customer_accepted_at: Optional[str]
    admin_approved_at: Optional[str]
    accept_token: Optional[str]
    booking_token: Optional[str]
    booking_token_created_at: Optional[str]


class QuoteRequestRecord(QuoteRequest, total=False):
    followup_status: Optional[str]
    deposit_required_cad: Optional[float]
    deposit_status: Optional[str]
    deposit_paid_at: Optional[str]
    deposit_refund_status: Optional[str]
    deposit_refunded_at: Optional[str]
    deposit_last_error: Optional[str]


class ScreenshotAssistantAnalysis(TypedDict):
    analysis_id: str
    created_at: str
    updated_at: str
    operator_username: str
    status: str
    intake_json: Any
    normalized_candidate_json: Any
    guidance_json: Any
    quote_id: Optional[str]


class AttachmentRecord(TypedDict):
    attachment_id: str
    created_at: str
    quote_id: Optional[str]
    request_id: Optional[str]
    job_id: Optional[str]
    analysis_id: Optional[str]
    filename: str
    mime_type: str
    size_bytes: Optional[int]
    drive_file_id: str
    drive_web_view_link: Optional[str]
    ocr_json: NotRequired[Dict[str, Any]]


class PaymentAttempt(TypedDict):
    payment_attempt_id: str
    request_id: str
    provider: str
    amount_cad: float
    checkout_session_id: Optional[str]
    payment_intent_id: Optional[str]
    status: str
    created_at: str
    updated_at: str
    refund_id: Optional[str]
    last_error: Optional[str]


class WebhookEventRecord(TypedDict):
    provider_event_id: str
    provider: str
    event_type: str
    received_at: str
    processed_at: Optional[str]
    payload_json: Any


class NotificationAttemptRecord(TypedDict):
    event_type: str
    request_id: str
    quote_id: Optional[str]
    channel: str
    recipient: Optional[str]
    status: str
    attempt_count: int
    created_at: str
    updated_at: str
    sent_at: Optional[str]
    last_error: Optional[str]


class GptQuoteObservabilityRecord(TypedDict):
    timestamp: str
    route_name: str
    success: bool
    normalized_service_type: Optional[str]
    cash_total_cad: Optional[float]
    emt_total_cad: Optional[float]
    confidence_level: Optional[str]
    risk_flags: List[str]
    failure_reason: Optional[str]
    latency_ms: Optional[int]
    server_grounding_revision: Optional[str]
    caller_grounding_revision: Optional[str]


class AdminOpsQueueSources(TypedDict):
    counts: Dict[str, int]
    accepted_not_booked_detail_sources: List[Dict[str, Any]]


class PrelaunchCleanupPlan(TypedDict):
    db_path: str
    requested_quote_ids: List[str]
    found_quote_ids: List[str]
    missing_quote_ids: List[str]
    request_ids: List[str]
    job_ids: List[str]
    attachment_ids: List[str]
    counts: Dict[str, int]
    quotes: List[QuoteRecord]
    quote_requests: List[QuoteRequestRecord]
    jobs: List[Job]
    attachments: List[AttachmentRecord]


class PrelaunchCleanupResult(TypedDict):
    db_path: str
    requested_quote_ids: List[str]
    found_quote_ids: List[str]
    missing_quote_ids: List[str]
    deleted_quote_ids: List[str]
    deleted_request_ids: List[str]
    deleted_job_ids: List[str]
    deleted_attachment_ids: List[str]
    counts: Dict[str, int]


def _validate_deposit_status(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str) or value not in ALLOWED_DEPOSIT_STATUSES:
        allowed = ", ".join(repr(item) for item in ALLOWED_DEPOSIT_STATUSES)
        raise ValueError(f"deposit_status must be None or one of: {allowed}")


def _validate_payment_attempt_status(value: Any) -> str:
    if not isinstance(value, str) or value not in ALLOWED_PAYMENT_ATTEMPT_STATUSES:
        allowed = ", ".join(repr(item) for item in ALLOWED_PAYMENT_ATTEMPT_STATUSES)
        raise ValueError(f"payment_attempt.status must be one of: {allowed}")
    return value


def _validate_notification_attempt_status(value: Any) -> str:
    if not isinstance(value, str) or value not in ALLOWED_NOTIFICATION_ATTEMPT_STATUSES:
        allowed = ", ".join(repr(item) for item in ALLOWED_NOTIFICATION_ATTEMPT_STATUSES)
        raise ValueError(f"notification_attempt.status must be one of: {allowed}")
    return value


def _validate_quote_admin_status(value: Any) -> str:
    if not isinstance(value, str) or value not in ALLOWED_QUOTE_ADMIN_STATUSES:
        allowed = ", ".join(repr(item) for item in ALLOWED_QUOTE_ADMIN_STATUSES)
        raise ValueError(f"quote.admin_status must be one of: {allowed}")
    return value


def _validate_quote_request_followup_status(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        allowed = ", ".join(repr(item) for item in ALLOWED_QUOTE_REQUEST_FOLLOWUP_STATUSES)
        raise ValueError(f"quote_request.followup_status must be None or one of: {allowed}")
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in ALLOWED_QUOTE_REQUEST_FOLLOWUP_STATUSES:
        allowed = ", ".join(repr(item) for item in ALLOWED_QUOTE_REQUEST_FOLLOWUP_STATUSES)
        raise ValueError(f"quote_request.followup_status must be None or one of: {allowed}")
    return normalized


def _clean_missing_field(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _build_job_scheduling_context(
    request_id: Optional[str],
    fallback_notes: Optional[str] = None,
) -> Dict[str, Any]:
    missing_fields: List[str] = []
    request: Optional[QuoteRequest] = get_quote_request(request_id) if request_id else None

    requested_job_date = request.get("requested_job_date") if request else None
    requested_time_window = request.get("requested_time_window") if request else None
    notes = request.get("notes") if request else fallback_notes

    if request is None:
        missing_fields.extend(["quote_request", "requested_job_date", "requested_time_window"])
    else:
        if _clean_missing_field(requested_job_date):
            missing_fields.append("requested_job_date")
        if _clean_missing_field(requested_time_window):
            missing_fields.append("requested_time_window")

    return {
        "request_id": request.get("request_id") if request else request_id,
        "requested_job_date": requested_job_date,
        "requested_time_window": requested_time_window,
        "notes": notes,
        "scheduling_ready": len(missing_fields) == 0,
        "missing_fields": missing_fields,
    }


def is_token_expired(token_created_at: Optional[str], days: int = TOKEN_VALIDITY_DAYS) -> bool:
    """Check if a token has expired. Returns True if expired or if created_at is None."""
    if not token_created_at:
        return True
    try:
        created = datetime.fromisoformat(token_created_at)
        expiry = created + timedelta(days=days)
        # Use timezone-aware comparison if the parsed datetime is timezone-aware
        now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
        return now > expiry
    except (ValueError, TypeError):
        return True

# Explicit table list keeps backup/restore deterministic and safe.
KNOWN_TABLES = [
    "quotes",
    "quote_requests",
    "jobs",
    "completed_job_calibration_entries",
    "attachments",
    "screenshot_assistant_analyses",
    "admin_audit_log",
    "gpt_quote_observability",
    "gpt_admin_notes",
    "payment_attempts",
    "webhook_events",
    "notification_attempts",
]

# Cache table columns to support forward-compatible schemas (ex: quotes.job_type)
_TABLE_COL_CACHE: Dict[str, Tuple[str, ...]] = {}
_PHONE_DIGITS_RE = re.compile(r"\D+")


def _validate_table_name(table_name: str) -> str:
    """Validate table name is in known allowlist. Defense-in-depth against future refactors."""
    if table_name not in KNOWN_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


def _connect() -> sqlite3.Connection:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # enable a longer busy timeout to reduce "database is locked" errors under
    # concurrent access (workers, Render healty/checks, etc.).  The default 5
    # seconds was occasionally insufficient during spike tests.
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL mode improves concurrency by allowing readers and writers to operate
    # simultaneously; this mirrors recommendations from the audit.
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # some builds (older SQLite) may not support WAL; fail silently.
        pass
    return conn


def _resolve_db_path() -> Path:
    if DB_PATH != DEFAULT_DB_PATH:
        return DB_PATH

    env_path = os.getenv("BAYDELIVERY_DB_PATH")
    if env_path:
        env_path_obj = Path(env_path).resolve()
        app_data_dir = Path("app/data").resolve()
        try:
            # Ensure path is within app/data directory to prevent directory traversal
            env_path_obj.relative_to(app_data_dir)
            return env_path_obj
        except ValueError:
            # Allow explicit absolute production paths like /var/data/... while
            # still defaulting safely for local/dev if something invalid is set.
            if env_path_obj.is_absolute():
                return env_path_obj
            return DEFAULT_DB_PATH

    return DEFAULT_DB_PATH


def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """SQLite doesn't support ADD COLUMN IF NOT EXISTS reliably in all builds."""
    table = _validate_table_name(table)
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate column name" in msg:
            return
        raise


def _table_columns(conn: sqlite3.Connection, table: str) -> Tuple[str, ...]:
    """Return current columns for a table, cached per process."""
    table = _validate_table_name(table)
    cached = _TABLE_COL_CACHE.get(table)
    if cached is not None:
        return cached

    try:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.OperationalError:
        _TABLE_COL_CACHE[table] = tuple()
        return tuple()

    names = tuple(c["name"] for c in cols)
    _TABLE_COL_CACHE[table] = names
    return names


def _table_info(conn: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    """Return PRAGMA table_info rows (uncached; used for NOT NULL detection)."""
    table = _validate_table_name(table)
    try:
        return conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.OperationalError:
        return []


def _dedupe_quote_requests_by_quote_id(conn: sqlite3.Connection) -> None:
    """Backfill cleanup for pre-unique-index databases.

    Keeps the newest row per quote_id (by created_at, then rowid) and removes
    older duplicates so unique index creation succeeds on startup.
    """
    duplicate_quote_ids = conn.execute(
        """
        SELECT quote_id
        FROM quote_requests
        GROUP BY quote_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    for row in duplicate_quote_ids:
        quote_id = row["quote_id"]
        rows = conn.execute(
            """
            SELECT rowid
            FROM quote_requests
            WHERE quote_id = ?
            ORDER BY datetime(created_at) DESC, rowid DESC
            """,
            (quote_id,),
        ).fetchall()

        # Keep the newest row and remove the rest.
        rowids_to_delete = [r["rowid"] for r in rows[1:]]
        if not rowids_to_delete:
            continue

        placeholders = ",".join("?" for _ in rowids_to_delete)
        conn.execute(
            f"DELETE FROM quote_requests WHERE rowid IN ({placeholders})",
            rowids_to_delete,
        )


def _backfill_job_payment_status(conn: sqlite3.Connection) -> None:
    """Move status-like legacy payment_method values into payment_status."""
    columns = set(_table_columns(conn, "jobs"))
    if "payment_method" not in columns or "payment_status" not in columns:
        return

    for legacy_status in ("not_paid_yet", "partial_payment"):
        conn.execute(
            """
            UPDATE jobs
            SET payment_status = ?, payment_method = NULL
            WHERE payment_method = ?
            """,
            (legacy_status, legacy_status),
        )


def _normalize_job_payment_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    payment_method = row.get("payment_method")
    if payment_method not in {"not_paid_yet", "partial_payment"}:
        return row
    normalized = dict(row)
    normalized["payment_method"] = None
    normalized["payment_status"] = normalized.get("payment_status") or payment_method
    return normalized


def _normalize_quote_admin_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    if row.get("admin_status") in ALLOWED_QUOTE_ADMIN_STATUSES:
        return row
    normalized = dict(row)
    normalized["admin_status"] = "pending"
    return normalized


def init_db() -> None:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                accept_token TEXT,
                admin_status TEXT NOT NULL DEFAULT 'pending' CHECK (admin_status IN ('pending', 'expired'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_requests (
                request_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                job_address TEXT,
                job_description_customer TEXT,
                job_description_internal TEXT,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                notes TEXT,
                requested_job_date TEXT,
                requested_time_window TEXT,
                customer_accepted_at TEXT,
                admin_approved_at TEXT,
                accept_token TEXT,
                booking_token TEXT,
                booking_token_created_at TEXT,
                followup_status TEXT CHECK (followup_status IS NULL OR followup_status IN ('needs_followup', 'contacted', 'waiting_on_customer', 'not_ready', 'closed_no_followup')),
                deposit_required_cad REAL,
                deposit_status TEXT CHECK (deposit_status IS NULL OR deposit_status IN ('not_required', 'required', 'pending', 'paid', 'failed')),
                deposit_paid_at TEXT,
                deposit_refund_status TEXT,
                deposit_refunded_at TEXT,
                deposit_last_error TEXT
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                job_address TEXT,
                job_description_customer TEXT,
                job_description_internal TEXT,
                service_type TEXT NOT NULL,
                cash_total_cad REAL NOT NULL,
                emt_total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                notes TEXT,
                actual_hours REAL,
                actual_crew_size INTEGER,
                actual_labor_cost_cad REAL,
                actual_disposal_cost_cad REAL,
                actual_fuel_cost_cad REAL,
                actual_other_costs_cad REAL,
                final_amount_collected_cad REAL,
                payment_method TEXT CHECK ({JOB_COSTING_PAYMENT_METHOD_CHECK_SQL}),
                payment_status TEXT CHECK ({JOB_PAYMENT_STATUS_CHECK_SQL}),
                job_profit_status TEXT CHECK ({JOB_PROFIT_STATUS_CHECK_SQL}),
                quote_accuracy_note TEXT,
                disposal_receipt_note TEXT
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS completed_job_calibration_entries (
                entry_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                operator_username TEXT NOT NULL,
                job_title TEXT NOT NULL,
                service_type TEXT NOT NULL,
                secondary_category TEXT,
                quoted_price_cad REAL,
                actual_collected_cad REAL NOT NULL,
                crew_size INTEGER NOT NULL,
                duration_hours REAL NOT NULL,
                labour_hours REAL,
                disposal_cost_cad REAL,
                fuel_cost_cad REAL,
                other_costs_cad REAL,
                difficulty TEXT CHECK ({MANUAL_CALIBRATION_DIFFICULTY_CHECK_SQL}),
                access_difficulty TEXT CHECK ({MANUAL_CALIBRATION_ACCESS_DIFFICULTY_CHECK_SQL}),
                disassembly_required INTEGER NOT NULL DEFAULT 0,
                dense_materials INTEGER NOT NULL DEFAULT 0,
                underquoted INTEGER NOT NULL DEFAULT 0,
                painful_job INTEGER NOT NULL DEFAULT 0,
                pricing_result TEXT NOT NULL CHECK ({MANUAL_CALIBRATION_PRICING_RESULT_CHECK_SQL}),
                notes TEXT,
                calibration_note TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                attachment_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                quote_id TEXT,
                request_id TEXT,
                job_id TEXT,
                analysis_id TEXT,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER,
                drive_file_id TEXT NOT NULL,
                drive_web_view_link TEXT,
                ocr_json TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS screenshot_assistant_analyses (
                analysis_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                operator_username TEXT NOT NULL,
                status TEXT NOT NULL,
                intake_json TEXT NOT NULL,
                normalized_candidate_json TEXT NOT NULL,
                guidance_json TEXT NOT NULL,
                quote_id TEXT
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS payment_attempts (
                payment_attempt_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                amount_cad REAL NOT NULL,
                checkout_session_id TEXT,
                payment_intent_id TEXT,
                status TEXT NOT NULL CHECK ({PAYMENT_ATTEMPT_STATUS_CHECK_SQL}),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                refund_id TEXT,
                last_error TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                provider_event_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                received_at TEXT NOT NULL,
                processed_at TEXT,
                payload_json TEXT NOT NULL,
                UNIQUE(provider, provider_event_id)
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS notification_attempts (
                event_type TEXT NOT NULL,
                request_id TEXT NOT NULL,
                quote_id TEXT,
                channel TEXT NOT NULL,
                recipient TEXT,
                status TEXT NOT NULL DEFAULT 'pending' CHECK ({NOTIFICATION_ATTEMPT_STATUS_CHECK_SQL}),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sent_at TEXT,
                last_error TEXT,
                UNIQUE(request_id, event_type)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gpt_quote_observability (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                route_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                normalized_service_type TEXT,
                cash_total_cad REAL,
                emt_total_cad REAL,
                confidence_level TEXT,
                risk_flags_json TEXT NOT NULL,
                failure_reason TEXT,
                latency_ms INTEGER,
                server_grounding_revision TEXT,
                caller_grounding_revision TEXT
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS gpt_admin_notes (
                note_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                source TEXT NOT NULL DEFAULT 'internal_gpt' CHECK (source = 'internal_gpt'),
                related_entity_type TEXT NOT NULL CHECK ({GPT_ADMIN_NOTE_RELATED_ENTITY_TYPE_CHECK_SQL}),
                related_entity_id TEXT,
                note_type TEXT NOT NULL CHECK ({GPT_ADMIN_NOTE_TYPE_CHECK_SQL}),
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                recommendation TEXT,
                customer_message_draft TEXT,
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                follow_up_needed INTEGER NOT NULL DEFAULT 0,
                customer_visible INTEGER NOT NULL DEFAULT 0 CHECK (customer_visible = 0),
                pricing_effect TEXT NOT NULL DEFAULT 'none' CHECK (pricing_effect = 'none'),
                review_status TEXT NOT NULL DEFAULT 'open' CHECK ({GPT_ADMIN_NOTE_REVIEW_STATUS_CHECK_SQL}),
                idempotency_key TEXT UNIQUE,
                payload_hash TEXT NOT NULL,
                server_grounding_revision TEXT,
                caller_grounding_revision TEXT
            )
            """
        )

        # Backfill: add missing columns if older DB is present
        _try_add_column(conn, "quotes", "accept_token TEXT")
        _try_add_column(conn, "quotes", f"admin_status TEXT NOT NULL DEFAULT 'pending' CHECK ({QUOTE_ADMIN_STATUS_CHECK_SQL})")
        _try_add_column(conn, "quote_requests", "notes TEXT")
        _try_add_column(conn, "quote_requests", "requested_job_date TEXT")
        _try_add_column(conn, "quote_requests", "requested_time_window TEXT")
        _try_add_column(conn, "quote_requests", "customer_accepted_at TEXT")
        _try_add_column(conn, "quote_requests", "admin_approved_at TEXT")
        _try_add_column(conn, "quote_requests", "accept_token TEXT")
        _try_add_column(conn, "quote_requests", "booking_token TEXT")
        _try_add_column(conn, "quote_requests", "booking_token_created_at TEXT")
        _try_add_column(conn, "quote_requests", f"followup_status TEXT CHECK ({QUOTE_REQUEST_FOLLOWUP_STATUS_CHECK_SQL})")
        _try_add_column(conn, "quote_requests", "deposit_required_cad REAL")
        _try_add_column(conn, "quote_requests", f"deposit_status TEXT CHECK ({DEPOSIT_STATUS_CHECK_SQL})")
        _try_add_column(conn, "quote_requests", "deposit_paid_at TEXT")
        _try_add_column(conn, "quote_requests", "deposit_refund_status TEXT")
        _try_add_column(conn, "quote_requests", "deposit_refunded_at TEXT")
        _try_add_column(conn, "quote_requests", "deposit_last_error TEXT")
        _try_add_column(conn, "gpt_quote_observability", "server_grounding_revision TEXT")
        _try_add_column(conn, "gpt_quote_observability", "caller_grounding_revision TEXT")

        # Add scheduling columns to jobs table
        _try_add_column(conn, "jobs", "scheduled_start TEXT")
        _try_add_column(conn, "jobs", "scheduled_end TEXT")
        _try_add_column(conn, "jobs", "google_calendar_event_id TEXT")
        _try_add_column(conn, "jobs", "calendar_sync_status TEXT")
        _try_add_column(conn, "jobs", "calendar_last_error TEXT")
        _try_add_column(conn, "jobs", "started_at TEXT")
        _try_add_column(conn, "jobs", "completed_at TEXT")
        _try_add_column(conn, "jobs", "cancelled_at TEXT")
        _try_add_column(conn, "jobs", "closeout_notes TEXT")
        _try_add_column(conn, "jobs", "actual_hours REAL")
        _try_add_column(conn, "jobs", "actual_crew_size INTEGER")
        _try_add_column(conn, "jobs", "actual_labor_cost_cad REAL")
        _try_add_column(conn, "jobs", "actual_disposal_cost_cad REAL")
        _try_add_column(conn, "jobs", "actual_fuel_cost_cad REAL")
        _try_add_column(conn, "jobs", "actual_other_costs_cad REAL")
        _try_add_column(conn, "jobs", "final_amount_collected_cad REAL")
        _try_add_column(conn, "jobs", f"payment_method TEXT CHECK ({JOB_COSTING_PAYMENT_METHOD_CHECK_SQL})")
        _try_add_column(conn, "jobs", f"payment_status TEXT CHECK ({JOB_PAYMENT_STATUS_CHECK_SQL})")
        _try_add_column(conn, "jobs", f"job_profit_status TEXT CHECK ({JOB_PROFIT_STATUS_CHECK_SQL})")
        _try_add_column(conn, "jobs", "quote_accuracy_note TEXT")
        _try_add_column(conn, "jobs", "disposal_receipt_note TEXT")
        _TABLE_COL_CACHE.pop("jobs", None)
        _backfill_job_payment_status(conn)

        # Add assistant-compatible linkage to attachments without breaking existing uploads
        _try_add_column(conn, "attachments", "analysis_id TEXT")
        _try_add_column(conn, "attachments", "ocr_json TEXT")
        _try_add_column(conn, "screenshot_assistant_analyses", "quote_id TEXT")

        # Ensure uniqueness of quote_id in quote_requests for safe joins/status lookups
        try:
            _dedupe_quote_requests_by_quote_id(conn)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_quote_requests_quote_id ON quote_requests(quote_id)"
            )
        except Exception:
            # Don't block startup; worst case we just don't get the unique index.
            pass

        # Refresh schema cache in case init created new tables/cols.
        _TABLE_COL_CACHE.clear()

        # Ensure admin_audit_log table exists for audit logging
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operator_username TEXT NOT NULL,
                action_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                error_summary TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# =========================
# Quotes
# =========================

def _derive_quote_job_type(record: Dict[str, Any]) -> str:
    """
    Forward-compat: some schemas include quotes.job_type NOT NULL.
    Best-effort derive a stable value from the request.
    """
    jt = record.get("job_type")
    if isinstance(jt, str) and jt.strip():
        return jt.strip()

    req = record.get("request") or {}
    if isinstance(req, dict):
        st = req.get("service_type") or req.get("job_type")
        if isinstance(st, str) and st.strip():
            return st.strip()

    return "unknown"


def _derive_quote_total_cad(record: Dict[str, Any]) -> float:
    """
    Forward-compat: some schemas include quotes.total_cad NOT NULL.
    We derive a stable numeric value from the response totals.

    Default: use cash_total_cad as the base amount (pre-HST).
    Fallback to emt_total_cad, then 0.0.
    """
    resp = record.get("response") or {}
    if isinstance(resp, dict):
        for key in ("cash_total_cad", "emt_total_cad"):
            v = resp.get(key)
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v)
                except Exception:
                    pass
    return 0.0


def _missing_required_columns(table_info: List[sqlite3.Row], provided: Dict[str, Any]) -> List[str]:
    """
    Identify NOT NULL columns with no default that we're not providing.
    Skip PK columns (SQLite allows implicit PK behavior in some cases).
    """
    missing: List[str] = []
    for col in table_info:
        name = col["name"]
        notnull = int(col["notnull"] or 0) == 1
        has_default = col["dflt_value"] is not None
        is_pk = int(col["pk"] or 0) == 1

        if is_pk:
            continue
        if not notnull:
            continue
        if has_default:
            continue
        if name not in provided:
            missing.append(name)

    return missing


def save_quote(record: Dict[str, Any]) -> None:
    """
    Persist quote records in a schema-aware, forward-compatible way.

    Strategy:
    - Determine actual table columns via PRAGMA.
    - Build an insert dict with values we can derive.
    - Filter to existing columns.
    - If schema includes additional NOT NULL columns without defaults, raise a clear error.
    """
    conn = _connect()
    try:
        cols = _table_columns(conn, "quotes")
        info = _table_info(conn, "quotes")

        # Values we can always provide
        insert_fields: Dict[str, Any] = {
            "quote_id": record["quote_id"],
            "created_at": record["created_at"],
            "request_json": json.dumps(record["request"], ensure_ascii=False),
            "response_json": json.dumps(record["response"], ensure_ascii=False),
        }

        # Accept token (server-generated, passed in from caller)
        if "accept_token" in cols:
            insert_fields["accept_token"] = record.get("accept_token")

        if "admin_status" in cols:
            insert_fields["admin_status"] = _validate_quote_admin_status(record.get("admin_status", "pending"))

        # Forward-compat derived columns
        if "job_type" in cols:
            insert_fields["job_type"] = _derive_quote_job_type(record)
        if "total_cad" in cols:
            insert_fields["total_cad"] = _derive_quote_total_cad(record)

        # Filter to columns that exist
        filtered = {k: v for k, v in insert_fields.items() if k in cols}

        # Fail fast if the schema requires columns we can't satisfy
        missing = _missing_required_columns(info, filtered)
        if missing:
            raise ValueError(
                "quotes table has NOT NULL columns without defaults that save_quote() "
                f"cannot populate: {missing}. "
                "Make save_quote schema-aware for these columns or add DB defaults."
            )

        col_names = list(filtered.keys())
        placeholders = ", ".join(["?"] * len(col_names))
        col_sql = ", ".join(col_names)
        values = tuple(filtered[c] for c in col_names)

        conn.execute(
            f"""
            INSERT OR REPLACE INTO quotes ({col_sql})
            VALUES ({placeholders})
            """,
            values,
        )
        conn.commit()
    finally:
        conn.close()


def get_quote_record(quote_id: str) -> Optional[QuoteRecord]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    row_dict = dict(row)

    try:
        request_obj = json.loads(row_dict["request_json"])
    except Exception:
        request_obj = row_dict["request_json"]

    try:
        response_obj = json.loads(row_dict["response_json"])
    except Exception:
        response_obj = row_dict["response_json"]

    out: QuoteRecord = {
        "quote_id": row_dict["quote_id"],
        "created_at": row_dict["created_at"],
        "request": request_obj,
        "response": response_obj,
        "accept_token": row_dict.get("accept_token"),
    }
    if "admin_status" in row_dict:
        out["admin_status"] = row_dict.get("admin_status") or "pending"

    if "job_type" in row_dict:
        out["job_type"] = row_dict["job_type"]
    if "total_cad" in row_dict:
        out["total_cad"] = row_dict["total_cad"]

    return cast(QuoteRecord, out)


def list_quotes(limit: int = 50, *, include_expired: bool = False, offset: int = 0) -> List[QuoteRecord]:
    conn = _connect()
    try:
        where_sql = "" if include_expired else "WHERE COALESCE(admin_status, 'pending') != 'expired'"
        rows = conn.execute(
            f"""
            SELECT *
            FROM quotes
            {where_sql}
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        ).fetchall()
    finally:
        conn.close()

    out: List[QuoteRecord] = []
    for r in rows:
        try:
            req = json.loads(r["request_json"])
        except Exception:
            req = r["request_json"]
        try:
            resp = json.loads(r["response_json"])
        except Exception:
            resp = r["response_json"]

        item: QuoteRecord = {
            "quote_id": r["quote_id"],
            "created_at": r["created_at"],
            "request": req,
            "response": resp,
            "accept_token": r["accept_token"] if "accept_token" in r.keys() else None,
        }
        if "admin_status" in r.keys():
            item["admin_status"] = r["admin_status"] or "pending"
        if "job_type" in r.keys():
            item["job_type"] = r["job_type"]
        if "total_cad" in r.keys():
            item["total_cad"] = r["total_cad"]
        out.append(item)

    return out


def _normalize_history_phone(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    digits = _PHONE_DIGITS_RE.sub("", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return digits


def _register_customer_history_sql_functions(conn: sqlite3.Connection) -> None:
    conn.create_function("normalize_history_phone", 1, _normalize_history_phone)


def _request_phone_from_json(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("customer_phone") if isinstance(value.get("customer_phone"), str) else None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        if isinstance(parsed, dict):
            phone = parsed.get("customer_phone")
            return phone if isinstance(phone, str) else None
    return None


def _customer_history_payload(
    *,
    status: str,
    label: str,
    previous_requests: int = 0,
    previous_jobs: int = 0,
    previous_quotes: int = 0,
    last_seen: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "label": label,
        "previous_requests": previous_requests,
        "previous_jobs": previous_jobs,
        "previous_quotes": previous_quotes,
        "last_seen": last_seen,
        "match_basis": "phone" if status != "unavailable" else None,
    }


def _parse_history_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        if raw_value.endswith("Z"):
            raw_value = f"{raw_value[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_history_timestamp(values: List[Any]) -> Optional[str]:
    latest_value: Optional[str] = None
    latest_dt: Optional[datetime] = None
    for value in values:
        parsed = _parse_history_datetime(value)
        if parsed is None:
            continue
        if latest_dt is None or parsed > latest_dt:
            latest_dt = parsed
            latest_value = str(value)
    return latest_value


def load_customer_history_context(*, quote_id: str, customer_phone: Any) -> Dict[str, Any]:
    """Return conservative, read-only customer history context for admin quote detail."""
    phone_key = _normalize_history_phone(customer_phone)
    if phone_key is None:
        return _customer_history_payload(status="unavailable", label="Customer history unavailable")

    previous_requests = 0
    previous_jobs = 0
    previous_quotes = 0
    last_seen_values: List[Any] = []

    conn = _connect()
    try:
        _register_customer_history_sql_functions(conn)
        request_rows = conn.execute(
            f"""
            SELECT request_id, quote_id, customer_phone, created_at
            FROM quote_requests
            WHERE COALESCE(quote_id, '') <> ?
              AND normalize_history_phone(customer_phone) = ?
            """,
            (quote_id, phone_key),
        ).fetchall()
        job_rows = conn.execute(
            f"""
            SELECT job_id, quote_id, customer_phone, created_at
            FROM jobs
            WHERE COALESCE(quote_id, '') <> ?
              AND normalize_history_phone(customer_phone) = ?
            """,
            (quote_id, phone_key),
        ).fetchall()
        quote_rows = conn.execute(
            f"""
            SELECT q.quote_id, q.created_at, q.request_json
            FROM quotes AS q
            WHERE COALESCE(q.quote_id, '') <> ?
              AND json_valid(q.request_json) = 1
              AND normalize_history_phone(json_extract(q.request_json, '$.customer_phone')) = ?
              AND NOT EXISTS (
                  SELECT 1 FROM quote_requests AS qr WHERE qr.quote_id = q.quote_id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM jobs AS j WHERE j.quote_id = q.quote_id
              )
            """,
            (quote_id, phone_key),
        ).fetchall()
    finally:
        conn.close()

    for row in request_rows:
        if _normalize_history_phone(row["customer_phone"]) == phone_key:
            previous_requests += 1
            if row["created_at"]:
                last_seen_values.append(str(row["created_at"]))

    for row in job_rows:
        if _normalize_history_phone(row["customer_phone"]) == phone_key:
            previous_jobs += 1
            if row["created_at"]:
                last_seen_values.append(str(row["created_at"]))

    for row in quote_rows:
        if _normalize_history_phone(_request_phone_from_json(row["request_json"])) == phone_key:
            previous_quotes += 1
            if row["created_at"]:
                last_seen_values.append(str(row["created_at"]))

    last_seen = _latest_history_timestamp(last_seen_values)
    if previous_requests or previous_jobs:
        return _customer_history_payload(
            status="repeat_customer",
            label="Repeat customer",
            previous_requests=previous_requests,
            previous_jobs=previous_jobs,
            previous_quotes=previous_quotes,
            last_seen=last_seen,
        )
    if previous_quotes:
        return _customer_history_payload(
            status="possible_repeat_customer",
            label="Possible repeat customer",
            previous_quotes=previous_quotes,
            last_seen=last_seen,
        )
    return _customer_history_payload(status="new_customer", label="New customer")


ADMIN_OPS_BOARD_COUNT_KEYS = (
    "new_requests",
    "needs_followup",
    "accepted_not_booked",
    "upcoming_jobs",
    "completed_missing_costs",
    "owner_review",
    "stale_quotes",
)

ACCEPTED_NOT_BOOKED_DETAIL_ROW_LIMIT = 50


def _count_query(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else 0


def load_accepted_not_booked_detail_sources() -> List[Dict[str, Any]]:
    """Return targeted source rows for accepted or approved work waiting on scheduling."""
    accepted_not_booked_request_where = (
        "qr.status IN ('customer_accepted', 'admin_approved') AND NOT EXISTS ("
        "SELECT 1 FROM jobs AS j WHERE j.request_id = qr.request_id OR j.quote_id = qr.quote_id"
        ")"
    )
    accepted_not_booked_job_where = (
        "j.status IN ('approved', 'scheduled') AND "
        "(j.scheduled_start IS NULL OR TRIM(j.scheduled_start) = '')"
    )

    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT *
            FROM (
                SELECT
                    'request' AS item_type,
                    qr.request_id AS item_id,
                    qr.created_at AS created_at,
                    COALESCE(qr.customer_accepted_at, qr.admin_approved_at, qr.created_at) AS submitted_at,
                    qr.status AS status,
                    qr.request_id AS request_id,
                    NULL AS job_id,
                    qr.quote_id AS quote_id,
                    qr.customer_name AS customer_name,
                    qr.customer_phone AS customer_phone,
                    qr.service_type AS service_type,
                    qr.job_address AS job_address,
                    qr.requested_job_date AS requested_job_date,
                    qr.requested_time_window AS requested_time_window,
                    NULL AS scheduled_start,
                    NULL AS scheduled_end,
                    NULL AS google_calendar_event_id,
                    qr.notes AS notes
                FROM quote_requests AS qr
                WHERE {accepted_not_booked_request_where}

                UNION ALL

                SELECT
                    'job' AS item_type,
                    j.job_id AS item_id,
                    j.created_at AS created_at,
                    COALESCE(qr.admin_approved_at, qr.customer_accepted_at, j.created_at) AS submitted_at,
                    j.status AS status,
                    j.request_id AS request_id,
                    j.job_id AS job_id,
                    j.quote_id AS quote_id,
                    j.customer_name AS customer_name,
                    j.customer_phone AS customer_phone,
                    j.service_type AS service_type,
                    j.job_address AS job_address,
                    qr.requested_job_date AS requested_job_date,
                    qr.requested_time_window AS requested_time_window,
                    j.scheduled_start AS scheduled_start,
                    j.scheduled_end AS scheduled_end,
                    j.google_calendar_event_id AS google_calendar_event_id,
                    COALESCE(qr.notes, j.notes) AS notes
                FROM jobs AS j
                LEFT JOIN quote_requests AS qr ON qr.request_id = j.request_id
                WHERE {accepted_not_booked_job_where}
            )
            ORDER BY datetime(submitted_at) DESC, item_type ASC, item_id ASC
            LIMIT ?
            """,
            (ACCEPTED_NOT_BOOKED_DETAIL_ROW_LIMIT,),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def _json_truthy(column: str, field_name: str) -> str:
    return (
        f"LOWER(TRIM(CAST(json_extract({column}, '$.{field_name}') AS TEXT))) "
        "IN ('1', 'true', 'yes', 'y', 'on')"
    )


def _json_int(column: str, field_name: str) -> str:
    return f"CAST(json_extract({column}, '$.{field_name}') AS INTEGER)"


def _json_text_in(column: str, field_name: str, values: Tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return (
        f"LOWER(TRIM(CAST(json_extract({column}, '$.{field_name}') AS TEXT))) "
        f"IN ({quoted_values})"
    )


_DEMOLITION_OWNER_REVIEW_TEXT_SIGNALS: Tuple[str, ...] = (
    "apartment",
    "apartments",
    "apartment building",
    "asbestos",
    "awkward debris",
    "backyard",
    "back yard",
    "basement",
    "block",
    "blocks",
    "brick",
    "bricks",
    "bathroom tile",
    "bathroom tiles",
    "ceramic tile",
    "ceramic tiles",
    "chimney",
    "chimneys",
    "concrete",
    "condo",
    "condos",
    "deck",
    "decks",
    "dismantle",
    "downstairs",
    "dirt",
    "elevator",
    "elevators",
    "fence",
    "fences",
    "fireplace",
    "fireplaces",
    "floor tile",
    "floor tiles",
    "gazebo",
    "gazebos",
    "hazardous material",
    "hazardous materials",
    "heavy awkward debris",
    "hidden debris",
    "hidden material",
    "hidden material behind wall",
    "hidden rubble",
    "high rise",
    "inside removal",
    "lath and plaster",
    "liability sensitive",
    "long carry",
    "masonry",
    "masonry debris",
    "mortar",
    "mortars",
    "no photo",
    "no photos",
    "no driveway access",
    "not sure what material",
    "outbuilding",
    "outbuildings",
    "permit required",
    "permit sensitive",
    "regulated material",
    "regulated materials",
    "rubble",
    "shed",
    "sheds",
    "shingle",
    "shingles",
    "soil",
    "stairs",
    "stair",
    "stone",
    "stones",
    "structure",
    "structures",
    "tear down",
    "teardown",
    "tile",
    "tiles",
    "roof shingles",
    "asphalt shingles",
    "wet shingles",
    "tight access",
    "unclear material",
    "unknown debris",
    "unknown disposal volume",
    "unknown material",
    "unknown materials",
    "unknown volume",
    "upstairs unit",
    "without photos",
)
_DEMOLITION_OWNER_REVIEW_UTILITY_CONTEXT_TEXT_SIGNALS: Tuple[str, ...] = (
    "bulkhead",
    "bulkheads",
    "ceiling opening",
    "ceiling openings",
    "interior wall",
    "interior walls",
    "selective demolition",
    "selective demo",
    "wall",
    "walls",
)
_DEMOLITION_OWNER_REVIEW_UTILITY_ADJACENT_TEXT_SIGNALS: Tuple[str, ...] = (
    "duct",
    "ducting",
    "ductwork",
    "furnace",
    "hvac",
    "pipe",
    "pipes",
    "plumbing",
    "utilities",
    "utility line",
    "utility lines",
    "water heater",
    "water heaters",
)
_DEMOLITION_OWNER_REVIEW_ROOF_HEAVY_TEXT_SIGNALS: Tuple[str, ...] = (
    "roof debris",
    "roof tear off",
    "roof tear-off",
    "roofing",
    "roofing material",
)
_DEMOLITION_OWNER_REVIEW_CONSTRUCTION_MATERIAL_VALUES: Tuple[str, ...] = (
    "concrete",
    "other",
    "shingles",
    "tile",
)
_DEMOLITION_OWNER_REVIEW_DENSE_MATERIAL_VALUES: Tuple[str, ...] = (
    "brick",
    "concrete",
    "other",
    "shingles",
    "soil",
    "stone",
    "tile",
)


def _owner_review_like_patterns(value: str) -> Tuple[str, ...]:
    normalized_value = value.replace("'", "''").lower()
    words = tuple(part for part in normalized_value.split() if part)
    if len(words) <= 1:
        return (f"%{normalized_value}%",)
    return tuple(f"%{separator.join(words)}%" for separator in (" ", "-", "_", "/", "."))


def _text_expr_like_any(text_expr: str, values: Tuple[str, ...]) -> str:
    clauses = []
    for value in values:
        for pattern in _owner_review_like_patterns(value):
            clauses.append(f"{text_expr} LIKE '{pattern}'")
    return f"({' OR '.join(clauses)})"


def _sql_normalized_text_expr(text_expr: str) -> str:
    normalized_expr = f"LOWER({text_expr})"
    for codepoint in (9, 10, 13):
        normalized_expr = f"REPLACE({normalized_expr}, CHAR({codepoint}), ' ')"
    for old in ("-", "_", "/", ".", ",", ";", ":", "(", ")", "[", "]"):
        normalized_expr = f"REPLACE({normalized_expr}, '{old}', ' ')"
    return f"(' ' || {normalized_expr} || ' ')"


def _normalized_owner_review_patterns(value: str) -> Tuple[str, ...]:
    normalized_value = " ".join(value.replace("'", "''").lower().split())
    words = tuple(part for part in normalized_value.split() if part)
    if len(words) <= 1:
        return (f"% {normalized_value} %",)
    patterns = []
    for widths in product((1, 2, 3), repeat=len(words) - 1):
        phrase = words[0]
        for width, word in zip(widths, words[1:]):
            phrase += (" " * width) + word
        patterns.append(f"% {phrase} %")
    return tuple(patterns)


def _normalized_text_expr_like_any(text_expr: str, values: Tuple[str, ...]) -> str:
    normalized_expr = _sql_normalized_text_expr(text_expr)
    clauses = []
    for value in values:
        for pattern in _normalized_owner_review_patterns(value):
            clauses.append(f"{normalized_expr} LIKE '{pattern}'")
    return f"({' OR '.join(clauses)})"


def _json_text_like_any(column: str, field_name: str, values: Tuple[str, ...]) -> str:
    text_expr = f"LOWER(COALESCE(CAST(json_extract({column}, '$.{field_name}') AS TEXT), ''))"
    return _text_expr_like_any(text_expr, values)


def _json_combined_normalized_text_like_any(
    column: str,
    field_names: Tuple[str, ...],
    values: Tuple[str, ...],
) -> str:
    text_parts = " || ' ' || ".join(
        f"COALESCE(CAST(json_extract({column}, '$.{field_name}') AS TEXT), '')"
        for field_name in field_names
    )
    return _normalized_text_expr_like_any(text_parts, values)


def _json_combined_text_like_all_groups(
    column: str,
    field_names: Tuple[str, ...],
    first_values: Tuple[str, ...],
    second_values: Tuple[str, ...],
) -> str:
    return (
        f"({_json_combined_normalized_text_like_any(column, field_names, first_values)} "
        f"AND {_json_combined_normalized_text_like_any(column, field_names, second_values)})"
    )


def _owner_review_manual_signal_filter(alias: str) -> str:
    request_json = f"{alias}.request_json"
    return f"""
        CASE
            WHEN json_valid({request_json}) = 1 THEN
                CASE
                    WHEN {_json_text_in(request_json, "dense_material_type", ("concrete", "brick", "stone", "soil"))}
                      OR {_json_text_in(request_json, "construction_debris_type", ("concrete",))}
                      OR ({_json_truthy(request_json, "mixed_load")}
                          AND {_json_truthy(request_json, "contains_scrap")}
                          AND {_json_truthy(request_json, "contains_garbage")})
                      OR {_json_truthy(request_json, "has_refrigerant_appliance")}
                      OR {_json_text_in(request_json, "appliance_type", ("fridge", "freezer", "air_conditioner", "dehumidifier"))}
                      OR {_json_int(request_json, "stairs_count")} >= 3
                      OR ({_json_truthy(request_json, "basement_or_inside_removal")}
                          AND {_json_int(request_json, "stairs_count")} >= 1)
                      OR {_json_truthy(request_json, "demolition_ripout")}
                      OR ({_json_text_in(request_json, "service_type", ("demolition",))}
                          AND ({_json_text_in(request_json, "construction_debris_type", _DEMOLITION_OWNER_REVIEW_CONSTRUCTION_MATERIAL_VALUES)}
                               OR {_json_text_in(request_json, "dense_material_type", _DEMOLITION_OWNER_REVIEW_DENSE_MATERIAL_VALUES)}
                               OR {_json_truthy(request_json, "has_dense_materials")}
                               OR (LOWER(TRIM(CAST(json_extract({request_json}, '$.access_difficulty') AS TEXT))) NOT IN ('', 'normal'))
                               OR {_json_int(request_json, "floor_count")} >= 2
                               OR {_json_truthy(request_json, "basement_or_inside_removal")}
                               OR {_json_int(request_json, "stairs_count")} > 0))
                      OR ({_json_text_in(request_json, "service_type", ("demolition",))}
                          AND ({_json_text_like_any(request_json, "description", _DEMOLITION_OWNER_REVIEW_TEXT_SIGNALS)}
                               OR {_json_text_like_any(request_json, "job_description_customer", _DEMOLITION_OWNER_REVIEW_TEXT_SIGNALS)}
                               OR {_json_combined_normalized_text_like_any(request_json, ("description", "job_description_customer"), _DEMOLITION_OWNER_REVIEW_ROOF_HEAVY_TEXT_SIGNALS)}
                               OR {_json_combined_text_like_all_groups(request_json, ("description", "job_description_customer"), _DEMOLITION_OWNER_REVIEW_UTILITY_CONTEXT_TEXT_SIGNALS, _DEMOLITION_OWNER_REVIEW_UTILITY_ADJACENT_TEXT_SIGNALS)}))
                    THEN 1
                    ELSE 0
                END
            ELSE 0
        END = 1
    """


def load_admin_ops_queue_sources(*, stale_pending_before_iso: str, upcoming_start_iso: str) -> AdminOpsQueueSources:
    """Return targeted read-only counts and risk-advisory candidates for the admin ops board."""
    counts: Dict[str, int] = {key: 0 for key in ADMIN_OPS_BOARD_COUNT_KEYS}
    accepted_not_booked_detail_sources: List[Dict[str, Any]] = []

    new_requests_where = "status = 'customer_pending'"
    followup_where = (
        "followup_status IN ('needs_followup', 'contacted', 'waiting_on_customer', 'not_ready')"
    )
    accepted_not_booked_request_where = (
        "qr.status IN ('customer_accepted', 'admin_approved') AND NOT EXISTS ("
        "SELECT 1 FROM jobs AS j WHERE j.request_id = qr.request_id OR j.quote_id = qr.quote_id"
        ")"
    )
    accepted_not_booked_job_where = (
        "status IN ('approved', 'scheduled') AND "
        "(scheduled_start IS NULL OR TRIM(scheduled_start) = '')"
    )
    upcoming_jobs_where = (
        "status = 'scheduled' AND "
        "scheduled_start IS NOT NULL AND TRIM(scheduled_start) <> '' AND "
        "datetime(scheduled_start) IS NOT NULL AND "
        "datetime(scheduled_start) >= datetime(?)"
    )
    completed_missing_costing_where = (
        "status = 'completed' AND ("
        "actual_hours IS NULL OR TRIM(CAST(actual_hours AS TEXT)) = '' OR "
        "actual_crew_size IS NULL OR TRIM(CAST(actual_crew_size AS TEXT)) = '' OR "
        "actual_labor_cost_cad IS NULL OR TRIM(CAST(actual_labor_cost_cad AS TEXT)) = '' OR "
        "actual_disposal_cost_cad IS NULL OR TRIM(CAST(actual_disposal_cost_cad AS TEXT)) = '' OR "
        "actual_fuel_cost_cad IS NULL OR TRIM(CAST(actual_fuel_cost_cad AS TEXT)) = '' OR "
        "actual_other_costs_cad IS NULL OR TRIM(CAST(actual_other_costs_cad AS TEXT)) = '' OR "
        "final_amount_collected_cad IS NULL OR TRIM(CAST(final_amount_collected_cad AS TEXT)) = '' OR "
        "payment_status IS NULL OR TRIM(payment_status) = '' OR "
        "job_profit_status IS NULL OR TRIM(job_profit_status) = ''"
        ")"
    )
    stale_pending_where = (
        "COALESCE(admin_status, 'pending') = 'pending' AND datetime(created_at) <= datetime(?)"
    )
    owner_review_profit_flags_where = (
        "status = 'completed' AND job_profit_status IN ('underquoted', 'painful')"
    )
    owner_review_job_manual_signal_where = _owner_review_manual_signal_filter("j")
    owner_review_request_manual_signal_where = _owner_review_manual_signal_filter("qr")
    owner_review_quote_manual_signal_where = _owner_review_manual_signal_filter("q")

    conn = _connect()
    try:
        counts["new_requests"] = _count_query(
            conn,
            f"SELECT COUNT(*) FROM quote_requests WHERE {new_requests_where}",
        )

        counts["needs_followup"] = _count_query(
            conn,
            f"SELECT COUNT(*) FROM quote_requests WHERE {followup_where}",
        )

        counts["accepted_not_booked"] = _count_query(
            conn,
            f"""
            SELECT COUNT(*) FROM (
                SELECT 'request:' || qr.request_id AS op_key
                FROM quote_requests AS qr
                WHERE {accepted_not_booked_request_where}
                UNION ALL
                SELECT 'job:' || j.job_id AS op_key
                FROM jobs AS j
                WHERE {accepted_not_booked_job_where}
            )
            """,
        )

        counts["upcoming_jobs"] = _count_query(
            conn,
            f"SELECT COUNT(*) FROM jobs WHERE {upcoming_jobs_where}",
            (upcoming_start_iso,),
        )

        counts["completed_missing_costs"] = _count_query(
            conn,
            f"SELECT COUNT(*) FROM jobs WHERE {completed_missing_costing_where}",
        )

        counts["stale_quotes"] = _count_query(
            conn,
            f"SELECT COUNT(*) FROM quotes WHERE {stale_pending_where}",
            (stale_pending_before_iso,),
        )

        counts["owner_review"] = _count_query(
            conn,
            f"""
            SELECT COUNT(*) FROM (
                SELECT 'job-profit:' || j.job_id AS op_key
                FROM jobs AS j
                WHERE {owner_review_profit_flags_where}
                UNION ALL
                SELECT 'job:' || j.job_id AS op_key
                FROM jobs AS j
                WHERE j.status IN ('approved', 'scheduled', 'in_progress')
                  AND j.request_json IS NOT NULL
                  AND TRIM(j.request_json) <> ''
                  AND ({owner_review_job_manual_signal_where})
                UNION ALL
                SELECT 'request:' || qr.request_id AS op_key
                FROM quote_requests AS qr
                WHERE qr.status IN ('customer_pending', 'customer_accepted', 'admin_approved')
                  AND qr.request_json IS NOT NULL
                  AND TRIM(qr.request_json) <> ''
                  AND ({owner_review_request_manual_signal_where})
                  AND NOT EXISTS (
                      SELECT 1 FROM jobs AS j WHERE j.request_id = qr.request_id OR j.quote_id = qr.quote_id
                  )
                UNION ALL
                SELECT 'quote:' || q.quote_id AS op_key
                FROM quotes AS q
                WHERE COALESCE(q.admin_status, 'pending') = 'pending'
                  AND q.request_json IS NOT NULL
                  AND TRIM(q.request_json) <> ''
                  AND ({owner_review_quote_manual_signal_where})
                  AND NOT EXISTS (SELECT 1 FROM quote_requests AS qr WHERE qr.quote_id = q.quote_id)
                  AND NOT EXISTS (SELECT 1 FROM jobs AS j WHERE j.quote_id = q.quote_id)
            )
            """,
        )
    finally:
        conn.close()

    accepted_not_booked_detail_sources = load_accepted_not_booked_detail_sources()

    return {
        "counts": counts,
        "accepted_not_booked_detail_sources": accepted_not_booked_detail_sources,
    }


# =========================
# Completed Job Profit Report
# =========================

_PROFIT_REPORT_FIELDS = (
    "job_id",
    "service_type",
    "status",
    "actual_labor_cost_cad",
    "actual_disposal_cost_cad",
    "actual_fuel_cost_cad",
    "actual_other_costs_cad",
    "final_amount_collected_cad",
    "payment_method",
    "payment_status",
    "job_profit_status",
    "scheduled_start",
    "customer_name",
)


def load_completed_job_profit_report_sources(*, limit: int = 200) -> List[Dict[str, Any]]:
    """Return completed job rows with all profit-report fields for read-only analysis.

    Only returns jobs with status='completed'. No mutations.
    """
    safe_limit = max(1, min(int(limit), 500))
    cols = ", ".join(_PROFIT_REPORT_FIELDS)
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {cols} FROM jobs WHERE status = 'completed' ORDER BY scheduled_start DESC NULLS LAST LIMIT ?",
            (safe_limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# =========================
# Manual Completed Job Calibration Entries
# =========================

_MANUAL_CALIBRATION_TEXT_LIMITS = {
    "updated_at": 80,
    "job_title": 120,
    "service_type": 120,
    "secondary_category": 120,
    "notes": 1000,
    "calibration_note": 1000,
}


def _required_limited_text(value: Any, field_name: str, max_length: int) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text[:max_length]


def _optional_limited_text(value: Any, field_name: str) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:_MANUAL_CALIBRATION_TEXT_LIMITS[field_name]]


def _required_positive_float(value: Any, field_name: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than 0")
    return parsed


def _required_positive_int(value: Any, field_name: str) -> int:
    parsed_float = float(value)
    if not parsed_float.is_integer():
        raise ValueError(f"{field_name} must be a whole number")
    parsed = int(parsed_float)
    if parsed < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return parsed


def _optional_nonnegative_float(value: Any, field_name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _normalize_bool_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "on"} else 0
    return 1 if bool(value) else 0


def _optional_enum(value: Any, field_name: str, allowed: Tuple[str, ...]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed)}")
    return normalized


def _required_enum(value: Any, field_name: str, allowed: Tuple[str, ...]) -> str:
    normalized = _optional_enum(value, field_name, allowed)
    if normalized is None:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_completed_job_calibration_entry(
    entry: Dict[str, Any],
) -> CompletedJobCalibrationEntry:
    crew_size = _required_positive_int(entry.get("crew_size"), "crew_size")
    duration_hours = round(_required_positive_float(entry.get("duration_hours"), "duration_hours"), 2)
    labour_hours = _optional_nonnegative_float(entry.get("labour_hours"), "labour_hours")
    if labour_hours is None:
        labour_hours = round(crew_size * duration_hours, 2)
    else:
        labour_hours = round(labour_hours, 2)

    normalized: CompletedJobCalibrationEntry = {
        "entry_id": _required_limited_text(entry.get("entry_id"), "entry_id", 120),
        "created_at": _required_limited_text(entry.get("created_at"), "created_at", 80),
        "updated_at": _optional_limited_text(entry.get("updated_at"), "updated_at"),
        "operator_username": _required_limited_text(entry.get("operator_username"), "operator_username", 120),
        "job_title": _required_limited_text(
            entry.get("job_title"),
            "job_title",
            _MANUAL_CALIBRATION_TEXT_LIMITS["job_title"],
        ),
        "service_type": _required_limited_text(
            entry.get("service_type"),
            "service_type",
            _MANUAL_CALIBRATION_TEXT_LIMITS["service_type"],
        ),
        "secondary_category": _optional_limited_text(entry.get("secondary_category"), "secondary_category"),
        "quoted_price_cad": _optional_nonnegative_float(entry.get("quoted_price_cad"), "quoted_price_cad"),
        "actual_collected_cad": round(
            _required_positive_float(entry.get("actual_collected_cad"), "actual_collected_cad"),
            2,
        ),
        "crew_size": crew_size,
        "duration_hours": duration_hours,
        "labour_hours": labour_hours,
        "disposal_cost_cad": _optional_nonnegative_float(entry.get("disposal_cost_cad"), "disposal_cost_cad"),
        "fuel_cost_cad": _optional_nonnegative_float(entry.get("fuel_cost_cad"), "fuel_cost_cad"),
        "other_costs_cad": _optional_nonnegative_float(entry.get("other_costs_cad"), "other_costs_cad"),
        "difficulty": _optional_enum(
            entry.get("difficulty"),
            "difficulty",
            ALLOWED_MANUAL_CALIBRATION_DIFFICULTIES,
        ),
        "access_difficulty": _optional_enum(
            entry.get("access_difficulty"),
            "access_difficulty",
            ALLOWED_MANUAL_CALIBRATION_ACCESS_DIFFICULTIES,
        ),
        "disassembly_required": _normalize_bool_int(entry.get("disassembly_required")),
        "dense_materials": _normalize_bool_int(entry.get("dense_materials")),
        "underquoted": _normalize_bool_int(entry.get("underquoted")),
        "painful_job": _normalize_bool_int(entry.get("painful_job")),
        "pricing_result": _required_enum(
            entry.get("pricing_result"),
            "pricing_result",
            ALLOWED_MANUAL_CALIBRATION_PRICING_RESULTS,
        ),
        "notes": _optional_limited_text(entry.get("notes"), "notes"),
        "calibration_note": _optional_limited_text(entry.get("calibration_note"), "calibration_note"),
    }
    return normalized


def save_completed_job_calibration_entry(
    entry: Dict[str, Any],
) -> CompletedJobCalibrationEntry:
    normalized = _normalize_completed_job_calibration_entry(entry)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO completed_job_calibration_entries (
                entry_id, created_at, updated_at, operator_username,
                job_title, service_type, secondary_category,
                quoted_price_cad, actual_collected_cad, crew_size,
                duration_hours, labour_hours, disposal_cost_cad,
                fuel_cost_cad, other_costs_cad, difficulty,
                access_difficulty, disassembly_required, dense_materials,
                underquoted, painful_job, pricing_result, notes,
                calibration_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["entry_id"],
                normalized["created_at"],
                normalized["updated_at"],
                normalized["operator_username"],
                normalized["job_title"],
                normalized["service_type"],
                normalized["secondary_category"],
                normalized["quoted_price_cad"],
                normalized["actual_collected_cad"],
                normalized["crew_size"],
                normalized["duration_hours"],
                normalized["labour_hours"],
                normalized["disposal_cost_cad"],
                normalized["fuel_cost_cad"],
                normalized["other_costs_cad"],
                normalized["difficulty"],
                normalized["access_difficulty"],
                normalized["disassembly_required"],
                normalized["dense_materials"],
                normalized["underquoted"],
                normalized["painful_job"],
                normalized["pricing_result"],
                normalized["notes"],
                normalized["calibration_note"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return normalized


def _manual_completed_jobs_limit(limit: int = 10) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 10
    if parsed <= 0:
        parsed = 10
    return min(parsed, 25)


def list_completed_job_calibration_entries(
    limit: int = 10,
) -> List[CompletedJobCalibrationEntry]:
    safe_limit = _manual_completed_jobs_limit(limit)
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM completed_job_calibration_entries
            ORDER BY datetime(created_at) DESC, entry_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    finally:
        conn.close()

    return [cast(CompletedJobCalibrationEntry, dict(row)) for row in rows]


def get_completed_job_calibration_entry(entry_id: str) -> Optional[CompletedJobCalibrationEntry]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM completed_job_calibration_entries WHERE entry_id = ?",
            (entry_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return cast(CompletedJobCalibrationEntry, dict(row))


_GPT_ADMIN_NOTE_TEXT_LIMITS = {
    "note_id": 120,
    "created_at": 80,
    "updated_at": 80,
    "related_entity_id": 160,
    "title": 120,
    "summary": 1200,
    "recommendation": 1000,
    "customer_message_draft": 1000,
    "idempotency_key": 160,
    "payload_hash": 128,
    "server_grounding_revision": 120,
    "caller_grounding_revision": 120,
}


def _optional_gpt_admin_note_text(value: Any, field_name: str) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    limit = _GPT_ADMIN_NOTE_TEXT_LIMITS[field_name]
    if len(text) > limit:
        raise ValueError(f"{field_name} must be {limit} characters or fewer")
    return text


def _normalize_gpt_admin_note_flag(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    if len(text) > 40:
        raise ValueError("risk flag values must be 40 characters or fewer")
    return text


def _normalize_gpt_admin_note_risk_flags(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("risk_flags must be a list")

    flags: List[str] = []
    for item in value:
        flag = _normalize_gpt_admin_note_flag(item)
        if flag and flag not in flags:
            flags.append(flag)
        if len(flags) > 10:
            raise ValueError("risk_flags may include at most 10 items")
    return flags


def _row_to_gpt_admin_note(row: sqlite3.Row) -> GptAdminNoteRecord:
    try:
        raw_flags = json.loads(row["risk_flags_json"]) if row["risk_flags_json"] else []
    except (TypeError, ValueError):
        raw_flags = []
    risk_flags = [str(flag) for flag in raw_flags] if isinstance(raw_flags, list) else []

    return {
        "note_id": row["note_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "source": row["source"],
        "related_entity_type": row["related_entity_type"],
        "related_entity_id": row["related_entity_id"],
        "note_type": row["note_type"],
        "title": row["title"],
        "summary": row["summary"],
        "recommendation": row["recommendation"],
        "customer_message_draft": row["customer_message_draft"],
        "risk_flags": risk_flags,
        "follow_up_needed": bool(row["follow_up_needed"]),
        "customer_visible": bool(row["customer_visible"]),
        "pricing_effect": row["pricing_effect"],
        "review_status": row["review_status"],
        "idempotency_key": row["idempotency_key"],
        "payload_hash": row["payload_hash"],
        "server_grounding_revision": row["server_grounding_revision"],
        "caller_grounding_revision": row["caller_grounding_revision"],
    }


def _normalize_gpt_admin_note_record(record: Dict[str, Any]) -> Dict[str, Any]:
    related_entity_type = _required_enum(
        record.get("related_entity_type"),
        "related_entity_type",
        ALLOWED_GPT_ADMIN_NOTE_RELATED_ENTITY_TYPES,
    )
    related_entity_id = _optional_gpt_admin_note_text(record.get("related_entity_id"), "related_entity_id")
    if related_entity_type != "general" and not related_entity_id:
        raise ValueError("related_entity_id is required unless related_entity_type is general")

    return {
        "note_id": _required_limited_text(
            record.get("note_id"),
            "note_id",
            _GPT_ADMIN_NOTE_TEXT_LIMITS["note_id"],
        ),
        "created_at": _required_limited_text(
            record.get("created_at"),
            "created_at",
            _GPT_ADMIN_NOTE_TEXT_LIMITS["created_at"],
        ),
        "updated_at": _optional_gpt_admin_note_text(record.get("updated_at"), "updated_at"),
        "source": "internal_gpt",
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "note_type": _required_enum(
            record.get("note_type"),
            "note_type",
            ALLOWED_GPT_ADMIN_NOTE_TYPES,
        ),
        "title": _required_limited_text(
            record.get("title"),
            "title",
            _GPT_ADMIN_NOTE_TEXT_LIMITS["title"],
        ),
        "summary": _required_limited_text(
            record.get("summary"),
            "summary",
            _GPT_ADMIN_NOTE_TEXT_LIMITS["summary"],
        ),
        "recommendation": _optional_gpt_admin_note_text(record.get("recommendation"), "recommendation"),
        "customer_message_draft": _optional_gpt_admin_note_text(
            record.get("customer_message_draft"),
            "customer_message_draft",
        ),
        "risk_flags": _normalize_gpt_admin_note_risk_flags(record.get("risk_flags")),
        "follow_up_needed": _normalize_bool_int(record.get("follow_up_needed")),
        "customer_visible": 0,
        "pricing_effect": "none",
        "review_status": _required_enum(
            record.get("review_status", "open"),
            "review_status",
            ALLOWED_GPT_ADMIN_NOTE_REVIEW_STATUSES,
        ),
        "idempotency_key": _optional_gpt_admin_note_text(record.get("idempotency_key"), "idempotency_key"),
        "payload_hash": _required_limited_text(
            record.get("payload_hash"),
            "payload_hash",
            _GPT_ADMIN_NOTE_TEXT_LIMITS["payload_hash"],
        ),
        "server_grounding_revision": _optional_gpt_admin_note_text(
            record.get("server_grounding_revision"),
            "server_grounding_revision",
        ),
        "caller_grounding_revision": _optional_gpt_admin_note_text(
            record.get("caller_grounding_revision"),
            "caller_grounding_revision",
        ),
    }


def save_gpt_admin_note(
    record: Dict[str, Any],
    *,
    duplicate_since_created_at: Optional[str] = None,
) -> GptAdminNoteRecord:
    normalized = _normalize_gpt_admin_note_record(record)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if normalized["idempotency_key"]:
            existing = _get_gpt_admin_note_by_idempotency_key_conn(
                conn,
                normalized["idempotency_key"],
            )
            if existing is not None:
                conn.rollback()
                raise GptAdminNoteIdempotencyReplay(existing)

        if duplicate_since_created_at is not None:
            duplicate = _get_recent_gpt_admin_note_by_payload_hash_conn(
                conn,
                normalized["payload_hash"],
                duplicate_since_created_at,
            )
            if duplicate is not None:
                conn.rollback()
                raise GptAdminNoteDuplicatePayload(duplicate)

        try:
            conn.execute(
                """
                INSERT INTO gpt_admin_notes (
                    note_id, created_at, updated_at, source, related_entity_type,
                    related_entity_id, note_type, title, summary, recommendation,
                    customer_message_draft, risk_flags_json, follow_up_needed,
                    customer_visible, pricing_effect, review_status, idempotency_key,
                    payload_hash, server_grounding_revision, caller_grounding_revision
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized["note_id"],
                    normalized["created_at"],
                    normalized["updated_at"],
                    normalized["source"],
                    normalized["related_entity_type"],
                    normalized["related_entity_id"],
                    normalized["note_type"],
                    normalized["title"],
                    normalized["summary"],
                    normalized["recommendation"],
                    normalized["customer_message_draft"],
                    json.dumps(normalized["risk_flags"], ensure_ascii=False),
                    normalized["follow_up_needed"],
                    normalized["customer_visible"],
                    normalized["pricing_effect"],
                    normalized["review_status"],
                    normalized["idempotency_key"],
                    normalized["payload_hash"],
                    normalized["server_grounding_revision"],
                    normalized["caller_grounding_revision"],
                ),
            )
        except sqlite3.IntegrityError as exc:
            existing = None
            if normalized["idempotency_key"]:
                existing = _get_gpt_admin_note_by_idempotency_key_conn(
                    conn,
                    normalized["idempotency_key"],
                )
            conn.rollback()
            if existing is not None:
                raise GptAdminNoteIdempotencyReplay(existing) from exc
            raise
        conn.commit()
    finally:
        conn.close()

    saved = get_gpt_admin_note(normalized["note_id"])
    if saved is None:
        raise RuntimeError("GPT admin note was not saved")
    return saved


def _get_gpt_admin_note_by_idempotency_key_conn(
    conn: sqlite3.Connection,
    idempotency_key: str,
) -> Optional[GptAdminNoteRecord]:
    row = conn.execute(
        "SELECT * FROM gpt_admin_notes WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchone()
    if not row:
        return None
    return _row_to_gpt_admin_note(row)


def _get_recent_gpt_admin_note_by_payload_hash_conn(
    conn: sqlite3.Connection,
    payload_hash: str,
    since_created_at: str,
) -> Optional[GptAdminNoteRecord]:
    row = conn.execute(
        """
        SELECT *
        FROM gpt_admin_notes
        WHERE payload_hash = ?
          AND julianday(created_at) >= julianday(?)
        ORDER BY julianday(created_at) DESC, rowid DESC
        LIMIT 1
        """,
        (payload_hash, since_created_at),
    ).fetchone()
    if not row:
        return None
    return _row_to_gpt_admin_note(row)


def get_gpt_admin_note(note_id: str) -> Optional[GptAdminNoteRecord]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM gpt_admin_notes WHERE note_id = ?",
            (note_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return _row_to_gpt_admin_note(row)


def get_gpt_admin_note_by_idempotency_key(
    idempotency_key: str,
) -> Optional[GptAdminNoteRecord]:
    conn = _connect()
    try:
        return _get_gpt_admin_note_by_idempotency_key_conn(conn, idempotency_key)
    finally:
        conn.close()


def get_recent_gpt_admin_note_by_payload_hash(
    payload_hash: str,
    since_created_at: str,
) -> Optional[GptAdminNoteRecord]:
    conn = _connect()
    try:
        return _get_recent_gpt_admin_note_by_payload_hash_conn(
            conn,
            payload_hash,
            since_created_at,
        )
    finally:
        conn.close()


def _gpt_admin_notes_limit(limit: int = 50) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 50
    if parsed <= 0:
        parsed = 50
    return min(parsed, 100)


def list_gpt_admin_notes(
    limit: int = 50,
    *,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    review_status: Optional[str] = None,
) -> List[GptAdminNoteRecord]:
    safe_limit = _gpt_admin_notes_limit(limit)
    clauses: List[str] = []
    params: List[Any] = []

    if related_entity_type is not None:
        normalized_type = _required_enum(
            related_entity_type,
            "related_entity_type",
            ALLOWED_GPT_ADMIN_NOTE_RELATED_ENTITY_TYPES,
        )
        clauses.append("related_entity_type = ?")
        params.append(normalized_type)

    if related_entity_id is not None:
        clauses.append("related_entity_id = ?")
        params.append(str(related_entity_id).strip())

    if review_status is not None:
        normalized_status = _required_enum(
            review_status,
            "review_status",
            ALLOWED_GPT_ADMIN_NOTE_REVIEW_STATUSES,
        )
        clauses.append("review_status = ?")
        params.append(normalized_status)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(safe_limit)
    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT *
            FROM gpt_admin_notes
            {where_sql}
            ORDER BY julianday(created_at) DESC, rowid DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_gpt_admin_note(row) for row in rows]


def update_quote_admin_status(quote_id: str, admin_status: str) -> Optional[QuoteRecord]:
    normalized_status = _validate_quote_admin_status(admin_status)
    conn = _connect()
    try:
        row = conn.execute("SELECT quote_id FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            """
            UPDATE quotes
            SET admin_status = ?
            WHERE quote_id = ?
            """,
            (normalized_status, quote_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_quote_record(quote_id)


# =========================
# Quote requests
# =========================

def _quote_request_from_row(
    row: sqlite3.Row,
    *,
    include_payment_fields: bool = False,
    include_followup_status: bool = False,
) -> QuoteRequest | QuoteRequestRecord:
    row_dict = dict(row)

    try:
        req = json.loads(row_dict["request_json"])
    except Exception:
        req = row_dict["request_json"]

    out: Dict[str, Any] = {
        "request_id": row_dict["request_id"],
        "created_at": row_dict["created_at"],
        "status": row_dict["status"],
        "quote_id": row_dict["quote_id"],
        "customer_name": row_dict["customer_name"],
        "customer_phone": row_dict["customer_phone"],
        "job_address": row_dict["job_address"],
        "job_description_customer": row_dict["job_description_customer"],
        "job_description_internal": row_dict["job_description_internal"],
        "service_type": row_dict["service_type"],
        "cash_total_cad": row_dict["cash_total_cad"],
        "emt_total_cad": row_dict["emt_total_cad"],
        "request_json": req,
        "notes": row_dict["notes"],
        "requested_job_date": row_dict["requested_job_date"],
        "requested_time_window": row_dict["requested_time_window"],
        "customer_accepted_at": row_dict["customer_accepted_at"],
        "admin_approved_at": row_dict["admin_approved_at"],
        "accept_token": row_dict["accept_token"],
        "booking_token": row_dict["booking_token"],
        "booking_token_created_at": row_dict["booking_token_created_at"],
    }

    if include_followup_status:
        out["followup_status"] = row_dict.get("followup_status")

    if include_payment_fields:
        out.update(
            {
                "deposit_required_cad": row_dict.get("deposit_required_cad"),
                "deposit_status": row_dict.get("deposit_status"),
                "deposit_paid_at": row_dict.get("deposit_paid_at"),
                "deposit_refund_status": row_dict.get("deposit_refund_status"),
                "deposit_refunded_at": row_dict.get("deposit_refunded_at"),
                "deposit_last_error": row_dict.get("deposit_last_error"),
            }
        )
        return cast(QuoteRequestRecord, out)

    return cast(QuoteRequest, out)


def save_quote_request(record: Dict[str, Any]) -> None:
    _validate_deposit_status(record.get("deposit_status"))
    followup_status = _validate_quote_request_followup_status(record.get("followup_status"))

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO quote_requests
            (request_id, created_at, status, quote_id,
             customer_name, customer_phone, job_address,
             job_description_customer, job_description_internal,
             service_type, cash_total_cad, emt_total_cad,
             request_json, notes, requested_job_date, requested_time_window,
             customer_accepted_at, admin_approved_at, accept_token, booking_token, booking_token_created_at,
             followup_status, deposit_required_cad, deposit_status, deposit_paid_at, deposit_refund_status,
             deposit_refunded_at, deposit_last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["request_id"],
                record["created_at"],
                record["status"],
                record["quote_id"],
                record.get("customer_name"),
                record.get("customer_phone"),
                record.get("job_address"),
                record.get("job_description_customer"),
                record.get("job_description_internal"),
                record["service_type"],
                float(record["cash_total_cad"]),
                float(record["emt_total_cad"]),
                json.dumps(record["request_json"], ensure_ascii=False),
                record.get("notes"),
                record.get("requested_job_date"),
                record.get("requested_time_window"),
                record.get("customer_accepted_at"),
                record.get("admin_approved_at"),
                record.get("accept_token"),
                record.get("booking_token"),
                record.get("booking_token_created_at"),
                followup_status,
                record.get("deposit_required_cad"),
                record.get("deposit_status"),
                record.get("deposit_paid_at"),
                record.get("deposit_refund_status"),
                record.get("deposit_refunded_at"),
                record.get("deposit_last_error"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_quote_request(request_id: str) -> Optional[QuoteRequest]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM quote_requests WHERE request_id = ?", (request_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return cast(QuoteRequest, _quote_request_from_row(row))


def get_quote_request_record(request_id: str) -> Optional[QuoteRequestRecord]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM quote_requests WHERE request_id = ?", (request_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return cast(QuoteRequestRecord, _quote_request_from_row(row, include_payment_fields=True, include_followup_status=True))


def get_quote_request_by_quote_id(quote_id: str) -> Optional[QuoteRequest]:
    conn = _connect()
    try:
        row = conn.execute("SELECT request_id FROM quote_requests WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return get_quote_request(row["request_id"])


def list_quote_requests(
    limit: int = 50,
    *,
    include_followup_status: bool = False,
    offset: int = 0,
) -> List[QuoteRequest]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT request_id
            FROM quote_requests
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        ).fetchall()
    finally:
        conn.close()

    out: List[QuoteRequest] = []
    for r in rows:
        if include_followup_status:
            item = get_quote_request_record(r["request_id"])
        else:
            item = get_quote_request(r["request_id"])
        if item is not None:
            out.append(cast(QuoteRequest, item))
    return out


def update_quote_request(
    request_id: str,
    *,
    status: Optional[str] = None,
    notes: Any = UNSET,
    requested_job_date: Any = UNSET,
    requested_time_window: Any = UNSET,
    customer_accepted_at: Any = UNSET,
    admin_approved_at: Any = UNSET,
    booking_token: Any = UNSET,
    booking_token_created_at: Any = UNSET,
    followup_status: Any = UNSET,
    deposit_required_cad: Any = UNSET,
    deposit_status: Any = UNSET,
    deposit_paid_at: Any = UNSET,
    deposit_refund_status: Any = UNSET,
    deposit_refunded_at: Any = UNSET,
    deposit_last_error: Any = UNSET,
) -> Optional[QuoteRequest]:
    existing = get_quote_request_record(request_id)
    if not existing:
        return None

    updated: Dict[str, Any] = dict(existing)

    # Status is not nullable in our schema; `None` means "leave unchanged".
    if status is not None:
        validate_quote_request_transition(existing["status"], status)
        updated["status"] = status

    # Nullable fields: UNSET means "leave unchanged", None means "clear"
    if notes is not UNSET:
        updated["notes"] = notes
    if requested_job_date is not UNSET:
        updated["requested_job_date"] = requested_job_date
    if requested_time_window is not UNSET:
        updated["requested_time_window"] = requested_time_window
    if customer_accepted_at is not UNSET:
        updated["customer_accepted_at"] = customer_accepted_at
    if admin_approved_at is not UNSET:
        updated["admin_approved_at"] = admin_approved_at
    if booking_token is not UNSET:
        updated["booking_token"] = booking_token
    if booking_token_created_at is not UNSET:
        updated["booking_token_created_at"] = booking_token_created_at
    if followup_status is not UNSET:
        updated["followup_status"] = _validate_quote_request_followup_status(followup_status)
    if deposit_required_cad is not UNSET:
        updated["deposit_required_cad"] = deposit_required_cad
    if deposit_status is not UNSET:
        _validate_deposit_status(deposit_status)
        updated["deposit_status"] = deposit_status
    if deposit_paid_at is not UNSET:
        updated["deposit_paid_at"] = deposit_paid_at
    if deposit_refund_status is not UNSET:
        updated["deposit_refund_status"] = deposit_refund_status
    if deposit_refunded_at is not UNSET:
        updated["deposit_refunded_at"] = deposit_refunded_at
    if deposit_last_error is not UNSET:
        updated["deposit_last_error"] = deposit_last_error

    save_quote_request(
        {
            "request_id": updated["request_id"],
            "created_at": updated["created_at"],
            "status": updated["status"],
            "quote_id": updated["quote_id"],
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
            "requested_job_date": updated.get("requested_job_date"),
            "requested_time_window": updated.get("requested_time_window"),
            "customer_accepted_at": updated.get("customer_accepted_at"),
            "admin_approved_at": updated.get("admin_approved_at"),
            "accept_token": updated.get("accept_token"),
            "booking_token": updated.get("booking_token"),
            "booking_token_created_at": updated.get("booking_token_created_at"),
            "followup_status": updated.get("followup_status"),
            "deposit_required_cad": updated.get("deposit_required_cad"),
            "deposit_status": updated.get("deposit_status"),
            "deposit_paid_at": updated.get("deposit_paid_at"),
            "deposit_refund_status": updated.get("deposit_refund_status"),
            "deposit_refunded_at": updated.get("deposit_refunded_at"),
            "deposit_last_error": updated.get("deposit_last_error"),
        }
    )
    return get_quote_request(request_id)


def update_quote_request_followup_status(request_id: str, followup_status: Any) -> Optional[QuoteRequestRecord]:
    updated = update_quote_request(request_id, followup_status=followup_status)
    if updated is None:
        return None
    return get_quote_request_record(request_id)


# =========================
# Payment attempts
# =========================

def _payment_attempt_from_row(row: sqlite3.Row) -> PaymentAttempt:
    return {
        "payment_attempt_id": row["payment_attempt_id"],
        "request_id": row["request_id"],
        "provider": row["provider"],
        "amount_cad": row["amount_cad"],
        "checkout_session_id": row["checkout_session_id"],
        "payment_intent_id": row["payment_intent_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "refund_id": row["refund_id"],
        "last_error": row["last_error"],
    }


def save_payment_attempt(record: Dict[str, Any]) -> None:
    status = _validate_payment_attempt_status(record.get("status"))

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO payment_attempts
            (payment_attempt_id, request_id, provider, amount_cad, checkout_session_id,
             payment_intent_id, status, created_at, updated_at, refund_id, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["payment_attempt_id"],
                record["request_id"],
                record["provider"],
                float(record["amount_cad"]),
                record.get("checkout_session_id"),
                record.get("payment_intent_id"),
                status,
                record["created_at"],
                record["updated_at"],
                record.get("refund_id"),
                record.get("last_error"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_payment_attempt(payment_attempt_id: str) -> Optional[PaymentAttempt]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM payment_attempts WHERE payment_attempt_id = ?",
            (payment_attempt_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return _payment_attempt_from_row(row)


def list_payment_attempts_for_request(request_id: str, limit: int = 50) -> List[PaymentAttempt]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM payment_attempts
            WHERE request_id = ?
            ORDER BY datetime(created_at) DESC, payment_attempt_id DESC
            LIMIT ?
            """,
            (request_id, int(limit)),
        ).fetchall()
    finally:
        conn.close()

    return [_payment_attempt_from_row(row) for row in rows]


def update_payment_attempt(
    payment_attempt_id: str,
    *,
    checkout_session_id: Any = UNSET,
    payment_intent_id: Any = UNSET,
    status: Any = UNSET,
    updated_at: Any = UNSET,
    refund_id: Any = UNSET,
    last_error: Any = UNSET,
) -> Optional[PaymentAttempt]:
    existing = get_payment_attempt(payment_attempt_id)
    if not existing:
        return None

    updated: Dict[str, Any] = dict(existing)

    if checkout_session_id is not UNSET:
        updated["checkout_session_id"] = checkout_session_id
    if payment_intent_id is not UNSET:
        updated["payment_intent_id"] = payment_intent_id
    if status is not UNSET:
        updated["status"] = _validate_payment_attempt_status(status)
    if updated_at is not UNSET:
        updated["updated_at"] = updated_at
    if refund_id is not UNSET:
        updated["refund_id"] = refund_id
    if last_error is not UNSET:
        updated["last_error"] = last_error

    save_payment_attempt(updated)
    return get_payment_attempt(payment_attempt_id)


# =========================
# Webhook events
# =========================

def _webhook_event_from_row(row: sqlite3.Row) -> WebhookEventRecord:
    payload: Any = row["payload_json"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass

    return {
        "provider_event_id": row["provider_event_id"],
        "provider": row["provider"],
        "event_type": row["event_type"],
        "received_at": row["received_at"],
        "processed_at": row["processed_at"],
        "payload_json": payload,
    }


def save_webhook_event(record: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO webhook_events
            (provider_event_id, provider, event_type, received_at, processed_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["provider_event_id"],
                record["provider"],
                record["event_type"],
                record["received_at"],
                record.get("processed_at"),
                json.dumps(record.get("payload_json"), ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_webhook_event(provider: str, provider_event_id: str) -> Optional[WebhookEventRecord]:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE provider = ? AND provider_event_id = ?
            """,
            (provider, provider_event_id),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return _webhook_event_from_row(row)


def mark_webhook_event_processed(
    provider: str,
    provider_event_id: str,
    *,
    processed_at: Optional[str],
) -> Optional[WebhookEventRecord]:
    existing = get_webhook_event(provider, provider_event_id)
    if not existing:
        return None

    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE webhook_events
            SET processed_at = ?
            WHERE provider = ? AND provider_event_id = ?
            """,
            (processed_at, provider, provider_event_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_webhook_event(provider, provider_event_id)


# =========================
# Notification attempts
# =========================

def _notification_attempt_from_row(row: sqlite3.Row) -> NotificationAttemptRecord:
    return {
        "event_type": row["event_type"],
        "request_id": row["request_id"],
        "quote_id": row["quote_id"],
        "channel": row["channel"],
        "recipient": row["recipient"],
        "status": row["status"],
        "attempt_count": int(row["attempt_count"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "sent_at": row["sent_at"],
        "last_error": row["last_error"],
    }


def _parse_notification_attempt_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    raw_value = value.strip()
    if not raw_value:
        return None
    normalized = raw_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_pending_notification_attempt_stale(updated_at: Any, *, now_iso: str) -> bool:
    now_dt = _parse_notification_attempt_datetime(now_iso) or datetime.now(timezone.utc)
    updated_dt = _parse_notification_attempt_datetime(updated_at)
    if updated_dt is None:
        # Invalid timestamps are treated as stale so retries are not permanently blocked.
        return True
    stale_after = timedelta(minutes=NOTIFICATION_PENDING_STALE_THRESHOLD_MINUTES)
    return now_dt - updated_dt >= stale_after


def reserve_notification_attempt(
    *,
    request_id: str,
    event_type: str,
    quote_id: Optional[str],
    channel: str,
    recipient: Optional[str],
    created_at: str,
) -> Optional[NotificationAttemptRecord]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            """
            SELECT *
            FROM notification_attempts
            WHERE request_id = ? AND event_type = ?
            """,
            (request_id, event_type),
        ).fetchone()

        if existing:
            existing_record = _notification_attempt_from_row(existing)
            if existing_record["status"] == "sent":
                conn.commit()
                return None

            if existing_record["status"] == "pending":
                if not _is_pending_notification_attempt_stale(
                    existing_record.get("updated_at"),
                    now_iso=created_at,
                ):
                    conn.commit()
                    return None

                conn.execute(
                    """
                    UPDATE notification_attempts
                    SET quote_id = ?,
                        channel = ?,
                        recipient = ?,
                        status = 'pending',
                        attempt_count = attempt_count + 1,
                        updated_at = ?,
                        sent_at = NULL,
                        last_error = NULL
                    WHERE request_id = ?
                      AND event_type = ?
                      AND status = 'pending'
                    """,
                    (quote_id, channel, recipient, created_at, request_id, event_type),
                )
                row = conn.execute(
                    """
                    SELECT *
                    FROM notification_attempts
                    WHERE request_id = ? AND event_type = ?
                    """,
                    (request_id, event_type),
                ).fetchone()
                conn.commit()
                return _notification_attempt_from_row(row) if row else None

            conn.execute(
                """
                UPDATE notification_attempts
                SET quote_id = ?,
                    channel = ?,
                    recipient = ?,
                    status = 'pending',
                    updated_at = ?,
                    sent_at = NULL,
                    last_error = NULL
                WHERE request_id = ?
                  AND event_type = ?
                  AND status IN ('failed', 'skipped')
                """,
                (quote_id, channel, recipient, created_at, request_id, event_type),
            )
            row = conn.execute(
                """
                SELECT *
                FROM notification_attempts
                WHERE request_id = ? AND event_type = ?
                """,
                (request_id, event_type),
            ).fetchone()
            conn.commit()
            return _notification_attempt_from_row(row) if row else None

        conn.execute(
            """
            INSERT INTO notification_attempts
            (event_type, request_id, quote_id, channel, recipient, status, attempt_count, created_at, updated_at, sent_at, last_error)
            VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, NULL, NULL)
            """,
            (event_type, request_id, quote_id, channel, recipient, created_at, created_at),
        )
        row = conn.execute(
            """
            SELECT *
            FROM notification_attempts
            WHERE request_id = ? AND event_type = ?
            """,
            (request_id, event_type),
        ).fetchone()
        conn.commit()
        return _notification_attempt_from_row(row) if row else None
    finally:
        conn.close()


def get_notification_attempt(request_id: str, event_type: str) -> Optional[NotificationAttemptRecord]:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM notification_attempts
            WHERE request_id = ? AND event_type = ?
            """,
            (request_id, event_type),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return _notification_attempt_from_row(row)


def list_notification_attempts(limit: int = 50) -> List[NotificationAttemptRecord]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM notification_attempts
            ORDER BY datetime(created_at) DESC, request_id ASC, event_type ASC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    return [_notification_attempt_from_row(row) for row in rows]


def _update_notification_attempt(
    request_id: str,
    event_type: str,
    *,
    status: str,
    updated_at: str,
    sent_at: Any = UNSET,
    last_error: Any = UNSET,
    increment_attempt_count: bool = False,
) -> Optional[NotificationAttemptRecord]:
    validated_status = _validate_notification_attempt_status(status)
    assignments = ["status = ?", "updated_at = ?"]
    values: List[Any] = [validated_status, updated_at]

    if sent_at is not UNSET:
        assignments.append("sent_at = ?")
        values.append(sent_at)
    if last_error is not UNSET:
        assignments.append("last_error = ?")
        values.append(last_error)
    if increment_attempt_count:
        assignments.append("attempt_count = attempt_count + 1")

    values.extend([request_id, event_type])
    conn = _connect()
    try:
        conn.execute(
            f"""
            UPDATE notification_attempts
            SET {", ".join(assignments)}
            WHERE request_id = ? AND event_type = ?
            """,
            values,
        )
        conn.commit()
    finally:
        conn.close()

    return get_notification_attempt(request_id, event_type)


def mark_notification_attempt_sent(
    request_id: str,
    event_type: str,
    *,
    sent_at: str,
) -> Optional[NotificationAttemptRecord]:
    return _update_notification_attempt(
        request_id,
        event_type,
        status="sent",
        updated_at=sent_at,
        sent_at=sent_at,
        last_error=None,
        increment_attempt_count=True,
    )


def mark_notification_attempt_failed(
    request_id: str,
    event_type: str,
    *,
    failed_at: str,
    last_error: str,
) -> Optional[NotificationAttemptRecord]:
    return _update_notification_attempt(
        request_id,
        event_type,
        status="failed",
        updated_at=failed_at,
        sent_at=None,
        last_error=last_error,
        increment_attempt_count=True,
    )


def mark_notification_attempt_skipped(
    request_id: str,
    event_type: str,
    *,
    skipped_at: str,
    last_error: str,
) -> Optional[NotificationAttemptRecord]:
    return _update_notification_attempt(
        request_id,
        event_type,
        status="skipped",
        updated_at=skipped_at,
        sent_at=None,
        last_error=last_error,
        increment_attempt_count=True,
    )


# =========================
# Jobs
# =========================

def save_job(job: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs
            (job_id, created_at, status, quote_id, request_id,
             customer_name, customer_phone, job_address,
             job_description_customer, job_description_internal,
             service_type, cash_total_cad, emt_total_cad, request_json, notes,
             scheduled_start, scheduled_end, google_calendar_event_id,
             calendar_sync_status, calendar_last_error, started_at,
             completed_at, cancelled_at, closeout_notes,
             actual_hours, actual_crew_size, actual_labor_cost_cad,
             actual_disposal_cost_cad, actual_fuel_cost_cad, actual_other_costs_cad,
             final_amount_collected_cad, payment_method,
             payment_status, job_profit_status, quote_accuracy_note, disposal_receipt_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job["job_id"],
                job["created_at"],
                job["status"],
                job["quote_id"],
                job["request_id"],
                job.get("customer_name"),
                job.get("customer_phone"),
                job.get("job_address"),
                job.get("job_description_customer"),
                job.get("job_description_internal"),
                job["service_type"],
                float(job["cash_total_cad"]),
                float(job["emt_total_cad"]),
                json.dumps(job["request_json"], ensure_ascii=False),
                job.get("notes"),
                job.get("scheduled_start"),
                job.get("scheduled_end"),
                job.get("google_calendar_event_id"),
                job.get("calendar_sync_status"),
                job.get("calendar_last_error"),
                job.get("started_at"),
                job.get("completed_at"),
                job.get("cancelled_at"),
                job.get("closeout_notes"),
                job.get("actual_hours"),
                job.get("actual_crew_size"),
                job.get("actual_labor_cost_cad"),
                job.get("actual_disposal_cost_cad"),
                job.get("actual_fuel_cost_cad"),
                job.get("actual_other_costs_cad"),
                job.get("final_amount_collected_cad"),
                job.get("payment_method"),
                job.get("payment_status"),
                job.get("job_profit_status"),
                job.get("quote_accuracy_note"),
                job.get("disposal_receipt_note"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[Job]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    row_dict = dict(row)

    try:
        req = json.loads(row_dict["request_json"])
    except Exception:
        req = row_dict["request_json"]

    return {
        "job_id": row_dict["job_id"],
        "created_at": row_dict["created_at"],
        "status": row_dict["status"],
        "quote_id": row_dict["quote_id"],
        "request_id": row_dict["request_id"],
        "customer_name": row_dict["customer_name"],
        "customer_phone": row_dict["customer_phone"],
        "job_address": row_dict["job_address"],
        "job_description_customer": row_dict["job_description_customer"],
        "job_description_internal": row_dict["job_description_internal"],
        "service_type": row_dict["service_type"],
        "cash_total_cad": row_dict["cash_total_cad"],
        "emt_total_cad": row_dict["emt_total_cad"],
        "request_json": req,
        "notes": row_dict["notes"],
        "scheduled_start": row_dict["scheduled_start"] if "scheduled_start" in row_dict else None,
        "scheduled_end": row_dict["scheduled_end"] if "scheduled_end" in row_dict else None,
        "google_calendar_event_id": row_dict["google_calendar_event_id"] if "google_calendar_event_id" in row_dict else None,
        "calendar_sync_status": row_dict["calendar_sync_status"] if "calendar_sync_status" in row_dict else None,
        "calendar_last_error": row_dict["calendar_last_error"] if "calendar_last_error" in row_dict else None,
        "started_at": row_dict["started_at"] if "started_at" in row_dict else None,
        "completed_at": row_dict["completed_at"] if "completed_at" in row_dict else None,
        "cancelled_at": row_dict["cancelled_at"] if "cancelled_at" in row_dict else None,
        "closeout_notes": row_dict["closeout_notes"] if "closeout_notes" in row_dict else None,
        "actual_hours": row_dict["actual_hours"] if "actual_hours" in row_dict else None,
        "actual_crew_size": row_dict["actual_crew_size"] if "actual_crew_size" in row_dict else None,
        "actual_labor_cost_cad": row_dict["actual_labor_cost_cad"] if "actual_labor_cost_cad" in row_dict else None,
        "actual_disposal_cost_cad": row_dict["actual_disposal_cost_cad"] if "actual_disposal_cost_cad" in row_dict else None,
        "actual_fuel_cost_cad": row_dict["actual_fuel_cost_cad"] if "actual_fuel_cost_cad" in row_dict else None,
        "actual_other_costs_cad": row_dict["actual_other_costs_cad"] if "actual_other_costs_cad" in row_dict else None,
        "final_amount_collected_cad": row_dict["final_amount_collected_cad"] if "final_amount_collected_cad" in row_dict else None,
        "payment_method": row_dict["payment_method"] if "payment_method" in row_dict else None,
        "payment_status": row_dict["payment_status"] if "payment_status" in row_dict else None,
        "job_profit_status": row_dict["job_profit_status"] if "job_profit_status" in row_dict else None,
        "quote_accuracy_note": row_dict["quote_accuracy_note"] if "quote_accuracy_note" in row_dict else None,
        "disposal_receipt_note": row_dict["disposal_receipt_note"] if "disposal_receipt_note" in row_dict else None,
        "scheduling_context": _build_job_scheduling_context(
            row_dict["request_id"],
            fallback_notes=row_dict["notes"],
        ),
    }


def require_job(job_id: str) -> Job:
    job = get_job(job_id)
    if job is None:
        raise KeyError(f"Job not found: {job_id}")
    return job


def get_job_by_quote_id(quote_id: str) -> Optional[Job]:
    conn = _connect()
    try:
        row = conn.execute("SELECT job_id FROM jobs WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return get_job(row["job_id"])


def list_jobs(limit: int = 50, *, offset: int = 0) -> List[Job]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT job_id
            FROM jobs
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        ).fetchall()
    finally:
        conn.close()

    out: List[Job] = []
    for r in rows:
        item = get_job(r["job_id"])
        if item is not None:
            out.append(item)
    return out


# Explicit allowlist of fields that can be updated via update_job()
# This prevents potential SQL injection if the function is refactored in the future
_ALLOWED_JOB_UPDATE_FIELDS = {
    "status",
    "notes",
    "scheduled_start",
    "scheduled_end",
    "google_calendar_event_id",
    "calendar_sync_status",
    "calendar_last_error",
    "started_at",
    "completed_at",
    "cancelled_at",
    "closeout_notes",
}


def update_job(
    job_id: str,
    *,
    status: Any = UNSET,
    scheduled_start: Any = UNSET,
    scheduled_end: Any = UNSET,
    google_calendar_event_id: Any = UNSET,
    calendar_sync_status: Any = UNSET,
    calendar_last_error: Any = UNSET,
    started_at: Any = UNSET,
    completed_at: Any = UNSET,
    cancelled_at: Any = UNSET,
    closeout_notes: Any = UNSET,
) -> Optional[Job]:
    existing = get_job(job_id)
    if not existing:
        return None

    # Build partial UPDATE query with explicit field validation
    updates: List[str] = []
    params: List[Any] = []

    if status is not UNSET:
        field_name = "status"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(status)
    if scheduled_start is not UNSET:
        field_name = "scheduled_start"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(scheduled_start)
    if scheduled_end is not UNSET:
        field_name = "scheduled_end"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(scheduled_end)
    if google_calendar_event_id is not UNSET:
        field_name = "google_calendar_event_id"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(google_calendar_event_id)
    if calendar_sync_status is not UNSET:
        field_name = "calendar_sync_status"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(calendar_sync_status)
    if calendar_last_error is not UNSET:
        field_name = "calendar_last_error"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        # Truncate to reasonable length (e.g., 500 chars)
        error_str = str(calendar_last_error) if calendar_last_error else None
        if error_str and len(error_str) > 500:
            logger.warning(f"Calendar sync error for job {job_id} (full): {error_str}")
            error_str = error_str[:500] + "... (truncated)"
        updates.append(f"{field_name} = ?")
        params.append(error_str)
    if started_at is not UNSET:
        field_name = "started_at"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(started_at)
    if completed_at is not UNSET:
        field_name = "completed_at"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(completed_at)
    if cancelled_at is not UNSET:
        field_name = "cancelled_at"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        updates.append(f"{field_name} = ?")
        params.append(cancelled_at)
    if closeout_notes is not UNSET:
        field_name = "closeout_notes"
        if field_name not in _ALLOWED_JOB_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' is not allowed for update")
        notes_str = str(closeout_notes) if closeout_notes else None
        updates.append(f"{field_name} = ?")
        params.append(notes_str)

    if not updates:
        return existing  # No changes

    query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
    params.append(job_id)

    conn = _connect()
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()

    # Return updated job
    return cast(Optional[Job], get_job(job_id))


_JOB_COSTING_FIELDS = {
    "actual_hours",
    "actual_crew_size",
    "actual_labor_cost_cad",
    "actual_disposal_cost_cad",
    "actual_fuel_cost_cad",
    "actual_other_costs_cad",
    "final_amount_collected_cad",
    "payment_method",
    "payment_status",
    "job_profit_status",
    "quote_accuracy_note",
    "disposal_receipt_note",
}


def _nullable_nonnegative_float(value: Any, field_name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _nullable_positive_int(value: Any, field_name: str) -> Optional[int]:
    if value is None or value == "":
        return None
    parsed_float = float(value)
    if not parsed_float.is_integer():
        raise ValueError(f"{field_name} must be a whole number")
    parsed = int(parsed_float)
    if parsed < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return parsed


def _nullable_limited_text(value: Any, max_length: int = 500) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def update_job_costing(job_id: str, **fields: Any) -> Optional[Job]:
    existing = get_job(job_id)
    if not existing:
        return None

    unknown_fields = set(fields) - _JOB_COSTING_FIELDS
    if unknown_fields:
        raise ValueError(f"Unsupported job costing fields: {', '.join(sorted(unknown_fields))}")

    normalized: Dict[str, Any] = {}
    for field_name, raw_value in fields.items():
        if field_name in {
            "actual_hours",
            "actual_labor_cost_cad",
            "actual_disposal_cost_cad",
            "actual_fuel_cost_cad",
            "actual_other_costs_cad",
            "final_amount_collected_cad",
        }:
            normalized[field_name] = _nullable_nonnegative_float(raw_value, field_name)
            continue
        if field_name == "actual_crew_size":
            normalized[field_name] = _nullable_positive_int(raw_value, field_name)
            continue
        if field_name == "payment_method":
            value = _nullable_limited_text(raw_value, max_length=20)
            value = value.lower() if value is not None else None
            if value is not None and value not in ALLOWED_JOB_COSTING_PAYMENT_METHODS:
                raise ValueError(
                    "payment_method must be one of: cash, emt, other"
                )
            normalized[field_name] = value
            continue
        if field_name == "payment_status":
            value = _nullable_limited_text(raw_value, max_length=30)
            value = value.lower() if value is not None else None
            if value is not None and value not in ALLOWED_JOB_PAYMENT_STATUSES:
                raise ValueError("payment_status must be one of: not_paid_yet, partial_payment, paid_in_full")
            normalized[field_name] = value
            continue
        if field_name == "job_profit_status":
            value = _nullable_limited_text(raw_value, max_length=30)
            value = value.lower() if value is not None else None
            if value is not None and value not in ALLOWED_JOB_PROFIT_STATUSES:
                raise ValueError("job_profit_status must be one of: underquoted, fair, profitable, painful")
            normalized[field_name] = value
            continue
        normalized[field_name] = _nullable_limited_text(raw_value, max_length=500)

    if not normalized:
        return existing

    updates = [f"{field_name} = ?" for field_name in normalized]
    params = list(normalized.values())
    params.append(job_id)

    conn = _connect()
    try:
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params)
        conn.commit()
    finally:
        conn.close()

    return cast(Optional[Job], get_job(job_id))


# =========================
# Attachments
# =========================

def save_attachment(att: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO attachments
            (attachment_id, created_at, quote_id, request_id, job_id, analysis_id,
             filename, mime_type, size_bytes, drive_file_id, drive_web_view_link, ocr_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                att["attachment_id"],
                att["created_at"],
                att.get("quote_id"),
                att.get("request_id"),
                att.get("job_id"),
                att.get("analysis_id"),
                att["filename"],
                att["mime_type"],
                int(att["size_bytes"]) if att.get("size_bytes") is not None else None,
                att["drive_file_id"],
                att.get("drive_web_view_link"),
                json.dumps(att.get("ocr_json") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _parse_attachment_row(row: sqlite3.Row) -> AttachmentRecord:
    ocr_payload = row["ocr_json"] if "ocr_json" in row.keys() else None
    if isinstance(ocr_payload, str):
        try:
            ocr_payload = json.loads(ocr_payload)
        except Exception:
            ocr_payload = {}
    if not isinstance(ocr_payload, dict):
        ocr_payload = {}

    return {
        "attachment_id": row["attachment_id"],
        "created_at": row["created_at"],
        "quote_id": row["quote_id"],
        "request_id": row["request_id"],
        "job_id": row["job_id"],
        "analysis_id": row["analysis_id"] if "analysis_id" in row.keys() else None,
        "filename": row["filename"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "drive_file_id": row["drive_file_id"],
        "drive_web_view_link": row["drive_web_view_link"],
        "ocr_json": ocr_payload,
    }


def list_attachments(quote_id: Optional[str] = None, analysis_id: Optional[str] = None, limit: int = 50) -> List[AttachmentRecord]:
    where: List[str] = []
    params: List[Any] = []

    if quote_id:
        where.append("quote_id = ?")
        params.append(quote_id)

    if analysis_id:
        where.append("analysis_id = ?")
        params.append(analysis_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT
            attachment_id, created_at, quote_id, request_id, job_id, analysis_id,
            filename, mime_type, size_bytes, drive_file_id, drive_web_view_link, ocr_json
        FROM attachments
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(int(limit))

    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [_parse_attachment_row(r) for r in rows]


def list_attachments_by_ids(attachment_ids: List[str]) -> List[AttachmentRecord]:
    normalized_ids = [str(att_id).strip() for att_id in attachment_ids if str(att_id).strip()]
    if not normalized_ids:
        return []

    placeholders = ",".join(["?"] * len(normalized_ids))
    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT
                attachment_id, created_at, quote_id, request_id, job_id, analysis_id,
                filename, mime_type, size_bytes, drive_file_id, drive_web_view_link, ocr_json
            FROM attachments
            WHERE attachment_id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            normalized_ids,
        ).fetchall()
    finally:
        conn.close()

    return [_parse_attachment_row(r) for r in rows]


def assign_attachments_to_analysis(attachment_ids: List[str], analysis_id: str) -> None:
    normalized_ids = [str(att_id).strip() for att_id in attachment_ids if str(att_id).strip()]
    if not normalized_ids:
        return

    placeholders = ",".join(["?"] * len(normalized_ids))
    conn = _connect()
    try:
        conn.execute(
            f"UPDATE attachments SET analysis_id = ? WHERE attachment_id IN ({placeholders})",
            [analysis_id, *normalized_ids],
        )
        conn.commit()
    finally:
        conn.close()


def assign_analysis_attachments_to_quote(analysis_id: str, quote_id: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE attachments
            SET quote_id = ?
            WHERE analysis_id = ?
              AND quote_id IS NULL
            """,
            (quote_id, analysis_id),
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_screenshot_assistant_analysis(row: sqlite3.Row) -> ScreenshotAssistantAnalysis:
    row_dict = dict(row)
    for key in ("intake_json", "normalized_candidate_json", "guidance_json"):
        value = row_dict.get(key)
        if isinstance(value, str):
            try:
                row_dict[key] = json.loads(value)
            except Exception:
                pass
    return cast(ScreenshotAssistantAnalysis, row_dict)


def save_screenshot_assistant_analysis(record: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO screenshot_assistant_analyses
            (analysis_id, created_at, updated_at, operator_username, status, intake_json, normalized_candidate_json, guidance_json, quote_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["analysis_id"],
                record["created_at"],
                record["updated_at"],
                record["operator_username"],
                record["status"],
                json.dumps(record.get("intake_json") or {}, ensure_ascii=False),
                json.dumps(record.get("normalized_candidate_json") or {}, ensure_ascii=False),
                json.dumps(record.get("guidance_json") or {}, ensure_ascii=False),
                record.get("quote_id"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_screenshot_assistant_analysis(analysis_id: str) -> Optional[ScreenshotAssistantAnalysis]:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT analysis_id, created_at, updated_at, operator_username, status, intake_json,
                   normalized_candidate_json, guidance_json, quote_id
            FROM screenshot_assistant_analyses
            WHERE analysis_id = ?
            """,
            (analysis_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return _row_to_screenshot_assistant_analysis(row)


def list_screenshot_assistant_analyses(limit: int = 50) -> List[ScreenshotAssistantAnalysis]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT analysis_id, created_at, updated_at, operator_username, status, intake_json,
                   normalized_candidate_json, guidance_json, quote_id
            FROM screenshot_assistant_analyses
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_screenshot_assistant_analysis(row) for row in rows]


def list_admin_audit_log(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT timestamp, operator_username, action_type, entity_type, record_id, success, error_summary
            FROM admin_audit_log
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "timestamp": r["timestamp"],
            "operator_username": r["operator_username"],
            "action_type": r["action_type"],
            "entity_type": r["entity_type"],
            "record_id": r["record_id"],
            "success": bool(r["success"]),
            "error_summary": r["error_summary"],
        }
        for r in rows
    ]


def _normalize_prelaunch_cleanup_quote_ids(quote_ids: List[str]) -> List[str]:
    normalized_ids: List[str] = []
    seen: set[str] = set()
    for quote_id in quote_ids:
        normalized = str(quote_id or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_ids.append(normalized)
    if not normalized_ids:
        raise ValueError("At least one quote_id is required for prelaunch cleanup.")
    return normalized_ids


def _placeholder_sql(values: List[str]) -> str:
    return ", ".join(["?"] * len(values))


def _load_prelaunch_cleanup_plan(conn: sqlite3.Connection, quote_ids: List[str]) -> PrelaunchCleanupPlan:
    normalized_quote_ids = _normalize_prelaunch_cleanup_quote_ids(quote_ids)
    quote_placeholders = _placeholder_sql(normalized_quote_ids)

    quote_rows = conn.execute(
        f"""
        SELECT quote_id
        FROM quotes
        WHERE quote_id IN ({quote_placeholders})
        ORDER BY datetime(created_at) DESC, quote_id ASC
        """,
        normalized_quote_ids,
    ).fetchall()
    found_quote_ids = [str(row["quote_id"]) for row in quote_rows]
    missing_quote_ids = [quote_id for quote_id in normalized_quote_ids if quote_id not in found_quote_ids]

    request_ids: List[str] = []
    if normalized_quote_ids:
        normalized_quote_placeholders = _placeholder_sql(normalized_quote_ids)
        request_rows = conn.execute(
            f"""
            SELECT request_id
            FROM quote_requests
            WHERE quote_id IN ({normalized_quote_placeholders})
            ORDER BY datetime(created_at) DESC, request_id ASC
            """,
            normalized_quote_ids,
        ).fetchall()
        request_ids = [str(row["request_id"]) for row in request_rows]

    job_ids: List[str] = []
    if normalized_quote_ids or request_ids:
        job_clauses: List[str] = []
        job_params: List[str] = []
        if normalized_quote_ids:
            job_clauses.append(f"quote_id IN ({_placeholder_sql(normalized_quote_ids)})")
            job_params.extend(normalized_quote_ids)
        if request_ids:
            job_clauses.append(f"request_id IN ({_placeholder_sql(request_ids)})")
            job_params.extend(request_ids)
        job_rows = conn.execute(
            f"""
            SELECT job_id
            FROM jobs
            WHERE {' OR '.join(job_clauses)}
            ORDER BY datetime(created_at) DESC, job_id ASC
            """,
            job_params,
        ).fetchall()
        job_ids = [str(row["job_id"]) for row in job_rows]

    attachment_ids: List[str] = []
    if normalized_quote_ids or request_ids or job_ids:
        attachment_clauses: List[str] = []
        attachment_params: List[str] = []
        if normalized_quote_ids:
            attachment_clauses.append(f"quote_id IN ({_placeholder_sql(normalized_quote_ids)})")
            attachment_params.extend(normalized_quote_ids)
        if request_ids:
            attachment_clauses.append(f"request_id IN ({_placeholder_sql(request_ids)})")
            attachment_params.extend(request_ids)
        if job_ids:
            attachment_clauses.append(f"job_id IN ({_placeholder_sql(job_ids)})")
            attachment_params.extend(job_ids)
        attachment_rows = conn.execute(
            f"""
            SELECT attachment_id
            FROM attachments
            WHERE {' OR '.join(attachment_clauses)}
            ORDER BY datetime(created_at) DESC, attachment_id ASC
            """,
            attachment_params,
        ).fetchall()
        attachment_ids = [str(row["attachment_id"]) for row in attachment_rows]

    return {
        "db_path": str(_resolve_db_path()),
        "requested_quote_ids": normalized_quote_ids,
        "found_quote_ids": found_quote_ids,
        "missing_quote_ids": missing_quote_ids,
        "request_ids": request_ids,
        "job_ids": job_ids,
        "attachment_ids": attachment_ids,
        "counts": {
            "quotes": len(found_quote_ids),
            "quote_requests": len(request_ids),
            "jobs": len(job_ids),
            "attachments": len(attachment_ids),
        },
        "quotes": [quote for quote in (get_quote_record(quote_id) for quote_id in found_quote_ids) if quote is not None],
        "quote_requests": [
            quote_request
            for quote_request in (get_quote_request_record(request_id) for request_id in request_ids)
            if quote_request is not None
        ],
        "jobs": [job for job in (get_job(job_id) for job_id in job_ids) if job is not None],
        "attachments": list_attachments_by_ids(attachment_ids),
    }


def plan_prelaunch_test_data_cleanup(quote_ids: List[str]) -> PrelaunchCleanupPlan:
    conn = _connect()
    try:
        return _load_prelaunch_cleanup_plan(conn, quote_ids)
    finally:
        conn.close()


def _delete_rows_by_ids(conn: sqlite3.Connection, table: str, column: str, ids: List[str]) -> None:
    if not ids:
        return
    safe_table = _validate_table_name(table)
    conn.execute(
        f"DELETE FROM {safe_table} WHERE {column} IN ({_placeholder_sql(ids)})",
        ids,
    )


def apply_prelaunch_test_data_cleanup(quote_ids: List[str]) -> PrelaunchCleanupResult:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cleanup_plan = _load_prelaunch_cleanup_plan(conn, quote_ids)
        _delete_rows_by_ids(conn, "attachments", "attachment_id", cleanup_plan["attachment_ids"])
        _delete_rows_by_ids(conn, "jobs", "job_id", cleanup_plan["job_ids"])
        _delete_rows_by_ids(conn, "quote_requests", "request_id", cleanup_plan["request_ids"])
        _delete_rows_by_ids(conn, "quotes", "quote_id", cleanup_plan["found_quote_ids"])
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

    return {
        "db_path": cleanup_plan["db_path"],
        "requested_quote_ids": cleanup_plan["requested_quote_ids"],
        "found_quote_ids": cleanup_plan["found_quote_ids"],
        "missing_quote_ids": cleanup_plan["missing_quote_ids"],
        "deleted_quote_ids": cleanup_plan["found_quote_ids"],
        "deleted_request_ids": cleanup_plan["request_ids"],
        "deleted_job_ids": cleanup_plan["job_ids"],
        "deleted_attachment_ids": cleanup_plan["attachment_ids"],
        "counts": cleanup_plan["counts"],
    }


def save_gpt_quote_observability_event(record: GptQuoteObservabilityRecord) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO gpt_quote_observability (
                timestamp,
                route_name,
                success,
                normalized_service_type,
                cash_total_cad,
                emt_total_cad,
                confidence_level,
                risk_flags_json,
                failure_reason,
                latency_ms,
                server_grounding_revision,
                caller_grounding_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["timestamp"],
                record["route_name"],
                int(record["success"]),
                record.get("normalized_service_type"),
                record.get("cash_total_cad"),
                record.get("emt_total_cad"),
                record.get("confidence_level"),
                json.dumps(record.get("risk_flags") or [], ensure_ascii=False),
                record.get("failure_reason"),
                record.get("latency_ms"),
                record.get("server_grounding_revision"),
                record.get("caller_grounding_revision"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_gpt_quote_observability(limit: int = 50) -> List[GptQuoteObservabilityRecord]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT
                timestamp,
                route_name,
                success,
                normalized_service_type,
                cash_total_cad,
                emt_total_cad,
                confidence_level,
                risk_flags_json,
                failure_reason,
                latency_ms,
                server_grounding_revision,
                caller_grounding_revision
            FROM gpt_quote_observability
            ORDER BY timestamp DESC, event_id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    items: List[GptQuoteObservabilityRecord] = []
    for row in rows:
        try:
            risk_flags_raw = json.loads(row["risk_flags_json"]) if row["risk_flags_json"] else []
        except (TypeError, ValueError):
            risk_flags_raw = []
        risk_flags = [str(flag) for flag in risk_flags_raw] if isinstance(risk_flags_raw, list) else []
        items.append(
            {
                "timestamp": row["timestamp"],
                "route_name": row["route_name"],
                "success": bool(row["success"]),
                "normalized_service_type": row["normalized_service_type"],
                "cash_total_cad": row["cash_total_cad"],
                "emt_total_cad": row["emt_total_cad"],
                "confidence_level": row["confidence_level"],
                "risk_flags": risk_flags,
                "failure_reason": row["failure_reason"],
                "latency_ms": row["latency_ms"],
                "server_grounding_revision": row["server_grounding_revision"],
                "caller_grounding_revision": row["caller_grounding_revision"],
            }
        )
    return items


# =========================
# Admin backup / restore
# =========================

def export_db_to_json() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "meta": {"format": "bay-delivery-sqlite-backup", "version": 1},
        "tables": {},
    }

    conn = _connect()
    try:
        for table in KNOWN_TABLES:
            try:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            except sqlite3.OperationalError:
                payload["tables"][table] = []
                continue

            out_rows: List[Dict[str, Any]] = []
            for r in rows:
                row_dict: Dict[str, Any] = dict(r)
                row_dict = _sanitize_backup_tokens(table, row_dict)
                for k in list(row_dict.keys()):
                    if k.endswith("_json") or k in {"request_json", "response_json"}:
                        v = row_dict.get(k)
                        if v is None:
                            continue
                        if isinstance(v, str):
                            try:
                                row_dict[k] = json.loads(v)
                            except Exception:
                                row_dict[k] = v
                out_rows.append(row_dict)

            payload["tables"][table] = out_rows
    finally:
        conn.close()

    return payload


def _sanitize_backup_tokens(table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    if table == "quotes" and row.get("accept_token"):
        row["accept_token"] = BACKUP_TOKEN_ROTATION_PLACEHOLDER
    elif table == "quote_requests":
        for token_field in ("accept_token", "booking_token"):
            if row.get(token_field):
                row[token_field] = BACKUP_TOKEN_ROTATION_PLACEHOLDER
    return row


def _fresh_workflow_token() -> str:
    return str(uuid4())


def _restore_token_created_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _has_exported_token(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _rotate_restored_quote_tokens(
    row: Dict[str, Any],
    quote_accept_tokens_by_id: Dict[str, str],
) -> Dict[str, Any]:
    rotated = dict(row)
    token = _fresh_workflow_token()
    rotated["accept_token"] = token

    quote_id = rotated.get("quote_id")
    if quote_id is not None:
        quote_accept_tokens_by_id[str(quote_id)] = token

    return rotated


def _rotate_restored_quote_request_tokens(
    row: Dict[str, Any],
    quote_accept_tokens_by_id: Dict[str, str],
    restored_at: str,
) -> Dict[str, Any]:
    rotated = dict(row)

    quote_id = rotated.get("quote_id")
    quote_accept_token = quote_accept_tokens_by_id.get(str(quote_id)) if quote_id is not None else None
    if quote_accept_token is not None:
        rotated["accept_token"] = quote_accept_token
    elif _has_exported_token(rotated.get("accept_token")):
        rotated["accept_token"] = _fresh_workflow_token()

    if _has_exported_token(rotated.get("booking_token")):
        rotated["booking_token"] = _fresh_workflow_token()
        rotated["booking_token_created_at"] = restored_at

    return rotated


def import_db_from_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Backup payload must be a JSON object")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup payload missing 'tables' object")

    init_db()
    restored_counts: Dict[str, int] = {}
    quote_accept_tokens_by_id: Dict[str, str] = {}
    restored_at = _restore_token_created_at()

    conn = _connect()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")

        for table in KNOWN_TABLES:
            safe_table = _validate_table_name(table)
            try:
                conn.execute(f"DELETE FROM {safe_table}")
            except sqlite3.OperationalError:
                continue

        for table in KNOWN_TABLES:
            safe_table = _validate_table_name(table)
            rows_in = tables.get(safe_table, [])
            if not rows_in:
                restored_counts[safe_table] = 0
                continue
            if not isinstance(rows_in, list):
                raise ValueError(f"Table '{safe_table}' must be a list of rows")

            try:
                col_rows = conn.execute(f"PRAGMA table_info({safe_table})").fetchall()
            except sqlite3.OperationalError:
                restored_counts[safe_table] = 0
                continue

            cols = [c["name"] for c in col_rows]
            if not cols:
                restored_counts[safe_table] = 0
                continue

            placeholders = ",".join(["?"] * len(cols))
            col_sql = ",".join(cols)
            sql = f"INSERT OR REPLACE INTO {safe_table} ({col_sql}) VALUES ({placeholders})"

            values_to_insert: List[List[Any]] = []
            for raw in rows_in:
                if not isinstance(raw, dict):
                    raise ValueError(f"Row in '{safe_table}' must be an object")

                if safe_table == "jobs":
                    raw = _normalize_job_payment_fields(raw)
                if safe_table == "quotes":
                    raw = _normalize_quote_admin_fields(raw)
                    raw = _rotate_restored_quote_tokens(raw, quote_accept_tokens_by_id)
                if safe_table == "quote_requests":
                    raw = _rotate_restored_quote_request_tokens(raw, quote_accept_tokens_by_id, restored_at)

                row_vals: List[Any] = []
                for col in cols:
                    v = raw.get(col)
                    if col.endswith("_json") or col in {"request_json", "response_json"}:
                        if v is None:
                            row_vals.append(None)
                        elif isinstance(v, str):
                            row_vals.append(v)
                        else:
                            row_vals.append(json.dumps(v, ensure_ascii=False))
                        continue
                    row_vals.append(v)

                values_to_insert.append(row_vals)

            conn.executemany(sql, values_to_insert)
            restored_counts[safe_table] = len(values_to_insert)

        conn.execute("COMMIT")
        conn.execute("PRAGMA foreign_keys = ON")

        # Schema cache may now be stale (tables could differ after restore)
        _TABLE_COL_CACHE.clear()
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

    return {"ok": True, "restored": restored_counts}
