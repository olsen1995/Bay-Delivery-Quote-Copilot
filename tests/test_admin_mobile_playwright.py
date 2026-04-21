from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import requests

playwright = pytest.importorskip(
    "playwright.async_api",
    reason="Playwright is not installed. Install playwright to run /admin/mobile browser tests.",
)
pytest_asyncio = pytest.importorskip(
    "pytest_asyncio",
    reason="pytest-asyncio is required to run async Playwright smoke tests.",
)

Browser = playwright.Browser
Error = playwright.Error
Page = playwright.Page
Route = playwright.Route
expect = playwright.expect
async_playwright = playwright.async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
ADMIN_USERNAME = "mobile-admin"
ADMIN_PASSWORD = "mobile-password"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    health_url = f"{base_url}/health"
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            response = requests.get(health_url, timeout=1.5)
            if response.status_code == 200:
                return
        except Exception as exc:  # pragma: no cover - only used when server boot is slow/flaky
            last_error = exc
        time.sleep(0.2)

    raise AssertionError(f"Timed out waiting for {health_url} to become healthy: {last_error}")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    port = _free_port()
    db_dir = tmp_path_factory.mktemp("admin-mobile-playwright-db")
    db_path = db_dir / "bay_delivery_playwright.sqlite3"
    env = os.environ.copy()
    env.update(
        {
            "ADMIN_USERNAME": ADMIN_USERNAME,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
            "BAYDELIVERY_DB_PATH": str(db_path),
        }
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{port}"

    try:
        _wait_for_server(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            process.kill()
            process.wait(timeout=5)


@pytest_asyncio.fixture()
async def browser() -> Browser:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
        except Error as exc:
            pytest.skip(f"Playwright browser is not available: {exc}")
        try:
            yield browser
        finally:
            await browser.close()


@pytest_asyncio.fixture()
async def page(browser: Browser) -> Page:
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    )
    page = await context.new_page()
    try:
        yield page
    finally:
        await page.close()
        await context.close()


async def _json_response(route: Route, payload: Any, status: int = 200) -> None:
    await route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


async def _install_mock_admin_api(page: Page) -> None:
    mock_state: dict[str, Any] = {
        "requests": [
            {
                "request_id": "req-mobile-1",
                "customer_name": "Morgan Request",
                "customer_phone": "555-0202",
                "job_address": "22 Queue St",
                "service_type": "haul_away",
                "status": "customer_pending",
                "requested_job_date": "2026-03-26",
                "requested_time_window": "afternoon",
                "notes": "Waiting for operator follow-up.",
            }
        ],
        "jobs": [
            {
                "job_id": "job-mobile-1",
                "customer_name": "Jordan Job",
                "job_address": "88 Schedule Ave",
                "service_type": "haul_away",
                "status": "scheduled",
                "scheduled_start": "2026-03-27T09:00:00",
                "calendar_sync_status": "synced",
                "calendar_last_error": "",
                "scheduling_context": {
                    "requested_job_date": "2026-03-27",
                    "requested_time_window": "morning",
                },
            }
        ],
    }

    async def handle_quotes(route: Route) -> None:
        await _json_response(route, {"items": []})

    async def handle_requests(route: Route) -> None:
        await _json_response(route, {"items": mock_state["requests"]})

    async def handle_jobs(route: Route) -> None:
        await _json_response(route, {"items": mock_state["jobs"]})

    await page.route("**/admin/api/quotes?limit=1", handle_quotes)
    await page.route("**/admin/api/quote-requests?limit=20", handle_requests)
    await page.route("**/admin/api/jobs?limit=20", handle_jobs)


async def _login(page: Page, base_url: str) -> None:
    await page.goto(f"{base_url}/admin/mobile", wait_until="networkidle")
    await page.locator("#mobileAdminUsername").fill(ADMIN_USERNAME)
    await page.locator("#mobileAdminPassword").fill(ADMIN_PASSWORD)
    await page.locator("#loginBtn").click()
    await expect(page.locator("#authenticatedShell")).to_be_visible(timeout=10_000)


@pytest.mark.asyncio
async def test_admin_mobile_mocked_ui_regression(page: Page, live_server: str) -> None:
    await _install_mock_admin_api(page)
    await _login(page, live_server)

    await expect(page.locator("#requestCount")).to_have_text("1")
    await expect(page.locator("#upcomingCount")).to_have_text("1")

    await page.locator("button[data-screen='requestsScreen']").click()
    await expect(page.locator("#requestsList")).to_contain_text("Morgan Request")
    await expect(page.locator("#requestsList")).to_contain_text("Waiting for operator follow-up.")

    await page.locator("button[data-screen='jobsScreen']").click()
    await expect(page.locator("#jobsList")).to_contain_text("Jordan Job")
    await expect(page.locator("#jobsList")).to_contain_text("synced")

    await page.locator("button[data-screen='homeScreen']").click()
    await expect(page.locator("#homeOpsSummary")).to_contain_text("Operations Overview")
    await expect(page.locator("#homeOpsSummary")).to_contain_text("No quote authoring")
    await expect(page.locator("#authenticatedShell")).not_to_contain_text("New Intake")
    await expect(page.locator("#authenticatedShell")).not_to_contain_text("Create Quote Draft")


@pytest.mark.asyncio
async def test_admin_mobile_prelogin_refresh_guard_blocks_protected_calls(page: Page, live_server: str) -> None:
    await _install_mock_admin_api(page)

    request_counts = {"quote_requests": 0, "jobs": 0}

    def track_request(request: Any) -> None:
        url = request.url
        if "/admin/api/quote-requests?limit=20" in url:
            request_counts["quote_requests"] += 1
        if "/admin/api/jobs?limit=20" in url:
            request_counts["jobs"] += 1

    page.on("request", track_request)

    await page.goto(f"{live_server}/admin/mobile", wait_until="networkidle")
    await expect(page.locator("#loginScreen")).to_be_visible()
    await expect(page.locator("#authenticatedShell")).not_to_be_visible()
    await expect(page.locator("nav.mobileNav")).not_to_be_visible()
    await expect(page.locator("#homeScreen")).not_to_be_visible()
    await page.evaluate(
        """
        async () => {
            if (typeof window.refreshAllData === "function") {
                await window.refreshAllData(document.getElementById("loginStatus"));
            }
        }
        """
    )
    await page.wait_for_timeout(300)

    assert request_counts["quote_requests"] == 0
    assert request_counts["jobs"] == 0
    await expect(page.locator("#loginStatus")).to_contain_text("Log in to refresh mobile admin data.")

    await page.locator("#mobileAdminUsername").fill(ADMIN_USERNAME)
    await page.locator("#mobileAdminPassword").fill(ADMIN_PASSWORD)
    await page.locator("#loginBtn").click()

    await expect(page.locator("#authenticatedShell")).to_be_visible(timeout=10_000)
    await expect(page.locator("#requestCount")).to_have_text("1")
    await expect(page.locator("#upcomingCount")).to_have_text("1")

    assert request_counts["quote_requests"] >= 1
    assert request_counts["jobs"] >= 1


@pytest.mark.asyncio
async def test_admin_mobile_real_backend_login_no_pageerror(page: Page, live_server: str) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    await _login(page, live_server)

    await expect(page.locator("#logoutBtn")).to_be_visible()
    await expect(page.locator("#homeScreen")).to_be_visible()
    await expect(page.locator("#requestCount")).to_be_visible()
    await expect(page.locator("#upcomingCount")).to_be_visible()
    await expect(page.locator("#authenticatedShell")).not_to_contain_text("New Intake")

    await page.wait_for_timeout(500)
    assert not page_errors, f"Unexpected pageerror/uncaught exception(s): {page_errors}"
