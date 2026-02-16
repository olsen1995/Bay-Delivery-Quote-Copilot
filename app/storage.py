from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path("app/data/bay_delivery.sqlite3")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
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
