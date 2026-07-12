import importlib.util
import importlib
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient


_REPO_ROOT = Path(__file__).resolve().parents[1]
_OPERATIONAL_DB_PATH = (_REPO_ROOT / "app/data/bay_delivery.sqlite3").resolve()
_PYTEST_DB_TEMP_DIR: tempfile.TemporaryDirectory | None = None


def _configure_pytest_database() -> None:
    global _PYTEST_DB_TEMP_DIR

    if "BAYDELIVERY_DB_PATH" in os.environ:
        configured_value = os.environ["BAYDELIVERY_DB_PATH"]
        if not configured_value:
            raise pytest.UsageError(
                "Pytest database isolation refused an empty BAYDELIVERY_DB_PATH because "
                "the application would fall back to app/data/bay_delivery.sqlite3."
            )
        selected_path = Path(configured_value).expanduser().resolve()
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="bay-delivery-pytest-db-")
        selected_path = (Path(temp_dir.name) / "pytest.sqlite3").resolve()
        if selected_path == _REPO_ROOT or _REPO_ROOT in selected_path.parents:
            temp_dir.cleanup()
            raise pytest.UsageError(
                "Pytest database isolation refused to create its temporary database "
                "inside the repository."
            )
        _PYTEST_DB_TEMP_DIR = temp_dir
        os.environ["BAYDELIVERY_DB_PATH"] = str(selected_path)

    if selected_path == _OPERATIONAL_DB_PATH:
        if _PYTEST_DB_TEMP_DIR is not None:
            _PYTEST_DB_TEMP_DIR.cleanup()
            _PYTEST_DB_TEMP_DIR = None
        raise pytest.UsageError(
            "Pytest database isolation refused the operational database path: "
            f"{_OPERATIONAL_DB_PATH}"
        )


_configure_pytest_database()

from app.abuse_controls import RateLimitMiddleware
from app import main as main_module
from app.main import app

_PLAYWRIGHT_TEST_FILES = (
    "tests/test_launch_smoke_playwright.py",
    "tests/test_admin_mobile_playwright.py",
)


def _ensure_playwright_prerequisites() -> None:
    missing = []
    if importlib.util.find_spec("pytest_asyncio") is None:
        missing.append("pytest-asyncio")
    try:
        importlib.import_module("playwright.async_api")
    except ModuleNotFoundError:
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
                break
            current = current.app
    main_module.clear_gpt_quote_rate_limit_state()


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

    missing_files = [
        test_file
        for test_file in _PLAYWRIGHT_TEST_FILES
        if not any(test_file in item.nodeid for item in items)
    ]
    if missing_files:
        missing_text = ", ".join(missing_files)
        raise pytest.UsageError(
            "--require-playwright was set, but both Playwright smoke test files are required. "
            "Missing selection for: "
            f"{missing_text}. Required files: tests/test_launch_smoke_playwright.py, "
            "tests/test_admin_mobile_playwright.py."
        )


def pytest_unconfigure(config: pytest.Config) -> None:
    global _PYTEST_DB_TEMP_DIR

    if _PYTEST_DB_TEMP_DIR is not None:
        _PYTEST_DB_TEMP_DIR.cleanup()
        _PYTEST_DB_TEMP_DIR = None


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    _clear_rate_limit_buckets()
    yield
