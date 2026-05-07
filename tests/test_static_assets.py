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
    assert re.search(
        r"@media \(max-width: 720px\)\{\s*\.stickyMobileCall\{ display: flex; \}\s*\}",
        site_css,
    )


def test_quote_page_phase_a_guidance_copy_is_present() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "Start with the estimate." in quote_html
    assert "Share the job details used for your estimate." in quote_html
    assert 'id="serviceDetailsSummary"' in quote_html
    assert 'id="serviceDetailsLead"' in quote_html
    assert 'id="serviceDetailsPanel" class="detailPanel" open' in quote_html
    assert "Not sure? Give your best estimate. Clear, close guesses are enough to start." in quote_html
    assert "Required for moves and deliveries so the estimate reflects the actual route." in quote_html
    assert "A full kitchen garbage bag = 1. If unsure, estimate slightly higher." in quote_html
    assert "Most jobs are 5–10 bags. Adjust if needed." in quote_html
    assert "Examples: drywall, tile, concrete, shingles, soil. These are heavier and cost more." in quote_html
    assert "Easy = curbside / garage. Medium = short walk / a few stairs. Hard = basement / long carry / tight access." in quote_html
    assert "Optional photos can be added after you submit a booking request to help Bay Delivery review the job" in quote_html
    assert "Optional photos come after the booking request submission to help Bay Delivery review the job and improve follow-up accuracy." in quote_html
    assert "Prefer to send photos after your booking request? You can add them in Step 5 to help Bay Delivery review the job and improve follow-up accuracy." in quote_html
    assert "After you submit your booking request, add photos here if they help Bay Delivery review the job and improve follow-up accuracy." in quote_html
    assert "After you see your estimate, review what is included and compare Cash vs EMT totals." in quote_html
    assert "Booking requests and optional photos come after acceptance." not in quote_html
    assert "Optional photos come after that." not in quote_html
    assert "Step 1 of 4" not in quote_html
    assert "Step 2 of 4" not in quote_html
    assert "Step 3 of 4" not in quote_html
    assert "Step 4 of 4" not in quote_html
    assert "friendlyQuoteErrorMessage" in quote_js
    assert "syncBagCountNudge" in quote_js
    assert "What this estimate includes" in quote_js
    assert "What happens next" in quote_js
    assert "About this estimate" in quote_js
    assert "Photos are optional after you submit the booking request if they help Bay Delivery review the job and improve follow-up accuracy." in quote_js
    assert "Accept Estimate & Continue" in quote_js
    assert "Your job is not booked until Bay Delivery reviews and confirms it." in quote_js
    assert "quoteResultIncluded" in quote_css
    assert "quoteInfoCard" in quote_css


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

    assert '<option value="" selected>Select bag type if known</option>' in quote_html
    assert '<option value="" selected>Select trailer space used if known</option>' in quote_html
    assert '<option value="light" selected>' not in quote_html
    assert '<option value="under_quarter" selected>' not in quote_html


def test_admin_uploads_page_uses_external_script_for_csp():
    """Ensure admin uploads JS executes under CSP by avoiding inline script blocks."""
    uploads_html = Path("static/admin_uploads.html").read_text(encoding="utf-8")

    assert '<script src="/static/admin_uploads.js" defer></script>' in uploads_html
    assert "<script>" not in uploads_html
    assert "onclick=" not in uploads_html
    assert "onload=" not in uploads_html


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
    for heading in ["Recent Estimates", "Booking Requests", "Jobs", "Screenshot Intake Guidance (Read-Only)", "Screenshot Intake History (Read-Only)"]:
        assert f"<h3>{heading}</h3>" in protected_block
        assert f"<h3>{heading}</h3>" not in remainder

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
    assert "Quote Risk Assessment" in admin_js
    assert 'const assessment = detail.internal_risk_assessment || null;' in admin_js
    assert 'Array.isArray(safeGet(assessment, "risk_flags", null))' in admin_js
    assert 'if (assessment && (assessment.confidence_level || riskFlags.length)) {' in admin_js
    assert '/admin/api/quotes/${encodeURIComponent(quoteId)}' in admin_js
    assert ".quoteDetailToggle" in admin_css
    assert ".quoteDetailPanel" in admin_css
    assert ".quoteRiskSection" in admin_css
    assert ".quoteRiskFlags" in admin_css
    assert ".risk-confidence-medium" in admin_css


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
    assert 'createTable(["Request", "Customer", "Job", "Requested", "Follow-up", "Totals", "Actions"])' in admin_js
    assert "function createFollowupStatusControl(item)" in admin_js
    assert "/followup-status" in admin_js
    assert "followup_status: followupStatus || null" in admin_js
    assert ".followupStatusControl" in admin_css
    assert ".followupStatusSelect" in admin_css
    assert "followup_status" not in mobile_html
    assert "followup_status" not in mobile_js
    assert "/followup-status" not in mobile_js


def test_desktop_admin_includes_daily_ops_queue_only() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    assert "Daily Ops Queue" in admin_html
    assert "Nothing is approved, expired, scheduled, or contacted from this queue." in admin_html
    assert 'const opsQueue = await fetchJSON("/admin/api/ops-queue");' in admin_js
    assert "async function refreshOpsQueueBestEffort()" in admin_js
    assert "function renderOpsQueueError()" in admin_js
    assert "Daily Ops Queue could not load. Core admin data is still available." in admin_js
    assert "void refreshOpsQueueBestEffort();" in admin_js
    refresh_all = re.search(r"async function refreshAll\(\) \{(?P<body>.*?)\n\}\n\nfunction handleCredsKeydown", admin_js, re.S)
    assert refresh_all is not None
    assert "/admin/api/ops-queue" not in refresh_all.group("body")
    assert "function renderOpsQueue(queue)" in admin_js
    assert ".opsQueueGrid" in admin_css
    assert ".opsQueueSection" in admin_css
    assert "Daily Ops Queue" not in mobile_html
    assert "/admin/api/ops-queue" not in mobile_js
    assert "opsQueueBox" not in mobile_js


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
