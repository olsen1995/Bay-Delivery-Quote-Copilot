from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app.main import app


PUBLIC_SITE_ORIGIN = "https://bay-delivery-quote-copilot.onrender.com"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
ROBOTS_TXT = (
    "User-agent: *\n"
    "Allow: /\n"
    "Disallow: /admin/api/\n"
    "Disallow: /api/\n"
    "Disallow: /quote/\n"
    "Disallow: /health\n"
    "Disallow: /docs\n"
    "Disallow: /redoc\n"
    "Disallow: /openapi.json\n"
    f"Sitemap: {PUBLIC_SITE_ORIGIN}/sitemap.xml\n"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_robots_txt_uses_exact_public_crawl_policy(client: TestClient) -> None:
    response = client.get("/robots.txt", headers={"Host": "hostile.example"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.text == ROBOTS_TXT
    assert response.text.endswith("\n")
    assert "User-agent: *" in response.text
    assert "Allow: /" in response.text
    for directive in (
        "Disallow: /admin/api/",
        "Disallow: /api/",
        "Disallow: /quote/",
        "Disallow: /health",
        "Disallow: /docs",
        "Disallow: /redoc",
        "Disallow: /openapi.json",
    ):
        assert directive in response.text.splitlines()
    assert "Disallow: /admin" not in response.text.splitlines()
    assert "Disallow: /quote" not in response.text.splitlines()
    assert f"Sitemap: {PUBLIC_SITE_ORIGIN}/sitemap.xml" in response.text.splitlines()
    assert "hostile.example" not in response.text


def test_sitemap_contains_only_verified_public_pages(client: TestClient) -> None:
    response = client.get("/sitemap.xml", headers={"Host": "hostile.example"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.content)
    assert root.tag == f"{{{SITEMAP_NAMESPACE}}}urlset"
    urls = root.findall(f"{{{SITEMAP_NAMESPACE}}}url")
    locations = {
        location.text
        for location in root.findall(f"{{{SITEMAP_NAMESPACE}}}url/{{{SITEMAP_NAMESPACE}}}loc")
    }

    assert len(urls) == 2
    assert locations == {
        f"{PUBLIC_SITE_ORIGIN}/",
        f"{PUBLIC_SITE_ORIGIN}/quote",
    }
    for excluded_path in ("/admin", "/health", "/api/", "/static/", "/services"):
        assert excluded_path not in response.text
    assert "hostile.example" not in response.text


def test_crawlability_routes_are_excluded_from_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/robots.txt" not in paths
    assert "/sitemap.xml" not in paths


@pytest.mark.parametrize(
    ("path", "static_path"),
    [
        ("/admin", Path("static/admin.html")),
        ("/admin/mobile", Path("static/admin_mobile.html")),
        ("/admin/uploads", Path("static/admin_uploads.html")),
    ],
)
def test_admin_shells_are_noindex_and_preserve_existing_file_responses(
    client: TestClient,
    path: str,
    static_path: Path,
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.history == []
    assert response.request.url.path == path
    assert response.content == static_path.read_bytes()
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


@pytest.mark.parametrize(
    ("path", "static_path"),
    [
        ("/static/admin.html", Path("static/admin.html")),
        ("/static/admin_mobile.html", Path("static/admin_mobile.html")),
        ("/static/admin_uploads.html", Path("static/admin_uploads.html")),
    ],
)
def test_direct_static_admin_shells_are_noindex_and_preserve_static_responses(
    client: TestClient,
    path: str,
    static_path: Path,
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.history == []
    assert response.request.url.path == path
    assert response.content == static_path.read_bytes()
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


@pytest.mark.parametrize(
    ("path", "static_path"),
    [
        ("/", Path("static/index.html")),
        ("/quote", Path("static/quote.html")),
    ],
)
def test_public_pages_remain_indexable_and_preserve_existing_file_responses(
    client: TestClient,
    path: str,
    static_path: Path,
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.history == []
    assert response.request.url.path == path
    assert response.content == static_path.read_bytes()
    assert "noindex" not in response.headers.get("x-robots-tag", "").lower()


def test_saved_quote_review_query_is_noindex_and_preserves_quote_page(client: TestClient) -> None:
    response = client.get("/quote?quote_id=test-quote")

    assert response.status_code == 200
    assert response.history == []
    assert response.request.url.path == "/quote"
    assert response.content == Path("static/quote.html").read_bytes()
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


def test_unrelated_quote_query_remains_indexable(client: TestClient) -> None:
    response = client.get("/quote?source=google")

    assert response.status_code == 200
    assert response.history == []
    assert response.request.url.path == "/quote"
    assert response.content == Path("static/quote.html").read_bytes()
    assert "noindex" not in response.headers.get("x-robots-tag", "").lower()
