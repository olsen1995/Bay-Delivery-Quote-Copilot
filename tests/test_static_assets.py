import hashlib
import json
import re
import struct
from pathlib import Path


PUBLIC_SITE_ORIGIN = "https://bay-delivery-quote-copilot.onrender.com"
SOCIAL_IMAGE_URL = (
    f"{PUBLIC_SITE_ORIGIN}/static/assets/brand/bay-delivery-social-share-1200x630.png"
)
LOGO_URL = f"{PUBLIC_SITE_ORIGIN}/static/assets/brand/bay-delivery-logo-horizontal-header.png"
HOMEPAGE_TITLE = "Bay Delivery | Junk Removal, Moving Help & Hauling in North Bay"
HOMEPAGE_DESCRIPTION = (
    "Bay Delivery provides junk removal, dump runs, moving help, furniture delivery, "
    "property cleanups, demolition, scrap removal, trailer hauling, and general labour "
    "in North Bay and surrounding communities."
)
QUOTE_TITLE = "Request an Estimate | Bay Delivery North Bay"
QUOTE_DESCRIPTION = (
    "Send Bay Delivery your job details, location, access information, and photos to "
    "request an estimate for local moving, hauling, cleanup, delivery, demolition, "
    "and removal services."
)
APPROVED_SERVICE_AREAS = [
    "North Bay",
    "Callander",
    "Corbeil",
    "Astorville",
    "Bonfield",
    "Sturgeon Falls",
    "Powassan",
]
APPROVED_SERVICE_NAMES = [
    "Junk Removal & Dump Runs",
    "Moving Help",
    "Furniture & Appliance Delivery",
    "Property Cleanups",
    "Demolition & Tear-Out Help",
    "Scrap Metal Removal",
    "Trailer Hauling",
    "General Labour",
]


def _head_html(document: str) -> str:
    return document.split("</head>", 1)[0]


def _body_sha256(document: str) -> str:
    body = "<body" + document.split("<body", 1)[1]
    return hashlib.sha256(body.encode("utf-8")).hexdigest().upper()


def _normalized_public_shell(document: str, tag: str, shell_name: str) -> str:
    match = re.search(
        rf'<{tag}\b(?=[^>]*\bdata-public-shell="{shell_name}")[^>]*>.*?</{tag}>',
        document,
        re.DOTALL,
    )
    assert match is not None, f"Missing {shell_name} public shell"
    without_current_page = re.sub(r'\s+aria-current="page"', "", match.group(0))
    return re.sub(r"\s+", " ", without_current_page).strip()


def _nav_html(document: str, aria_label: str) -> str:
    match = re.search(
        rf'<nav\b(?=[^>]*\baria-label="{re.escape(aria_label)}")[^>]*>.*?</nav>',
        document,
        re.DOTALL,
    )
    assert match is not None, f"Missing navigation landmark: {aria_label}"
    return match.group(0)


def _quote_contract_sha256(document: str) -> str:
    start = document.index('<section class="quoteTrustStrip"')
    upload_start = document.index(
        '<div class="card hidden stageCard" id="uploadCard">',
        start,
    )
    depth = 0
    end: int | None = None
    for match in re.finditer(r"<div\b[^>]*>|</div\s*>", document[upload_start:], re.IGNORECASE):
        if match.group(0).lower().startswith("<div"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                end = upload_start + match.end()
                break
    assert end is not None, "Could not locate the end of #uploadCard"
    normalized = re.sub(r"\s+", " ", document[start:end]).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def _meta_content(head: str, attribute: str, value: str) -> str:
    matches = re.findall(
        rf'<meta\s+{attribute}="{re.escape(value)}"\s+content="([^"]*)"\s*/?>',
        head,
    )
    assert len(matches) == 1, f"Expected one meta tag for {attribute}={value}, found {len(matches)}"
    return matches[0]


def _json_ld_blocks(head: str) -> list[dict[str, object]]:
    blocks = re.findall(
        r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
        head,
        re.DOTALL,
    )
    return [json.loads(block) for block in blocks]


def _find_forbidden_json_keys(value: object, forbidden: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(key for key in value if key in forbidden)
        for nested_value in value.values():
            found.update(_find_forbidden_json_keys(nested_value, forbidden))
    elif isinstance(value, list):
        for nested_value in value:
            found.update(_find_forbidden_json_keys(nested_value, forbidden))
    return found


def test_homepage_has_approved_public_metadata() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    head = _head_html(index_html)

    assert re.findall(r"<title>(.*?)</title>", head) == [HOMEPAGE_TITLE]
    assert _meta_content(head, "name", "description") == HOMEPAGE_DESCRIPTION
    assert re.findall(r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>', head) == [
        f"{PUBLIC_SITE_ORIGIN}/"
    ]
    assert _meta_content(head, "property", "og:title") == HOMEPAGE_TITLE
    assert _meta_content(head, "property", "og:description") == HOMEPAGE_DESCRIPTION
    assert _meta_content(head, "property", "og:type") == "website"
    assert _meta_content(head, "property", "og:url") == f"{PUBLIC_SITE_ORIGIN}/"
    assert _meta_content(head, "property", "og:image") == SOCIAL_IMAGE_URL
    assert _meta_content(head, "property", "og:image:width") == "1200"
    assert _meta_content(head, "property", "og:image:height") == "630"
    assert _meta_content(head, "property", "og:image:alt") == "Bay Delivery — Fast. Reliable. Local."
    assert _meta_content(head, "name", "twitter:card") == "summary_large_image"
    assert _meta_content(head, "name", "twitter:title") == HOMEPAGE_TITLE
    assert _meta_content(head, "name", "twitter:description") == HOMEPAGE_DESCRIPTION
    assert _meta_content(head, "name", "twitter:image") == SOCIAL_IMAGE_URL


def test_homepage_has_valid_organization_structured_data() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    blocks = _json_ld_blocks(_head_html(index_html))

    assert len(blocks) == 1
    organization = blocks[0]
    assert organization["@context"] == "https://schema.org"
    assert organization["@type"] == "Organization"
    assert organization["name"] == "Bay Delivery"
    assert organization["url"] == f"{PUBLIC_SITE_ORIGIN}/"
    assert organization["logo"] == LOGO_URL
    assert organization["image"] == SOCIAL_IMAGE_URL
    assert organization["telephone"] == "+1-705-303-4409"
    assert organization["email"] == "BayDeliveryNB@gmail.com"

    service_areas = organization["areaServed"]
    assert isinstance(service_areas, list)
    assert service_areas == [
        {"@type": "Place", "name": area_name}
        for area_name in APPROVED_SERVICE_AREAS
    ]

    catalog = organization["hasOfferCatalog"]
    assert catalog == {
        "@type": "OfferCatalog",
        "name": "Bay Delivery services",
        "itemListElement": [
            {
                "@type": "Offer",
                "itemOffered": {
                    "@type": "Service",
                    "name": service_name,
                },
            }
            for service_name in APPROVED_SERVICE_NAMES
        ],
    }
    assert "serviceType" not in json.dumps(organization)
    assert _find_forbidden_json_keys(
        organization,
        {
            "address",
            "streetAddress",
            "postalCode",
            "openingHours",
            "priceRange",
            "AggregateRating",
            "aggregateRating",
            "Review",
            "review",
            "ratingValue",
            "reviewCount",
            "sameAs",
        },
    ) == set()


def test_quote_page_has_approved_public_metadata_without_structured_data() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    head = _head_html(quote_html)

    assert re.findall(r"<title>(.*?)</title>", head) == [QUOTE_TITLE]
    assert _meta_content(head, "name", "description") == QUOTE_DESCRIPTION
    assert re.findall(r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>', head) == [
        f"{PUBLIC_SITE_ORIGIN}/quote"
    ]
    assert _meta_content(head, "property", "og:title") == QUOTE_TITLE
    assert _meta_content(head, "property", "og:description") == QUOTE_DESCRIPTION
    assert _meta_content(head, "property", "og:type") == "website"
    assert _meta_content(head, "property", "og:url") == f"{PUBLIC_SITE_ORIGIN}/quote"
    assert _meta_content(head, "property", "og:image") == SOCIAL_IMAGE_URL
    assert _meta_content(head, "property", "og:image:width") == "1200"
    assert _meta_content(head, "property", "og:image:height") == "630"
    assert _meta_content(head, "property", "og:image:alt") == "Bay Delivery — Fast. Reliable. Local."
    assert _meta_content(head, "name", "twitter:card") == "summary_large_image"
    assert _meta_content(head, "name", "twitter:title") == QUOTE_TITLE
    assert _meta_content(head, "name", "twitter:description") == QUOTE_DESCRIPTION
    assert _meta_content(head, "name", "twitter:image") == SOCIAL_IMAGE_URL
    assert _json_ld_blocks(head) == []


def test_shared_public_shell_body_baseline_and_asset_references() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert _body_sha256(index_html) == "B5FF22FBC1EC72EF80394FF43B2534BC20D439493837CB9E8F7F8A2806991D40"
    assert _body_sha256(quote_html) == "3B20A22A90F543D1770596FEEA2A97E009D7FD2C73F1195D088AA675C473EA59"
    assert re.findall(r'<link\s+rel="stylesheet"\s+href="([^"]+)"', index_html) == [
        "/static/public.css",
        "/static/site.css"
    ]
    assert re.findall(r'<link\s+rel="stylesheet"\s+href="([^"]+)"', quote_html) == [
        "/static/public.css",
        "/static/quote.css"
    ]
    assert re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', index_html) == [
        "/static/public.js",
        "/static/site.js",
    ]
    assert re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', quote_html) == [
        "/static/public.js",
        "/static/quote.js"
    ]


def test_public_pages_load_shared_shell_assets_in_order() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert re.findall(r'<link\s+rel="stylesheet"\s+href="([^"]+)"', index_html) == [
        "/static/public.css",
        "/static/site.css",
    ]
    assert re.findall(r'<link\s+rel="stylesheet"\s+href="([^"]+)"', quote_html) == [
        "/static/public.css",
        "/static/quote.css",
    ]
    assert re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', index_html) == [
        "/static/public.js",
        "/static/site.js",
    ]
    assert re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', quote_html) == [
        "/static/public.js",
        "/static/quote.js",
    ]
    for document in [index_html, quote_html]:
        for script_tag in re.findall(r"<script\b[^>]*>", document):
            if "src=" in script_tag:
                assert " defer" in script_tag


def test_public_pages_do_not_add_inline_executable_javascript() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    for document in [index_html, quote_html]:
        inline_scripts = [
            attrs
            for attrs, _body in re.findall(r"<script\b([^>]*)>(.*?)</script>", document, re.DOTALL)
            if "src=" not in attrs
        ]
        assert all('type="application/ld+json"' in attrs for attrs in inline_scripts)
        assert "onclick=" not in document
        assert "onload=" not in document
    assert len(re.findall(r'<script\s+type="application/ld\+json">', index_html)) == 1
    assert re.findall(r'<script\s+type="application/ld\+json">', quote_html) == []


def test_homepage_json_ld_source_remains_unchanged() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    block = re.search(
        r'<script type="application/ld\+json">.*?</script>',
        index_html,
        re.DOTALL,
    )
    assert block is not None
    assert hashlib.sha256(block.group(0).encode("utf-8")).hexdigest().upper() == (
        "BFCDEE003C9CAA7D1490BAD38A2DF66E78A0B65C42CAD9699B642843D42E2A72"
    )


def test_public_shell_progressive_enhancement_and_breakpoint_contract() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    public_css = Path("static/public.css").read_text(encoding="utf-8")
    public_js = Path("static/public.js").read_text(encoding="utf-8")

    for document in [index_html, quote_html]:
        assert '<html lang="en" class="bd-no-js">' in document
        assert re.search(
            r'<button(?=[^>]*\bid="publicMenuToggle")(?=[^>]*\btype="button")'
            r'(?=[^>]*\baria-controls="publicMobileNav")'
            r'(?=[^>]*\baria-expanded="false")'
            r'(?=[^>]*\baria-label="Open navigation menu")'
            r'(?=[^>]*\bhidden)[^>]*>',
            document,
        )
        mobile_nav_tag = re.search(
            r'<nav(?=[^>]*\bid="publicMobileNav")(?=[^>]*\bdata-state="open")[^>]*>',
            document,
        )
        assert mobile_nav_tag is not None
        assert " hidden" not in mobile_nav_tag.group(0)

    assert ".bd-public-mobile-nav[hidden]" in public_css
    assert "display: none;" in public_css
    assert "@media (min-width: 1180px)" in public_css
    assert "@media (max-width: 640px)" in public_css
    assert "@media (min-width: 641px) and (max-width: 1179px)" in public_css
    assert "768px" not in public_css
    assert 'matchMedia("(min-width: 1180px)")' in public_js
    assert "768px" not in public_js
    assert 'root.classList.replace("bd-no-js", "bd-js")' in public_js
    assert 'menuToggle.setAttribute("aria-label", "Open navigation menu")' in public_js
    assert 'menuToggle.setAttribute("aria-label", "Close navigation menu")' in public_js


def test_public_shell_design_tokens_focus_and_typography_scope() -> None:
    public_css = Path("static/public.css").read_text(encoding="utf-8")
    for token in [
        "--bd-black: #111111;",
        "--bd-near-black: #171717;",
        "--bd-red: #d92d27;",
        "--bd-red-hover: #a92824;",
        "--bd-cream: #fff4e4;",
        "--bd-white: #ffffff;",
        "--bd-text: #1f2933;",
        "--bd-muted: #5d6875;",
        "--bd-border-color: #e6ded2;",
        "--bd-border-rule: 1px solid var(--bd-border-color);",
        "--bd-success: #18794e;",
        "--bd-warning: #b45309;",
        "--bd-error: #b42318;",
        "--bd-focus: rgba(217, 45, 39, 0.34);",
        '--bd-font-body: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;',
        '--bd-font-heading: "Arial Narrow", "Roboto Condensed", "Helvetica Neue", Arial, sans-serif;',
    ]:
        assert token in public_css
    assert "outline: 3px solid var(--bd-red);" in public_css
    assert "outline-offset: 3px;" in public_css
    assert "box-shadow: 0 0 0 5px var(--bd-focus);" in public_css
    assert not re.search(r"(?:^|,)\s*h[123](?:\s*,|\s*\{)", public_css, re.MULTILINE)


def test_public_page_landmarks_skip_link_and_unique_ids() -> None:
    for path in [Path("static/index.html"), Path("static/quote.html")]:
        document = path.read_text(encoding="utf-8")
        body = document.split("<body", 1)[1]
        first_focusable = re.search(r'<(?:a|button|input|select|textarea)\b[^>]*>', body)
        assert first_focusable is not None
        assert 'class="bd-skip-link"' in first_focusable.group(0)
        assert 'href="#main-content"' in first_focusable.group(0)
        assert len(re.findall(r'<main\b[^>]*\bid="main-content"[^>]*\btabindex="-1"[^>]*>', document)) == 1
        assert len(re.findall(r"<main\b", document)) == 1
        assert len(re.findall(r"<header\b", document)) == 1
        assert len(re.findall(r"<footer\b", document)) == 1
        assert len(re.findall(r"<h1\b", document)) == 1
        ids = re.findall(r'\bid="([^"]+)"', document)
        assert len(ids) == len(set(ids)), f"Duplicate IDs in {path}"


def test_public_shell_navigation_targets_and_current_page_state() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    expected_hrefs = [
        "/",
        "/#servicesTitle",
        "/#howTitle",
        "/#trustFaqTitle",
        "/#workTitle",
        "/quote",
    ]

    for document, current_href in [(index_html, "/"), (quote_html, "/quote")]:
        for label in ["Primary navigation", "Mobile navigation"]:
            nav = _nav_html(document, label)
            assert re.findall(r'<a\s+href="([^"]+)"(?:\s+aria-current="page")?>', nav) == expected_hrefs
            current_links = re.findall(
                r'<a\s+href="([^"]+)"\s+aria-current="page">',
                nav,
            )
            assert current_links == [current_href]
        assert document.count('aria-current="page"') == 2

    homepage_ids = set(re.findall(r'\bid="([^"]+)"', index_html))
    for href in expected_hrefs:
        if href.startswith("/#"):
            assert href[2:] in homepage_ids
    assert "/privacy" not in index_html + quote_html
    assert "/accessibility" not in index_html + quote_html
    assert "facebook.com" not in _normalized_public_shell(index_html, "header", "header")
    assert "google.com/search" not in _normalized_public_shell(index_html, "header", "header")


def test_copied_public_shells_match_after_current_page_normalization() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    assert _normalized_public_shell(index_html, "header", "header") == _normalized_public_shell(
        quote_html,
        "header",
        "header",
    )
    assert _normalized_public_shell(index_html, "footer", "footer") == _normalized_public_shell(
        quote_html,
        "footer",
        "footer",
    )


def test_public_javascript_is_menu_only_and_focus_safe() -> None:
    public_js = Path("static/public.js").read_text(encoding="utf-8")

    for forbidden in [
        "fetch(",
        "XMLHttpRequest",
        "FormData",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "/quote/calculate",
        "/quote/upload-photos",
        "quote_id",
        "accept_token",
    ]:
        assert forbidden not in public_js
    assert "mobileNav.contains(document.activeElement)" in public_js
    assert "document.activeElement === menuToggle" in public_js
    assert "publicLogo.focus({ preventScroll: true })" in public_js
    assert "event.preventDefault()" not in public_js
    assert 'typeof desktopQuery.addEventListener === "function"' in public_js
    assert 'typeof desktopQuery.addListener === "function"' in public_js
    assert 'desktopQuery.addEventListener("change", handleDesktopChange)' in public_js
    assert "desktopQuery.addListener(handleDesktopChange)" in public_js
    assert public_js.index("if (!desktopListenerInstalled) return;") < public_js.rindex(
        "setMenuState(false)"
    )


def test_complete_quote_content_contract_remains_unchanged() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    assert _quote_contract_sha256(quote_html) == (
        "BABF0E971EEB9A3D627F85BDF0D6D6F7F92BB5F2CCB379BD2DC28455B08CC4CB"
    )
    assert quote_html.count('id="quoteForm"') == 1
    assert Path("static/quote.js").read_text(encoding="utf-8")


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\xff\xd8"), f"{path} is not a JPEG file"
    offset = 2
    while offset < len(data):
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += segment_length
    raise AssertionError(f"Could not read JPEG dimensions for {path}")


def _webp_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP", f"{path} is not WebP"
    chunk = data[12:16]
    if chunk == b"VP8 ":
        assert data[23:26] == b"\x9d\x01\x2a", f"Missing VP8 frame header in {path}"
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    raise AssertionError(f"Unsupported WebP chunk {chunk!r} in {path}")


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
    logo_asset = Path("static/assets/brand/bay-delivery-logo-horizontal-header.png")
    social_asset = Path("static/assets/brand/bay-delivery-social-share-1200x630.png")

    assert logo_asset.exists()
    width, height = struct.unpack(">II", logo_asset.read_bytes()[16:24])
    assert width == 600
    assert height == 177
    assert logo_asset.stat().st_size < 300_000
    assert social_asset.exists()
    social_width, social_height = struct.unpack(">II", social_asset.read_bytes()[16:24])
    assert social_width == 1200
    assert social_height == 630
    assert social_asset.stat().st_size < 500_000
    assert 'src="/static/assets/brand/bay-delivery-logo-horizontal-header.png"' in index_html
    assert 'alt="Bay Delivery"' in index_html
    assert f'<meta property="og:image" content="{SOCIAL_IMAGE_URL}" />' in index_html
    assert f'<meta name="twitter:image" content="{SOCIAL_IMAGE_URL}" />' in index_html
    assert 'href="/quote">Request a Quote<' in index_html
    assert 'href="tel:+17053034409"' in index_html
    assert 'href="tel:+12493588087"' in index_html
    assert "705-303-4409" in index_html
    assert "249-358-8087" in index_html
    assert "Get My Fast Estimate" not in index_html


def test_quote_page_uses_current_logo_asset() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    logo_asset = Path("static/assets/brand/bay-delivery-logo-horizontal-header.png")

    assert logo_asset.exists()
    assert 'src="/static/assets/brand/bay-delivery-logo-horizontal-header.png"' in quote_html
    assert 'alt="Bay Delivery"' in quote_html
    assert 'src="/static/images/bay-delivery-logo.png"' not in quote_html
    assert 'src="/static/images/logo.jpg"' not in quote_html
    assert 'href="tel:+17053034409"' in quote_html
    assert 'href="tel:+12493588087"' not in quote_html
    assert "705-303-4409" in quote_html
    assert "Call/Text Austin 249-358-8087" not in quote_html


def test_quote_page_owns_public_stylesheet_boundary() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="/static/quote.css" />' in quote_html
    assert '<link rel="stylesheet" href="/static/admin.css" />' not in quote_html

    for selector in [
        "body.quotePage",
        ".quotePage .quote-content h1",
        ".quotePage .quote-content h2",
        ".quotePage .quote-content h3",
        ".quotePage label",
        ".quotePage .muted",
        ".quotePage .row",
        ".quotePage .card",
        ".quotePage .btn",
        ".quotePage .btn:hover",
        ".quotePage .btn:disabled",
        ".quotePage input",
        ".quotePage select",
        ".quotePage textarea",
        ".quotePage input:focus",
        ".quotePage select:focus",
        ".quotePage textarea:focus",
        ".quotePage input::placeholder",
        ".quotePage textarea::placeholder",
    ]:
        assert selector in quote_css

    if "var(--brand-red)" in quote_css:
        quote_scope = re.search(r"\.quotePage\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
        assert quote_scope is not None
        assert "--brand-red: var(--quote-accent);" in quote_scope.group("body")


def test_quote_heading_styles_are_scoped_to_quote_content() -> None:
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    for level in ["h1", "h2", "h3"]:
        assert re.search(
            rf"(?m)^\.quotePage \.quote-content {level}\s*(?:,|\{{)",
            quote_css,
        )
        assert not re.search(
            rf"(?m)^\.quotePage {level}\s*(?:,|\{{)",
            quote_css,
        )


def test_quote_page_review_followup_layout_guards() -> None:
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    checkbox_match = re.search(r"\.quotePage \.checkboxLabel\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert checkbox_match is not None
    checkbox_body = checkbox_match.group("body")
    assert "display: grid;" in checkbox_body
    assert "grid-template-columns: 18px 1fr;" in checkbox_body
    assert "align-items: start;" in checkbox_body

    hidden_row_match = re.search(r"\.quotePage \.row\.hidden\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert hidden_row_match is not None
    assert "display: none;" in hidden_row_match.group("body")

    assert "@media (max-width: 980px)" in quote_css
    mobile_css = quote_css[quote_css.index("@media (max-width: 980px)") :]
    assert re.search(r"\.quotePage \.row\s*\{(?P<body>.*?)\n\s*\}", mobile_css, re.S)
    mobile_row_body = re.search(r"\.quotePage \.row\s*\{(?P<body>.*?)\n\s*\}", mobile_css, re.S).group("body")
    assert "grid-template-columns: 1fr;" in mobile_row_body


def test_quote_page_dark_panel_text_contrast_is_scoped() -> None:
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    form_title_match = re.search(r"\.quotePage \.formSectionTitle\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert form_title_match is not None
    assert "color: #f5f8fd;" in form_title_match.group("body")

    dark_lead_match = re.search(
        r"\.quotePage \.formSection \.sectionLead,\s*"
        r"\.quotePage \.detailPanel \.sectionLead,\s*"
        r"\.quotePage \.customerFlowGroup \.muted\s*\{(?P<body>.*?)\n\}",
        quote_css,
        re.S,
    )
    assert dark_lead_match is not None
    assert "color: rgba(213, 222, 235, 0.86);" in dark_lead_match.group("body")


def test_homepage_premium_polish_stays_local_service_first() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    hero_asset = Path("static/images/homepage/bay-delivery-wood-pallet-debris-haul-hero.webp")

    assert hero_asset.exists()
    assert 'src="/static/images/homepage/bay-delivery-wood-pallet-debris-haul-hero.webp"' in index_html
    assert 'src="/static/images/homepage-hero-full.jpg"' not in index_html
    assert 'src="/static/assets/bay-delivery-premium-hero.png"' not in index_html
    assert "working_assets/" not in index_html
    assert "working_assets/" not in site_css
    assert "Junk removal, moving help &amp; hauling in North Bay." in index_html
    assert "Serving North Bay &amp; surrounding area" in index_html
    assert "Wood pallets and renovation debris loaded for hauling by Bay Delivery" in index_html
    assert 'class="serviceGrid"' in index_html
    assert 'class="homeSectionInner homeTrustStrip__grid"' in index_html
    assert "var(--bd-red)" in site_css
    assert ".homeHero__media" in site_css
    assert ".homeTrustStrip" in site_css
    assert "overflow-x: hidden;" in site_css
    assert "--quote-accent: #d92d27;" in quote_css
    assert "--brand-red: #d92d27;" in admin_css


def test_pr320_review_followup_readability_and_hero_asset_are_safe() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")
    hero_asset = Path("static/images/homepage/bay-delivery-wood-pallet-debris-haul-hero.webp")

    width, height = _webp_dimensions(hero_asset)
    assert width == 1600
    assert height == 900
    assert 100_000 < hero_asset.stat().st_size < 450_000
    assert "image/jpeg" not in hero_asset.read_bytes().decode("latin1", errors="ignore")
    assert "705-303-4409" not in hero_asset.read_bytes().decode("latin1", errors="ignore")
    assert "object-fit: cover;" in site_css
    assert "aspect-ratio: 16 / 9;" in site_css
    assert "GET A QUOTE" not in hero_asset.read_bytes().decode("latin1", errors="ignore")
    assert "Minimum 4 hours. Minimum crew 2." not in index_html
    assert 'class="homeMobileActions"' in index_html
    assert ".quotePage .quoteHeroShell" in quote_css

    assert "color: #f5f8fd;" in re.search(
        r"\.quotePage input,\s*\.quotePage select,\s*\.quotePage textarea\s*\{(?P<body>.*?)\n\}",
        quote_css,
        re.S,
    ).group("body")
    assert "color: rgba(213, 222, 235, 0.86);" in re.search(
        r"\.quotePage input::placeholder,\s*\.quotePage textarea::placeholder\s*\{(?P<body>.*?)\n\}",
        quote_css,
        re.S,
    ).group("body")
    assert "color: #f5f8fd;" in re.search(
        r"\.quotePage \.formSection label,\s*\.quotePage \.detailPanel label,\s*\.quotePage \.customerFlowGroup label\s*\{(?P<body>.*?)\n\}",
        quote_css,
        re.S,
    ).group("body")
    assert "background: rgba(255, 255, 255, 0.96);" in quote_css
    assert "color: var(--quote-text);" in re.search(
        r"\.quoteAmountCard strong\s*\{(?P<body>.*?)\n\}",
        quote_css,
        re.S,
    ).group("body")
    assert ".quoteResultBreakdown," in quote_css
    assert ".estimateDetails" in quote_css

def test_static_pages_reference_favicon_without_browser_fallback() -> None:
    """Ensure routed HTML pages avoid browser fallback requests for /favicon.ico."""
    shared_favicon_path = Path("static/favicon.svg")
    homepage_favicon_path = Path("static/assets/brand/bay-delivery-favicon-512.png")

    assert shared_favicon_path.exists()
    assert shared_favicon_path.stat().st_size < 2048
    assert homepage_favicon_path.exists()
    assert homepage_favicon_path.stat().st_size < 500_000

    shared_favicon_link = '<link rel="icon" type="image/svg+xml" href="/static/favicon.svg" />'
    homepage_favicon_link = '<link rel="icon" type="image/png" sizes="512x512" href="/static/assets/brand/bay-delivery-favicon-512.png" />'

    expected_links = {
        Path("static/index.html"): homepage_favicon_link,
        Path("static/quote.html"): homepage_favicon_link,
        Path("static/admin.html"): shared_favicon_link,
        Path("static/admin_mobile.html"): shared_favicon_link,
        Path("static/admin_uploads.html"): shared_favicon_link,
    }

    for html_path, favicon_link in expected_links.items():
        content = html_path.read_text(encoding="utf-8")
        assert favicon_link in content, f"{html_path} is missing the expected favicon link"
        assert "/favicon.ico" not in content


def test_quote_page_brand_header_matches_homepage_direction() -> None:
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    body_match = re.search(r"body\.quotePage\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert body_match is not None
    assert "font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;" in body_match.group("body")

    logo_match = re.search(r"\.quotePage \.brandLogo\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert logo_match is not None
    logo_body = logo_match.group("body")
    assert "height: 60px;" in logo_body
    assert "max-width: 260px;" in logo_body
    assert "border-radius: 0;" in logo_body
    assert "background: transparent;" in logo_body
    assert "border: 0;" in logo_body
    assert "box-shadow: none;" in logo_body
    assert "padding: 0;" in logo_body
    for old_square_logo_rule in [
        "width: 58px;",
        "height: 58px;",
        "border-radius: 13px;",
        "border: 2px solid",
        "padding: 5px;",
        "box-shadow: 0 8px 16px",
    ]:
        assert old_square_logo_rule not in logo_body

    topbar_match = re.search(r"\.quotePage \.topbar\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert topbar_match is not None
    topbar_body = topbar_match.group("body")
    assert "display: flex;" in topbar_body
    assert "background: transparent;" in topbar_body
    assert "box-shadow: none;" in topbar_body

    nav_match = re.search(r"\.quotePage \.topbar \.badgeLink\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert nav_match is not None
    nav_body = nav_match.group("body")
    assert "border-radius: 999px;" in nav_body
    assert "background: rgba(255, 255, 255, 0.82);" in nav_body
    assert "box-shadow: 0 8px 18px rgba(7, 24, 39, 0.08);" in nav_body
    assert ".quotePage .toplinks" in quote_css

    button_match = re.search(r"\.quotePage \.btn\s*\{(?P<body>.*?)\n\}", quote_css, re.S)
    assert button_match is not None
    assert "font-family: inherit;" in button_match.group("body")


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

    assert 'class="homeSection serviceAreaSection"' in index_html
    assert "Serving North Bay and surrounding areas." in index_html
    assert "Bay Delivery serves North Bay, Callander, Corbeil, Astorville, Bonfield, Sturgeon Falls, and Powassan" in index_html
    for area_name in ["Callander", "Powassan", "Bonfield", "Astorville", "Corbeil", "Sturgeon Falls"]:
        assert area_name in index_html
    assert "Availability and travel costs depend on the job location and scope." in index_html
    assert "Photos are encouraged when available" in index_html
    assert "Cash totals are shown without HST." in index_html
    assert "EMT/e-transfer totals include 13% HST." in index_html
    assert "Submitting a quote or booking request does not reserve a date." in index_html
    assert "Bay Delivery confirms the job details and scheduling directly." in index_html
    assert ".serviceAreaSection" in site_css
    assert ".faqList" in site_css


def test_homepage_mobile_actions_are_hidden_by_default_and_mobile_only() -> None:
    site_css = Path("static/site.css").read_text(encoding="utf-8")

    base_match = re.search(r"\.homeMobileActions\s*\{(?P<body>.*?)\n\}", site_css, re.DOTALL)
    assert base_match is not None
    base_body = base_match.group("body")
    assert "display: none;" in base_body
    assert "display: grid;" not in base_body
    mobile_match = re.search(
        r"@media \(max-width: 720px\)\s*\{(?P<body>.*?\.homeMobileActions:not\(\[hidden\]\)\s*\{(?P<call_body>.*?)\n  \}.*?)\n\}",
        site_css,
        re.DOTALL,
    )
    assert mobile_match is not None
    mobile_call_body = mobile_match.group("call_body")
    assert "display: grid;" in mobile_call_body
    assert "env(safe-area-inset-bottom)" in mobile_call_body


def test_quote_page_phase_a_guidance_copy_is_present() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "Start with a simple estimate." in quote_html
    assert "Quick answers now. Choose a service, describe the job, and add optional details if they help." in quote_html
    assert "Share job details" in quote_html
    assert "Review your estimate" in quote_html
    assert "Accept or decline" in quote_html
    assert "Send a booking request" in quote_html
    assert "Add optional photos" in quote_html
    assert "1. Choose a service" in quote_html
    assert "2. Describe the job" in quote_html
    assert "3. Optional details" in quote_html
    assert "Access and location" in quote_html
    assert "Special or heavy items" in quote_html
    assert "4. Your contact details" in quote_html
    assert 'id="serviceDetailsSummary"' in quote_html
    assert 'id="serviceDetailsLead"' in quote_html
    assert 'id="serviceDetailsPanel" class="detailPanel"' in quote_html
    assert 'id="serviceDetailsPanel" class="detailPanel" open' not in quote_html
    assert "Answer what you can. Not sure is okay." in quote_html
    assert "What needs to be moved, removed, delivered, or cleaned up?" in quote_html
    assert "Where is it located?" in quote_html
    assert "Any special or heavy items?" in quote_html
    assert "Required for moves and deliveries." in quote_html
    assert "Use full kitchen-size bags as a rough count." in quote_html
    assert "Most jobs are 5-10 bags. Adjust if needed." in quote_html
    assert "Heavy items help Bay Delivery bring the right setup." in quote_html
    assert "Choose the closest match. Add a note if you are not sure." in quote_html
    assert "After you submit your booking request, add photos here if they help Bay Delivery confirm scope." in quote_html
    assert "After you see your estimate, you can accept and share your preferred day and time window." in quote_html
    assert "How did you hear about us? (optional)" in quote_html
    assert quote_html.index('<label for="description">Job description</label>') < quote_html.index('id="serviceDetailsPanel"')
    assert quote_html.count("Tell us about the job") == 0
    assert "Start your estimate" in quote_html
    assert "photoHelpGroup" not in quote_html
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
    assert ".detailPanel:not([open])" in quote_css


def test_quote_page_mobile_polish_preserves_one_form_flow() -> None:
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    quote_css = Path("static/quote.css").read_text(encoding="utf-8")

    assert "@media (max-width: 720px)" in quote_css
    assert ".progressCard" in quote_css
    assert "overflow-x: auto;" in quote_css
    assert "scroll-snap-type: x proximity;" in quote_css
    mobile_quote_css = quote_css[quote_css.index("@media (max-width: 720px)") :]
    mobile_content_match = re.search(r"\.quotePage \.quote-content\s*\{(?P<body>.*?)\n\s*\}", mobile_quote_css, re.S)
    assert mobile_content_match is not None
    assert "padding-bottom: 92px;" in mobile_content_match.group("body")
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
    for label in ["Job details", "Access and location", "Special or heavy items"]:
        assert f'<p class="customerFlowLabel">{label}</p>' in quote_html
    assert '<p class="customerFlowLabel">5. Photos can help</p>' not in quote_html

    assert "admin dashboard" not in index_html.lower()
    assert "Bay Delivery confirms the job details and scheduling directly." in index_html

    assert re.search(
        r"\.quotePage,\s*\.quotePage \*,\s*\.quotePage \*::before,\s*\.quotePage \*::after\s*\{[^}]*box-sizing:\s*border-box;",
        quote_css,
        re.S,
    )

    mobile_quote_css = quote_css[quote_css.index("@media (max-width: 720px)") :]
    assert "overflow-x: hidden;" not in mobile_quote_css
    assert re.search(r"\.quotePage \.container > \*\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)
    assert re.search(r"\.quoteTrustStrip\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)
    assert re.search(r"\.quoteTrustStrip\s*\{[^}]*overflow-x:\s*auto;", mobile_quote_css, re.S)
    assert re.search(r"\.flowProgress\s*\{[^}]*max-width:\s*100%;", mobile_quote_css, re.S)
    assert re.search(r"\.flowStep\s*\{[^}]*min-width:\s*0;", mobile_quote_css, re.S)

    mobile_site_css = site_css[site_css.index("@media (max-width: 720px)") :]
    assert re.search(r"\.homeMobileActions:not\(\[hidden\]\)\s*\{[^}]*display:\s*grid;", mobile_site_css, re.S)
    assert re.search(r"\.homeMobileActions:not\(\[hidden\]\)\s*\{[^}]*position:\s*fixed;", mobile_site_css, re.S)
    assert "env(safe-area-inset-bottom)" in mobile_site_css
    assert re.search(r"\.homeMobileActions a\s*\{[^}]*min-height:\s*var\(--bd-button-height\);", mobile_site_css, re.S)
    assert re.search(r"\.homeMobileActions a\s*\{[^}]*white-space:\s*nowrap;", mobile_site_css, re.S)


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
    assert 'id="adminProtectedDashboard" class="protectedDashboard" hidden aria-hidden="true"' in admin_html
    assert not re.search(r"\sstyle=", admin_html)
    assert 'class="card adminHero adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert 'class="dashboardGrid adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert 'class="card dataCard mt18 adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true"' in admin_html
    assert 'id="scheduleModal" class="modal" hidden aria-hidden="true"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js
    assert "const adminProtectedSections = Array.from(document.querySelectorAll(\"[data-admin-protected='true']\"));" in admin_js
    assert "adminProtectedSections.forEach((section) => {" in admin_js
    assert "admin-authenticated" in admin_js
    assert "style.display" not in admin_js
    assert 'setAttribute("style"' not in admin_js
    assert 'removeAttribute("style"' not in admin_js
    assert 'adminProtectedDashboard.removeAttribute("hidden");' in admin_js
    assert 'adminProtectedDashboard.setAttribute("aria-hidden", "false");' in admin_js
    assert 'adminProtectedDashboard.setAttribute("hidden", "");' in admin_js
    assert 'adminProtectedDashboard.setAttribute("aria-hidden", "true");' in admin_js
    assert 'modal.removeAttribute("hidden");' in admin_js
    assert 'modal.setAttribute("aria-hidden", "false");' in admin_js
    assert 'modal.setAttribute("hidden", "");' in admin_js
    assert 'modal.setAttribute("aria-hidden", "true");' in admin_js
    assert ".adminPage.admin-authenticated .protectedDashboard" in admin_css
    assert ".protectedDashboard[hidden]" in admin_css
    assert ".adminProtectedSection[hidden]" in admin_css
    assert ".modal[hidden]" in admin_css

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
    for heading in ["Screenshot Intake Guidance (Read-Only)", "Screenshot Intake History (Read-Only)"]:
        assert f"<summary>{heading}</summary>" in protected_block
        assert f"<summary>{heading}</summary>" not in remainder

    assert 'id="adminProtectedDashboard"' in admin_html
    assert "setProtectedDashboardVisible(true);" in admin_js
    assert "setProtectedDashboardVisible(false);" in admin_js


def test_desktop_admin_uses_branded_dark_theme_tokens() -> None:
    """Ensure desktop admin visual polish stays aligned with the public Bay Delivery theme."""
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")

    for expected in [
        "--admin-bg: #071827;",
        "--brand-red: #d92d27;",
        "--brand-red-deep: #a92824;",
        "linear-gradient(180deg, rgba(9, 36, 58, 0.78), transparent 340px)",
        "linear-gradient(135deg, rgba(7, 24, 39, 0.98), rgba(18, 31, 44, 0.97))",
        "background: var(--brand-red);",
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


def test_desktop_admin_includes_collapsed_gpt_notes_display_only() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    assert '<details id="gptAdminNotesSection" class="adminReferenceDetails gptAdminNotesSection adminProtectedSection" data-admin-protected="true" hidden aria-hidden="true">' in admin_html
    assert '<summary>GPT Notes (Advisory)</summary>' in admin_html
    assert "GPT-generated advisory notes." in admin_html
    assert "Does not change pricing, status, schedule, payment, or customer messages." in admin_html
    assert "Review before acting." in admin_html
    assert 'id="gptAdminNotesBox"' in admin_html
    assert "gptAdminNotesSection" in admin_css
    assert "gptAdminNoteCard" in admin_css
    assert 'const notes = await fetchJSON("/admin/api/gpt-notes");' in admin_js
    assert "async function refreshGptAdminNotesBestEffort()" in admin_js
    assert "function renderGptAdminNotes(notes)" in admin_js
    assert "void refreshGptAdminNotesBestEffort();" in admin_js
    assert "GPT notes could not load. Core admin data is still available." in admin_js
    assert "No GPT advisory notes yet." in admin_js
    for field_name in [
        "created_at",
        "related_entity_type",
        "related_entity_id",
        "note_type",
        "title",
        "summary",
        "recommendation",
        "customer_message_draft",
        "risk_flags",
        "follow_up_needed",
        "review_status",
        "server_grounding_revision",
        "caller_grounding_revision",
    ]:
        assert field_name in admin_js

    section_start = admin_html.index('id="gptAdminNotesSection"')
    section_tag = admin_html[admin_html.rfind("<details", 0, section_start):admin_html.index(">", section_start)]
    assert " open" not in section_tag

    render_match = re.search(
        r"function renderGptAdminNotes\(notes\) \{(?P<body>.*?)\n\}\n\nfunction renderGptAdminNotesError",
        admin_js,
        re.S,
    )
    assert render_match is not None
    render_body = render_match.group("body")
    assert "textContent" in render_body
    assert "innerHTML" not in render_body
    assert "insertAdjacentHTML" not in render_body

    for public_or_mobile_asset in [mobile_html, mobile_js, quote_html, quote_js, index_html]:
        assert "GPT Notes" not in public_or_mobile_asset
        assert "/admin/api/gpt-notes" not in public_or_mobile_asset
        assert "gptAdminNotes" not in public_or_mobile_asset


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


def test_desktop_admin_includes_booking_notification_status_visibility_only() -> None:
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")
    quote_js = Path("static/quote.js").read_text(encoding="utf-8")

    assert "function createBookingNotificationStatus(item)" in admin_js
    assert "item.booking_notification || {}" in admin_js
    assert "Internal alert sent" in admin_js
    assert "Internal alert pending" in admin_js
    assert "Internal alert not sent" in admin_js
    assert "Internal alert failed" in admin_js
    assert "Internal alert not recorded" in admin_js
    assert "Setup/off" in admin_js
    assert "Config needed" in admin_js
    assert "Review manually" in admin_js
    assert "tdTotals.append(stWrap, cash, emt, createBookingNotificationStatus(r));" in admin_js
    assert ".bookingNotificationStatus" in admin_css
    assert ".bookingNotificationMeta" in admin_css

    for forbidden in [
        "createBookingNotificationStatus",
        "booking_notification",
        "Internal alert",
        "notification_attempt",
    ]:
        assert forbidden not in mobile_html
        assert forbidden not in mobile_js
        assert forbidden not in quote_html
        assert forbidden not in quote_js

    for forbidden_endpoint in ["/sms", "/email", "/messages"]:
        assert forbidden_endpoint not in admin_js


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


def test_desktop_admin_collapsible_section_contract() -> None:
    admin_html = Path("static/admin.html").read_text(encoding="utf-8")
    admin_js = Path("static/admin.js").read_text(encoding="utf-8")
    admin_css = Path("static/admin.css").read_text(encoding="utf-8")
    mobile_html = Path("static/admin_mobile.html").read_text(encoding="utf-8")
    mobile_js = Path("static/admin_mobile.js").read_text(encoding="utf-8")

    expected_sections = {
        "adminQuotesSection": ("Recent Estimates", "quotesBox", True),
        "adminRequestsSection": ("Booking Requests", "requestsBox", True),
        "adminJobsSection": ("Jobs", "jobsBox", True),
        "adminFollowupHelperSection": ("Follow-Up Message Helper", "followupMessageDraft", False),
        "adminProfitReportSection": ("Completed Job Profit Review", "profitReportBox", False),
    }
    for section_id, (heading, render_target, should_default_open) in expected_sections.items():
        assert admin_html.count(f'id="{section_id}"') == 1
        section_match = re.search(
            rf'<details id="{section_id}"(?P<attrs>[^>]*)>\s*<summary class="sectionHeader compact adminSectionSummary">(?P<summary>.*?)</summary>',
            admin_html,
            re.S,
        )
        assert section_match is not None
        attrs = section_match.group("attrs")
        summary = section_match.group("summary")
        assert "adminSectionDetails" in attrs
        assert f"<h3>{heading}</h3>" in summary
        assert (re.search(r"\sopen(?:\s|>|$)", attrs) is not None) is should_default_open
        assert admin_html.count(f'id="{render_target}"') == 1

    for section_id in ["adminFollowupHelperSection", "adminJobsSection", "adminProfitReportSection"]:
        section_start = admin_html.index(f'id="{section_id}"')
        section_tag = admin_html[admin_html.rfind("<details", 0, section_start):admin_html.index(">", section_start)]
        assert 'data-admin-protected="true"' in section_tag
        assert 'hidden aria-hidden="true"' in section_tag

    for always_visible in ["adminOpsBoardSection", "acceptedNotBookedQueueSection"]:
        assert f'<div id="{always_visible}"' in admin_html
        assert f'<details id="{always_visible}"' not in admin_html

    assert "function openAdminSectionForFocus(target)" in admin_js
    focus_body = re.search(
        r"function focusAdminSection\(targetId, label\) \{(?P<body>.*?)\n\}\n\nfunction createOpsQueueShortcutButton",
        admin_js,
        re.S,
    )
    assert focus_body is not None
    assert "openAdminSectionForFocus(target);" in focus_body.group("body")
    assert ".open = true;" in admin_js
    assert ".adminSectionDetails" in admin_css
    assert ".adminSectionSummary" in admin_css

    for marker in ["adminSectionDetails", "adminSectionSummary", "Follow-Up Message Helper", "Completed Job Profit Review"]:
        assert marker not in mobile_html
        assert marker not in mobile_js


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

    contact_html = index_html[index_html.index('class="homeSection contactSection"'):index_html.index('</main>')]
    assert "Start with a clear estimate." in contact_html
    assert contact_html.count('href="/quote">Request a Quote</a>') == 1
    assert 'Get a Quote Online' not in index_html
    assert 'contactCTA' not in index_html
    assert '.contactGrid' in site_css
    assert '.contactSection__caveat' in site_css
    tablet_css = site_css[site_css.index("@media (min-width: 640px)"):]
    assert re.search(
        r"\.contactGrid\s*\{[^}]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);",
        tablet_css,
        re.S,
    )


def test_pr3_homepage_content_and_section_order_match_approved_plan() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    ordered_markers = [
        'class="homeHero"',
        'class="homeTrustStrip"',
        'id="servicesTitle"',
        'class="homeSection whySection"',
        'id="howTitle"',
        'id="workTitle"',
        'id="trustFaqTitle"',
        'id="faqTitle"',
        'id="contactTitle"',
        'class="homeMobileActions"',
        'data-public-shell="footer"',
    ]
    positions = [index_html.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions)

    exact_copy = [
        "Serving North Bay &amp; surrounding area",
        "Junk removal, moving help &amp; hauling in North Bay.",
        "Bay Delivery provides practical local help with junk removal, dump runs, moving, furniture delivery, property cleanups, demolition, trailer hauling, and more. Send us the job details and photos for a straightforward estimate.",
        "Local service",
        "Based in North Bay and serving nearby communities.",
        "Practical estimates",
        "Send the job details so Bay Delivery can review the work and provide an estimate.",
        "Helpful photos",
        "Photos can help show the load, access, materials, and work area.",
        "No automatic booking",
        "Sending a request does not reserve a date; Bay Delivery confirms details and scheduling.",
        "Practical help for homes, rentals &amp; local businesses.",
        "One local crew for jobs that need a truck, trailer, equipment, and reliable help.",
        "Single items, household junk, garage piles, renovation debris, yard waste, and full trailer loads.",
        "Local moves, apartment moves, storage moves, loading, unloading, and extra hands when needed.",
        "Marketplace purchases, store pickups, furniture delivery, appliance delivery, and single heavy items.",
        "Estate cleanouts, rental cleanouts, garage cleanouts, basement cleanouts, yard cleanup, and full-property clearing.",
        "Small demolition, sheds, decks, flooring, cabinets, interior tear-outs, debris removal, and cleanup.",
        "Appliances, metal items, equipment, and qualifying scrap loads, with curbside or inside removal reviewed from the submitted job details.",
        "Trailer hauling and transportation help for suitable loads across North Bay and surrounding areas.",
        "Loading, unloading, lifting, cleanup assistance, and practical labour support for jobs that need a hand.",
        "Why Bay Delivery",
        "Local help. Straight answers. Hard work.",
        "Bay Delivery is a local crew serving North Bay and surrounding communities with practical help and clear communication.",
        "Local Service",
        "Practical Estimates",
        "Estimates are based on the details you provide and the requirements of the job.",
        "The Right Equipment",
        "Truck, trailers, tools, and labour are matched to the job.",
        "Clear Communication",
        "Customers know what information is needed and what the next step will be.",
        "Three simple steps. No runaround.",
        "Tell us about the job",
        "Send the locations, job details, access information, and photos when available.",
        "Receive your estimate",
        "Bay Delivery reviews the submitted information and the production quote flow provides an estimate for you to review.",
        "Confirm the work",
        "If you want to continue, submit a booking request. Bay Delivery confirms the job details and scheduling directly.",
        "Real jobs. Real results.",
        "A look at recent junk removal, cleanup, hauling, and demolition work completed by Bay Delivery in North Bay and surrounding communities.",
        "Deck removal completed in North Bay",
        "Existing deck, landing, and stairs removed to open up the space.",
        "Wood pallet and renovation debris haul",
        "Wood debris and pallet material loaded for removal.",
        "Property cleanup load",
        "Mixed property-cleanup material secured for hauling.",
        "Brick removal in progress",
        "Brick and demolition debris being removed from the work area.",
        "Yard cleanup load",
        "Outdoor cleanup material loaded and ready for hauling.",
        "Serving North Bay and surrounding areas.",
        "Bay Delivery serves North Bay, Callander, Corbeil, Astorville, Bonfield, Sturgeon Falls, and Powassan, with surrounding-area requests reviewed from the submitted job details.",
        "Availability and travel costs depend on the job location and scope.",
        "Not sure if we cover your area?",
        "Send the job location with your details so Bay Delivery can review the request.",
        "Common questions.",
        "What areas does Bay Delivery serve?",
        "Bay Delivery serves North Bay, Callander, Corbeil, Astorville, Bonfield, Sturgeon Falls, and Powassan. Requests from surrounding areas are reviewed based on the job location and scope.",
        "How accurate is the online estimate?",
        "The estimate is based on the information submitted through the production quote flow. It may change if the job details, access, materials, volume, or other site conditions differ from what was provided.",
        "Should I include photos?",
        "Photos are encouraged when available because they can show the load, access, materials, and work area. Include clear views that help Bay Delivery understand the job.",
        "Is my job booked when I submit a booking request?",
        "No. Submitting a quote or booking request does not reserve a date. Bay Delivery confirms the job details and scheduling directly.",
        "Start with a clear estimate.",
        "Send Bay Delivery the job details and photos to request an estimate. Bay Delivery can then review the information and determine the next step.",
        "What is the difference between cash and EMT/e-transfer totals?",
        "Cash totals are shown without HST. EMT/e-transfer totals include 13% HST. Review the displayed estimate before deciding whether to continue.",
        "What kinds of jobs does Bay Delivery handle?",
        "Bay Delivery handles junk removal and dump runs, moving help, furniture and appliance delivery, property cleanups, demolition and tear-out help, scrap metal removal, trailer hauling, and general labour.",
        "Start with the job",
        "Submitting a quote or booking request does not reserve a date.",
    ]
    for copy in exact_copy:
        assert copy in index_html

    service_names = re.findall(r'<h3 class="serviceCard__title">(.*?)</h3>', index_html)
    assert [re.sub(r"&amp;", "&", name) for name in service_names] == APPROVED_SERVICE_NAMES
    assert index_html.count('class="serviceCard__cta" href="/quote">Request a Quote</a>') == 8
    assert "You're on the quote page" not in index_html
    assert "You’re on the quote page" not in index_html
    assert "google.com/search" not in index_html
    assert "AggregateRating" not in index_html


def test_pr3_homepage_assets_are_exact_and_optimized() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    expected = {
        "bay-delivery-wood-pallet-debris-haul-hero.webp": ((1600, 900), 332800),
        "bay-delivery-deck-removal-before-north-bay-gallery.webp": ((1200, 900), 355464),
        "bay-delivery-deck-removal-after-north-bay-gallery.webp": ((1200, 900), 402556),
        "bay-delivery-wood-pallet-debris-haul-north-bay-gallery.webp": ((1200, 900), 289300),
        "bay-delivery-property-cleanup-load-north-bay-gallery.webp": ((1200, 900), 212220),
        "bay-delivery-brick-removal-work-in-progress-north-bay-gallery.webp": ((1200, 900), 173166),
        "bay-delivery-yard-cleanup-trailer-north-bay-gallery.webp": ((1200, 900), 408708),
    }
    referenced = re.findall(r'/static/images/homepage/([^"\)]+\.webp)', index_html)
    assert sorted(set(referenced)) == sorted(expected)
    for filename, (dimensions, byte_size) in expected.items():
        path = Path("static/images/homepage") / filename
        assert path.exists()
        assert path.stat().st_size == byte_size
        assert _webp_dimensions(path) == dimensions

    assert re.search(
        r'<img(?=[^>]*bay-delivery-wood-pallet-debris-haul-hero\.webp)'
        r'(?![^>]*fetchpriority="high")(?=[^>]*loading="lazy")'
        r'(?=[^>]*decoding="async")(?=[^>]*width="1600")(?=[^>]*height="900")[^>]*>',
        index_html,
    )
    recent_work = index_html[index_html.index('id="workTitle"'):index_html.index('id="trustFaqTitle"')]
    assert recent_work.count('loading="lazy"') == 6
    assert recent_work.count('width="1200"') == 6
    assert recent_work.count('height="900"') == 6


def test_pr3_homepage_action_bar_is_two_action_progressive_enhancement() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    site_css = Path("static/site.css").read_text(encoding="utf-8")
    site_js = Path("static/site.js").read_text(encoding="utf-8")
    quote_html = Path("static/quote.html").read_text(encoding="utf-8")

    action_nav = _nav_html(index_html, "Homepage quick actions")
    assert re.findall(r'<a href="([^"]+)">([^<]+)</a>', action_nav) == [
        ("tel:+17053034409", "Call"),
        ("/quote", "Request a Quote"),
    ]
    assert " hidden" in action_nav.split(">", 1)[0]
    assert "sms:" not in action_nav
    assert "Text" not in action_nav
    assert "env(safe-area-inset-bottom)" in site_css
    assert "@media (max-width: 720px)" in site_css
    assert 'aria-live' not in action_nav
    assert 'src="/static/public.js" defer' in index_html
    assert 'src="/static/site.js" defer' in index_html
    assert index_html.index('/static/public.js') < index_html.index('/static/site.js')
    assert "/static/site.js" not in quote_html
    assert "homeMobileActions" not in quote_html

    for forbidden in [
        "fetch(", "XMLHttpRequest", "FormData", "localStorage", "sessionStorage",
        "document.cookie", "sms:", "quote_id", "accept_token", "/quote/calculate",
        ".focus(",
    ]:
        assert forbidden not in site_js
    for required in [
        'matchMedia("(max-width: 720px)")',
        'requestAnimationFrame',
        'addEventListener("scroll"',
        'addEventListener("resize"',
        'addEventListener("orientationchange"',
        '{ passive: true }',
        'hero.getBoundingClientRect().bottom <= 0',
        'footer.getBoundingClientRect().top',
    ]:
        assert required in site_js


def test_pr3_homepage_contacts_and_content_safety_are_exact() -> None:
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    main_html = index_html[index_html.index('<main id="main-content"'):index_html.index('<footer')]
    contact_html = main_html[main_html.index('id="contactTitle"'):]

    assert contact_html.count("249-358-8087") == 1
    assert '<span>Primary contact</span><strong>Bay Delivery</strong><a href="tel:+17053034409">705-303-4409</a>' in contact_html
    assert '<span>Additional contact</span><strong>Austin</strong><a href="tel:+12493588087">249-358-8087</a>' in contact_html
    assert '<span>Email</span><strong>Bay Delivery</strong><a href="mailto:BayDeliveryNB@gmail.com">BayDeliveryNB@gmail.com</a>' in contact_html
    assert 'href="tel:+12493588087"' in contact_html
    assert "249-358-8087" not in main_html[:main_html.index('id="contactTitle"')]
    assert 'href="mailto:BayDeliveryNB@gmail.com"' in contact_html
    assert 'href="tel:+17053034409"' in main_html
    assert "sms:" not in main_html
    for forbidden in ["Quote ID:", "confidence value", "booking confirmed", "priceRange"]:
        assert forbidden not in main_html
