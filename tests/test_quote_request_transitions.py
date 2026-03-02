import base64
import os
import base64
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.main import app


class QuoteRequestTransitionsTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_quote(self, quote_id: str) -> None:
        storage.save_quote(
            {
                "quote_id": quote_id,
                "created_at": "2026-02-26T10:00:00",
                "request": {
                    "customer_name": "Test",
                    "customer_phone": "555-0101",
                    "job_address": "Somewhere",
                    "job_description_customer": "desc",
                    "service_type": "dump_run",
                },
                "response": {
                    "job_description_internal": "desc",
                    "cash_total_cad": 100.0,
                    "emt_total_cad": 113.0,
                },
            }
        )

    def _seed_request(self, request_id: str, quote_id: str, status: str) -> None:
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "secret"

        token = base64.b64encode(b"admin:secret").decode("utf-8")
        self._admin_headers = {"Authorization": f"Basic {token}"}
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_quote(self, quote_id: str) -> None:
        storage.save_quote(
            {
                "quote_id": quote_id,
                "created_at": "2026-02-26T10:00:00",
                "request": {
                    "customer_name": "Test",
                    "customer_phone": "555-0101",
                    "job_address": "Somewhere",
                    "job_description_customer": "desc",
                    "service_type": "dump_run",
                },
                "response": {
                    "job_description_internal": "desc",
                    "cash_total_cad": 100.0,
                    "emt_total_cad": 113.0,
                },
            }
        )

    def _seed_request(self, request_id: str, quote_id: str, status: str) -> None:
        storage.save_quote_request(
            {
                "request_id": request_id,
                "request_id": request_id,
                "created_at": "2026-02-26T10:00:00",
                "status": status,
                "quote_id": quote_id,
                "status": status,
                "quote_id": quote_id,
                "customer_name": "Test",
                "customer_phone": None,
                "job_address": "Somewhere",
                "job_description_customer": "desc",
                "job_description_internal": "desc",
                "service_type": "dump_run",
                "cash_total_cad": 100.0,
                "emt_total_cad": 113.0,
                "request_json": {},
                "notes": "keep-me",
                "requested_job_date": None,
                "requested_time_window": None,
                "customer_accepted_at": None,
                "admin_approved_at": None,
                "requested_job_date": None,
                "requested_time_window": None,
                "customer_accepted_at": None,
                "admin_approved_at": None,
            }
        )

    def test_allowed_pending_to_accepted(self) -> None:
        quote_id = "q_pending_accept"
        self._seed_quote(quote_id)
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "accept"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "customer_accepted")

    def test_allowed_pending_to_declined(self) -> None:
        quote_id = "q_pending_decline"
        self._seed_quote(quote_id)
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "decline"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "customer_declined")

    def test_allowed_accepted_to_admin_approved(self) -> None:
        request_id = "req_accept_approve"
        quote_id = "q_accept_approve"
        self._seed_request(request_id, quote_id, "customer_accepted")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
    def test_allowed_pending_to_accepted(self) -> None:
        quote_id = "q_pending_accept"
        self._seed_quote(quote_id)
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "accept"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "customer_accepted")

    def test_allowed_pending_to_declined(self) -> None:
        quote_id = "q_pending_decline"
        self._seed_quote(quote_id)
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "decline"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "customer_declined")

    def test_allowed_accepted_to_admin_approved(self) -> None:
        request_id = "req_accept_approve"
        quote_id = "q_accept_approve"
        self._seed_request(request_id, quote_id, "customer_accepted")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["request"]["status"], "admin_approved")

    def test_allowed_accepted_to_rejected(self) -> None:
        request_id = "req_accept_reject"
        quote_id = "q_accept_reject"
        self._seed_request(request_id, quote_id, "customer_accepted")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "reject"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["request"]["status"], "rejected")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["request"]["status"], "admin_approved")

    def test_allowed_accepted_to_rejected(self) -> None:
        request_id = "req_accept_reject"
        quote_id = "q_accept_reject"
        self._seed_request(request_id, quote_id, "customer_accepted")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "reject"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["request"]["status"], "rejected")

    def test_forbidden_declined_to_admin_approved(self) -> None:
        request_id = "req_declined_approve"
        quote_id = "q_declined_approve"
        self._seed_request(request_id, quote_id, "customer_declined")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.json()
        self.assertTrue({"error", "from", "to", "allowed"}.issubset(payload.keys()))
        self.assertEqual(payload["error"], "invalid_status_transition")
        self.assertEqual(payload["from"], "customer_declined")
        self.assertEqual(payload["to"], "admin_approved")

    def test_forbidden_pending_to_admin_approved(self) -> None:
        request_id = "req_pending_approve"
        quote_id = "q_pending_approve"
        self._seed_request(request_id, quote_id, "customer_pending")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.json()
        self.assertTrue({"error", "from", "to", "allowed"}.issubset(payload.keys()))
        self.assertEqual(payload["error"], "invalid_status_transition")
        self.assertEqual(payload["from"], "customer_pending")
        self.assertEqual(payload["to"], "admin_approved")

    def test_forbidden_admin_approved_to_rejected(self) -> None:
        request_id = "req_approved_reject"
        quote_id = "q_approved_reject"
        self._seed_request(request_id, quote_id, "admin_approved")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "reject"},
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.json()
        self.assertTrue({"error", "from", "to", "allowed"}.issubset(payload.keys()))
        self.assertEqual(payload["error"], "invalid_status_transition")
        self.assertEqual(payload["from"], "admin_approved")
        self.assertEqual(payload["to"], "rejected")

    def test_forbidden_rejected_to_admin_approved(self) -> None:
        request_id = "req_rejected_approve"
        quote_id = "q_rejected_approve"
        self._seed_request(request_id, quote_id, "rejected")

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.json()
        self.assertTrue({"error", "from", "to", "allowed"}.issubset(payload.keys()))
        self.assertEqual(payload["error"], "invalid_status_transition")
        self.assertEqual(payload["from"], "rejected")
        self.assertEqual(payload["to"], "admin_approved")


if __name__ == "__main__":
    unittest.main()

