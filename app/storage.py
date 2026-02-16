from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("app/data/bay_delivery.sqlite3")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _try_add_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """
    SQLite doesn't support ADD COLUMN IF NOT EXISTS in all versions.
    We try and ignore if it already exists.
    """
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        # "duplicate column name" is the normal 'already exists' case
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

        # Jobs (base schema)
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

        # --- lightweight migrations for new mirrored fields ---
        # These are "indexable" columns that mirror what we also store inside job_json.
        _try_add_column(conn, "jobs", "customer_phone TEXT")
        _try_add_column(conn, "jobs", "job_description_customer TEXT")
        _try_add_column(conn, "jobs", "job_description_internal TEXT")
        _try_add_column(conn, "jobs", "payment_method TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_quote_id ON jobs(quote_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_customer_name ON jobs(customer_name)")


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
        row = conn.execute(
            "SELECT response_json FROM quotes WHERE quote_id = ?",
            (quote_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["response_json"])


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
        {
            "quote_id": r["quote_id"],
            "created_at": r["created_at"],
            "job_type": r["job_type"],
            "total_cad": float(r["total_cad"]),
        }
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
        {
            "quote_id": r["quote_id"],
            "created_at": r["created_at"],
            "job_type": r["job_type"],
            "total_cad": float(r["total_cad"]),
        }
        for r in rows
    ]


# =========================
# Jobs
# =========================

def save_job(job_obj: Dict[str, Any]) -> None:
    """
    job_obj must include:
      job_id, created_at, quote_id, status, total_cad, paid_cad, owing_cad, job_json

    Optional mirrored columns:
      customer_name, customer_phone, job_address,
      job_description_customer, job_description_internal,
      scheduled_start, scheduled_end, payment_method, notes
    """
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
        row = conn.execute(
            "SELECT job_json FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["job_json"])


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
            total_cad, paid_cad, owing_cad
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
        }
        for r in rows
    ]


def update_job_fields(
    job_id: str,
    *,
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    job_address: Optional[str] = None,
    job_description_customer: Optional[str] = None,
    job_description_internal: Optional[str] = None,
    scheduled_start: Optional[str] = None,
    scheduled_end: Optional[str] = None,
    payment_method: Optional[str] = None,
    paid_cad: Optional[float] = None,
    notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return None

    # Apply updates to canonical job_json
    if status is not None:
        job["status"] = status
    if customer_name is not None:
        job["customer_name"] = customer_name
    if customer_phone is not None:
        job["customer_phone"] = customer_phone
    if job_address is not None:
        job["job_address"] = job_address
    if job_description_customer is not None:
        job["job_description_customer"] = job_description_customer
    if job_description_internal is not None:
        job["job_description_internal"] = job_description_internal
    if scheduled_start is not None:
        job["scheduled_start"] = scheduled_start
    if scheduled_end is not None:
        job["scheduled_end"] = scheduled_end
    if payment_method is not None:
        job["payment_method"] = payment_method
    if notes is not None:
        job["notes"] = notes

    if paid_cad is not None:
        paid = max(0.0, float(paid_cad))
        total = float(job["total_cad"])
        owing = max(0.0, total - paid)
        job["paid_cad"] = paid
        job["owing_cad"] = owing

    # Persist job + mirrored columns for indexing/listing
    save_job(
        {
            "job_id": job["job_id"],
            "created_at": job["created_at"],
            "quote_id": job["quote_id"],
            "status": job["status"],
            "customer_name": job.get("customer_name"),
            "customer_phone": job.get("customer_phone"),
            "job_address": job.get("job_address"),
            "job_description_customer": job.get("job_description_customer"),
            "job_description_internal": job.get("job_description_internal"),
            "scheduled_start": job.get("scheduled_start"),
            "scheduled_end": job.get("scheduled_end"),
            "payment_method": job.get("payment_method"),
            "total_cad": float(job["total_cad"]),
            "paid_cad": float(job["paid_cad"]),
            "owing_cad": float(job["owing_cad"]),
            "notes": job.get("notes"),
            "job_json": job,
        }
    )

    return job
