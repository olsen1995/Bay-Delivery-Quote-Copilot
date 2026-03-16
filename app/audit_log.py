# Audit logging for admin actions

import sqlite3
from datetime import datetime
from typing import Optional

from app.storage import _connect

AUDIT_TABLE_NAME = "admin_audit_log"

# Table creation

def init_audit_table():
    conn = _connect()
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {AUDIT_TABLE_NAME} (
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

# Insert audit record

def log_admin_audit(
    operator_username: str,
    action_type: str,
    entity_type: str,
    record_id: str,
    success: bool,
    error_summary: Optional[str] = None,
):
    conn = _connect()
    try:
        conn.execute(
            f"""
            INSERT INTO {AUDIT_TABLE_NAME} (
                timestamp, operator_username, action_type, entity_type, record_id, success, error_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                datetime.now().isoformat(),
                operator_username,
                action_type,
                entity_type,
                record_id,
                int(success),
                error_summary,
            ],
        )
        conn.commit()
    finally:
        conn.close()
