import base64
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from app import storage
from app.main import app

class AdminAuditLogExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmp.name) / "test.sqlite3"
        storage.DB_PATH = self._db_path
        storage.init_db()
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "secret"
        token = base64.b64encode(b"admin:secret").decode("utf-8")
        self._admin_headers = {"Authorization": f"Basic {token}"}
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_unauthenticated_access_denied(self):
        resp = self.client.get("/admin/api/audit-log/export")
        assert resp.status_code in (401, 403)

    def test_authenticated_admin_success(self):
        # Insert a sample audit log row
        conn = storage._connect()
        conn.execute(
            "INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "2026-03-15T12:00:00",
                "admin",
                "export_test",
                "test_entity",
                "123",
                1,
                None,
            ],
        )
        conn.commit()
        conn.close()
        resp = self.client.get("/admin/api/audit-log/export", headers=self._admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=" in resp.headers["content-disposition"]
        csv_text = resp.text
        assert "operator_username" in csv_text
        assert "export_test" in csv_text

    def test_csv_header_and_content_shape(self):
        conn = storage._connect()
        conn.execute(
            "INSERT INTO admin_audit_log (timestamp, operator_username, action_type, entity_type, record_id, success, error_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "2026-03-15T12:01:00",
                "admin",
                "action",
                "entity",
                "456",
                0,
                "fail",
            ],
        )
        conn.commit()
        conn.close()
        token = base64.b64encode(b"admin:secret").decode("utf-8")
        headers = {"Authorization": f"Basic {token}"}
        resp = self.client.get("/admin/api/audit-log/export", headers=headers)
        assert resp.status_code == 200
        lines = resp.text.splitlines()
        header = lines[0].split(",")
        assert set(header) >= {"timestamp", "operator_username", "action_type", "entity_type", "record_id", "success", "error_summary"}
        assert "entity" in resp.text
        assert "fail" in resp.text
