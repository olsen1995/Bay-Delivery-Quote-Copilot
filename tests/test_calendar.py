import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import storage
from app.main import app


class CalendarIntegrationTests(unittest.TestCase):
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

    def _seed_job(self, job_id: str) -> None:
        storage.save_job({
            "job_id": job_id,
            "created_at": "2026-02-26T10:00:00",
            "status": "approved",
            "quote_id": "q123",
            "request_id": "r123",
            "customer_name": "Test Customer",
            "customer_phone": "555-0101",
            "job_address": "123 Main St",
            "job_description_customer": "Test job",
            "job_description_internal": "Internal desc",
            "service_type": "dump_run",
            "cash_total_cad": 100.0,
            "emt_total_cad": 113.0,
            "request_json": {"service_type": "dump_run"},
            "notes": "Test notes",
        })

    def test_schedule_job_success(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "2026-03-10T09:00:00", "scheduled_end": "2026-03-10T11:00:00"}

        with patch('app.gcalendar.is_configured', return_value=True), \
             patch('app.gcalendar.create_event', return_value='event123') as mock_create:
            resp = self.client.post("/admin/api/jobs/j123/schedule", json=payload, headers=self._admin_headers)
            self.assertEqual(resp.status_code, 200)
            job = storage.require_job("j123")
            self.assertEqual(job["calendar_sync_status"], "synced")
            self.assertEqual(job["google_calendar_event_id"], "event123")
            mock_create.assert_called_once()

    def test_schedule_job_invalid_datetime(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "invalid", "scheduled_end": "2026-03-10T11:00:00"}

        resp = self.client.post("/admin/api/jobs/j123/schedule", json=payload, headers=self._admin_headers)
        # 422 is the correct status for Pydantic validation errors
        self.assertEqual(resp.status_code, 422)

    def test_schedule_job_end_before_start(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "2026-03-10T11:00:00", "scheduled_end": "2026-03-10T09:00:00"}

        resp = self.client.post("/admin/api/jobs/j123/schedule", json=payload, headers=self._admin_headers)
        self.assertEqual(resp.status_code, 400)

    def test_schedule_job_not_found(self):
        payload = {"scheduled_start": "2026-03-10T09:00:00", "scheduled_end": "2026-03-10T11:00:00"}

        resp = self.client.post("/admin/api/jobs/j999/schedule", json=payload, headers=self._admin_headers)
        self.assertEqual(resp.status_code, 404)

    def test_schedule_job_no_auth(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "2026-03-10T09:00:00", "scheduled_end": "2026-03-10T11:00:00"}

        resp = self.client.post("/admin/api/jobs/j123/schedule", json=payload)
        self.assertEqual(resp.status_code, 401)

    def test_schedule_job_calendar_failure(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "2026-03-10T09:00:00", "scheduled_end": "2026-03-10T11:00:00"}

        with patch('app.gcalendar.is_configured', return_value=True), \
             patch('app.gcalendar.create_event', side_effect=Exception("API error")):
            resp = self.client.post("/admin/api/jobs/j123/schedule", json=payload, headers=self._admin_headers)
            self.assertEqual(resp.status_code, 200)
            job = storage.require_job("j123")
            self.assertEqual(job["calendar_sync_status"], "failed")
            self.assertIn("API error", job["calendar_last_error"])

    def test_reschedule_job_success(self):
        self._seed_job("j123")
        storage.update_job("j123", scheduled_start="2026-03-10T09:00:00Z", scheduled_end="2026-03-10T11:00:00Z", google_calendar_event_id="event123")
        payload = {"scheduled_start": "2026-03-10T10:00:00", "scheduled_end": "2026-03-10T12:00:00"}

        with patch('app.gcalendar.is_configured', return_value=True), \
             patch('app.gcalendar.update_event') as mock_update:
            resp = self.client.post("/admin/api/jobs/j123/reschedule", json=payload, headers=self._admin_headers)
            self.assertEqual(resp.status_code, 200)
            job = storage.require_job("j123")
            self.assertEqual(job["calendar_sync_status"], "synced")
            mock_update.assert_called_once()

    def test_reschedule_job_not_scheduled(self):
        self._seed_job("j123")
        payload = {"scheduled_start": "2026-03-10T10:00:00", "scheduled_end": "2026-03-10T12:00:00"}

        resp = self.client.post("/admin/api/jobs/j123/reschedule", json=payload, headers=self._admin_headers)
        self.assertEqual(resp.status_code, 400)

    def test_cancel_job_success(self):
        self._seed_job("j123")
        storage.update_job("j123", scheduled_start="2026-03-10T09:00:00Z", scheduled_end="2026-03-10T11:00:00Z", google_calendar_event_id="event123")

        with patch('app.gcalendar.is_configured', return_value=True), \
             patch('app.gcalendar.delete_event') as mock_delete:
            resp = self.client.post("/admin/api/jobs/j123/cancel", headers=self._admin_headers)
            self.assertEqual(resp.status_code, 200)
            job = storage.require_job("j123")
            self.assertEqual(job["status"], "cancelled")
            self.assertEqual(job["calendar_sync_status"], "cancelled")
            self.assertIsNone(job["google_calendar_event_id"])
            mock_delete.assert_called_once()

    def test_cancel_job_delete_failure_preserves_event_id(self):
        self._seed_job("j123")
        storage.update_job("j123", scheduled_start="2026-03-10T09:00:00Z", scheduled_end="2026-03-10T11:00:00Z", google_calendar_event_id="event123")

        with patch('app.gcalendar.is_configured', return_value=True), \
             patch('app.gcalendar.delete_event', side_effect=Exception("Delete failed")):
            resp = self.client.post("/admin/api/jobs/j123/cancel", headers=self._admin_headers)
            self.assertEqual(resp.status_code, 200)
            job = storage.require_job("j123")
            self.assertEqual(job["status"], "cancelled")
            self.assertEqual(job["calendar_sync_status"], "failed")
            self.assertEqual(job["google_calendar_event_id"], "event123")  # Preserved
            self.assertIn("Delete failed", job["calendar_last_error"])
