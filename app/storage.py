from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, NotRequired, Optional, Tuple, TypedDict, cast

from app.update_fields import validate_quote_request_transition

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("app/data/bay_delivery.sqlite3")
DB_PATH = DEFAULT_DB_PATH  # overridable by tests
UNSET = object()

# Token validity in days
TOKEN_VALIDITY_DAYS = 30


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
    scheduling_context: NotRequired[Dict[str, Any]]


class QuoteRecord(TypedDict):
    quote_id: str
    created_at: str
    request: Any
    response: Any
    accept_token: Optional[str]
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
KNOWN_TABLES = ["quotes", "quote_requests", "jobs", "attachments", "screenshot_assistant_analyses"]

# Cache table columns to support forward-compatible schemas (ex: quotes.job_type)
_TABLE_COL_CACHE: Dict[str, Tuple[str, ...]] = {}


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
                accept_token TEXT
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
                booking_token_created_at TEXT
            )
            """
        )

        conn.execute(
            """
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
                notes TEXT
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
                drive_web_view_link TEXT
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

        # Backfill: add missing columns if older DB is present
        _try_add_column(conn, "quotes", "accept_token TEXT")
        _try_add_column(conn, "quote_requests", "notes TEXT")
        _try_add_column(conn, "quote_requests", "requested_job_date TEXT")
        _try_add_column(conn, "quote_requests", "requested_time_window TEXT")
        _try_add_column(conn, "quote_requests", "customer_accepted_at TEXT")
        _try_add_column(conn, "quote_requests", "admin_approved_at TEXT")
        _try_add_column(conn, "quote_requests", "accept_token TEXT")
        _try_add_column(conn, "quote_requests", "booking_token TEXT")
        _try_add_column(conn, "quote_requests", "booking_token_created_at TEXT")

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

        # Add assistant-compatible linkage to attachments without breaking existing uploads
        _try_add_column(conn, "attachments", "analysis_id TEXT")
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

    if "job_type" in row_dict:
        out["job_type"] = row_dict["job_type"]
    if "total_cad" in row_dict:
        out["total_cad"] = row_dict["total_cad"]

    return cast(QuoteRecord, out)


def list_quotes(limit: int = 50) -> List[QuoteRecord]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM quotes
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (int(limit),),
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
        if "job_type" in r.keys():
            item["job_type"] = r["job_type"]
        if "total_cad" in r.keys():
            item["total_cad"] = r["total_cad"]
        out.append(item)

    return out


# =========================
# Quote requests
# =========================

def save_quote_request(record: Dict[str, Any]) -> None:
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
             customer_accepted_at, admin_approved_at, accept_token, booking_token, booking_token_created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    row_dict = dict(row)

    try:
        req = json.loads(row_dict["request_json"])
    except Exception:
        req = row_dict["request_json"]

    return {
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


def get_quote_request_by_quote_id(quote_id: str) -> Optional[QuoteRequest]:
    conn = _connect()
    try:
        row = conn.execute("SELECT request_id FROM quote_requests WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return get_quote_request(row["request_id"])


def list_quote_requests(limit: int = 50) -> List[QuoteRequest]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT request_id
            FROM quote_requests
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    out: List[QuoteRequest] = []
    for r in rows:
        item = get_quote_request(r["request_id"])
        if item is not None:
            out.append(item)
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
) -> Optional[QuoteRequest]:
    existing = get_quote_request(request_id)
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
        }
    )
    return cast(QuoteRequest, updated)


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
             completed_at, cancelled_at, closeout_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def list_jobs(limit: int = 50) -> List[Job]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT job_id
            FROM jobs
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (int(limit),),
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
             filename, mime_type, size_bytes, drive_file_id, drive_web_view_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_attachments(quote_id: Optional[str] = None, analysis_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
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
            filename, mime_type, size_bytes, drive_file_id, drive_web_view_link
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

    return [
        {
            "attachment_id": r["attachment_id"],
            "created_at": r["created_at"],
            "quote_id": r["quote_id"],
            "request_id": r["request_id"],
            "job_id": r["job_id"],
            "analysis_id": r["analysis_id"] if "analysis_id" in r.keys() else None,
            "filename": r["filename"],
            "mime_type": r["mime_type"],
            "size_bytes": r["size_bytes"],
            "drive_file_id": r["drive_file_id"],
            "drive_web_view_link": r["drive_web_view_link"],
        }
        for r in rows
    ]


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


def import_db_from_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Backup payload must be a JSON object")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup payload missing 'tables' object")

    init_db()
    restored_counts: Dict[str, int] = {}

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
