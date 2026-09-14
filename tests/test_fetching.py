import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.fetching.html_utils import extract_text_from_html
from app.fetching.http_fetcher import HttpSourceFetcher
from app.fetching.models import FetchedSource, FetchRequest, FetchStatus
from app.fetching.security import is_safe_url, validate_url_safety
from app.main import app
from app.schemas.discovery import DiscoveryLifecycleStage

client = TestClient(app)


# ---------------------------------------------------------------------------
# Security & URL Validation Tests
# ---------------------------------------------------------------------------

def test_url_safety_allowed_external_urls() -> None:
    """Standard HTTP/HTTPS public domain URLs pass safety checks."""
    assert is_safe_url("https://example.gov.in/report.html") is True
    assert is_safe_url("http://research-institute.org/data") is True
    assert is_safe_url("https://stats.oecd.org/dataset") is True


def test_url_safety_blocked_schemes_and_internal_hosts() -> None:
    """Localhost, loopback, private IPs, and non-HTTP schemes are rejected."""
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("ftp://ftp.example.com") is False
    assert is_safe_url("http://localhost:8000/api") is False
    assert is_safe_url("http://127.0.0.1:11434") is False
    assert is_safe_url("http://0.0.0.0:80") is False
    assert is_safe_url("http://192.168.1.1/admin") is False
    assert is_safe_url("http://10.0.0.1/status") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data") is False


# ---------------------------------------------------------------------------
# HTML Parsing & Content Sanitation Tests
# ---------------------------------------------------------------------------

def test_html_text_extraction_strips_boilerplate() -> None:
    """HTML parser strips script, style, nav, and preserves structured headings and paragraphs."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Higher Education Statistics Report 2025</title>
        <style>body { font-size: 14px; }</style>
        <script>alert("tracker");</script>
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <h1>Annual Higher Education Digest</h1>
        <p>India has <strong>43 million</strong> college students enrolled across recognized universities in 2025.</p>
        <noscript>Please enable javascript</noscript>
        <footer>Copyright 2025 Ministry</footer>
    </body>
    </html>
    """
    clean_text, title = extract_text_from_html(sample_html)
    assert title == "Higher Education Statistics Report 2025"
    assert "alert" not in clean_text
    assert "font-size" not in clean_text
    assert "Annual Higher Education Digest" in clean_text
    assert "43 million" in clean_text
    assert "college students" in clean_text


# ---------------------------------------------------------------------------
# HttpSourceFetcher Unit Tests (Mocked Network Transport)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_http_fetcher_success_html() -> None:
    """TEST 1: Valid HTTP fetch retrieves HTML, extracts text, and tags FETCHED stage."""
    html_content = "<html><head><title>Test Report</title></head><body><p>There are 500,000 developers in India.</p></body></html>"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=html_content,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    fetcher = HttpSourceFetcher()
    
    # Inject mock transport
    client_mock = httpx.AsyncClient(transport=transport)
    # Monkeypatch client instantiation
    from unittest.mock import patch
    with patch("httpx.AsyncClient", return_value=client_mock):
        result = await fetcher.fetch(
            url="https://example.gov.in/test-report.html",
            title="Pre-declared Title",
            source_name="Ministry of Education",
        )

    assert result.fetch_status == FetchStatus.SUCCESS.value
    assert result.http_status == 200
    assert "500,000 developers in India" in result.content
    assert result.lifecycle_stage == DiscoveryLifecycleStage.FETCHED.value
    assert result.domain == "example.gov.in"


@pytest.mark.anyio
async def test_http_fetcher_blocked_unsafe_url() -> None:
    """TEST 2 & 3: Localhost / private IP URLs are blocked with FetchStatus.BLOCKED."""
    fetcher = HttpSourceFetcher()
    result = await fetcher.fetch("http://127.0.0.1:8000/internal")
    assert result.fetch_status == FetchStatus.BLOCKED.value
    assert "security" in result.error_message.lower()


@pytest.mark.anyio
async def test_http_fetcher_http_404() -> None:
    """TEST 4: HTTP 404 response produces FetchStatus.FETCH_FAILED."""
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found", request=request)

    from unittest.mock import patch
    client_mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = HttpSourceFetcher()
    with patch("httpx.AsyncClient", return_value=client_mock):
        result = await fetcher.fetch("https://example.com/missing-page")

    assert result.fetch_status == FetchStatus.FETCH_FAILED.value
    assert result.http_status == 404


@pytest.mark.anyio
async def test_http_fetcher_http_500() -> None:
    """TEST 5: HTTP 500 server error produces FetchStatus.FETCH_FAILED."""
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Server Error", request=request)

    from unittest.mock import patch
    client_mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = HttpSourceFetcher()
    with patch("httpx.AsyncClient", return_value=client_mock):
        result = await fetcher.fetch("https://example.com/server-error")

    assert result.fetch_status == FetchStatus.FETCH_FAILED.value
    assert result.http_status == 500


@pytest.mark.anyio
async def test_http_fetcher_timeout() -> None:
    """TEST 6: Network timeout produces FetchStatus.TIMEOUT."""
    from unittest.mock import patch
    fetcher = HttpSourceFetcher()
    with patch("httpx.AsyncClient.stream", side_effect=httpx.ReadTimeout("Read timed out")):
        result = await fetcher.fetch("https://example.com/slow-endpoint")

    assert result.fetch_status == FetchStatus.TIMEOUT.value
    assert "timed out" in result.error_message.lower()


@pytest.mark.anyio
async def test_http_fetcher_unsupported_content_type() -> None:
    """TEST 9: Unsupported content types (e.g. PDF/Binary) return UNSUPPORTED_CONTENT."""
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"%PDF-1.5...",
            headers={"content-type": "application/pdf"},
            request=request,
        )

    from unittest.mock import patch
    client_mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = HttpSourceFetcher()
    with patch("httpx.AsyncClient", return_value=client_mock):
        result = await fetcher.fetch("https://example.com/document.pdf")

    assert result.fetch_status == FetchStatus.UNSUPPORTED_CONTENT.value
    assert "pdf" in result.error_message.lower()


@pytest.mark.anyio
async def test_http_fetcher_oversized_response() -> None:
    """TEST 8: Responses exceeding max_bytes are stopped with FetchStatus.OVERSIZED."""
    # Create large byte chunks
    big_content = b"x" * 2000

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=big_content,
            headers={"content-type": "text/plain"},
            request=request,
        )

    from unittest.mock import patch
    client_mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = HttpSourceFetcher(max_bytes=1000)  # limit to 1000 bytes
    with patch("httpx.AsyncClient", return_value=client_mock):
        result = await fetcher.fetch("https://example.com/big-file.txt")

    assert result.fetch_status == FetchStatus.OVERSIZED.value
    assert "exceeded" in result.error_message.lower()


def test_fetched_source_cannot_claim_verified_stage() -> None:
    """TEST 23: Epistemic guard ensures FetchedSource cannot have lifecycle_stage='verified'."""
    with pytest.raises(ValidationError) as exc:
        FetchedSource(
            original_url="https://example.com/test",
            fetch_status=FetchStatus.SUCCESS,
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        )
    assert "verified" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# API Endpoint Tests (POST /api/v1/evidence/fetch)
# ---------------------------------------------------------------------------

def test_api_fetch_source_success() -> None:
    """TEST 25: API endpoint returns 200 with FetchedSource."""
    from unittest.mock import AsyncMock, patch
    mock_fetched = FetchedSource(
        original_url="https://statistics.gov.in/higher-ed.html",
        title="Higher Ed Statistics",
        content="India has 43 million college students.",
        content_type="text/html",
        http_status=200,
        content_length_bytes=1024,
        fetch_status=FetchStatus.SUCCESS,
        source_name="National Statistics",
    )
    with patch("app.services.fetch_service.SourceFetchService.fetch_source", new_callable=AsyncMock, return_value=mock_fetched):
        response = client.post(
            "/api/v1/evidence/fetch",
            json={
                "url": "https://statistics.gov.in/higher-ed.html",
                "title": "Higher Ed Statistics",
                "source_name": "National Statistics",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fetch_status"] == "success"
        assert data["lifecycle_stage"] == "fetched"
        assert "43 million" in data["content"]


def test_api_fetch_source_rejected_invalid_url() -> None:
    """TEST 26: API rejects non-HTTP/HTTPS URLs with 422."""
    response = client.post(
        "/api/v1/evidence/fetch",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422
