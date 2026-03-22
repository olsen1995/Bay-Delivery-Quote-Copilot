from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import requests

playwright = pytest.importorskip(
    "playwright.sync_api",
    reason="Playwright is not installed. Install playwright to run /admin/mobile browser tests.",
)

Browser = playwright.Browser
Error = playwright.Error
Page = playwright.Page
Route = playwright.Route
expect = playwright.expect
sync_playwright = playwright.sync_playwright

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
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    )
    page = context.new_page()
    yield page
    context.close()


def _json_response(route: Route, payload: Any, status: int = 200) -> None:
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


def _analysis_payload(*, analysis_id: str, message: str, quote_id: str | None = None) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "status": "draft",
        "quote_id": quote_id,
        "intake": {
            "message": message,
            "requested_job_date": "2026-03-25",
            "requested_time_window": "morning",
            "candidate_inputs": {
                "customer_name": "Taylor Example",
                "customer_phone": "555-0101",
                "description": "Mocked reviewed summary",
                "service_type": "haul_away",
                "job_address": "123 Example St",
                "estimated_hours": 1.5,
                "crew_size": 2,
            },
            "operator_overrides": {},
        },
        "attachments": [],
        "autofill_suggestions": {
            "customer_name": {"value": "Taylor Example"},
            "job_address": {"value": "123 Example St"},
        },
        "autofill_missing_fields": [],
        "autofill_warnings": [],
        "normalized_candidate": {
            "service_type": "haul_away",
        },
        "quote_guidance": {
            "service_type": "haul_away",
            "confidence": "medium",
            "source": "existing_quote_pricing_logic",
            "cash_total_cad": 150,
            "emt_total_cad": 169.5,
            "range": {
                "minimum_safe_cash_cad": 140,
                "recommended_target_cash_cad": 150,
                "upper_reasonable_cash_cad": 180,
            },
            "unknowns": ["final load volume"],
            "risk_notes": ["Operator should confirm driveway access."],
            "disclaimer": "Recommendation only. Review before creating a quote draft.",
        },
    }


def _install_mock_admin_api(page: Page) -> None:
    mock_state: dict[str, Any] = {
        "analyses": [],
        "analysis_by_id": {},
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
        "intake_call_count": 0,
    }

    def handle_quotes(route: Route) -> None:
        _json_response(route, {"items": []})

    def handle_analyses_list(route: Route) -> None:
        _json_response(route, {"items": mock_state["analyses"]})

    def handle_requests(route: Route) -> None:
        _json_response(route, {"items": mock_state["requests"]})

    def handle_jobs(route: Route) -> None:
        _json_response(route, {"items": mock_state["jobs"]})

    def handle_analysis_detail(route: Route) -> None:
        parsed = urlparse(route.request.url)
        path_parts = [part for part in parsed.path.split("/") if part]
        analysis_id = path_parts[-1] if path_parts else ""

        if (
            route.request.method != "GET"
            or len(path_parts) != 5
            or analysis_id in {"intake", "quote-draft"}
        ):
            route.fallback()
            return

        payload = mock_state["analysis_by_id"].get(analysis_id)
        if payload is None:
            _json_response(route, {"detail": "Not found"}, status=404)
            return
        _json_response(route, payload)

    def handle_intake(route: Route) -> None:
        mock_state["intake_call_count"] += 1
        post_data = route.request.post_data_json() or {}
        message = str(post_data.get("message") or "")

        if mock_state["intake_call_count"] == 2:
            time.sleep(0.6)
            stale_payload = _analysis_payload(
                analysis_id="analysis-stale-response",
                message=message or "Race draft should not win",
            )
            _json_response(route, stale_payload)
            return

        analysis = _analysis_payload(
            analysis_id="analysis-mocked-1",
            message=message or "Need help removing a loveseat and misc boxes.",
        )
        mock_state["analysis_by_id"][analysis["analysis_id"]] = analysis
        mock_state["analyses"] = [analysis]
        _json_response(route, analysis)

    def handle_quote_draft(route: Route) -> None:
        parsed = urlparse(route.request.url)
        path_parts = [part for part in parsed.path.split("/") if part]
        analysis_id = path_parts[-2]
        base_analysis = mock_state["analysis_by_id"].get(analysis_id) or _analysis_payload(
            analysis_id=analysis_id,
            message="Need help removing a loveseat and misc boxes.",
        )
        linked = {**base_analysis, "quote_id": "q-mobile-1"}
        mock_state["analysis_by_id"][analysis_id] = linked
        mock_state["analyses"] = [linked]
        _json_response(
            route,
            {
                "quote": {"quote_id": "q-mobile-1"},
                "analysis": linked,
            },
        )

    page.route("**/admin/api/quotes?limit=1", handle_quotes)
    page.route("**/admin/api/screenshot-assistant/analyses?limit=20", handle_analyses_list)
    page.route("**/admin/api/quote-requests?limit=20", handle_requests)
    page.route("**/admin/api/jobs?limit=20", handle_jobs)
    page.route("**/admin/api/screenshot-assistant/analyses/intake", handle_intake)
    page.route("**/admin/api/screenshot-assistant/analyses/*/quote-draft", handle_quote_draft)
    page.route("**/admin/api/screenshot-assistant/analyses/*", handle_analysis_detail)


def _login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/admin/mobile", wait_until="networkidle")
    page.locator("#mobileAdminUsername").fill(ADMIN_USERNAME)
    page.locator("#mobileAdminPassword").fill(ADMIN_PASSWORD)
    page.locator("#loginBtn").click()
    expect(page.locator("#authenticatedShell")).to_be_visible(timeout=10_000)


def test_admin_mobile_mocked_ui_regression(page: Page, live_server: str) -> None:
    _install_mock_admin_api(page)
    _login(page, live_server)

    expect(page.locator("#draftCount")).to_have_text("0")
    expect(page.locator("#requestCount")).to_have_text("1")
    expect(page.locator("#upcomingCount")).to_have_text("1")

    page.locator("button[data-screen='requestsScreen']").click()
    expect(page.locator("#requestsList")).to_contain_text("Morgan Request")
    expect(page.locator("#requestsList")).to_contain_text("Waiting for operator follow-up.")

    page.locator("button[data-screen='jobsScreen']").click()
    expect(page.locator("#jobsList")).to_contain_text("Jordan Job")
    expect(page.locator("#jobsList")).to_contain_text("synced")

    page.locator("button[data-screen='homeScreen']").click()
    page.locator("#homeNewIntakeBtn").click()

    expect(page.locator("#intakeScreen")).to_be_visible()
    expect(page.locator("#currentDraftMeta")).to_have_text("No draft selected yet.")
    expect(page.locator("#intakeMessage")).to_be_editable()
    expect(page.locator("#intakeDescription")).to_be_editable()

    sample_message = "Customer needs loveseat pickup plus a few loose boxes from the garage."
    page.locator("#intakeMessage").fill(sample_message)
    page.locator("#saveDraftBtn").click()

    expect(page.locator("#currentDraftMeta")).to_contain_text("analysis-mocked-1")
    expect(page.locator("#currentDraftMeta")).to_contain_text("Draft")
    expect(page.locator("#intakeDescription")).to_have_value("Mocked reviewed summary")
    expect(page.locator("#quoteGuidanceBox")).to_contain_text("existing_quote_pricing_logic")
    expect(page.locator("#handoffStatus")).to_contain_text("Create a quote draft before preparing customer handoff.")
    expect(page.locator("#createQuoteDraftBtn")).to_be_enabled()
    expect(page.locator("#prepareHandoffBtn")).to_be_disabled()

    page.locator("#createQuoteDraftBtn").click()
    expect(page.locator("#handoffStatus")).to_contain_text("Quote draft q-mobile-1 linked")
    expect(page.locator("#draftLockNotice")).to_be_visible()
    expect(page.locator("#saveDraftBtn")).to_be_disabled()
    expect(page.locator("#uploadScreenshotsBtn")).to_be_disabled()
    expect(page.locator("#createQuoteDraftBtn")).to_be_disabled()
    expect(page.locator("#prepareHandoffBtn")).to_be_enabled()

    page.locator("#newDraftBtn").click()
    expect(page.locator("#draftLockNotice")).to_be_hidden()
    expect(page.locator("#intakeStatus")).to_contain_text("Start a draft, paste the message, then save/analyze.")

    page.locator("#intakeMessage").fill("Race draft should not win")
    page.evaluate("() => document.getElementById('saveDraftBtn').click()")
    page.locator("#newDraftBtn").click()
    page.locator("#intakeMessage").fill("Fresh draft should remain")

    page.wait_for_timeout(900)

    expect(page.locator("#currentDraftMeta")).to_have_text("No draft selected yet.")
    expect(page.locator("#intakeMessage")).to_have_value("Fresh draft should remain")
    expect(page.locator("#intakeStatus")).to_contain_text("Start a draft, paste the message, then save/analyze.")


def test_admin_mobile_real_backend_login_no_pageerror(page: Page, live_server: str) -> None:
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    _login(page, live_server)

    expect(page.locator("#logoutBtn")).to_be_visible()
    expect(page.locator("#homeScreen")).to_be_visible()
    expect(page.locator("#draftCount")).to_be_visible()
    expect(page.locator("#requestCount")).to_be_visible()
    expect(page.locator("#upcomingCount")).to_be_visible()

    page.wait_for_timeout(500)
    assert not page_errors, f"Unexpected pageerror/uncaught exception(s): {page_errors}"
