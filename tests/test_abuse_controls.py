from fastapi.testclient import TestClient

from app.abuse_controls import RateLimitMiddleware
from app.main import app


BASE_PAYLOAD = {
    "customer_name": "Rate Tester",
    "customer_phone": "555-0100",
    "job_address": "123 Main St",
    "job_description_customer": "desc",
    "description": "desc",
    "service_type": "haul_away",
    "payment_method": "cash",
    "pickup_address": "1 Pickup Rd",
    "dropoff_address": "2 Dropoff Ave",
    "estimated_hours": 1.0,
    "crew_size": 1,
    "garbage_bag_count": 0,
    "mattresses_count": 0,
    "box_springs_count": 0,
    "scrap_pickup_location": "curbside",
    "travel_zone": "in_town",
}


def _clear_rate_limit_buckets(test_client: TestClient) -> None:
    current = test_client.app.middleware_stack
    while hasattr(current, "app"):
        if isinstance(current, RateLimitMiddleware):
            current.clear_buckets()
            return
        current = current.app


class TestRateLimits:
    def setup_method(self):
        self.client = TestClient(app)
        self.client.__enter__()
        _clear_rate_limit_buckets(self.client)

    def teardown_method(self):
        self.client.__exit__(None, None, None)

    def test_same_ip_exceeding_limit_returns_429(self):
        headers = {"x-forwarded-for": "203.0.113.10", "x-enable-rate-limit-tests": "1"}

        for _ in range(10):
            response = self.client.post("/quote/calculate", headers=headers, json=BASE_PAYLOAD)
            assert response.status_code == 200

        blocked = self.client.post("/quote/calculate", headers=headers, json=BASE_PAYLOAD)
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "rate limit exceeded"}

    def test_different_ip_has_separate_bucket(self):
        blocked_ip_headers = {"x-forwarded-for": "198.51.100.1", "x-enable-rate-limit-tests": "1"}
        other_ip_headers = {"x-forwarded-for": "198.51.100.2", "x-enable-rate-limit-tests": "1"}

        for _ in range(10):
            response = self.client.post("/quote/calculate", headers=blocked_ip_headers, json=BASE_PAYLOAD)
            assert response.status_code == 200

        blocked = self.client.post("/quote/calculate", headers=blocked_ip_headers, json=BASE_PAYLOAD)
        assert blocked.status_code == 429

        allowed = self.client.post("/quote/calculate", headers=other_ip_headers, json=BASE_PAYLOAD)
        assert allowed.status_code == 200
