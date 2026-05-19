import re
from pathlib import Path


def test_homepage_images_exist():
    """Validate that all images referenced in the homepage HTML exist on disk."""
    index_path = Path("static/index.html")
    content = index_path.read_text(encoding='utf-8')

    # Find all img src paths under /static/images/
    matches = re.findall(r'src="/static/images/([^"]+)"', content)

    for img in matches:
        img_path = Path("static/images") / img
        assert img_path.exists(), f"Referenced image {img} does not exist"

def test_homepage_logo_and_primary_cta_are_present() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    assert 'src="/static/images/logo.jpg"' in index_html
    assert 'alt="Bay Delivery"' in index_html
    assert 'href="/quote">Get My Fast Estimate<' in index_html

def test_static_pages_reference_shared_favicon() -> None:
    """Ensure routed HTML pages avoid browser fallback requests for /favicon.ico."""
    favicon_path = Path("static/favicon.svg")
    assert favicon_path.exists()
    assert favicon_path.stat().st_size < 2048

    favicon_link = '<link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />'
    for html_path in [
        Path("static/index.html"),
        Path("static/quote.html"),
        Path("static/admin.html"),
        Path("static/admin_mobile.html"),
        Path("static/admin_uploads.html"),
    ]:
        content = html_path.read_text(encoding="utf-8")
        assert favicon_link in content, f"{html_path} is missing the shared favicon link"
        assert "/favicon.ico" not in content


def test_quote_page_uses_external_script_for_csp():
    """Ensure quote page JS executes under CSP by avoiding inline script blocks."""
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert '<script src="/static/quote.js" defer></script>' in quote_html
    assert "<script>" not in quote_html


def test_quote_upload_formdata_includes_accept_token() -> None:
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")

    assert 'formData.append("quote_id", lastQuoteId);' in quote_js
    assert 'formData.append("accept_token", lastAcceptToken);' in quote_js


def test_quote_page_supports_persisted_review_mode() -> None:
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")

    for helper_name in [
        "persistedReviewFields",
        "setPersistedReviewMode",
        "populateQuoteFormFromRequest",
        "showPersistedQuoteReview",
        "loadPersistedQuoteReview",
    ]:
        assert quote_js.count(f"function {helper_name}(") == 1

    assert "let persistedReviewMode = false;" in quote_js
    assert "persistedReviewHelperText" in quote_js
    assert "setPersistedReviewMode(true);" in quote_js
    assert "function syncQuoteCalculateActionState()" in quote_js
    assert "calcBtn.disabled = persistedReviewMode || quoteCalculationInFlight;" in quote_js
    assert 'if (clearBtn) clearBtn.disabled = persistedReviewMode;' in quote_js
    assert 'if (persistedReviewMode) {' in quote_js
    assert 'showBox("flowStatus", persistedReviewHelperText, "info");' in quote_js
    assert "new URLSearchParams(window.location.search)" in quote_js
    assert "new URLSearchParams((window.location.hash || \"\").replace(/^#/, \"\"))" in quote_js
    assert 'params.get("quote_id")' in quote_js
    assert 'hashParams.get("accept_token")' in quote_js
    assert 'Authorization: `Bearer ${acceptToken}`' in quote_js
    assert '/view?accept_token=' not in quote_js
    assert 'loadPersistedQuoteReview();' in quote_js
    assert 'showPersistedQuoteReview' in quote_js
    assert 'data.booking_submitted' in quote_js
    assert 'revealCard("uploadCard", true);' in quote_js
    assert "You are reviewing a saved estimate prepared for you. Review the pricing and request details here, and contact Bay Delivery if anything needs to be updated." in quote_js
    assert 'const res = await fetch("/quote/calculate"' in quote_js


def test_quote_page_guards_duplicate_calculation_submits() -> None:
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")

    guard_check = "if (quoteCalculationInFlight) return;"
    guard_set = "quoteCalculationInFlight = true;"
    fetch_call = 'const res = await fetch("/quote/calculate"'
    cleanup_reset = "quoteCalculationInFlight = false;"
    calc_handler = 'el("btnCalc").addEventListener("click", async () => {'
    calc_handler_start = quote_js.index(calc_handler)
    finally_start = quote_js.index("} finally {", calc_handler_start)

    assert "let quoteCalculationInFlight = false;" in quote_js
    assert "function syncQuoteCalculateActionState()" in quote_js
    assert "calcBtn.disabled = persistedReviewMode || quoteCalculationInFlight;" in quote_js
    assert guard_check in quote_js
    assert guard_set in quote_js
    assert cleanup_reset in quote_js
    assert quote_js.index(guard_check, calc_handler_start) < quote_js.index('hideBox("resultBox");', calc_handler_start)
    assert quote_js.index(guard_set) < quote_js.index(fetch_call)
    assert quote_js.index(cleanup_reset, finally_start) > finally_start


def test_quote_failure_copy_includes_manual_contact_fallback() -> None:
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")

    assert "function manualQuoteFallbackMessage(reason)" in quote_js
    assert "call or text Dan at (705) 303-4409" in quote_js
    assert "BayDeliveryNB@gmail.com" in quote_js
    assert "Bay Delivery can review the job manually." in quote_js
    assert 'manualQuoteFallbackMessage("Request timed out. Please try again in a moment.")' in quote_js
    assert 'manualQuoteFallbackMessage("Failed to contact server.")' in quote_js


def test_homepage_includes_service_area_trust_faq_copy() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")

    assert 'class="trustFaqSection"' in index_html
    assert "Service Area &amp; Estimate Notes" in index_html
    assert "Bay Delivery serves North Bay and surrounding areas" in index_html
    for area_name in ["Callander", "Powassan", "Bonfield", "Astorville", "Corbeil", "Sturgeon Falls"]:
        assert area_name in index_html
    assert "Out-of-town jobs may include additional travel cost." in index_html
    assert "Photos are optional but helpful." in index_html
    assert "Pricing may be confirmed or adjusted if job details differ" in index_html
    assert "Cash has no HST." in index_html
    assert "EMT/e-transfer includes 13% HST" in index_html
    assert "Submitting a booking request does not confirm the job." in index_html
    assert "Bay Delivery follows up before the booking is locked in." in index_html
    assert ".trustFaqSection" in site_css
    assert ".trustFaqGrid" in site_css


def test_sticky_mobile_call_is_hidden_by_default_and_mobile_only() -> None:
    site_css = Path("static/site.css").read_text(encoding="utf-8")

    base_match = re.search(r"\.stickyMobileCall\{(?P<body>.*?)\n\}", site_css, re.DOTALL)
    assert base_match is not None
    base_body = base_match.group("body")
    assert "display: none;" in base_body
    assert "display: flex;" not in base_body
    mobile_match = re.search(
        r"@media \(max-width: 720px\)\{(?P<body>.*?\.stickyMobileCall\{(?P<call_body>.*?)\n  \}.*?)\n\}",
        site_css,
        re.DOTALL,
    )
    assert mobile_match is not None
    mobile_call_body = mobile_match.group("call_body")
    assert "display: flex;" in mobile_call_body
    assert "bottom: calc(18px + env(safe-area-inset-bottom));" in mobile_call_body


def test_quote_page_phase_a_guidance_copy_is_present() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "Start with a simple estimate." in quote_html
    assert "Quick answers now. Bay Delivery confirms final booking details" in quote_html
    assert 'id="serviceDetailsSummary"' in quote_html
    assert 'id="serviceDetailsLead"' in quote_html
    assert 'id="serviceDetailsPanel" class="detailPanel" open' in quote_html
    assert "Answer what you can. Not sure is okay." in quote_html
    assert "Tell us what needs to be moved, removed, delivered, or cleaned up." in quote_html
    assert "Where is it located?" in quote_html
    assert "Any special or heavy items?" in quote_html
    assert "Required for moves and deliveries." in quote_html
    assert "Use full kitchen-size bags as a rough count." in quote_html
    assert "Most jobs are 5-10 bags. Adjust if needed." in quote_html
    assert "Heavy items help Bay Delivery bring the right setup." in quote_html
    assert "Choose the closest match. Add a note if you are not sure." in quote_html
    assert "Photos help us confirm scope faster." in quote_html
    assert "After you submit your booking request, add photos here if they help Bay Delivery confirm scope." in quote_html
    assert "After you see your estimate, you can accept and share your preferred day and time window." in quote_html
    assert "How did you hear about us? (optional)" in quote_html
    for control_id in [
        "service_type",
        "description",
        "customer_name",
        "customer_phone",
        "job_address",
        "lead_source",
    ]:
        assert f'id="{control_id}"' in quote_html
    assert '<button class="btn" id="btnCalc" type="button">See My Estimate</button>' in quote_html
    assert '<button class="btn secondary" id="btnClear" type="button">Clear</button>' in quote_html
    assert re.search(r'<select(?=[^>]*\bid="lead_source")(?=[^>]*\bname="lead_source")[^>]*>', quote_html)
    for option_value in ["facebook", "google", "referral", "marketplace", "repeat_customer", "other"]:
        assert re.search(rf'<option[^>]*\bvalue="{re.escape(option_value)}"[^>]*>', quote_html)
    assert "lead_source: leadSource || \"unknown\"" in quote_js
    assert "Booking requests and optional photos come after acceptance." not in quote_html
    assert "Optional photos come after that." not in quote_html
    assert "Service type" not in quote_html
    assert "Estimated time on site" not in quote_html
    assert "Crew size" not in quote_html
    assert "Construction debris (if any)" not in quote_html
    assert "Heavy material type (if any)" not in quote_html
    assert "Trailer space used" not in quote_html
    assert "Step 1 of 4" not in quote_html
    assert "Step 2 of 4" not in quote_html
    assert "Step 3 of 4" not in quote_html
    assert "Step 4 of 4" not in quote_html
    assert "friendlyQuoteErrorMessage" in quote_js
    assert "syncBagCountNudge" in quote_js
    assert "What this estimate includes" in quote_js
    assert "What happens next" in quote_js
    assert "About this estimate" in quote_js
    assert "Photos are optional after your booking request if they help Bay Delivery confirm scope." in quote_js
    assert "Accept Estimate & Continue" in quote_js
    assert "The job is not booked yet." in quote_js
    assert "customerFlowGroup" in quote_css
    assert "customerFlowLabel" in quote_css
    assert "quoteResultIncluded" in quote_css
    assert "quoteInfoCard" in quote_css


def test_quote_page_mobile_polish_preserves_one_form_flow() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "@media (max-width: 720px)" in quote_css
    assert ".progressCard" in quote_css
    assert "overflow-x: auto;" in quote_css
    assert "scroll-snap-type: x proximity;" in quote_css
    assert "#quoteForm > .btnRow" in quote_css
    assert "position: sticky;" in quote_css
    assert "env(safe-area-inset-bottom)" in quote_css
    assert ".detailPanel" in quote_css
    assert ".customerFlowGroup" in quote_css

    assert quote_html.count('<form id="quoteForm" class="formWrap" novalidate>') == 1
    assert quote_html.count('id="btnCalc"') == 1
    assert quote_html.count('id="btnClear"') == 1
    assert ">See My Estimate<" in quote_html
    assert ">Clear<" in quote_html

    forbidden_step_machine_markers = [
        "btnNext",
        "btnBack",
        "quoteStepIndex",
        "currentQuoteStep",
        "goToStep",
        "nextStepButton",
        "backStepButton",
    ]
    for marker in forbidden_step_machine_markers:
        assert marker not in quote_html
        assert marker not in quote_js

    assert not re.search(r"<button[^>]*>\s*Next\s*</button>", quote_html, re.IGNORECASE)
    assert not re.search(r"<button[^>]*>\s*Back\s*</button>", quote_html, re.IGNORECASE)


def test_launch_mobile_quote_polish_copy_and_overflow_guards() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")

    assert "2-5. Job details" not in quote_html
    assert '<p class="customerFlowLabel">Step ' not in quote_html
    for label in ["Load details", "Access details", "Special items", "Photo guidance"]:
        assert f'<p class="customerFlowLabel">{label}</p>' in quote_html

    assert "admin dashboard" not in index_html.lower()
    assert "Bay Delivery confirms before scheduling." in index_html

    mobile_quote_css = quote_css[quote_css.index("@media (max-width: 720px)") :]
    assert "overflow-x: hidden;" in mobile_quote_css
    assert re.search(r"\.quotePage \.container > \*\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)
    assert re.search(r"\.quoteTrustStrip\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)
    assert re.search(r"\.quoteTrustStrip\s*\{[^}]*overflow-x:\s*auto;", mobile_quote_css, re.S)
    assert re.search(r"\.flowProgress\s*\{[^}]*max-width:\s*100%;", mobile_quote_css, re.S)
    assert re.search(r"\.flowStep\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)

    mobile_site_css = site_css[site_css.index("@media (max-width: 720px)") :]
    assert re.search(r"\.container\s*\{[^}]*padding-bottom:\s*96px;", mobile_site_css, re.S)
    assert re.search(r"\.hero \.heroCard:first-child\s*\{[^}]*padding-bottom:\s*88px;", mobile_site_css, re.S)
    assert re.search(r"\.stickyMobileCall\s*\{[^}]*bottom:\s*calc\(18px \+ env\(safe-area-inset-bottom\)\);", mobile_site_css, re.S)


def test_quote_visible_customer_copy_avoids_internal_jargon() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8").lower()
    quote_js = Path("static/quote.js").read_text(encoding="utf-8").lower()
    quote_css = Path("static/quote.css").read_text(encoding="utf-8").lower()

    banned_phrases = [
        "internal risk summary",
        "manual review required",
        "disposal risk",
        "dense material classification",
        "recommended trailer",
        "labour underpriced",
        "operating-cost target gap",
        "owner review",
        "internal risk",
        "margin",
        "profit",
        "pricing caution",
        "quote risk advisory",
        "internal_risk_assessment",
        "quote_risk_advisory",
        "quote_risk_summary",
        "follow-up message helper",
        "completed-job cost info",
        "known margin",
        "known profit",
        "underquoted",
        "painful",
        "pricing engine",
        "risk score",
    ]

    banned_phrases_css = [
        "internal risk summary",
        "quote risk advisory",
        "internal_risk_assessment",
        "quote_risk_advisory",
        "quote_risk_summary",
        "owner review",
    ]

    for phrase in banned_phrases:
        assert phrase not in quote_html
        assert phrase not in quote_js

    for phrase in banned_phrases_css:
        assert phrase not in quote_css


def test_quote_page_includes_haul_away_floor_fields() -> None:
    """Ensure haul-away-only floor-detail fields are present with backend-compatible values."""
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert 'id="haulAwayDetailsRow"' in quote_html
    assert re.search(r'<select(?=[^>]*\bid="bag_type")(?=[^>]*\bname="bag_type")[^>]*>', quote_html)
    assert re.search(r'<select(?=[^>]*\bid="trailer_fill_estimate")(?=[^>]*\bname="trailer_fill_estimate")[^>]*>', quote_html)

    for option_value in ["light", "heavy_mixed", "construction_debris"]:
        assert re.search(rf'<option[^>]*\bvalue="{re.escape(option_value)}"[^>]*>', quote_html)

    for option_value in ["under_quarter", "quarter", "half", "three_quarter", "full"]:
        assert re.search(rf'<option[^>]*\bvalue="{re.escape(option_value)}"[^>]*>', quote_html)

    assert '<option value="" selected>Not sure / not applicable</option>' in quote_html
    assert '<option value="light" selected>' not in quote_html
    assert '<option value="under_quarter" selected>' not in quote_html


def test_admin_uploads_page_uses_external_script_for_csp():
    """Ensure admin uploads JS executes under CSP by avoiding inline script blocks."""
    uploads_html = Path("static/admin_uploads.html").read_text(encoding="utf-8")

    assert '<script src="/static/admin_uploads.js" defer></script>' in uploads_html
    assert "<script>" not in uploads_html
    assert "onclick=" not in uploads_html
    assert "onload=" not in uploads_html


def test_admin_desktop_contains_accepted_not_booked_queue_ui() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    assert 'id="acceptedNotBookedQueueSection"' in admin_html
    assert 'id="acceptedNotBookedQueueBox"' in admin_html
    assert "Accepted, Not Booked" in admin_html
    assert "renderAcceptedNotBookedQueue" in admin_js
    assert "accepted_not_booked_items" in admin_js
    assert "acceptedNotBookedReadinessBadge" in admin_js
    assert "Showing latest ${items.length} of ${totalCount} accepted or approved items waiting on scheduling." in admin_js
    assert "shouldOpenAcceptedNotBookedItemInRescheduleMode" in admin_js
    assert "normalizedStatus === \"scheduled\"" in admin_js
    assert "item?.google_calendar_event_id" in admin_js
    assert "normalizedStatus === \"scheduled\" && hasCalendarEvent" in admin_js
    assert "showScheduleModal(item.job_id, openInRescheduleMode)" in admin_js
    assert "scheduleBtn.textContent = openInRescheduleMode ? \"Open Reschedule\" : \"Open Schedule\";" in admin_js
    assert ".acceptedNotBookedItem" in admin_css
    assert ".acceptedNotBookedReadinessBadge" in admin_css


def test_customer_and_mobile_assets_do_not_include_desktop_accepted_not_booked_queue() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    for content in [quote_html, quote_js, mobile_html, mobile_js]:
        assert "acceptedNotBookedQueueSection" not in content
        assert "acceptedNotBookedQueueBox" not in content
        assert "renderAcceptedNotBookedQueue" not in content


def test_admin_page_gates_protected_dashboard_until_auth_load():
    """Ensure protected admin dashboard shells are hidden by default until JS reveals them."""
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    assert 'id="adminProtectedDashboard"' in admin_html
    assert 'hidden aria-hidden="true" style="display:none"' in admin_html
    assert 'class="card adminHero adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert 'class="dashboardGrid adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert 'class="card dataCard mt18 adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js
    assert "const adminProtectedSections = Array.from(document.querySelectorAll(\"[data-admin-protected='true']\"));" in admin_js
    assert "adminProtectedSections.forEach((section) => {" in admin_js
    assert "admin-authenticated" in admin_js
    assert ".adminPage.admin-authenticated .protectedDashboard" in admin_css
    assert ".adminProtectedSection[hidden]" in admin_css

    protected_match = re.search(
        r'(<div id="adminProtectedDashboard" class="protectedDashboard" hidden aria-hidden="true" style="display:none">.*?</div>\s*</div>\s*<script src="/static/admin.js" defer></script>)',
        admin_html,
        re.DOTALL,
    )
    assert protected_match is not None

    protected_block = protected_match.group(1)
    remainder = admin_html.replace(protected_block, "", 1)
    for heading in ["Recent Estimates", "Booking Requests", "Jobs"]:
        assert f"<h3>{heading}</h3>" in protected_block
        assert f"<h3>{heading}</h3>" not in remainder
    for heading in ["Screenshot Intake Guidance (Read-Only)", "Screenshot Intake History (Read-Only)"]:
        assert f"<summary>{heading}</summary>" in protected_block
        assert f"<summary>{heading}</summary>" not in remainder

    assert 'id="adminProtectedDashboard"' in admin_html
    assert 'hidden aria-hidden="true" style="display:none"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js
    assert 'adminProtectedDashboard.style.display = "";' in admin_js
    assert 'adminProtectedDashboard.style.display = "none";' in admin_js


def test_desktop_admin_uses_branded_dark_theme_tokens() -> None:
    """Ensure desktop admin visual polish stays aligned with the public Bay Delivery theme."""
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    for expected in [
        "--admin-bg: #0b0b10;",
        "--brand-red-deep: #7a1020;",
        "radial-gradient(1200px 680px at 18% -10%, rgba(122, 16, 32, 0.34), transparent 62%)",
        "linear-gradient(155deg, rgba(18, 22, 31, 0.96), rgba(122, 16, 32, 0.9))",
        "linear-gradient(135deg, var(--brand-red-deep), var(--brand-red))",
        ".status-expired",
        "::placeholder",
    ]:
        assert expected in admin_css


def test_admin_page_includes_quote_detail_risk_panel() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    assert "Open a quote to review internal ops-only detail" in admin_html
    assert '["Quote", "Status", "Customer", "Service", "Address", "Estimated", "Actions"]' in admin_js
    assert "View Details" in admin_js
    assert "Hide Details" in admin_js
    assert "Quote Details" in admin_js
    assert "Lead & Customer History" in admin_js
    assert "function createLeadCustomerHistorySection(" in admin_js
    assert 'detail.lead_source || null' in admin_js
    assert 'detail.customer_history || null' in admin_js
    assert "Lead source" in admin_js
    assert "Customer history" in admin_js
    assert "Previous requests" in admin_js
    assert "Previous jobs" in admin_js
    assert "Last seen" in admin_js
    assert "Internal Risk Summary" in admin_js
    assert "function createInternalRiskSummarySection(" in admin_js
    assert "function createRawRiskDataSection(" in admin_js
    assert "Show raw risk data" in admin_js
    assert "function createInternalRiskSummarySignals(" not in admin_js
    assert 'detail.quote_risk_summary || null' in admin_js
    risk_summary_match = re.search(
        r"function createInternalRiskSummarySection\(summary\) \{(?P<body>.*?)\n\}\n\nfunction createQuoteRiskAdvisorySection",
        admin_js,
        re.DOTALL,
    )
    assert risk_summary_match is not None
    risk_summary_body = risk_summary_match.group("body")
    assert "makeRiskConfidenceBadge" not in risk_summary_body
    assert "makeQuoteRiskLevelBadge(riskLevel)" in risk_summary_body
    assert "formatRiskSummaryValue" in admin_js
    assert "function makeQuoteRiskLevelBadge(" in admin_js
    assert "quote-risk-level-low" in admin_js
    assert "quote-risk-level-medium" in admin_js
    assert "quote-risk-level-high" in admin_js
    assert "quote-risk-level-owner-review" in admin_js
    assert "Low risk" in admin_js
    assert "Medium risk" in admin_js
    assert "High risk" in admin_js
    assert "Owner review" in admin_js
    assert "Risk level" in admin_js
    assert "Reasons:" in admin_js
    assert "Missing info:" in admin_js
    assert "Suggested action" in admin_js
    assert "Crew suggestion" in admin_js
    assert "Trailer suggestion" in admin_js
    assert "Pricing caution" in admin_js
    assert "Internal advisory only - no quote total change" in admin_js
    assert "Quote Risk Assessment" in admin_js
    assert "Quote Risk Advisory" in admin_js
    assert 'detail.quote_risk_advisory || null' in admin_js
    assert "Internal advisory only - no pricing effect" in admin_js
    assert "Advisory flags:" in admin_js
    assert "Suggested actions:" in admin_js
    assert 'const assessment = detail.internal_risk_assessment || null;' in admin_js
    assert 'Array.isArray(safeGet(assessment, "risk_flags", null))' in admin_js
    assert "const rawRiskDataSection = createRawRiskDataSection(advisorySection, riskAssessmentSection);" in admin_js
    assert "panel.appendChild(rawRiskDataSection);" in admin_js
    detail_panel_match = re.search(
        r"function createQuoteDetailPanel\(detail\) \{(?P<body>.*?)\n\}\n\nfunction createQuoteDetailRow",
        admin_js,
        re.DOTALL,
    )
    assert detail_panel_match is not None
    detail_panel_body = detail_panel_match.group("body")
    assert "panel.appendChild(advisorySection);" not in detail_panel_body
    assert "panel.appendChild(riskSection);" not in detail_panel_body
    assert '/admin/api/quotes/${encodeURIComponent(quoteId)}' in admin_js
    assert ".quoteDetailToggle" in admin_css
    assert ".quoteDetailPanel" in admin_css
    assert ".leadCustomerHistorySection" in admin_css
    assert ".quoteRiskSection" in admin_css
    assert ".quoteRawRiskDetails" in admin_css
    assert ".quoteRawRiskDetails > summary" in admin_css
    assert ".quoteRiskFlags" in admin_css
    assert ".quoteRiskSummaryList" in admin_css
    assert ".quoteRiskLevel" in admin_css
    assert ".quote-risk-level-low" in admin_css
    assert ".quote-risk-level-medium" in admin_css
    assert ".quote-risk-level-high" in admin_css
    assert ".quote-risk-level-owner-review" in admin_css
    assert ".risk-confidence-medium" in admin_css


def test_desktop_admin_declutters_long_ids_and_reference_sections() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    mobile_css = Path("static/admin_mobile.css").read_text(encoding="utf-8")

    assert "function formatAdminDisplayId(" in admin_js
    assert 'return `${normalized.slice(0, 8)}…`;' in admin_js
    assert "function createAdminIdCode(" in admin_js
    assert ".adminDisplayId" in admin_css

    for expected in [
        "tdRec.appendChild(createAdminIdCode(entry.record_id));",
        '["Quote", item.quote_id || "-"]',
        'val.appendChild(createAdminIdCode(value));',
        "jobCode.textContent = formatAdminDisplayId(j.job_id || \"\");",
        "jobCode.title = j.job_id || \"\";",
        "qCode.textContent = formatAdminDisplayId(j.quote_id || \"\");",
        "qCode.title = j.quote_id || \"\";",
    ]:
        assert expected in admin_js

    for expected in [
        '<details class="adminReferenceDetails assistantCard">',
        '<summary>Screenshot Intake Guidance (Read-Only)</summary>',
        '<details class="adminReferenceDetails">',
        '<summary>Admin Audit Log</summary>',
        '<summary>Screenshot Intake History (Read-Only)</summary>',
        ".adminReferenceDetails",
        ".adminReferenceDetails > summary",
    ]:
        assert expected in admin_html or expected in admin_css

    desktop_only_markers = [
        "Show raw risk data",
        "formatAdminDisplayId",
        "adminReferenceDetails",
    ]
    for marker in desktop_only_markers:
        assert marker in admin_html or marker in admin_js or marker in admin_css
        assert marker not in quote_html
        assert marker not in quote_js
        assert marker not in quote_css
        assert marker not in mobile_html
        assert marker not in mobile_js
        assert marker not in mobile_css


def test_admin_page_includes_screenshot_assistant_shell() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")

    assert 'id="assistantAnalyzeBtn"' not in admin_html
    assert 'id="assistantStartDraftBtn"' not in admin_html
    assert 'id="assistantUploadBtn"' not in admin_html
    assert 'id="assistantScreenshotFiles"' not in admin_html
    assert 'id="assistantMessage"' not in admin_html
    assert 'id="assistantCustomerName"' not in admin_html
    assert 'id="assistantCustomerPhone"' not in admin_html
    assert 'id="assistantDescription"' not in admin_html
    assert 'id="assistantRequestedJobDate"' not in admin_html
    assert 'id="assistantRequestedTimeWindow"' not in admin_html
    assert 'id="assistantAttachmentIds"' not in admin_html
    assert 'id="assistantUploadList"' in admin_html
    assert 'id="assistantResultBox"' in admin_html
    assert 'id="assistantHistoryBox"' in admin_html
    assert 'id="assistantDraftMeta"' in admin_html
    assert 'id="assistantStatusLine"' in admin_html
    assert 'Screenshot Intake Guidance (Read-Only)' in admin_html
    assert 'Screenshot Intake History (Read-Only)' in admin_html
    assert 'Guidance is non-binding' in admin_html
    assert 'pricing is always determined by the quote engine.' in admin_html
    assert 'No quote drafting actions are available on desktop admin.' in admin_html
    assert '/admin/api/screenshot-assistant/analyses/intake' not in admin_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/attachments' not in admin_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisItems[0].analysis_id)}' in admin_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/quote-draft' not in admin_js
    assert '/admin/api/quotes/${encodeURIComponent(quoteId)}/handoff' not in admin_js
    assert 'Create Quote Draft' not in admin_js
    assert 'Prepare Customer Handoff' not in admin_js
    assert 'createQuoteDraftFromAnalysis' not in admin_js
    assert 'prepareCustomerHandoff' not in admin_js
    assert 'setAssistantDraftLocked' in admin_js
    assert '["Analysis", "Updated", "Service", "Cash", "Quote", "Attachments", "Mode"]' in admin_js
    assert 'submitScreenshotAssistantAnalysis' not in admin_js
    assert 'uploadScreenshotAssistantFiles' not in admin_js
    assert 'assistantSuggestionPanel' in admin_js
    assert 'assistantApplyAllSuggestionsBtn' not in admin_js
    assert 'applyAllEmptyAssistantSuggestions' not in admin_js
    assert 'applyAssistantSuggestion' not in admin_js
    assert 'let assistantDraftDirty = false;' in admin_js
    assert 'assistantUnsavedDraftWarning' in admin_js
    assert 'setAssistantDraftDirty' in admin_js
    assert 'markAssistantDraftDirty' in admin_js
    assert 'syncAssistantDraftActionState' in admin_js
    assert 'Autofill Suggestions' in admin_js
    assert 'Apply All Empty Fields' not in admin_js
    assert 'Read-only recommendation context for ops review.' in admin_js
    assert 'Quote Range Guidance' in admin_js
    assert 'Minimum Safe' in admin_js
    assert 'Recommended Target' in admin_js
    assert 'Upper Reasonable' in admin_js
    assert 'Confidence' in admin_js
    assert 'Unknowns:' in admin_js
    assert 'Risk Notes:' in admin_js
    assert 'Minimum Safe is a protective lower bound, not the preferred quote.' in admin_js
    assert 'Missing fields:' in admin_js
    assert 'Warnings:' in admin_js
    assert 'No message/OCR-based intake suggestions detected.' in admin_js


def test_completed_job_profit_report_desktop_only_assets() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert 'id="adminProfitReportSection"' in admin_html
    assert "Completed Job Profit Review" in admin_html
    assert "Internal report only." in admin_html
    assert 'id="profitReportBox"' in admin_html
    assert 'data-admin-protected="true"' in admin_html

    assert "/admin/api/completed-job-profit-report" in admin_js
    assert "function renderProfitReport(" in admin_js
    assert "function refreshProfitReportBestEffort(" in admin_js
    assert "Category Breakdown" in admin_js
    assert "Recent Completed Jobs" in admin_js
    assert "Missing cost data" in admin_js
    assert "Incomplete closeout" in admin_js
    assert "Underquoted" in admin_js
    assert "Painful job" in admin_js
    assert "Below 20% known margin" in admin_js

    assert ".profitReportSummaryGrid" in admin_css
    assert ".profitReportTable" in admin_css

    banned_mobile = [
        "Completed Job Profit Review",
        "profitReportBox",
        "/admin/api/completed-job-profit-report",
        "known_margin_pct",
        "known_profit_cad",
    ]
    for phrase in banned_mobile:
        assert phrase not in mobile_html
        assert phrase not in mobile_js

    banned_quote = [
        "completed job profit review",
        "/admin/api/completed-job-profit-report",
        "known_margin_pct",
        "known_profit_cad",
        "owner review",
    ]
    for phrase in banned_quote:
        assert phrase not in quote_html.lower()
        assert phrase not in quote_js.lower()
        assert phrase not in quote_css.lower()


def test_manual_completed_job_calibration_log_desktop_only_assets() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "Manual Completed Job Calibration Log" in admin_html
    assert "Internal calibration evidence only. Does not change quote prices." in admin_html
    assert 'id="manualCompletedJobsSection"' in admin_html
    assert 'id="manualCompletedJobForm"' in admin_html
    assert 'id="manualCompletedJobsBox"' in admin_html
    assert 'data-admin-protected="true"' in admin_html

    assert "/admin/api/manual-completed-jobs" in admin_js
    assert "function renderManualCompletedJobs(" in admin_js
    assert "function manualCompletedJobPayloadFromForm(" in admin_js
    assert "function refreshManualCompletedJobsBestEffort(" in admin_js
    assert "No manual calibration entries yet." in admin_js
    assert "Saved manual completed-job calibration entry." in admin_js

    for label in [
        "Job title",
        "Service type",
        "Secondary category",
        "Quoted price CAD",
        "Actual collected CAD",
        "Crew size",
        "Duration hours",
        "Labour hours",
        "Disassembly required",
        "Dense materials",
        "Underquoted",
        "Painful job",
        "Pricing result",
        "Calibration note",
    ]:
        assert label in admin_html or label in admin_js

    assert ".manualCompletedJobForm" in admin_css
    assert ".manualCompletedJobList" in admin_css

    banned_mobile = [
        "Manual Completed Job Calibration Log",
        "manualCompletedJobs",
        "/admin/api/manual-completed-jobs",
        "manual completed-job calibration",
    ]
    for phrase in banned_mobile:
        assert phrase not in mobile_html
        assert phrase not in mobile_js

    banned_quote = [
        "manual completed job calibration",
        "manual completed-job calibration",
        "/admin/api/manual-completed-jobs",
        "calibration evidence",
    ]
    for phrase in banned_quote:
        assert phrase not in quote_html.lower()
        assert phrase not in quote_js.lower()
        assert phrase not in quote_css.lower()
    assert '["Attachment", "Filename", "Type", "Size", "Uploaded", "OCR Status", "OCR Preview"]' in admin_js
    assert 'ocr_json' in admin_js
    assert 'Click Analyze Intake to save reviewed fields.' not in admin_js
    assert 'Desktop admin guidance is reference-only.' in admin_js


def test_admin_schedule_modal_includes_scheduling_handoff_context() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")

    assert 'id="scheduleContextBox"' in admin_html
    assert 'id="scheduleContextSummary"' in admin_html
    assert 'id="scheduleContextFields"' in admin_html
    assert "Scheduling handoff" in admin_html
    assert "renderScheduleContext" in admin_js
    for label in [
        "Requested Job Date",
        "Requested Time Window",
        "Booking Notes",
        "Calendar sync:",
        "Missing booking preference fields:",
        "Last calendar error:",
    ]:
        assert label in admin_js
    assert "Customer preferences captured for ops review" in admin_js
    assert "Follow up with the customer if needed before scheduling." in admin_js


def test_admin_page_includes_job_lifecycle_controls() -> None:
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")

    assert "Start Job" in admin_js
    assert "Mark Complete" in admin_js
    assert 'in_progress: "In progress"' in admin_js
    assert 'completed: "Completed"' in admin_js
    for label in ["Started:", "Completed:", "Cancelled:", "Close-out notes:"]:
        assert label in admin_js
    assert "/admin/api/jobs/${jobId}/start" in admin_js
    assert "/admin/api/jobs/${jobId}/complete" in admin_js


def test_desktop_admin_includes_completed_job_costing_controls_only() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    assert "record completed-job costing feedback" in admin_html
    assert "Completed Job Costing" in admin_js
    assert "Quoted cash" in admin_js
    assert "Quoted EMT" in admin_js
    assert "Quoted totals" in admin_js
    assert "Collected revenue" in admin_js
    assert "Known costs" in admin_js
    assert "Advisory profit" in admin_js
    assert "Final collected CAD" in admin_js
    assert "Actual costs recorded" in admin_js
    assert "Advisory known-cost profit" in admin_js
    assert "Needs revenue and costs" in admin_js
    assert "Record final collected and actual costs to review known-cost profit." in admin_js
    assert "Missing actual cost fields reduce confidence in this advisory margin." in admin_js
    assert "Admin-only advisory feedback for completed jobs." in admin_js
    assert "Payment method is how the customer paid; payment status is whether the money is fully collected." in admin_js
    assert "Known-cost profit uses saved final collected, labor, disposal, fuel, and other costs only; quote calculation is unchanged." in admin_js
    assert "input.inputMode = field === \"actual_crew_size\" ? \"numeric\" : \"decimal\";" in admin_js
    assert "/admin/api/jobs/${jobId}/costing" in admin_js
    assert 'if (j.status === "completed")' in admin_js
    assert "Labor used" in admin_js
    assert "Actual costs" in admin_js
    assert "Labor cost CAD" in admin_js
    assert "actual_labor_cost_cad" in admin_js
    assert "Other costs CAD" in admin_js
    assert "actual_other_costs_cad" in admin_js
    assert "Payment collection" in admin_js
    assert "Profit and notes" in admin_js
    assert "Separate how the customer paid from whether money is fully collected." in admin_js
    assert "Operator feedback for future review; pricing is unchanged." in admin_js
    assert "Payment method" in admin_js
    assert "payment_method" in admin_js
    assert "How they paid. This is separate from whether it is paid in full." in admin_js
    for method_option in [
        '["cash", "Cash"]',
        '["emt", "EMT / e-transfer"]',
        '["other", "Other"]',
    ]:
        assert method_option in admin_js
    assert "Payment status" in admin_js
    assert "payment_status" in admin_js
    assert "Collection state. Use this even when the method is known." in admin_js
    for status_option in [
        '["not_paid_yet", "Not paid yet"]',
        '["partial_payment", "Partial payment"]',
        '["paid_in_full", "Paid in full"]',
    ]:
        assert status_option in admin_js
    assert "job_profit_status" in admin_js
    for profit_label in [
        '["underquoted", "Underquoted - should have charged more"]',
        '["fair", "Fair - about right"]',
        '["profitable", "Profitable - strong margin"]',
        '["painful", "Painful - lost time or money"]',
    ]:
        assert profit_label in admin_js
    assert "Operator gut check only. This does not change pricing." in admin_js
    assert ".jobCostingPanel" in admin_css
    assert ".jobCostingGroup" in admin_css
    assert ".jobCostingGroupHeader" in admin_css
    assert ".jobCostingGroupGrid" in admin_css
    assert ".jobCostingState" in admin_css
    assert ".jobCostingHelp" in admin_css
    assert "/costing" not in mobile_html
    assert "/costing" not in mobile_js


def test_desktop_admin_includes_quote_request_followup_status_controls_only() -> None:
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    assert "quoteRequestFollowupOptions" in admin_js
    assert '["needs_followup", "Needs follow-up"]' in admin_js
    assert '["contacted", "Contacted"]' in admin_js
    assert '["waiting_on_customer", "Waiting on customer"]' in admin_js
    assert '["not_ready", "Not ready"]' in admin_js
    assert '["closed_no_followup", "Closed - no follow-up"]' in admin_js
    assert "quoteRequestFollowupQuickActions" in admin_js
    for label in ["Needs", "Contacted", "Waiting", "Not ready", "Close", "Unmark"]:
        assert f'"{label}"' in admin_js
    assert "Mark this request closed with no follow-up? You can unmark it later." in admin_js
    assert 'createTable(["Request", "Customer", "Job", "Requested", "Follow-up", "Totals", "Actions"])' in admin_js
    assert "function createFollowupStatusControl(item)" in admin_js
    assert "function createFollowupQuickActions(item)" in admin_js
    assert "/followup-status" in admin_js
    assert "followup_status: followupStatus || null" in admin_js
    assert ".followupStatusControl" in admin_css
    assert ".followupStatusSelect" in admin_css
    assert ".followupQuickActions" in admin_css
    quick_actions = re.search(
        r"function createFollowupQuickActions\(item\) \{(?P<body>.*?)\n\}\n\nfunction createFollowupStatusControl",
        admin_js,
        re.S,
    )
    assert quick_actions is not None
    quick_body = quick_actions.group("body")
    assert "quoteRequestFollowupQuickActions.forEach" in quick_body
    assert 'updateQuoteRequestFollowupStatus(item.request_id || "", action.value);' in quick_body
    assert 'updateQuoteRequestFollowupStatus(item.request_id || "", null);' in quick_body
    assert "selectedValue(item.followup_status)" in quick_body
    assert 'if (action.confirm && !confirm(action.confirm)) return;' in quick_body
    assert "/followup-status" not in quick_body
    assert "fetch" not in quick_body
    assert "followup_status" not in mobile_html
    assert "followup_status" not in mobile_js
    assert "/followup-status" not in mobile_js
    assert "followupQuickActions" not in mobile_html
    assert "followupQuickActions" not in mobile_js


def test_desktop_admin_includes_followup_message_helper_only() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8").lower()
    quote_js = Path("static/quote.js").read_text(encoding="utf-8").lower()
    quote_css = Path("static/quote.css").read_text(encoding="utf-8").lower()
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8").lower()
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8").lower()

    assert "Follow-Up Message Helper" in admin_html
    assert 'id="adminFollowupHelperSection"' in admin_html
    assert 'id="followupMessageScenario"' in admin_html
    assert 'id="followupMessageFormat"' in admin_html
    assert 'id="followupMessageContext"' in admin_html
    assert 'id="followupMessageContextSummary"' in admin_html
    assert 'id="followupMessageDraft"' in admin_html
    assert 'id="followupMessageCopyBtn"' in admin_html
    assert "Copy-only helper" in admin_html
    assert "does not send messages or update follow-up status" in admin_html

    for label in [
        "Need photos",
        "No reply / gentle follow-up",
        "Accepted but not booked",
        "Need access details",
        "Price concern / customer asking cheaper",
        "Completed job follow-up",
        "Review request",
        "Manual review / unclear job",
        "Missing completed-job cost info",
        "Text message",
        "Email",
    ]:
        assert label in admin_js

    assert "const followupMessageScenarioCatalog = [" in admin_js
    assert "function renderFollowupMessageHelper()" in admin_js
    assert "function buildFollowupMessageDraft(scenarioKey, format, context)" in admin_js
    assert "function copyFollowupMessageDraft()" in admin_js
    assert "navigator.clipboard.writeText" in admin_js
    assert "function normalizeBooleanLike(" in admin_js
    assert '["true", "yes", "y", "1", "on"].includes(normalized)' in admin_js
    assert '["false", "no", "n", "0", "off", ""].includes(normalized)' in admin_js
    assert "normalizeBooleanLike(request.basement_or_inside_removal)" in admin_js
    assert admin_js.index("function normalizeBooleanLike(") < admin_js.index("function buildPhotosPrompt(")
    assert admin_js.index("function normalizeBooleanLike(") < admin_js.index("function buildAccessPrompt(")
    assert ".followupHelperGrid" in admin_css
    assert ".followupHelperSummary" in admin_css
    assert ".followupHelperActions" in admin_css
    assert ".followupHelperNote" in admin_css

    copy_function = re.search(r"async function copyFollowupMessageDraft\(\) \{(?P<body>.*?)\n\}\n\nfunction setAssistantDraftLocked", admin_js, re.S)
    assert copy_function is not None
    copy_body = copy_function.group("body")
    assert "fetch(" not in copy_body
    for forbidden in [
        "/followup-status",
        "/decision",
        "/schedule",
        "/reschedule",
        "/costing",
        "/start",
        "/complete",
        "/cancel",
        "/sms",
        "/email",
        "/messages",
    ]:
        assert forbidden not in copy_body

    for forbidden in [
        "follow-up message helper",
        "completed-job cost info",
        "known margin",
        "known profit",
        "underquoted",
        "painful",
        "owner review",
        "internal risk",
        "quote_risk_advisory",
        "internal_risk_assessment",
        "pricing engine",
        "risk score",
    ]:
        assert forbidden not in quote_html
        assert forbidden not in quote_js
        assert forbidden not in quote_css
        assert forbidden not in mobile_html
        assert forbidden not in mobile_js


def test_quote_structured_intake_static_surfaces_are_desktop_only() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    for field in [
        "stairs_count",
        "floor_count",
        "basement_or_inside_removal",
        "demolition_ripout",
        "construction_debris_type",
        "dense_material_type",
        "mixed_load",
        "contains_scrap",
        "contains_garbage",
        "has_refrigerant_appliance",
        "appliance_type",
        "weather_protection_required",
    ]:
        assert field in quote_html or field in quote_js
        assert field in admin_js
        assert field not in mobile_html
        assert field not in mobile_js

    assert "Structured Intake" in admin_js
    assert "function createStructuredIntakeSection(" in admin_js
    assert "if (!rows.length) return null;" in admin_js
    assert "if (structuredIntakeSection)" in admin_js
    assert "Internal Risk Summary" in admin_js
    assert "Quote Risk Advisory" in admin_js
    assert "Internal Risk Summary" not in mobile_html
    assert "Internal Risk Summary" not in mobile_js
    assert "quote_risk_advisory" not in mobile_html
    assert "quote_risk_advisory" not in mobile_js
    assert "quote_risk_summary" not in mobile_html
    assert "quote_risk_summary" not in mobile_js
    assert "Quote Risk Advisory" not in mobile_html
    assert "Quote Risk Advisory" not in mobile_js
    assert "Lead & Customer History" not in mobile_html
    assert "Lead & Customer History" not in mobile_js
    assert "customer_history" not in mobile_html
    assert "customer_history" not in mobile_js


def test_desktop_admin_includes_daily_ops_board_only() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    assert "Daily Ops Board" in admin_html
    assert "Shortcuts only move you to existing admin controls. Changes happen only from explicit row actions." in admin_html
    assert 'id="adminOpsBoardSection"' in admin_html
    assert 'id="adminQuotesSection"' in admin_html
    assert 'id="adminRequestsSection"' in admin_html
    assert 'id="adminJobsSection"' in admin_html
    assert 'const opsQueue = await fetchJSON("/admin/api/ops-queue");' in admin_js
    assert "async function refreshOpsQueueBestEffort()" in admin_js
    assert "function renderOpsQueueError()" in admin_js
    assert "Daily Ops Board could not load. Core admin data is still available." in admin_js
    assert "void refreshOpsQueueBestEffort();" in admin_js
    refresh_all = re.search(r"async function refreshAll\(\) \{(?P<body>.*?)\n\}\n\nfunction handleCredsKeydown", admin_js, re.S)
    assert refresh_all is not None
    assert "/admin/api/ops-queue" not in refresh_all.group("body")
    assert "function renderOpsQueue(queue)" in admin_js
    assert "const cards = Array.isArray(queue && queue.cards) ? queue.cards : [];" in admin_js
    assert "new_requests" in admin_js
    assert "accepted_not_booked" in admin_js
    assert "completed_missing_costs" in admin_js
    assert "owner_review" in admin_js
    key_order = re.search(r"const dailyOpsBoardCardKeys = \[(?P<body>.*?)\];", admin_js, re.S)
    assert key_order is not None
    assert re.findall(r'"([^"]+)"', key_order.group("body")) == [
        "new_requests",
        "needs_followup",
        "accepted_not_booked",
        "upcoming_jobs",
        "completed_missing_costs",
        "owner_review",
        "stale_quotes",
    ]
    assert "const opsBoardShortcutsByKey = {" in admin_js
    assert "function focusAdminSection(targetId, label)" in admin_js
    assert "function createOpsQueueShortcutButton(shortcut)" in admin_js
    assert "data-ops-shortcut" in admin_js
    assert "Daily Ops Board shortcut opened:" in admin_js
    assert "Daily Ops Board shortcut target is not available. Refresh admin data and try again." in admin_js
    shortcut_block = re.search(
        r"const opsBoardShortcutsByKey = \{(?P<body>.*?)\nfunction renderOpsQueue",
        admin_js,
        re.S,
    )
    assert shortcut_block is not None
    shortcut_body = shortcut_block.group("body")
    for target_id in ["adminRequestsSection", "adminJobsSection", "adminQuotesSection"]:
        assert target_id in shortcut_body
    for forbidden in [
        "fetch(",
        'method: "POST"',
        "/followup-status",
        "/decision",
        "/expire",
        "/schedule",
        "/reschedule",
        "/costing",
        "/start",
        "/complete",
        "/cancel",
    ]:
        assert forbidden not in shortcut_body
    assert ".opsQueueGrid" in admin_css
    assert ".opsQueueCard" in admin_css
    assert ".opsQueueActions" in admin_css
    assert ".opsQueueShortcut" in admin_css
    assert ".adminSectionFocus" in admin_css
    assert "Daily Ops Board" not in mobile_html
    assert "/admin/api/ops-queue" not in mobile_js
    assert "opsQueueBox" not in mobile_js
    assert "opsQueueShortcut" not in mobile_html
    assert "opsQueueShortcut" not in mobile_js


def test_desktop_admin_includes_pending_estimate_cleanup_controls_only() -> None:
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    assert "Mark expired" in admin_js
    assert "This keeps the record but removes it from active review." in admin_js
    assert "async function fetchJSON(path, options = {})" in admin_js
    assert "Object.assign({}, options, { headers })" in admin_js
    assert "/admin/api/quotes/${encodeURIComponent(quoteId)}/expire" in admin_js
    expire_function = re.search(r"async function expireQuote\(quoteId\) \{(?P<body>.*?)\n\}\n\nfunction renderQuotes", admin_js, re.S)
    assert expire_function is not None
    expire_body = expire_function.group("body")
    assert "/admin/api/quotes/${encodeURIComponent(quoteId)}/expire" in expire_body
    assert 'method: "POST"' in expire_body
    assert 'expired: "Expired"' in admin_js
    assert "Mark expired" not in mobile_html
    assert "Mark expired" not in mobile_js
    assert "/expire" not in mobile_html
    assert "/expire" not in mobile_js


def test_admin_mobile_page_includes_dedicated_mobile_shell() -> None:
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    mobile_css = Path("static/admin_mobile.css").read_text(encoding="utf-8")
    main_py = Path("app/main.py").read_text(encoding="utf-8")

    assert '<script src="/static/admin_mobile.js" defer></script>' in mobile_html
    assert '<link rel="stylesheet" href="/static/admin_mobile.css" />' in mobile_html
    assert '<section id="loginScreen" class="screenCard">' in mobile_html
    assert 'Mobile Login' in mobile_html
    assert 'Home / Queue' in mobile_html
    assert 'Requests' in mobile_html
    assert 'Upcoming Jobs' in mobile_html
    assert 'data-screen="homeScreen"' in mobile_html
    assert 'data-screen="requestsScreen"' in mobile_html
    assert 'data-screen="jobsScreen"' in mobile_html
    assert 'New Intake' not in mobile_html
    assert 'Quote Draft' not in mobile_html
    assert 'Create Quote Draft' not in mobile_html
    assert 'Prepare Customer Handoff' not in mobile_html
    assert 'No quote authoring on mobile admin.' in mobile_html
    assert '/admin/api/quote-requests?limit=20' in mobile_js
    assert '/admin/api/jobs?limit=20' in mobile_js
    assert 'const state = {' in mobile_js
    assert '/admin/api/screenshot-assistant/analyses/intake' not in mobile_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(currentAnalysisId)}/quote-draft' not in mobile_js
    assert '/admin/api/quotes/${encodeURIComponent(quoteId)}/handoff' not in mobile_js
    assert 'button:disabled,' in mobile_css
    assert 'function renderRequests()' in mobile_js
    assert 'function renderJobs()' in mobile_js
    assert 'async function refreshAllData(statusTarget)' in mobile_js
    assert 'function logout()' in mobile_js
    assert 'localStorage' not in mobile_js
    assert '.mobileNav' in mobile_css
    assert '.metricGrid' in mobile_css
    assert '.cardItem' in mobile_css
    assert '.compactMetricCard' in mobile_css
    assert '@media (min-width: 760px)' in mobile_css
    assert '@app.get("/admin/mobile")' in main_py
    assert 'def admin_mobile_page():' in main_py
    assert 'return FileResponse(str(STATIC_DIR / "admin_mobile.html"))' in main_py


def test_homepage_contact_section_avoids_duplicate_large_ctas() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")

    assert 'Prefer to talk first?' in index_html
    assert 'class="contactQuickLink"' in index_html
    assert 'Get a Quote Online' not in index_html
    assert 'contactCTA' not in index_html
    assert '.contactQuickLink' in site_css
    assert '.contactHelper' in site_css
