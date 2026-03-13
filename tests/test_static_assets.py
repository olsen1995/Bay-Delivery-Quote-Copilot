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


def test_quote_page_includes_haul_away_floor_fields() -> None:
    """Ensure haul-away-only floor-detail fields are present with backend-compatible values."""
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert 'id="haulAwayDetailsRow"' in quote_html
    assert 'id="bag_type" name="bag_type"' in quote_html
    assert '<option value="light" selected>Light household bags</option>' in quote_html
    assert '<option value="heavy_mixed">Heavy mixed junk bags</option>' in quote_html
    assert '<option value="construction_debris">Construction / debris bags</option>' in quote_html
    assert 'id="trailer_fill_estimate" name="trailer_fill_estimate"' in quote_html
    assert '<option value="under_quarter" selected>Under 1/4 trailer</option>' in quote_html
    assert '<option value="quarter">About 1/4 trailer</option>' in quote_html
    assert '<option value="half">About 1/2 trailer</option>' in quote_html
    assert '<option value="three_quarter">About 3/4 trailer</option>' in quote_html
    assert '<option value="full">Full trailer</option>' in quote_html


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
    for heading in ["Recent Estimates", "Booking Requests", "Jobs"]:
        assert f"<h3>{heading}</h3>" in protected_block
        assert f"<h3>{heading}</h3>" not in remainder

    assert 'id="adminProtectedDashboard"' in admin_html
    assert 'hidden aria-hidden="true"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js
