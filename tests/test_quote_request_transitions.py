import tempfile
import unittest
from pathlib import Path

from app import storage


class QuoteRequestTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_db_path = storage.DB_PATH
        self.tmpdir = tempfile.TemporaryDirectory()
        storage.DB_PATH = Path(self.tmpdir.name) / "test.sqlite3"
        storage.init_db()

    def tearDown(self) -> None:
        storage.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def _seed_quote_request(self, request_id: str) -> None:
        storage.save_quote_request(
            {
                "request_id": request_id,
                "created_at": "2026-01-01T10:00:00-05:00",
                "status": "customer_accepted_pending_admin",
                "quote_id": f"quote-{request_id}",
                "customer_name": "Pat Lee",
                "customer_phone": "555-0101",
                "job_address": "123 Main St",
                "job_description_customer": "Old couch pickup",
                "job_description_internal": "Old couch pickup",
                "service_type": "haul_away",
                "cash_total_cad": 150.0,
                "emt_total_cad": 160.0,
                "request_json": {"seed": True},
                "notes": "initial",
                "requested_job_date": "2026-01-05",
                "requested_time_window": "AM",
                "customer_accepted_at": "2026-01-01T10:05:00-05:00",
                "admin_approved_at": None,
            }
        )

    def test_accept_then_decline_clears_customer_accepted_timestamp(self) -> None:
        request_id = "req-accept-decline"
        self._seed_quote_request(request_id)

        updated = storage.update_quote_request(
            request_id,
            status="customer_declined",
            customer_accepted_at=None,
            admin_approved_at=None,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "customer_declined")
        self.assertIsNone(updated["customer_accepted_at"])
        self.assertIsNone(updated["admin_approved_at"])

        persisted = storage.get_quote_request(request_id)
        self.assertIsNone(persisted["customer_accepted_at"])
        self.assertIsNone(persisted["admin_approved_at"])

    def test_approve_then_reject_clears_admin_approved_timestamp(self) -> None:
        request_id = "req-approve-reject"
        self._seed_quote_request(request_id)

        approved = storage.update_quote_request(
            request_id,
            status="admin_approved",
            admin_approved_at="2026-01-01T11:00:00-05:00",
        )
        self.assertIsNotNone(approved)
        self.assertEqual(approved["status"], "admin_approved")
        self.assertIsNotNone(approved["admin_approved_at"])

        rejected = storage.update_quote_request(
            request_id,
            status="rejected",
            admin_approved_at=None,
        )

        self.assertIsNotNone(rejected)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIsNone(rejected["admin_approved_at"])

        persisted = storage.get_quote_request(request_id)
        self.assertIsNone(persisted["admin_approved_at"])


if __name__ == "__main__":
    unittest.main()
