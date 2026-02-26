import tempfile
import unittest
from pathlib import Path

from app import storage


class QuoteRequestTransitionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmp.name) / "test.sqlite3"

        storage.DB_PATH = self._db_path
        storage.init_db()

        storage.save_quote_request(
            {
                "request_id": "req_1",
                "created_at": "2026-02-26T10:00:00",
                "status": "admin_approved",
                "quote_id": "quote_1",
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
                "requested_job_date": "2026-03-01",
                "requested_time_window": "AM",
                "customer_accepted_at": "2026-02-26T10:05:00",
                "admin_approved_at": "2026-02-26T10:10:00",
            }
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_approve_to_reject_clears_admin_approved_at(self) -> None:
        updated = storage.update_quote_request(
            "req_1",
            status="rejected",
            admin_approved_at=None,
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "rejected")
        self.assertIsNone(updated["admin_approved_at"])
        self.assertEqual(updated.get("notes"), "keep-me")

    def test_accept_to_decline_clears_customer_accepted_at(self) -> None:
        updated = storage.update_quote_request(
            "req_1",
            status="customer_declined",
            customer_accepted_at=None,
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "customer_declined")
        self.assertIsNone(updated["customer_accepted_at"])

    def test_unset_optional_fields_leave_existing_values(self) -> None:
        updated = storage.update_quote_request("req_1", status="admin_approved")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.get("requested_job_date"), "2026-03-01")
        self.assertEqual(updated.get("requested_time_window"), "AM")


if __name__ == "__main__":
    unittest.main()