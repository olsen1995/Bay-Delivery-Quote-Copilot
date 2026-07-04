from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import storage


@pytest.fixture(autouse=True)
def restore_db_path(monkeypatch: pytest.MonkeyPatch) -> None:
    original_db_path = storage.DB_PATH
    monkeypatch.delenv("BAYDELIVERY_DB_PATH", raising=False)
    storage._TABLE_COL_CACHE.clear()
    try:
        yield
    finally:
        storage.DB_PATH = original_db_path
        storage._TABLE_COL_CACHE.clear()


def _use_tmp_db(tmp_path: Path, name: str = "quote-request-duplicates.sqlite3") -> Path:
    db_path = tmp_path / name
    storage.DB_PATH = db_path
    storage._TABLE_COL_CACHE.clear()
    return db_path


def _create_legacy_quote_requests_table(conn: sqlite3.Connection, *, quote_id_not_null: bool = True) -> None:
    quote_id_constraint = "TEXT NOT NULL" if quote_id_not_null else "TEXT"
    conn.execute(
        f"""
        CREATE TABLE quote_requests (
            request_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            quote_id {quote_id_constraint},
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


def _insert_quote_request(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    quote_id: str | None,
    created_at: str,
    customer_name: str = "Sensitive Customer",
    customer_phone: str = "705-555-0101",
    job_address: str = "123 Private Road",
    job_description_customer: str = "Private customer description",
    job_description_internal: str = "Private internal description",
    cash_total_cad: float = 125.0,
    emt_total_cad: float = 141.25,
    request_json: str = '{"token": "private-token", "secret": "do-not-log"}',
    accept_token: str = "accept-secret",
    booking_token: str = "booking-secret",
) -> None:
    conn.execute(
        """
        INSERT INTO quote_requests
        (request_id, created_at, status, quote_id, customer_name, customer_phone, job_address,
         job_description_customer, job_description_internal, service_type, cash_total_cad,
         emt_total_cad, request_json, notes, requested_job_date, requested_time_window,
         customer_accepted_at, admin_approved_at, accept_token, booking_token, booking_token_created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            created_at,
            "customer_accepted",
            quote_id,
            customer_name,
            customer_phone,
            job_address,
            job_description_customer,
            job_description_internal,
            "haul_away",
            cash_total_cad,
            emt_total_cad,
            request_json,
            None,
            None,
            None,
            None,
            None,
            accept_token,
            booking_token,
            None,
        ),
    )


def _seed_legacy_quote_requests(
    db_path: Path,
    rows: list[tuple[str, str | None, str]],
    *,
    quote_id_not_null: bool = True,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        _create_legacy_quote_requests_table(conn, quote_id_not_null=quote_id_not_null)
        for request_id, quote_id, created_at in rows:
            _insert_quote_request(
                conn,
                request_id=request_id,
                quote_id=quote_id,
                created_at=created_at,
            )
        conn.commit()
    finally:
        conn.close()


def _quote_request_ids_for_quote_id(quote_id: str) -> list[str]:
    conn = storage._connect()
    try:
        rows = conn.execute(
            "SELECT request_id FROM quote_requests WHERE quote_id = ? ORDER BY request_id",
            (quote_id,),
        ).fetchall()
    finally:
        conn.close()
    return [row["request_id"] for row in rows]


def _quote_request_count_where(where_sql: str) -> int:
    conn = storage._connect()
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM quote_requests WHERE {where_sql}").fetchone()[0])
    finally:
        conn.close()


def _quote_request_quote_id_index_exists() -> bool:
    conn = storage._connect()
    try:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'index'
              AND name = 'uq_quote_requests_quote_id'
            """
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def test_init_db_preserves_duplicate_quote_requests_when_quote_id_blocks_unique_index(
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(tmp_path)
    _seed_legacy_quote_requests(
        db_path,
        [
            ("req-duplicate-old", "quote-duplicate", "2026-05-01T09:00:00"),
            ("req-duplicate-new", "quote-duplicate", "2026-05-01T10:00:00"),
        ],
    )

    storage.init_db()

    assert _quote_request_ids_for_quote_id("quote-duplicate") == [
        "req-duplicate-new",
        "req-duplicate-old",
    ]


def test_init_db_logs_safe_error_and_skips_unique_index_for_blocking_quote_id_duplicates(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_path = _use_tmp_db(tmp_path)
    _seed_legacy_quote_requests(
        db_path,
        [
            ("req-sensitive-a", "quote-sensitive", "2026-05-01T09:00:00"),
            ("req-sensitive-b", "quote-sensitive", "2026-05-01T10:00:00"),
        ],
    )

    with caplog.at_level("ERROR", logger="app.storage"):
        storage.init_db()

    log_text = caplog.text
    assert "quote_requests duplicate quote_id values block unique index creation" in log_text
    assert "uq_quote_requests_quote_id" in log_text
    assert "quote-sensitive" in log_text
    assert "req-sensitive-a" in log_text
    assert "req-sensitive-b" in log_text
    assert not _quote_request_quote_id_index_exists()

    forbidden_fragments = [
        "Sensitive Customer",
        "705-555-0101",
        "123 Private Road",
        "Private customer description",
        "Private internal description",
        "125.0",
        "141.25",
        "private-token",
        "do-not-log",
        "accept-secret",
        "booking-secret",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in log_text


def test_init_db_treats_repeated_blank_quote_ids_as_blocking_duplicates(
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(tmp_path)
    _seed_legacy_quote_requests(
        db_path,
        [
            ("req-blank-a", "", "2026-05-01T09:00:00"),
            ("req-blank-b", "", "2026-05-01T10:00:00"),
        ],
    )

    storage.init_db()

    assert _quote_request_ids_for_quote_id("") == ["req-blank-a", "req-blank-b"]
    assert not _quote_request_quote_id_index_exists()


def test_init_db_allows_repeated_null_quote_ids_like_sqlite_unique_index(
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(tmp_path)
    _seed_legacy_quote_requests(
        db_path,
        [
            ("req-null-a", None, "2026-05-01T09:00:00"),
            ("req-null-b", None, "2026-05-01T10:00:00"),
        ],
        quote_id_not_null=False,
    )

    storage.init_db()

    assert _quote_request_count_where("quote_id IS NULL") == 2
    assert _quote_request_quote_id_index_exists()


def test_init_db_creates_quote_request_quote_id_unique_index_on_clean_db(
    tmp_path: Path,
) -> None:
    db_path = _use_tmp_db(tmp_path)
    _seed_legacy_quote_requests(
        db_path,
        [
            ("req-clean-a", "quote-clean-a", "2026-05-01T09:00:00"),
            ("req-clean-b", "quote-clean-b", "2026-05-01T10:00:00"),
        ],
    )

    storage.init_db()

    assert _quote_request_quote_id_index_exists()
