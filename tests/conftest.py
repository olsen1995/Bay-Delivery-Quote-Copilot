import importlib.util

import pytest
from fastapi.testclient import TestClient

from app.abuse_controls import RateLimitMiddleware
from app.main import app

_PLAYWRIGHT_TEST_FILES = (
    "tests/test_launch_smoke_playwright.py",
    "tests/test_admin_mobile_playwright.py",
)


def _ensure_playwright_prerequisites() -> None:
    missing = []
    if importlib.util.find_spec("pytest_asyncio") is None:
        missing.append("pytest-asyncio")
    if importlib.util.find_spec("playwright.async_api") is None:
        missing.append("playwright")

    if missing:
        joined = ", ".join(missing)
        raise pytest.UsageError(
            "--require-playwright was set, but required dependencies are missing: "
            f"{joined}. Install with: pip install pytest-asyncio playwright"
        )

    from playwright.sync_api import Error, sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Error as exc:
        raise pytest.UsageError(
            "--require-playwright was set, but Chromium is not runnable for Playwright. "
            "Install browsers with: python -m playwright install chromium. "
            f"Original error: {exc}"
        )


def _clear_rate_limit_buckets() -> None:
    with TestClient(app) as client:
        current = client.app.middleware_stack
        while hasattr(current, "app"):
            if isinstance(current, RateLimitMiddleware):
                current.clear_buckets()
                return
            current = current.app


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--require-playwright",
        action="store_true",
        default=False,
        help=(
            "Fail loudly when Playwright browser-test prerequisites are missing. "
            "Use when local browser coverage is expected."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--require-playwright"):
        _ensure_playwright_prerequisites()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--require-playwright"):
        return

    has_playwright_items = any(
        any(test_file in item.nodeid for test_file in _PLAYWRIGHT_TEST_FILES) for item in items
    )
    if not has_playwright_items:
        raise pytest.UsageError(
            "--require-playwright was set, but no Playwright smoke tests were selected. "
            "Include tests/test_launch_smoke_playwright.py and tests/test_admin_mobile_playwright.py."
        )


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    _clear_rate_limit_buckets()
    yield
