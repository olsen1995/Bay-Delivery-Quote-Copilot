import pytest
from fastapi.testclient import TestClient

from app.abuse_controls import RateLimitMiddleware
from app.main import app


def _clear_rate_limit_buckets() -> None:
    with TestClient(app) as client:
        current = client.app.middleware_stack
        while hasattr(current, "app"):
            if isinstance(current, RateLimitMiddleware):
                current.clear_buckets()
                return
            current = current.app


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    _clear_rate_limit_buckets()
    yield
