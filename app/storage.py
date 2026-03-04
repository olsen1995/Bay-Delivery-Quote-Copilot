from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.update_fields import validate_quote_request_transition

DEFAULT_DB_PATH = Path("app/data/bay_delivery.sqlite3")
DB_PATH = DEFAULT_DB_PATH  # overridable by tests
UNSET = object()

# Explicit table list keeps backup/restore deterministic and safe.
KNOWN_TABLES = ["quotes", "quote_requests", "jobs", "attachments"]

# Cache table columns to support forward-compatible schemas (ex: quotes.job_type)
_TABLE_COL_CACHE: Dict[str, Tuple[str, ...]] = {}


def _connect() -> sqlite3.Connection:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_db_path() -> Path:
    if DB_PATH != DEFAULT_DB_PATH:
        return DB_PATH

    env_path = os.getenv("BAYDELIVERY_DB_PATH")
    if env_path:
        return Path(env_path)

    return DEFAULT_DB_PATH


def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """SQLite doesn't support ADD COLUMN IF NOT EXISTS reliably in all builds."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate column name" in msg:
            return
        raise


def _table_columns(conn: sqlite3.Connection, table: str) -> Tuple[str, ...]:
    """Return current columns for a table, cached per process."""
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
                response_json TEXT NOT NULL
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
                admin_approved_at TEXT
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
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER,
                drive_file_id TEXT NOT NULL,
                drive_web_view_link TEXT
            )
            """
        )

        # Backfill: add missing columns if older DB is present
        _try_add_column(conn, "quote_requests", "notes TEXT")
        _try_add_column(conn, "quote_requests", "requested_job_date TEXT")
        _try_add_column(conn, "quote_requests", "requested_time_window TEXT")
        _try_add_column(conn, "quote_requests", "customer_accepted_at TEXT")
        _try_add_column(conn, "quote_requests", "admin_approved_at TEXT")

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


def get_quote_record(quote_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    try:
        request_obj = json.loads(row["request_json"])
    except Exception:
        request_obj = row["request_json"]

    try:
        response_obj = json.loads(row["response_json"])
    except Exception:
        response_obj = row["response_json"]

    out: Dict[str, Any] = {
        "quote_id": row["quote_id"],
        "created_at": row["created_at"],
        "request": request_obj,
        "response": response_obj,
    }

    if "job_type" in row.keys():
        out["job_type"] = row["job_type"]
    if "total_cad" in row.keys():
        out["total_cad"] = row["total_cad"]

    return out


def list_quotes(limit: int = 50) -> List[Dict[str, Any]]:
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

    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            req = json.loads(r["request_json"])
        except Exception:
            req = r["request_json"]
        try:
            resp = json.loads(r["response_json"])
        except Exception:
            resp = r["response_json"]

        item: Dict[str, Any] = {
            "quote_id": r["quote_id"],
            "created_at": r["created_at"],
            "request": req,
            "response": resp,
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
             customer_accepted_at, admin_approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_quote_request(request_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM quote_requests WHERE request_id = ?", (request_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    try:
        req = json.loads(row["request_json"])
    except Exception:
        req = row["request_json"]

    return {
        "request_id": row["request_id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "quote_id": row["quote_id"],
        "customer_name": row["customer_name"],
        "customer_phone": row["customer_phone"],
        "job_address": row["job_address"],
        "job_description_customer": row["job_description_customer"],
        "job_description_internal": row["job_description_internal"],
        "service_type": row["service_type"],
        "cash_total_cad": row["cash_total_cad"],
        "emt_total_cad": row["emt_total_cad"],
        "request_json": req,
        "notes": row["notes"],
        "requested_job_date": row["requested_job_date"],
        "requested_time_window": row["requested_time_window"],
        "customer_accepted_at": row["customer_accepted_at"],
        "admin_approved_at": row["admin_approved_at"],
    }


def get_quote_request_by_quote_id(quote_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT request_id FROM quote_requests WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return get_quote_request(row["request_id"])


def list_quote_requests(limit: int = 50) -> List[Dict[str, Any]]:
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

    out: List[Dict[str, Any]] = []
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
) -> Optional[Dict[str, Any]]:
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
        }
    )
    return updated


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
             service_type, cash_total_cad, emt_total_cad, request_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    try:
        req = json.loads(row["request_json"])
    except Exception:
        req = row["request_json"]

    return {
        "job_id": row["job_id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "quote_id": row["quote_id"],
        "request_id": row["request_id"],
        "customer_name": row["customer_name"],
        "customer_phone": row["customer_phone"],
        "job_address": row["job_address"],
        "job_description_customer": row["job_description_customer"],
        "job_description_internal": row["job_description_internal"],
        "service_type": row["service_type"],
        "cash_total_cad": row["cash_total_cad"],
        "emt_total_cad": row["emt_total_cad"],
        "request_json": req,
        "notes": row["notes"],
    }


def get_job_by_quote_id(quote_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT job_id FROM jobs WHERE quote_id = ?", (quote_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return get_job(row["job_id"])


def list_jobs(limit: int = 50) -> List[Dict[str, Any]]:
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

    out: List[Dict[str, Any]] = []
    for r in rows:
        item = get_job(r["job_id"])
        if item is not None:
            out.append(item)
    return out


# =========================
# Attachments
# =========================

def save_attachment(att: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO attachments
            (attachment_id, created_at, quote_id, request_id, job_id,
             filename, mime_type, size_bytes, drive_file_id, drive_web_view_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                att["attachment_id"],
                att["created_at"],
                att.get("quote_id"),
                att.get("request_id"),
                att.get("job_id"),
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


def list_attachments(quote_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    where: List[str] = []
    params: List[Any] = []

    if quote_id:
        where.append("quote_id = ?")
        params.append(quote_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT
            attachment_id, created_at, quote_id, request_id, job_id,
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
            "filename": r["filename"],
            "mime_type": r["mime_type"],
            "size_bytes": r["size_bytes"],
            "drive_file_id": r["drive_file_id"],
            "drive_web_view_link": r["drive_web_view_link"],
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
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                continue

        for table in KNOWN_TABLES:
            rows_in = tables.get(table, [])
            if not rows_in:
                restored_counts[table] = 0
                continue
            if not isinstance(rows_in, list):
                raise ValueError(f"Table '{table}' must be a list of rows")

            try:
                col_rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            except sqlite3.OperationalError:
                restored_counts[table] = 0
                continue

            cols = [c["name"] for c in col_rows]
            if not cols:
                restored_counts[table] = 0
                continue

            placeholders = ",".join(["?"] * len(cols))
            col_sql = ",".join(cols)
            sql = f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({placeholders})"

            values_to_insert: List[List[Any]] = []
            for raw in rows_in:
                if not isinstance(raw, dict):
                    raise ValueError(f"Row in '{table}' must be an object")

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
            restored_counts[table] = len(values_to_insert)

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
