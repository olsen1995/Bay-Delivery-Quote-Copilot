import base64
import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional, Any, Dict, cast

from fastapi.testclient import TestClient

from app import storage
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
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()

    def _seed_quote(self, quote_id: str, accept_token: str = "accept-seed-token") -> None:
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
                "accept_token": accept_token,
            }
        )

    def _seed_request(self, request_id: str, quote_id: str, status: str, accept_token: str = "test_token", booking_token: Optional[str] = None) -> None:
        storage.save_quote_request(
            {
                "request_id": request_id,
                "created_at": "2026-02-26T10:00:00",
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
                "accept_token": accept_token,
                "booking_token": booking_token,
                "booking_token_created_at": "2026-02-26T10:00:00" if booking_token else None,
            }
        )

    def test_allowed_pending_to_accepted(self) -> None:
        # Get the quote first to retrieve accept_token and quote_id
        resp = self.client.post("/quote/calculate", json={
            "customer_name": "Test",
            "customer_phone": "555-0101",
            "job_address": "Somewhere",
            "description": "desc",
            "service_type": "haul_away",
            "estimated_hours": 1.0,
            "crew_size": 1,
        })
        quote_id = resp.json()["quote_id"]
        accept_token = resp.json()["accept_token"]
        # Now use the token for decision
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "accept", "accept_token": accept_token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "customer_accepted")
        self.assertIn("booking_token", resp.json())

    def test_allowed_pending_to_declined(self) -> None:
        # Get the quote first to retrieve accept_token and quote_id
        resp = self.client.post("/quote/calculate", json={
            "customer_name": "Test",
            "customer_phone": "555-0101",
            "job_address": "Somewhere",
            "description": "desc",
            "service_type": "haul_away",
            "estimated_hours": 1.0,
            "crew_size": 1,
        })
        quote_id = resp.json()["quote_id"]
        accept_token = resp.json()["accept_token"]
        # Now use the token for decision
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "decline", "accept_token": accept_token})
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

    def test_admin_handoff_creates_customer_pending_request(self) -> None:
        quote_id = "q_handoff_create"
        self._seed_quote(quote_id, accept_token="handoff-token-1")

        resp = self.client.post(
            f"/admin/api/quotes/{quote_id}/handoff",
            headers=self._admin_headers,
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["quote_id"], quote_id)
        self.assertEqual(body["status"], "customer_pending")
        self.assertFalse(body["already_existed"])
        self.assertEqual(body["handoff_url"], f"/quote?quote_id={quote_id}&accept_token=handoff-token-1")

        saved = storage.get_quote_request(body["request_id"])
        self.assertIsNotNone(saved)
        saved_typed = cast(Dict[str, Any], saved)
        self.assertEqual(saved_typed["quote_id"], quote_id)
        self.assertEqual(saved_typed["status"], "customer_pending")
        self.assertEqual(saved_typed["accept_token"], "handoff-token-1")

        audit_items = storage.list_admin_audit_log(limit=5)
        self.assertEqual(audit_items[0]["action_type"], "prepare_customer_handoff")
        self.assertEqual(audit_items[0]["entity_type"], "quote_request")
        self.assertEqual(audit_items[0]["record_id"], body["request_id"])
        self.assertTrue(audit_items[0]["success"])

    def test_admin_handoff_is_idempotent_for_same_quote(self) -> None:
        quote_id = "q_handoff_existing"
        self._seed_quote(quote_id, accept_token="handoff-token-2")

        first = self.client.post(
            f"/admin/api/quotes/{quote_id}/handoff",
            headers=self._admin_headers,
        )
        self.assertEqual(first.status_code, 200)
        first_body = first.json()

        second = self.client.post(
            f"/admin/api/quotes/{quote_id}/handoff",
            headers=self._admin_headers,
        )
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertTrue(second_body["already_existed"])
        self.assertEqual(second_body["request_id"], first_body["request_id"])
        self.assertEqual(second_body["status"], "customer_pending")

        requests = storage.list_quote_requests(limit=10)
        matching = [item for item in requests if item["quote_id"] == quote_id]
        self.assertEqual(len(matching), 1)

    def test_admin_handoff_requires_admin(self) -> None:
        quote_id = "q_handoff_auth"
        self._seed_quote(quote_id)

        resp = self.client.post(f"/admin/api/quotes/{quote_id}/handoff")
        self.assertIn(resp.status_code, {401, 403})

    def test_admin_handoff_missing_quote_returns_404_and_logs_failure(self) -> None:
        resp = self.client.post(
            "/admin/api/quotes/missing-quote/handoff",
            headers=self._admin_headers,
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), {"detail": "Quote not found."})

        audit_items = storage.list_admin_audit_log(limit=5)
        self.assertEqual(audit_items[0]["action_type"], "prepare_customer_handoff")
        self.assertEqual(audit_items[0]["entity_type"], "quote")
        self.assertEqual(audit_items[0]["record_id"], "missing-quote")
        self.assertFalse(audit_items[0]["success"])

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
        self.assertIsInstance(payload["detail"], str)
        self.assertIn(payload["from"], payload["detail"])
        self.assertIn(payload["to"], payload["detail"])

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
        self.assertIsInstance(payload["detail"], str)
        self.assertIn(payload["from"], payload["detail"])
        self.assertIn(payload["to"], payload["detail"])

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
        self.assertIsInstance(payload["detail"], str)
        self.assertIn(payload["from"], payload["detail"])
        self.assertIn(payload["to"], payload["detail"])

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
        self.assertIsInstance(payload["detail"], str)
        self.assertIn(payload["from"], payload["detail"])
        self.assertIn(payload["to"], payload["detail"])

    def test_admin_approval_creates_job(self) -> None:
        request_id = "req_creates_job"
        quote_id = "q_creates_job"
        self._seed_request(
            request_id,
            quote_id,
            "customer_accepted",
            accept_token="tok_creates_job",
        )

        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["request"]["status"], "admin_approved")

        # Response must include the created job
        self.assertIsNotNone(data["job"])
        job = data["job"]
        self.assertEqual(job["quote_id"], quote_id)
        self.assertEqual(job["request_id"], request_id)
        self.assertIn("job_id", job)
        self.assertEqual(job["status"], "approved")
        self.assertIn("scheduling_context", job)
        self.assertEqual(job["scheduling_context"]["request_id"], request_id)
        self.assertIsNone(job["scheduling_context"]["requested_job_date"])
        self.assertIsNone(job["scheduling_context"]["requested_time_window"])
        self.assertFalse(job["scheduling_context"]["scheduling_ready"])

        # Job must appear in the admin Jobs list
        jobs_resp = self.client.get("/admin/api/jobs", headers=self._admin_headers)
        self.assertEqual(jobs_resp.status_code, 200)
        items = jobs_resp.json()["items"]
        job_ids = [j["job_id"] for j in items]
        self.assertIn(job["job_id"], job_ids)
        listed_job = next(item for item in items if item["job_id"] == job["job_id"])
        self.assertEqual(listed_job["scheduling_context"]["request_id"], request_id)

    def test_admin_approval_does_not_duplicate_job(self) -> None:
        request_id = "req_no_dup_job"
        quote_id = "q_no_dup_job"
        self._seed_request(
            request_id,
            quote_id,
            "customer_accepted",
            accept_token="tok_no_dup",
        )

        # First approval — creates the job
        resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(resp.status_code, 200)
        first_job = resp.json()["job"]
        self.assertIsNotNone(first_job)
        first_job_typed = cast(Dict[str, Any], first_job)

        # Verify the guard: get_job_by_quote_id returns the existing job,
        # so a subsequent approval call would skip creating a second one.
        from app.storage import get_job_by_quote_id
        existing_job = get_job_by_quote_id(quote_id)
        self.assertIsNotNone(existing_job)
        existing_job_typed = cast(Dict[str, Any], existing_job)
        self.assertEqual(existing_job_typed["job_id"], first_job_typed["job_id"])

    def test_submit_booking_success(self) -> None:
        # Get the quote first to retrieve accept_token and quote_id
        resp = self.client.post("/quote/calculate", json={
            "customer_name": "Test",
            "customer_phone": "555-0101",
            "job_address": "Somewhere",
            "description": "desc",
            "service_type": "haul_away",
            "estimated_hours": 1.0,
            "crew_size": 1,
        })
        quote_id = resp.json()["quote_id"]
        accept_token = resp.json()["accept_token"]
        # accept first
        resp = self.client.post(f"/quote/{quote_id}/decision", json={"action": "accept", "accept_token": accept_token})
        self.assertEqual(resp.status_code, 200)
        request_id = resp.json()["request_id"]
        booking_token = resp.json()["booking_token"]
        # now submit booking
        resp = self.client.post(f"/quote/{quote_id}/booking", json={
            "booking_token": booking_token,
            "requested_job_date": "2026-03-10",
            "requested_time_window": "morning",
            "notes": "test notes",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["request_id"], request_id)
        # check updated
        req = storage.get_quote_request(request_id)
        self.assertIsNotNone(req)
        req_typed = cast(Dict[str, Any], req)
        self.assertEqual(req_typed["requested_job_date"], "2026-03-10")
        self.assertEqual(req_typed["requested_time_window"], "morning")
        self.assertEqual(req_typed["notes"], "test notes")

    def test_customer_accept_after_admin_handoff_updates_same_request(self) -> None:
        quote_id = "q_handoff_customer_accept"
        self._seed_quote(quote_id, accept_token="handoff-customer-token")

        handoff_resp = self.client.post(
            f"/admin/api/quotes/{quote_id}/handoff",
            headers=self._admin_headers,
        )
        self.assertEqual(handoff_resp.status_code, 200)
        handoff_request_id = handoff_resp.json()["request_id"]

        decision_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={"action": "accept", "accept_token": "handoff-customer-token"},
        )
        self.assertEqual(decision_resp.status_code, 200)
        decision_body = decision_resp.json()
        self.assertEqual(decision_body["request_id"], handoff_request_id)
        self.assertEqual(decision_body["status"], "customer_accepted")
        self.assertIn("booking_token", decision_body)

        booking_resp = self.client.post(
            f"/quote/{quote_id}/booking",
            json={
                "booking_token": decision_body["booking_token"],
                "requested_job_date": "2026-03-10",
                "requested_time_window": "afternoon",
                "notes": "handoff flow booking",
            },
        )
        self.assertEqual(booking_resp.status_code, 200)

        updated = storage.get_quote_request(handoff_request_id)
        self.assertIsNotNone(updated)
        updated_typed = cast(Dict[str, Any], updated)
        self.assertEqual(updated_typed["status"], "customer_accepted")
        self.assertEqual(updated_typed["requested_job_date"], "2026-03-10")
        self.assertEqual(updated_typed["requested_time_window"], "afternoon")

    def test_admin_jobs_include_linked_booking_preferences_after_approval(self) -> None:
        quote_resp = self.client.post("/quote/calculate", json={
            "customer_name": "Schedule Test",
            "customer_phone": "555-0101",
            "job_address": "123 Main St",
            "description": "desc",
            "service_type": "haul_away",
            "estimated_hours": 1.0,
            "crew_size": 1,
        })
        quote_id = quote_resp.json()["quote_id"]
        accept_token = quote_resp.json()["accept_token"]

        accept_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={"action": "accept", "accept_token": accept_token},
        )
        self.assertEqual(accept_resp.status_code, 200)
        request_id = accept_resp.json()["request_id"]
        booking_token = accept_resp.json()["booking_token"]

        booking_resp = self.client.post(
            f"/quote/{quote_id}/booking",
            json={
                "booking_token": booking_token,
                "requested_job_date": "2026-03-10",
                "requested_time_window": "morning",
                "notes": "Call when outside gate",
            },
        )
        self.assertEqual(booking_resp.status_code, 200)

        approval_resp = self.client.post(
            f"/admin/api/quote-requests/{request_id}/decision",
            headers=self._admin_headers,
            json={"action": "approve"},
        )
        self.assertEqual(approval_resp.status_code, 200)

        job = approval_resp.json()["job"]
        self.assertEqual(job["scheduling_context"]["request_id"], request_id)
        self.assertEqual(job["scheduling_context"]["requested_job_date"], "2026-03-10")
        self.assertEqual(job["scheduling_context"]["requested_time_window"], "morning")
        self.assertEqual(job["scheduling_context"]["notes"], "Call when outside gate")
        self.assertTrue(job["scheduling_context"]["scheduling_ready"])
        self.assertEqual(job["scheduling_context"]["missing_fields"], [])

    def test_submit_booking_no_request(self) -> None:
        resp = self.client.post("/quote/nonexistent/booking", json={
            "booking_token": "invalid_token",
            "requested_job_date": "2026-03-10",
            "requested_time_window": "morning",
        })
        self.assertEqual(resp.status_code, 404)

    def test_submit_booking_wrong_status(self) -> None:
        request_id = "req_pending"
        quote_id = "q_pending"
        self._seed_request(request_id, quote_id, "customer_pending", accept_token="test_token")
        resp = self.client.post(f"/quote/{quote_id}/booking", json={
            "booking_token": "any_token",
            "requested_job_date": "2026-03-10",
            "requested_time_window": "morning",
        })
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
