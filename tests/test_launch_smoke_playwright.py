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
    "playwright.sync_api",
    reason="Playwright is not installed. Install playwright to run launch smoke browser tests.",
)

Browser = playwright.Browser
Error = playwright.Error
Page = playwright.Page
expect = playwright.expect
sync_playwright = playwright.sync_playwright

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


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Error as exc:
            pytest.skip(f"Playwright browser is not available: {exc}")
        yield browser
        browser.close()


@pytest.fixture()
def page(browser: Browser) -> Page:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    yield page
    context.close()


def _next_booking_date() -> str:
    return (dt.date.today() + dt.timedelta(days=2)).isoformat()


def test_launch_happy_path_customer_quote_and_admin_visibility(page: Page, live_server: str) -> None:
    page.goto(f"{live_server}/", wait_until="networkidle")
    expect(page).to_have_url(re.compile(r".*/$"))
    expect(page.locator("a[href='/quote']").first).to_be_visible()

    page.locator("a[href='/quote']").first.click()
    expect(page).to_have_url(re.compile(r".*/quote$"))
    expect(page.locator("#quoteForm")).to_be_visible()

    page.locator("#btnCalc").click()
    expect(page.locator("#resultBox")).to_contain_text(
        "Please fill in all required fields (name, phone, address, and description)."
    )

    page.locator("#customer_name").fill(CUSTOMER_NAME)
    page.locator("#customer_phone").fill("705-555-0101")
    page.locator("#job_address").fill("123 Smoke Test Rd, North Bay")
    page.locator("#description").fill("Launch smoke validation for quote flow")
    page.locator("#btnCalc").click()

    expect(page.locator("#resultBox")).to_contain_text("Your Estimate", timeout=20_000)
    expect(page.locator("#resultBox")).to_contain_text("Quote ID:")
    expect(page.locator("#decisionCard")).to_be_visible()

    page.locator("#btnAccept").click()
    expect(page.locator("#flowStatus")).to_contain_text("Decision saved successfully.", timeout=20_000)
    expect(page.locator("#bookingCard")).to_be_visible()

    page.locator("#bookingDate").fill(_next_booking_date())
    page.locator("#bookingWindow").select_option("morning")
    page.locator("#bookingNotes").fill("Please call when on the way.")
    page.locator("#btnSubmitBooking").click()

    expect(page.locator("#bookingStatus")).to_contain_text("Booking submitted successfully.", timeout=20_000)
    booking_status_text = page.locator("#bookingStatus").inner_text()
    request_match = re.search(r"Request ID:\s*([^\s]+)", booking_status_text)
    assert request_match, f"Expected Request ID in booking status text: {booking_status_text}"
    request_id = request_match.group(1)

    page.goto(f"{live_server}/admin", wait_until="networkidle")
    expect(page.locator("#adminUsername")).to_be_visible()
    expect(page.locator("#adminPassword")).to_be_visible()
    expect(page.locator("#refreshBtn")).to_be_visible()

    page.locator("#adminUsername").fill(ADMIN_USERNAME)
    page.locator("#adminPassword").fill(ADMIN_PASSWORD)
    page.locator("#refreshBtn").click()

    expect(page.locator("#adminProtectedDashboard")).to_be_visible(timeout=20_000)
    expect(page.locator("#requestsBox table")).to_be_visible(timeout=20_000)
    expect(page.locator("#requestsBox")).to_contain_text(CUSTOMER_NAME)
    expect(page.locator("#requestsBox")).to_contain_text(request_id)
