import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import storage
from app.main import app


class AcceptTokenValidationTests(unittest.TestCase):
    """Tests for server-side accept_token persistence and validation."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmp.name) / "test.sqlite3"

        storage.DB_PATH = self._db_path
        storage.init_db()

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_correct_accept_token_accepted_on_first_decision(self) -> None:
        """Verify that the correct server-generated token is accepted on first decision."""
        # Calculate quote to get the server-generated accept_token
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Alice",
                "customer_phone": "705-555-0001",
                "job_address": "123 Main St",
                "description": "Move stuff",
                "service_type": "junk_removal",
                "estimated_hours": 2.0,
            },
        )
        self.assertEqual(200, calculate_resp.status_code)
        quote_data = calculate_resp.json()
        quote_id = quote_data["quote_id"]
        correct_token = quote_data["accept_token"]

        # Submit decision with the correct token
        decision_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "accept",
                "accept_token": correct_token,
                "notes": None,
            },
        )
        self.assertEqual(200, decision_resp.status_code)
        decision_data = decision_resp.json()
        self.assertTrue(decision_data.get("ok"))
        self.assertIsNotNone(decision_data.get("booking_token"))

    def test_wrong_accept_token_rejected_on_first_decision(self) -> None:
        """Verify that an incorrect token is rejected on first decision (401)."""
        # Calculate quote
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Bob",
                "customer_phone": "705-555-0002",
                "job_address": "456 Oak Ave",
                "description": "Move stuff",
                "service_type": "junk_removal",
                "estimated_hours": 1.0,
            },
        )
        self.assertEqual(200, calculate_resp.status_code)
        quote_data = calculate_resp.json()
        quote_id = quote_data["quote_id"]

        # Submit decision with a WRONG token
        decision_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "accept",
                "accept_token": "totally-wrong-token-xyz123",
                "notes": None,
            },
        )
        self.assertEqual(401, decision_resp.status_code)
        error_data = decision_resp.json()
        self.assertIn("Invalid or expired accept token", error_data.get("detail", ""))

    def test_wrong_token_does_not_establish_in_database(self) -> None:
        """Verify that a failed token submission doesn't get stored as the valid token."""
        # Calculate quote
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Charlie",
                "customer_phone": "705-555-0003",
                "job_address": "789 Pine Rd",
                "description": "Move stuff",
                "service_type": "junk_removal",
                "estimated_hours": 1.5,
            },
        )
        quote_data = calculate_resp.json()
        quote_id = quote_data["quote_id"]
        correct_token = quote_data["accept_token"]

        # First attempt: wrong token
        wrong_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "accept",
                "accept_token": "badtoken123",
                "notes": None,
            },
        )
        self.assertEqual(401, wrong_resp.status_code)

        # Second attempt: correct token should still work
        correct_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "accept",
                "accept_token": correct_token,
                "notes": None,
            },
        )
        self.assertEqual(200, correct_resp.status_code)
        self.assertTrue(correct_resp.json().get("ok"))

    def test_subsequent_decision_validates_against_stored_token(self) -> None:
        """Verify that a second call to decision validates against the stored token."""
        # Calculate quote
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Diana",
                "customer_phone": "705-555-0004",
                "job_address": "999 Elm St",
                "description": "Move stuff",
                "service_type": "junk_removal",
                "estimated_hours": 2.0,
            },
        )
        quote_data = calculate_resp.json()
        quote_id = quote_data["quote_id"]
        correct_token = quote_data["accept_token"]

        # First decision: accept with correct token
        first_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "accept",
                "accept_token": correct_token,
                "notes": "First notes",
            },
        )
        self.assertEqual(200, first_resp.status_code)
        self.assertEqual("customer_accepted", first_resp.json()["status"])

        # Second decision: attempt with wrong token should fail
        second_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "decline",
                "accept_token": "wrong-token-attempt",
                "notes": "Second attempt",
            },
        )
        self.assertEqual(401, second_resp.status_code)

    def test_quote_not_found_returns_404(self) -> None:
        """Verify that decision call on non-existent quote returns 404."""
        decision_resp = self.client.post(
            "/quote/nonexistent123/decision",
            json={
                "action": "accept",
                "accept_token": "any-token",
                "notes": None,
            },
        )
        self.assertEqual(404, decision_resp.status_code)
        error_data = decision_resp.json()
        self.assertIn("Quote not found", error_data.get("detail", ""))

    def test_decline_with_correct_token_accepted(self) -> None:
        """Verify that 'decline' action also validates and works correctly."""
        # Calculate quote
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Eve",
                "customer_phone": "705-555-0005",
                "job_address": "321 Cedar Ln",
                "description": "Move stuff",
                "service_type": "junk_removal",
                "estimated_hours": 1.0,
            },
        )
        quote_data = calculate_resp.json()
        quote_id = quote_data["quote_id"]
        correct_token = quote_data["accept_token"]

        # Decline with correct token
        decision_resp = self.client.post(
            f"/quote/{quote_id}/decision",
            json={
                "action": "decline",
                "accept_token": correct_token,
                "notes": None,
            },
        )
        self.assertEqual(200, decision_resp.status_code)
        decision_data = decision_resp.json()
        self.assertTrue(decision_data.get("ok"))
        self.assertEqual("customer_declined", decision_data.get("status"))

    def test_quote_review_view_allows_valid_accept_token(self) -> None:
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Frank",
                "customer_phone": "705-555-0006",
                "job_address": "111 Review St",
                "description": "Saved quote review",
                "service_type": "haul_away",
                "estimated_hours": 1.0,
                "crew_size": 1,
            },
        )
        self.assertEqual(200, calculate_resp.status_code)
        quote_data = calculate_resp.json()

        view_resp = self.client.get(
            f"/quote/{quote_data['quote_id']}/view",
            params={"accept_token": quote_data["accept_token"]},
        )
        self.assertEqual(200, view_resp.status_code)
        body = view_resp.json()
        self.assertEqual(body["quote_id"], quote_data["quote_id"])
        self.assertEqual(body["request"]["customer_name"], "Frank")
        self.assertIn("cash_total_cad", body["response"])
        self.assertIsNone(body["quote_request_status"])

    def test_quote_review_view_rejects_invalid_accept_token(self) -> None:
        calculate_resp = self.client.post(
            "/quote/calculate",
            json={
                "customer_name": "Grace",
                "customer_phone": "705-555-0007",
                "job_address": "222 Review St",
                "description": "Saved quote review",
                "service_type": "haul_away",
                "estimated_hours": 1.0,
                "crew_size": 1,
            },
        )
        self.assertEqual(200, calculate_resp.status_code)
        quote_data = calculate_resp.json()

        view_resp = self.client.get(
            f"/quote/{quote_data['quote_id']}/view",
            params={"accept_token": "wrong-token"},
        )
        self.assertEqual(401, view_resp.status_code)
        self.assertEqual(view_resp.json(), {"detail": "Invalid or expired accept token."})


if __name__ == "__main__":
    unittest.main()
