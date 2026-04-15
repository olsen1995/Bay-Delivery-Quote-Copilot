from __future__ import annotations

import datetime as dt
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

playwright = pytest.importorskip(
    "playwright.async_api",
    reason="Playwright is not installed. Install playwright to run launch smoke browser tests.",
)
pytest_asyncio = pytest.importorskip(
    "pytest_asyncio",
    reason="pytest-asyncio is required to run async Playwright smoke tests.",
)

Browser = playwright.Browser
Error = playwright.Error
Page = playwright.Page
expect = playwright.expect
async_playwright = playwright.async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
ADMIN_USERNAME = "launch-admin"
ADMIN_PASSWORD = "launch-password"
CUSTOMER_NAME = "Playwright Launch Smoke"


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
        except Exception as exc:  # pragma: no cover - startup timing guard
            last_error = exc
        time.sleep(0.2)

    raise AssertionError(f"Timed out waiting for {health_url} to become healthy: {last_error}")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    port = _free_port()
    db_dir = tmp_path_factory.mktemp("launch-smoke-playwright-db")
    db_path = db_dir / "bay_delivery_launch_smoke.sqlite3"
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
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    try:
        yield page
    finally:
        await page.close()
        await context.close()


def _next_booking_date() -> str:
    return (dt.date.today() + dt.timedelta(days=2)).isoformat()


@pytest.mark.asyncio
async def test_launch_happy_path_customer_quote_and_admin_visibility(page: Page, live_server: str) -> None:
    await page.goto(f"{live_server}/", wait_until="networkidle")
    await expect(page).to_have_url(re.compile(r".*/$"))
    await expect(page.locator("a[href='/quote']").first).to_be_visible()

    await page.locator("a[href='/quote']").first.click()
    await expect(page).to_have_url(re.compile(r".*/quote$"))
    await expect(page.locator("#quoteForm")).to_be_visible()

    await page.locator("#btnCalc").click()
    await expect(page.locator("#resultBox")).to_contain_text("Please fill in the required fields:")
    await expect(page.locator("#resultBox")).to_contain_text("Customer name")
    await expect(page.locator("#resultBox")).to_contain_text("Customer phone")
    await expect(page.locator("#resultBox")).to_contain_text("Job address")
    await expect(page.locator("#resultBox")).to_contain_text("Description")

    await page.locator("#customer_name").fill(CUSTOMER_NAME)
    await page.locator("#customer_phone").fill("705-555-0101")
    await page.locator("#job_address").fill("123 Smoke Test Rd, North Bay")
    await page.locator("#description").fill("Launch smoke validation for quote flow")
    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Your Estimate", timeout=20_000)
    await expect(page.locator("#resultBox")).to_contain_text("Quote ID:")
    await expect(page.locator("#decisionCard")).to_be_visible()

    await page.locator("#btnAccept").click()
    await expect(page.locator("#flowStatus")).to_contain_text("Decision saved successfully.", timeout=20_000)
    await expect(page.locator("#bookingCard")).to_be_visible()
    await expect(page.locator("#decisionCard")).to_be_hidden()

    await page.locator("#bookingDate").fill(_next_booking_date())
    await page.locator("#bookingWindow").select_option("morning")
    await page.locator("#bookingNotes").fill("Please call when on the way.")
    await page.locator("#btnSubmitBooking").click()

    await expect(page.locator("#bookingStatus")).to_contain_text("Booking submitted successfully.", timeout=20_000)
    booking_status_text = await page.locator("#bookingStatus").inner_text()
    request_match = re.search(r"Request ID:\s*([^\s]+)", booking_status_text)
    assert request_match, f"Expected Request ID in booking status text: {booking_status_text}"
    request_id = request_match.group(1)

    await page.goto(f"{live_server}/admin", wait_until="networkidle")
    await expect(page.locator("#adminUsername")).to_be_visible()
    await expect(page.locator("#adminPassword")).to_be_visible()


@pytest.mark.asyncio
async def test_launch_quote_route_missing_fields_are_named(page: Page, live_server: str) -> None:
    await page.goto(f"{live_server}/quote", wait_until="networkidle")
    await expect(page.locator("#quoteForm")).to_be_visible()

    await page.locator("#customer_name").fill(CUSTOMER_NAME)
    await page.locator("#customer_phone").fill("705-555-0101")
    await page.locator("#job_address").fill("123 Smoke Test Rd, North Bay")
    await page.locator("#description").fill("Route required field validation smoke")
    await page.locator("#service_type").select_option("small_move")
    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Please fill in the required fields:")
    await expect(page.locator("#resultBox")).to_contain_text("Pickup address")
    await expect(page.locator("#resultBox")).to_contain_text("Dropoff address")
    await expect(page.locator("#resultBox")).to_contain_text("Pickup and dropoff addresses are required for moves and deliveries")
    await expect(page.locator("#serviceDetailsPanel")).to_have_attribute("open", "")


@pytest.mark.asyncio
async def test_quote_estimate_breakdown_and_decline_path(page: Page, live_server: str) -> None:
    await page.goto(f"{live_server}/quote", wait_until="networkidle")
    await expect(page.locator("#quoteForm")).to_be_visible()

    await page.locator("#customer_name").fill("Playwright Decline Smoke")
    await page.locator("#customer_phone").fill("705-555-0112")
    await page.locator("#job_address").fill("456 Coverage Ave, North Bay")
    await page.locator("#description").fill("Verify estimate transparency details and decline flow")

    await page.locator("#serviceDetailsPanel summary").click()
    assert await page.locator("#serviceDetailsPanel").evaluate("node => node.open") is True

    await page.locator("#access_difficulty").select_option("difficult")
    await page.locator("#has_dense_materials").check()
    await page.locator("#garbage_bag_count").fill("8")

    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Pricing Breakdown", timeout=20_000)
    await expect(page.locator("#resultBox")).to_contain_text("What this estimate includes")
    await expect(page.locator("#resultBox")).to_contain_text("What happens next")
    await expect(page.locator("#resultBox")).to_contain_text("Estimate Details")
    await expect(page.locator("#resultBox")).to_contain_text("Estimate Confidence")
    await expect(page.locator("#resultBox")).to_contain_text("Difficult access")
    await expect(page.locator("#resultBox")).to_contain_text("Heavy or dense materials included")
    await expect(page.locator("#resultBox")).to_contain_text("Disposal included")
    await expect(page.locator("#resultBox")).to_contain_text("Next step: review this estimate, then choose Accept Estimate if you want to continue.")
    await expect(page.locator("#decisionCard")).to_be_visible()

    await page.locator("#btnDecline").click()

    await expect(page.locator("#decisionStatus")).to_contain_text("Decision saved successfully.", timeout=20_000)
    await expect(page.locator("#decisionStatus")).to_contain_text("You declined this estimate. No booking will be created.")
