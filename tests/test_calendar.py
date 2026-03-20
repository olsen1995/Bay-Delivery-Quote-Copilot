import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import gcalendar, storage
from app.main import app
from app.services import booking_service


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
        storage.DB_PATH = storage.DEFAULT_DB_PATH
        storage._TABLE_COL_CACHE.clear()

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

    def _seed_quote_request(self, request_id: str = "r-approved", quote_id: str = "q-approved") -> None:
        storage.save_quote_request({
            "request_id": request_id,
            "created_at": "2026-02-26T09:00:00",
            "status": "customer_accepted",
            "quote_id": quote_id,
            "customer_name": "Approved Customer",
            "customer_phone": "555-0123",
            "job_address": "456 Approved Ave",
            "job_description_customer": "Approved job",
            "job_description_internal": "Approved internal desc",
            "service_type": "dump_run",
            "cash_total_cad": 200.0,
            "emt_total_cad": 226.0,
            "request_json": {"service_type": "dump_run"},
            "notes": "Needs approval",
            "requested_job_date": "2026-03-10",
            "requested_time_window": "morning",
            "customer_accepted_at": "2026-02-26T09:00:00",
            "admin_approved_at": None,
            "accept_token": "accept-token",
            "booking_token": "booking-token",
            "booking_token_created_at": "2026-02-26T09:00:00",
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

    def test_jobs_payload_includes_scheduling_context(self):
        self._seed_quote_request()

        result = booking_service.process_admin_decision(
            "r-approved",
            action="approve",
            notes=None,
            notes_provided=False,
            now_iso="2026-02-26T10:00:00",
        )

        job_id = result["job"]["job_id"]
        resp = self.client.get("/admin/api/jobs", headers=self._admin_headers)
        self.assertEqual(resp.status_code, 200)
        listed_job = next(item for item in resp.json()["items"] if item["job_id"] == job_id)
        self.assertEqual(listed_job["scheduling_context"]["request_id"], "r-approved")
        self.assertEqual(listed_job["scheduling_context"]["requested_job_date"], "2026-03-10")
        self.assertEqual(listed_job["scheduling_context"]["requested_time_window"], "morning")
        self.assertEqual(listed_job["scheduling_context"]["notes"], "Needs approval")
        self.assertTrue(listed_job["scheduling_context"]["scheduling_ready"])
        self.assertEqual(listed_job["scheduling_context"]["missing_fields"], [])

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

    def test_admin_approval_creates_schedulable_job(self):
        self._seed_quote_request()

        result = booking_service.process_admin_decision(
            "r-approved",
            action="approve",
            notes=None,
            notes_provided=False,
            now_iso="2026-02-26T10:00:00",
        )

        created_job = result["job"]
        self.assertIsNotNone(created_job)
        self.assertEqual(created_job["status"], "approved")

        payload = {"scheduled_start": "2026-03-10T09:00:00", "scheduled_end": "2026-03-10T11:00:00"}
        with patch('app.gcalendar.is_configured', return_value=False):
            resp = self.client.post(f"/admin/api/jobs/{created_job['job_id']}/schedule", json=payload, headers=self._admin_headers)

        self.assertEqual(resp.status_code, 200)
        scheduled_job = storage.require_job(created_job["job_id"])
        self.assertEqual(scheduled_job["status"], "approved")
        self.assertEqual(scheduled_job["calendar_sync_status"], "not_configured")
        self.assertIsNotNone(scheduled_job["scheduled_start"])
        self.assertIsNotNone(scheduled_job["scheduled_end"])

    def test_calendar_event_payload_uses_richer_job_context(self):
        job = {
            "job_id": "j123",
            "created_at": "2026-02-26T10:00:00",
            "status": "approved",
            "quote_id": "q123",
            "request_id": "r123",
            "customer_name": "Taylor Customer",
            "customer_phone": "555-0101",
            "job_address": "123 Main St, Nanaimo, BC",
            "job_description_customer": "Remove a couch",
            "job_description_internal": "Bring straps and blankets",
            "service_type": "item_delivery",
            "cash_total_cad": 100.0,
            "emt_total_cad": 113.0,
            "request_json": {"service_type": "item_delivery"},
            "notes": "Customer note",
            "scheduled_start": None,
            "scheduled_end": None,
            "google_calendar_event_id": None,
            "calendar_sync_status": None,
            "calendar_last_error": None,
            "scheduling_context": {
                "request_id": "r123",
                "requested_job_date": "2026-03-10",
                "requested_time_window": "afternoon",
                "notes": "Call when outside gate",
                "scheduling_ready": True,
                "missing_fields": [],
            },
        }

        captured = {}

        class _FakeInsert:
            def execute(self):
                return {"id": "event123"}

        class _FakeEvents:
            def insert(self, *, calendarId, body):
                captured["calendarId"] = calendarId
                captured["body"] = body
                return _FakeInsert()

        class _FakeService:
            def events(self):
                return _FakeEvents()

        with patch("app.gcalendar._service", return_value=_FakeService()), patch("app.gcalendar._calendar_id", return_value="calendar123"):
            event_id = gcalendar.create_event(job, "2026-03-10T17:00:00+00:00", "2026-03-10T19:00:00+00:00")

        self.assertEqual(event_id, "event123")
        self.assertEqual(captured["calendarId"], "calendar123")
        self.assertEqual(captured["body"]["summary"], "Item Delivery - Taylor Customer - 123 Main St")
        description = captured["body"]["description"]
        self.assertIn("Customer: Taylor Customer", description)
        self.assertIn("Phone: 555-0101", description)
        self.assertIn("Address: 123 Main St, Nanaimo, BC", description)
        self.assertIn("Quote ID: q123", description)
        self.assertIn("Request ID: r123", description)
        self.assertIn("Job ID: j123", description)
        self.assertIn("Requested Date: 2026-03-10", description)
        self.assertIn("Requested Window: afternoon", description)
        self.assertIn("Booking Notes: Call when outside gate", description)
        self.assertIn("Internal Summary: Bring straps and blankets", description)
