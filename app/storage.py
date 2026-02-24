from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("app/data/bay_delivery.sqlite3")

# Explicit table list keeps backup/restore deterministic and safe.
KNOWN_TABLES = ["quotes", "quote_requests", "jobs", "attachments"]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """SQLite doesn't support ADD COLUMN IF NOT EXISTS reliably in all builds."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate column name" in msg:
            return
        raise


def init_db() -> None:
    with _connect() as conn:
        # Quotes
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                job_type TEXT NOT NULL,
                total_cad REAL NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_created_at ON quotes(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_job_type ON quotes(job_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_total_cad ON quotes(total_cad)")

        # Jobs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                status TEXT NOT NULL,
                customer_name TEXT,
                job_address TEXT,
                scheduled_start TEXT,
                scheduled_end TEXT,
                total_cad REAL NOT NULL,
                paid_cad REAL NOT NULL,
                owing_cad REAL NOT NULL,
                notes TEXT,
                job_json TEXT NOT NULL
            )
            """
        )
        _try_add_column(conn, "jobs", "customer_phone TEXT")
        _try_add_column(conn, "jobs", "job_description_customer TEXT")
        _try_add_column(conn, "jobs", "job_description_internal TEXT")
        _try_add_column(conn, "jobs", "payment_method TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_quote_id ON jobs(quote_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_customer_name ON jobs(customer_name)")

        # Quote Requests
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
                notes TEXT
            )
            """
        )
        _try_add_column(conn, "quote_requests", "requested_job_date TEXT")
        _try_add_column(conn, "quote_requests", "requested_time_window TEXT")
        _try_add_column(conn, "quote_requests", "customer_accepted_at TEXT")
        _try_add_column(conn, "quote_requests", "admin_approved_at TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_requests_created_at ON quote_requests(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_requests_status ON quote_requests(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_requests_service_type ON quote_requests(service_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_requests_quote_id ON quote_requests(quote_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_requests_requested_job_date ON quote_requests(requested_job_date)")

        # Attachments (Google Drive references)
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_created_at ON attachments(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_quote_id ON attachments(quote_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_request_id ON attachments(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_job_id ON attachments(job_id)")


# =========================
# Quotes
# =========================

def save_quote(
    quote_id: str,
    created_at: str,
    job_type: str,
    total_cad: float,
    request_obj: Dict[str, Any],
    response_obj: Dict[str, Any],
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO quotes
            (quote_id, created_at, job_type, total_cad, request_json, response_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                quote_id,
                created_at,
                job_type,
                float(total_cad),
                json.dumps(request_obj, ensure_ascii=False),
                json.dumps(response_obj, ensure_ascii=False),
            ),
        )


def get_quote(quote_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT response_json FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["response_json"])


def get_quote_record(quote_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT quote_id, created_at, job_type, total_cad, request_json, response_json
            FROM quotes
            WHERE quote_id = ?
            """,
            (quote_id,),
        ).fetchone()
        if not row:
            return None

        return {
            "quote_id": row["quote_id"],
            "created_at": row["created_at"],
            "job_type": row["job_type"],
            "total_cad": float(row["total_cad"]),
            "request_obj": json.loads(row["request_json"]),
            "response_obj": json.loads(row["response_json"]),
        }


def list_quotes(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT quote_id, created_at, job_type, total_cad
            FROM quotes
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    return [
        {"quote_id": r["quote_id"], "created_at": r["created_at"], "job_type": r["job_type"], "total_cad": float(r["total_cad"])}
        for r in rows
    ]


def search_quotes(
    limit: int = 50,
    job_type: Optional[str] = None,
    min_total: Optional[float] = None,
    max_total: Optional[float] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    where: List[str] = []
    params: List[Any] = []

    if job_type:
        where.append("job_type = ?")
        params.append(job_type)
    if min_total is not None:
        where.append("total_cad >= ?")
        params.append(float(min_total))
    if max_total is not None:
        where.append("total_cad <= ?")
        params.append(float(max_total))
    if after:
        where.append("created_at >= ?")
        params.append(after)
    if before:
        where.append("created_at <= ?")
        params.append(before)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT quote_id, created_at, job_type, total_cad
        FROM quotes
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(int(limit))

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {"quote_id": r["quote_id"], "created_at": r["created_at"], "job_type": r["job_type"], "total_cad": float(r["total_cad"])}
        for r in rows
    ]


# =========================
# Jobs
# =========================

def save_job(job_obj: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs
            (job_id, created_at, quote_id, status,
             customer_name, customer_phone, job_address,
             job_description_customer, job_description_internal,
             scheduled_start, scheduled_end,
             payment_method,
             total_cad, paid_cad, owing_cad,
             notes, job_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_obj["job_id"],
                job_obj["created_at"],
                job_obj["quote_id"],
                job_obj["status"],
                job_obj.get("customer_name"),
                job_obj.get("customer_phone"),
                job_obj.get("job_address"),
                job_obj.get("job_description_customer"),
                job_obj.get("job_description_internal"),
                job_obj.get("scheduled_start"),
                job_obj.get("scheduled_end"),
                job_obj.get("payment_method"),
                float(job_obj["total_cad"]),
                float(job_obj["paid_cad"]),
                float(job_obj["owing_cad"]),
                job_obj.get("notes"),
                json.dumps(job_obj["job_json"], ensure_ascii=False),
            ),
        )


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT job_json FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["job_json"])


def get_job_by_quote_id(quote_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                job_id, created_at, quote_id, status,
                customer_name, customer_phone, job_address,
                scheduled_start, scheduled_end,
                payment_method,
                total_cad, paid_cad, owing_cad,
                notes
            FROM jobs
            WHERE quote_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (quote_id,),
        ).fetchone()

        if not row:
            return None

        return {
            "job_id": row["job_id"],
            "created_at": row["created_at"],
            "quote_id": row["quote_id"],
            "status": row["status"],
            "customer_name": row["customer_name"],
            "customer_phone": row["customer_phone"],
            "job_address": row["job_address"],
            "scheduled_start": row["scheduled_start"],
            "scheduled_end": row["scheduled_end"],
            "payment_method": row["payment_method"],
            "total_cad": float(row["total_cad"]),
            "paid_cad": float(row["paid_cad"]),
            "owing_cad": float(row["owing_cad"]),
            "notes": row["notes"],
        }


def list_jobs(
    limit: int = 50,
    status: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    where: List[str] = []
    params: List[Any] = []

    if status:
        where.append("status = ?")
        params.append(status)
    if after:
        where.append("created_at >= ?")
        params.append(after)
    if before:
        where.append("created_at <= ?")
        params.append(before)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT
            job_id, created_at, quote_id, status,
            customer_name, customer_phone, job_address,
            scheduled_start, scheduled_end,
            payment_method,
            total_cad, paid_cad, owing_cad,
            notes
        FROM jobs
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(int(limit))

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            "job_id": r["job_id"],
            "created_at": r["created_at"],
            "quote_id": r["quote_id"],
            "status": r["status"],
            "customer_name": r["customer_name"],
            "customer_phone": r["customer_phone"],
            "job_address": r["job_address"],
            "scheduled_start": r["scheduled_start"],
            "scheduled_end": r["scheduled_end"],
            "payment_method": r["payment_method"],
            "total_cad": float(r["total_cad"]),
            "paid_cad": float(r["paid_cad"]),
            "owing_cad": float(r["owing_cad"]),
            "notes": r["notes"],
        }
        for r in rows
    ]


# =========================
# Quote Requests
# =========================

def save_quote_request(req_obj: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO quote_requests
            (request_id, created_at, status, quote_id,
             customer_name, customer_phone, job_address,
             job_description_customer, job_description_internal,
             service_type, cash_total_cad, emt_total_cad,
             request_json, notes,
             requested_job_date, requested_time_window,
             customer_accepted_at, admin_approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req_obj["request_id"],
                req_obj["created_at"],
                req_obj["status"],
                req_obj["quote_id"],
                req_obj.get("customer_name"),
                req_obj.get("customer_phone"),
                req_obj.get("job_address"),
                req_obj.get("job_description_customer"),
                req_obj.get("job_description_internal"),
                req_obj["service_type"],
                float(req_obj["cash_total_cad"]),
                float(req_obj["emt_total_cad"]),
                json.dumps(req_obj["request_json"], ensure_ascii=False),
                req_obj.get("notes"),
                req_obj.get("requested_job_date"),
                req_obj.get("requested_time_window"),
                req_obj.get("customer_accepted_at"),
                req_obj.get("admin_approved_at"),
            ),
        )


def get_quote_request(request_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id, created_at, status, quote_id,
                customer_name, customer_phone, job_address,
                job_description_customer, job_description_internal,
                service_type, cash_total_cad, emt_total_cad,
                request_json, notes,
                requested_job_date, requested_time_window,
                customer_accepted_at, admin_approved_at
            FROM quote_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if not row:
            return None

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
            "cash_total_cad": float(row["cash_total_cad"]),
            "emt_total_cad": float(row["emt_total_cad"]),
            "request_json": json.loads(row["request_json"]),
            "notes": row["notes"],
            "requested_job_date": row["requested_job_date"],
            "requested_time_window": row["requested_time_window"],
            "customer_accepted_at": row["customer_accepted_at"],
            "admin_approved_at": row["admin_approved_at"],
        }




def get_quote_request_by_quote_id(quote_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id, created_at, status, quote_id,
                customer_name, customer_phone, job_address,
                job_description_customer, job_description_internal,
                service_type, cash_total_cad, emt_total_cad,
                request_json, notes,
                requested_job_date, requested_time_window,
                customer_accepted_at, admin_approved_at
            FROM quote_requests
            WHERE quote_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (quote_id,),
        ).fetchone()
        if not row:
            return None

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
            "cash_total_cad": float(row["cash_total_cad"]),
            "emt_total_cad": float(row["emt_total_cad"]),
            "request_json": json.loads(row["request_json"]),
            "notes": row["notes"],
            "requested_job_date": row["requested_job_date"],
            "requested_time_window": row["requested_time_window"],
            "customer_accepted_at": row["customer_accepted_at"],
            "admin_approved_at": row["admin_approved_at"],
        }

def list_quote_requests(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    where: List[str] = []
    params: List[Any] = []

    if status:
        where.append("status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT
            request_id, created_at, status, quote_id,
            customer_name, customer_phone, job_address,
            service_type, cash_total_cad, emt_total_cad,
            requested_job_date, requested_time_window
        FROM quote_requests
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(int(limit))

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            "request_id": r["request_id"],
            "created_at": r["created_at"],
            "status": r["status"],
            "quote_id": r["quote_id"],
            "customer_name": r["customer_name"],
            "customer_phone": r["customer_phone"],
            "job_address": r["job_address"],
            "service_type": r["service_type"],
            "cash_total_cad": float(r["cash_total_cad"]),
            "emt_total_cad": float(r["emt_total_cad"]),
            "requested_job_date": r["requested_job_date"],
            "requested_time_window": r["requested_time_window"],
        }
        for r in rows
    ]


def update_quote_request(
    request_id: str,
    *,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    requested_job_date: Optional[str] = None,
    requested_time_window: Optional[str] = None,
    customer_accepted_at: Optional[str] = None,
    admin_approved_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    existing = get_quote_request(request_id)
    if not existing:
        return None

    updated: Dict[str, Any] = dict(existing)

    if status is not None:
        updated["status"] = status
    if notes is not None:
        updated["notes"] = notes
    if requested_job_date is not None:
        updated["requested_job_date"] = requested_job_date
    if requested_time_window is not None:
        updated["requested_time_window"] = requested_time_window
    if customer_accepted_at is not None:
        updated["customer_accepted_at"] = customer_accepted_at
    if admin_approved_at is not None:
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
# Attachments
# =========================

def save_attachment(att: Dict[str, Any]) -> None:
    with _connect() as conn:
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

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

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

    with _connect() as conn:
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

    return payload


def import_db_from_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Backup payload must be a JSON object")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup payload missing 'tables' object")

    init_db()
    restored_counts: Dict[str, int] = {}

    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
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
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

    return {"ok": True, "restored": restored_counts}