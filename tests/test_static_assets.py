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
    assert 'if (calcBtn) calcBtn.disabled = persistedReviewMode;' in quote_js
    assert 'if (clearBtn) clearBtn.disabled = persistedReviewMode;' in quote_js
    assert 'if (persistedReviewMode) {' in quote_js
    assert 'showBox("flowStatus", persistedReviewHelperText, "info");' in quote_js
    assert "new URLSearchParams(window.location.search)" in quote_js
    assert 'params.get("quote_id")' in quote_js
    assert 'params.get("accept_token")' in quote_js
    assert '/view?accept_token=' in quote_js
    assert 'loadPersistedQuoteReview();' in quote_js
    assert 'showPersistedQuoteReview' in quote_js
    assert "You are reviewing a saved quote prepared for you. To request changes, contact Bay Delivery." in quote_js
    assert 'const res = await fetch("/quote/calculate"' in quote_js


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
    assert 'hidden aria-hidden="true"' in admin_html
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
        r'(<div id="adminProtectedDashboard" class="protectedDashboard" hidden aria-hidden="true">.*?</div>\s*</div>\s*<script src="/static/admin.js" defer></script>)',
        admin_html,
        re.DOTALL,
    )
    assert protected_match is not None

    protected_block = protected_match.group(1)
    remainder = admin_html.replace(protected_block, "", 1)
    for heading in ["Recent Estimates", "Booking Requests", "Jobs", "Screenshot Quote Assistant", "Screenshot Assistant Drafts"]:
        assert f"<h3>{heading}</h3>" in protected_block
        assert f"<h3>{heading}</h3>" not in remainder

    assert 'id="adminProtectedDashboard"' in admin_html
    assert 'hidden aria-hidden="true"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js


def test_admin_page_includes_screenshot_assistant_shell() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    assert 'id="assistantAnalyzeBtn"' in admin_html
    assert 'id="assistantStartDraftBtn"' in admin_html
    assert 'id="assistantUploadBtn"' in admin_html
    assert 'id="assistantScreenshotFiles"' in admin_html
    assert 'id="assistantUploadList"' in admin_html
    assert 'id="assistantResultBox"' in admin_html
    assert 'id="assistantHistoryBox"' in admin_html
    assert 'id="assistantCustomerName"' in admin_html
    assert 'id="assistantCustomerPhone"' in admin_html
    assert 'id="assistantDescription"' in admin_html
    assert 'id="assistantRequestedJobDate"' in admin_html
    assert 'id="assistantRequestedTimeWindow"' in admin_html
    assert 'Screenshot Quote Assistant' in admin_html
    assert 'Screenshot Assistant Drafts' in admin_html
    assert 'optionally create a real quote draft from the saved analysis' in admin_html
    assert '/admin/api/screenshot-assistant/analyses/intake' in admin_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/attachments' in admin_js
    assert '/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/quote-draft' in admin_js
    assert '/admin/api/quotes/${encodeURIComponent(quoteId)}/handoff' in admin_js
    assert 'assistantCreateQuoteDraftBtn' in admin_js
    assert 'assistantPrepareHandoffBtn' in admin_js
    assert 'Create Quote Draft' in admin_js
    assert 'Prepare Customer Handoff' in admin_js
    assert 'Linked quote draft' in admin_js
    assert 'Customer handoff' in admin_js
    assert 'This analysis is locked because a quote draft has already been created.' in admin_js
    assert 'setAssistantDraftLocked' in admin_js
    assert 'beginNewScreenshotAssistantDraft' in admin_js
    assert '["Analysis", "Updated", "Service", "Cash", "Quote", "Attachments", "Mode"]' in admin_js
    assert 'submitScreenshotAssistantAnalysis' in admin_js
    assert 'uploadScreenshotAssistantFiles' in admin_js
    assert 'createQuoteDraftFromAnalysis' in admin_js
    assert 'prepareCustomerHandoff' in admin_js
    assert 'assistantSuggestionPanel' in admin_js
    assert 'assistantApplyAllSuggestionsBtn' in admin_js
    assert 'applyAllEmptyAssistantSuggestions' in admin_js
    assert 'applyAssistantSuggestion' in admin_js
    assert 'let assistantDraftDirty = false;' in admin_js
    assert 'assistantUnsavedDraftWarning' in admin_js
    assert 'setAssistantDraftDirty' in admin_js
    assert 'markAssistantDraftDirty' in admin_js
    assert 'syncAssistantDraftActionState' in admin_js
    assert 'Autofill Suggestions' in admin_js
    assert 'Apply All Empty Fields' in admin_js
    assert 'Suggestions stay non-binding until you explicitly apply or edit them.' in admin_js
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
    assert 'No message/OCR-based suggestions detected yet.' in admin_js
    assert '["Attachment", "Filename", "Type", "Size", "Uploaded", "OCR Status", "OCR Preview"]' in admin_js
    assert 'Upload results include best-effort OCR status and a short preview for admin review.' in admin_html
    assert 'ocr_json' in admin_js
    assert 'Click Analyze Intake to save reviewed fields before creating a quote draft.' in admin_js
    assert 'assistantCreateQuoteDraftHelper' in admin_js
    assert 'button.disabled = !adminSessionReady || assistantDraftDirty;' in admin_js
    assert 'if (assistantDraftDirty) {' in admin_js
    assert 'markAssistantDraftDirty(assistantUnsavedDraftWarning)' in admin_js
    assert '.assistantUploadRow' in admin_css
    assert '.assistantDraftBar' in admin_css


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
