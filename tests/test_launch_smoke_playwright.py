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
    await expect(page.locator("#serviceDetailsPanel")).not_to_have_attribute("open", "")
    await page.locator("#serviceDetailsSummary").click()
    await page.locator("#trailer_fill_estimate").select_option("under_quarter")
    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Your Estimate", timeout=20_000)
    await expect(page.locator("#resultBox")).to_contain_text("Quote ID:")
    await expect(page.locator("#decisionCard")).to_be_visible()

    await page.locator("#btnAccept").click()
    await expect(page.locator("#flowStatus")).to_contain_text("Decision saved successfully.", timeout=20_000)
    await expect(page.locator("#flowStatus")).to_contain_text("Please share your booking preferences below")
    await expect(page.locator("#flowStatus")).to_contain_text("The job is not booked yet")
    await expect(page.locator("#flowStatus")).to_contain_text("The job is not booked yet.")
    await expect(page.locator("#bookingCard")).to_be_visible()
    await expect(page.locator("#decisionCard")).to_be_hidden()

    await page.locator("#bookingDate").fill(_next_booking_date())
    await page.locator("#bookingWindow").select_option("morning")
    await page.locator("#bookingNotes").fill("Please call when on the way.")
    await page.locator("#btnSubmitBooking").click()

    await expect(page.locator("#bookingStatus")).to_contain_text("Your preferred timing has been sent to Bay Delivery", timeout=20_000)
    await expect(page.locator("#bookingStatus")).to_contain_text("We will follow up to confirm the final schedule")
    booking_status_text = await page.locator("#bookingStatus").inner_text()
    request_match = re.search(r"Request ID:\s*([^\s]+)", booking_status_text)
    assert request_match, f"Expected Request ID in booking status text: {booking_status_text}"
    request_id = request_match.group(1)

    await page.goto(f"{live_server}/admin", wait_until="networkidle")
    await expect(page.locator("#adminUsername")).to_be_visible()
    await expect(page.locator("#adminPassword")).to_be_visible()
    await expect(page.locator("#adminProtectedDashboard")).not_to_be_visible()
    await expect(page.get_by_role("heading", name="Admin Dashboard")).not_to_be_visible()
    await expect(page.get_by_role("heading", name="Recent Estimates")).not_to_be_visible()
    await expect(page.get_by_role("heading", name="Booking Requests")).not_to_be_visible()
    await expect(page.get_by_role("heading", name="Admin Audit Log")).not_to_be_visible()
    await expect(page.get_by_role("heading", name="Jobs")).not_to_be_visible()


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
    await expect(page.locator("#serviceDetailsPanel")).to_be_visible()

    await page.locator("#customer_name").fill("Playwright Decline Smoke")
    await page.locator("#customer_phone").fill("705-555-0112")
    await page.locator("#job_address").fill("456 Coverage Ave, North Bay")
    await page.locator("#description").fill("Verify estimate transparency details and decline flow")

    await expect(page.locator("#serviceDetailsPanel")).not_to_have_attribute("open", "")
    assert await page.locator("#serviceDetailsPanel").evaluate("node => node.open") is False

    await page.locator("#serviceDetailsSummary").click()
    await expect(page.locator("#loadCountRow")).to_be_visible()
    await expect(page.locator("#denseMaterialsGroup")).to_be_visible()
    await page.locator("#access_difficulty").select_option("difficult")
    await page.locator("#has_dense_materials").check()
    await page.locator("#garbage_bag_count").fill("3")
    await expect(page.locator("#bagCountNudge")).to_be_visible()
    await page.locator("#garbage_bag_count").fill("8")
    await expect(page.locator("#bagCountNudge")).to_be_hidden()

    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Pricing Breakdown", timeout=20_000)
    await expect(page.locator("#resultBox")).to_contain_text("What this estimate includes")
    await expect(page.locator("#resultBox")).to_contain_text("What happens next")
    await expect(page.locator("#resultBox")).to_contain_text("Estimate Details")
    await expect(page.locator("#resultBox")).to_contain_text("About this estimate")
    await expect(page.locator("#resultBox")).to_contain_text("Apartment/stairs/basement or longer carry")
    await expect(page.locator("#resultBox")).to_contain_text("Heavy materials included")
    await expect(page.locator("#resultBox")).to_contain_text("Disposal included")
    await expect(page.locator("#resultBox")).to_contain_text("Next step: decide whether this estimate works for you. Accept Estimate & Continue opens the booking request form.")
    await expect(page.locator("#resultBox")).to_contain_text("Bay Delivery confirms details before anything is booked.")
    await expect(page.locator("#decisionCard")).to_be_visible()
    await expect(page.locator("#uploadCard")).to_be_hidden()

    await page.locator("#btnDecline").click()

    await expect(page.locator("#decisionStatus")).to_contain_text("Decision saved successfully.", timeout=20_000)
    await expect(page.locator("#decisionStatus")).to_contain_text("You declined this estimate. No booking request will be created.")


@pytest.mark.asyncio
async def test_haul_away_requires_structured_load_detail(page: Page, live_server: str) -> None:
    await page.goto(f"{live_server}/quote", wait_until="networkidle")
    await expect(page.locator("#quoteForm")).to_be_visible()

    await page.locator("#customer_name").fill("Playwright Vague Scope")
    await page.locator("#customer_phone").fill("705-555-0113")
    await page.locator("#job_address").fill("789 Scope Ave, North Bay")
    await page.locator("#description").fill("Need help with some stuff.")
    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Please add at least one load detail so we can quote your junk removal.")
    await expect(page.locator("#resultBox")).to_contain_text("Examples: bags, trailer space used, mattresses, box springs, or heavy materials.")
    await expect(page.locator("#serviceDetailsPanel")).to_have_attribute("open", "")

    await page.locator("#trailer_fill_estimate").select_option("under_quarter")
    await page.locator("#btnCalc").click()

    await expect(page.locator("#resultBox")).to_contain_text("Pricing Breakdown", timeout=20_000)
    await expect(page.locator("#resultBox")).to_contain_text("Estimated junk load (Under 1/4 trailer)")
    await expect(page.locator("#resultBox")).not_to_contain_text("Estimated junk load (0 bags)")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/", "/quote"])
async def test_public_shell_skip_link_focus(page: Page, live_server: str, route: str) -> None:
    await page.goto(f"{live_server}{route}", wait_until="networkidle")
    skip_link = page.locator(".bd-skip-link")
    await page.keyboard.press("Tab")
    await expect(skip_link).to_be_focused()
    await expect(skip_link).to_have_attribute("href", "#main-content")
    await skip_link.click()
    await expect(page.locator("#main-content")).to_be_focused()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/", "/quote"])
async def test_public_shell_desktop_navigation(page: Page, live_server: str, route: str) -> None:
    await page.set_viewport_size({"width": 1280, "height": 900})
    await page.goto(f"{live_server}{route}", wait_until="networkidle")

    await expect(page.locator(".bd-public-header")).to_be_visible()
    await expect(page.locator(".bd-public-logo")).to_be_visible()
    await expect(page.get_by_role("navigation", name="Primary navigation")).to_be_visible()
    await expect(page.get_by_role("navigation", name="Mobile navigation")).to_be_hidden()
    await expect(page.locator("#publicMenuToggle")).to_be_hidden()
    await expect(page.locator('.bd-public-phone[href="tel:+17053034409"]')).to_be_visible()
    await expect(page.locator('.bd-public-cta[href="/quote"]')).to_be_visible()
    await page.locator(".bd-public-footer").scroll_into_view_if_needed()
    await expect(page.locator(".bd-public-footer")).to_be_visible()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/", "/quote"])
async def test_public_shell_mobile_menu_aria_and_escape(page: Page, live_server: str, route: str) -> None:
    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(f"{live_server}{route}", wait_until="networkidle")

    menu_toggle = page.locator("#publicMenuToggle")
    mobile_nav = page.locator("#publicMobileNav")
    await expect(menu_toggle).to_be_visible()
    await expect(menu_toggle).to_have_attribute("aria-expanded", "false")
    await expect(menu_toggle).to_have_attribute("aria-label", "Open navigation menu")
    await expect(mobile_nav).to_have_attribute("data-state", "closed")
    await expect(mobile_nav).to_have_attribute("hidden", "")

    await menu_toggle.click()
    await expect(menu_toggle).to_have_attribute("aria-expanded", "true")
    await expect(menu_toggle).to_have_attribute("aria-label", "Close navigation menu")
    await expect(mobile_nav).to_have_attribute("data-state", "open")
    await expect(mobile_nav).not_to_have_attribute("hidden", "")
    await expect(mobile_nav.locator("a").first).to_be_visible()

    await page.keyboard.press("Escape")
    await expect(menu_toggle).to_have_attribute("aria-expanded", "false")
    await expect(menu_toggle).to_have_attribute("aria-label", "Open navigation menu")
    await expect(mobile_nav).to_have_attribute("data-state", "closed")
    await expect(mobile_nav).to_have_attribute("hidden", "")
    await expect(menu_toggle).to_be_focused()


@pytest.mark.asyncio
async def test_public_shell_mobile_link_focus_is_safe_before_hiding(page: Page, live_server: str) -> None:
    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(f"{live_server}/", wait_until="networkidle")
    await page.locator("#publicMenuToggle").click()
    await page.evaluate(
        """() => {
          const nav = document.querySelector('#publicMobileNav');
          window.__focusWasOutsideMenuBeforeHide = false;
          new MutationObserver(() => {
            if (nav.hidden) {
              window.__focusWasOutsideMenuBeforeHide = !nav.contains(document.activeElement);
            }
          }).observe(nav, { attributes: true, attributeFilter: ['hidden'] });
        }"""
    )
    services_link = page.locator('#publicMobileNav a[href="/#servicesTitle"]')
    await services_link.focus()
    await page.keyboard.press("Enter")
    await expect(page).to_have_url(re.compile(r".*/#servicesTitle$"))
    assert await page.evaluate("window.__focusWasOutsideMenuBeforeHide") is True
    await expect(page.locator("#publicMobileNav")).to_have_attribute("hidden", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("focus_target", ["trigger", "link"])
async def test_public_shell_desktop_transition_moves_mobile_focus_to_logo(
    page: Page,
    live_server: str,
    focus_target: str,
) -> None:
    await page.set_viewport_size({"width": 1024, "height": 800})
    await page.goto(f"{live_server}/", wait_until="networkidle")
    menu_toggle = page.locator("#publicMenuToggle")
    await menu_toggle.click()
    if focus_target == "trigger":
        await menu_toggle.focus()
    else:
        await page.locator("#publicMobileNav a").first.focus()

    await page.set_viewport_size({"width": 1180, "height": 800})
    await expect(page.locator(".bd-public-logo")).to_be_focused()
    await expect(page.locator("#publicMobileNav")).to_have_attribute("hidden", "")
    await expect(menu_toggle).to_be_hidden()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/", "/quote"])
async def test_public_shell_no_javascript_mobile_navigation(
    browser: Browser,
    live_server: str,
    route: str,
) -> None:
    context = await browser.new_context(
        java_script_enabled=False,
        viewport={"width": 390, "height": 844},
    )
    try:
        expected_hrefs = [
            "/",
            "/#servicesTitle",
            "/#howTitle",
            "/#trustFaqTitle",
            "/#workTitle",
            "/quote",
        ]
        for href in expected_hrefs:
            no_js_page = await context.new_page()
            await no_js_page.goto(f"{live_server}{route}", wait_until="networkidle")
            await expect(no_js_page.get_by_role("navigation", name="Primary navigation")).to_be_hidden()
            await expect(no_js_page.get_by_role("navigation", name="Mobile navigation")).to_be_visible()
            await expect(no_js_page.locator("#publicMenuToggle")).to_be_hidden()
            link = no_js_page.locator(f'#publicMobileNav a[href="{href}"]')
            await expect(link).to_be_visible()
            await link.click()
            if href.startswith("/#"):
                await expect(no_js_page).to_have_url(re.compile(rf".*/{re.escape(href[1:])}$"))
            elif href == "/quote":
                await expect(no_js_page).to_have_url(re.compile(r".*/quote$"))
            else:
                await expect(no_js_page).to_have_url(re.compile(r".*/$"))
            await no_js_page.close()
    finally:
        await context.close()


@pytest.mark.asyncio
async def test_public_shell_responsive_layouts_have_no_overflow(page: Page, live_server: str) -> None:
    for width in [320, 360, 390, 430, 640, 641, 768, 1024, 1179, 1180, 1280, 1440, 1680]:
        for route in ["/", "/quote"]:
            await page.set_viewport_size({"width": width, "height": 900})
            await page.goto(f"{live_server}{route}", wait_until="networkidle")
            overflow = await page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            assert overflow <= 1, f"Horizontal overflow at {width}px on {route}: {overflow}px"

            if width <= 640:
                logo_top = await page.locator(".bd-public-logo").evaluate("node => node.offsetTop")
                toggle_top = await page.locator("#publicMenuToggle").evaluate("node => node.offsetTop")
                phone_top = await page.locator(".bd-public-phone").evaluate("node => node.offsetTop")
                cta_top = await page.locator(".bd-public-cta").evaluate("node => node.offsetTop")
                assert abs(logo_top - toggle_top) <= 4
                assert abs(phone_top - cta_top) <= 4
                assert phone_top > logo_top


@pytest.mark.asyncio
@pytest.mark.parametrize("width", [390, 1280])
async def test_public_shell_anchor_offsets_clear_sticky_header(
    page: Page,
    live_server: str,
    width: int,
) -> None:
    await page.set_viewport_size({"width": width, "height": 900})
    await page.goto(f"{live_server}/", wait_until="networkidle")
    if width < 1180:
        await page.locator("#publicMenuToggle").click()
        await page.locator('#publicMobileNav a[href="/#servicesTitle"]').click()
    else:
        await page.locator('.bd-public-nav--desktop a[href="/#servicesTitle"]').click()
    await expect(page).to_have_url(re.compile(r".*/#servicesTitle$"))
    target_top = await page.locator("#servicesTitle").evaluate(
        "node => node.getBoundingClientRect().top"
    )
    header_bottom = await page.locator(".bd-public-header").evaluate(
        "node => node.getBoundingClientRect().bottom"
    )
    assert target_top >= header_bottom - 1
    assert target_top < 900
