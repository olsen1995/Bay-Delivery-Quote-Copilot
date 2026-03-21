from pathlib import Path

import pytest

from app import storage


@pytest.fixture(autouse=True)
def restore_db_path() -> None:
    original_db_path = storage.DB_PATH
    try:
        yield
    finally:
        storage.DB_PATH = original_db_path
        storage._TABLE_COL_CACHE.clear()



def _init_tmp_db(tmp_path: Path) -> None:
    storage.DB_PATH = tmp_path / "attachments.sqlite3"
    storage.init_db()


def test_save_attachment_without_analysis_id(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_attachment(
        {
            "attachment_id": "att-1",
            "created_at": "2026-03-01T10:00:00",
            "quote_id": "quote-1",
            "request_id": None,
            "job_id": None,
            "filename": "before.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 123,
            "drive_file_id": "drive-1",
            "drive_web_view_link": "https://example.com/1",
        }
    )

    items = storage.list_attachments(quote_id="quote-1")
    assert len(items) == 1
    assert items[0]["analysis_id"] is None


def test_save_attachment_with_analysis_id_and_round_trip_backup(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_attachment(
        {
            "attachment_id": "att-2",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": "analysis-1",
            "filename": "prequote.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
            "ocr_json": {
                "status": "success",
                "text": "Call me at 415-555-0199",
                "preview": "Call me at 415-555-0199",
                "warning": None,
            },
        }
    )

    items = storage.list_attachments(limit=10)
    assert len(items) == 1
    assert items[0]["analysis_id"] == "analysis-1"
    assert items[0]["ocr_json"]["status"] == "success"

    payload = storage.export_db_to_json()
    attachment_rows = payload["tables"]["attachments"]
    assert len(attachment_rows) == 1
    assert attachment_rows[0]["analysis_id"] == "analysis-1"
    assert attachment_rows[0]["ocr_json"]["status"] == "success"

    restored_db_path = tmp_path / "attachments-restored.sqlite3"
    storage.DB_PATH = restored_db_path
    storage.init_db()
    result = storage.import_db_from_json(payload)

    assert result["ok"] is True
    assert result["restored"]["attachments"] == 1

    restored_items = storage.list_attachments(limit=10)
    assert len(restored_items) == 1
    assert restored_items[0]["analysis_id"] == "analysis-1"
    assert restored_items[0]["ocr_json"]["status"] == "success"


def test_assign_analysis_attachments_to_quote_adds_quote_link_without_removing_analysis(tmp_path: Path) -> None:
    _init_tmp_db(tmp_path)

    storage.save_attachment(
        {
            "attachment_id": "att-quote-link",
            "created_at": "2026-03-01T10:05:00",
            "quote_id": None,
            "request_id": None,
            "job_id": None,
            "analysis_id": "analysis-quote-link",
            "filename": "prequote.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 456,
            "drive_file_id": "drive-2",
            "drive_web_view_link": "https://example.com/2",
        }
    )

    storage.assign_analysis_attachments_to_quote("analysis-quote-link", "quote-123")

    items = storage.list_attachments(analysis_id="analysis-quote-link", limit=10)
    assert len(items) == 1
    assert items[0]["analysis_id"] == "analysis-quote-link"
    assert items[0]["quote_id"] == "quote-123"
