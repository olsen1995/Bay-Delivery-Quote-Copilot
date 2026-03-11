from collections import deque
import os

from fastapi.testclient import TestClient

from app.abuse_controls import RateLimitMiddleware
from app import main as main_module
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
    middleware = _get_rate_limit_middleware(test_client)
    middleware.clear_buckets()


def _get_rate_limit_middleware(test_client: TestClient) -> RateLimitMiddleware:
    current = test_client.app.middleware_stack
    while hasattr(current, "app"):
        if isinstance(current, RateLimitMiddleware):
            return current
        current = current.app
    raise AssertionError("RateLimitMiddleware not found")


class TestRateLimits:
    def setup_method(self):
        # Enable X-Forwarded-For trust for rate limit tests that use it
        os.environ["BAYDELIVERY_TRUST_X_FORWARDED_FOR"] = "true"
        self.client = TestClient(app)
        self.client.__enter__()
        _clear_rate_limit_buckets(self.client)

    def teardown_method(self):
        self.client.__exit__(None, None, None)
        # Clean up the environment variable
        os.environ.pop("BAYDELIVERY_TRUST_X_FORWARDED_FOR", None)

    def test_same_ip_exceeding_limit_returns_429(self):
        headers = {"x-forwarded-for": "203.0.113.10"}

        for _ in range(10):
            response = self.client.post("/quote/calculate", headers=headers, json=BASE_PAYLOAD)
            assert response.status_code == 200

        blocked = self.client.post("/quote/calculate", headers=headers, json=BASE_PAYLOAD)
        assert blocked.status_code == 429
        assert blocked.json() == {"detail": "rate limit exceeded"}

    def test_different_ip_has_separate_bucket(self):
        blocked_ip_headers = {"x-forwarded-for": "198.51.100.1"}
        other_ip_headers = {"x-forwarded-for": "198.51.100.2"}

        for _ in range(10):
            response = self.client.post("/quote/calculate", headers=blocked_ip_headers, json=BASE_PAYLOAD)
            assert response.status_code == 200

        blocked = self.client.post("/quote/calculate", headers=blocked_ip_headers, json=BASE_PAYLOAD)
        assert blocked.status_code == 429

        allowed = self.client.post("/quote/calculate", headers=other_ip_headers, json=BASE_PAYLOAD)
        assert allowed.status_code == 200

    def test_empty_stale_rate_limit_bucket_is_evicted_and_recreated(self, monkeypatch):
        headers = {"x-forwarded-for": "203.0.113.44"}
        middleware = _get_rate_limit_middleware(self.client)
        now = 10_000.0
        key = (headers["x-forwarded-for"], "quote_calculate")
        stale_bucket = deque([now - 120.0])
        middleware._buckets[key] = stale_bucket

        monkeypatch.setattr("app.abuse_controls.time.time", lambda: now)

        response = self.client.post("/quote/calculate", headers=headers, json=BASE_PAYLOAD)

        assert response.status_code == 200
        assert key in middleware._buckets
        assert middleware._buckets[key] is not stale_bucket
        assert list(middleware._buckets[key]) == [now]


def test_admin_failed_attempt_bucket_removed_when_all_attempts_expire(monkeypatch):
    now = 10_000.0
    client_ip = "198.51.100.44"

    monkeypatch.setattr("app.main.time.time", lambda: now)

    main_module._admin_failed_attempts.clear()
    main_module._admin_failed_attempts[client_ip] = [now - (main_module._admin_lockout_window + 1)]

    assert main_module._check_admin_lockout(client_ip) is False
    assert client_ip not in main_module._admin_failed_attempts
