import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.config import settings
from app.discovery.base import (
    BaseDiscoveryProvider,
    DiscoveryProviderException,
    DiscoveryProviderUnavailableException,
)
from app.discovery.live_provider import LiveDiscoveryProvider, infer_source_category
from app.discovery.mock_provider import MockDiscoveryProvider
from app.main import app
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    DiscoveryResponse,
    DiscoveryStatus,
    ResearchQuery,
    SourceCategory,
)
from app.services.discovery_service import (
    DiscoveryService,
    get_discovery_provider,
    get_discovery_service,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers & Mock Response Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TAVILY_RESPONSE = {
    "results": [
        {
            "title": "Higher Education Enrollment in India 2025",
            "url": "https://education.gov.in/reports/higher-ed-2025.pdf",
            "content": "According to the official AISHE survey, India has 43.3 million higher education students.",
            "score": 0.94,
            "published_date": "2025-01-15",
        },
        {
            "title": "EdTech Market Analysis & Demographics",
            "url": "https://gartner.com/reports/edtech-india-2025",
            "content": "The market demand for engineering and online learning platforms continues to expand rapidly.",
            "score": 0.88,
            "published_date": "2025-02-10",
        },
    ]
}

SAMPLE_SEARXNG_RESPONSE = {
    "results": [
        {
            "title": "National Statistics Office Higher Education Data",
            "url": "https://mospi.gov.in/statistical-yearbook",
            "content": "Official statistics digest covering all collegiate enrollments.",
            "score": 0.91,
        }
    ]
}

SAMPLE_GENERIC_RESPONSE = {
    "items": [
        {
            "name": "Indian Higher Education Report",
            "link": "https://reuters.com/business/education/india-student-surge",
            "description": "Student population hits record numbers across undergraduate universities.",
            "relevance": 0.85,
        }
    ]
}


# ---------------------------------------------------------------------------
# Unit Tests for LiveDiscoveryProvider
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_01_live_provider_valid_response() -> None:
    """Test 1: Live provider successfully parses and normalizes standard search API results."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-mock-test-key-12345",
        provider_type="tavily",
    )
    query = ResearchQuery(
        metric_required="Number of college students in India",
        geography="India",
        year=2025,
        max_results=5,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    assert len(results) == 2
    assert results[0].title == "Higher Education Enrollment in India 2025"
    assert results[0].url == "https://education.gov.in/reports/higher-ed-2025.pdf"
    assert results[0].domain == "education.gov.in"
    assert results[0].category == SourceCategory.OFFICIAL_GOVERNMENT
    assert results[0].lifecycle_stage == DiscoveryLifecycleStage.DISCOVERED
    assert results[0].relevance_score == 0.94
    assert results[0].publication_date == "2025-01-15"
    assert "43.3 million" in results[0].snippet

    assert results[1].domain == "gartner.com"
    assert results[1].category == SourceCategory.INDUSTRY_ANALYST


@pytest.mark.anyio
async def test_02_multiple_search_results_bounded_by_max_results() -> None:
    """Test 2: Results are strictly capped by max_results."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-mock-test-key-12345",
        provider_type="tavily",
    )
    query = ResearchQuery(
        metric_required="Number of college students in India",
        max_results=1,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    assert len(results) == 1
    assert results[0].title == "Higher Education Enrollment in India 2025"


@pytest.mark.anyio
async def test_03_malformed_provider_json_response() -> None:
    """Test 3: Malformed JSON response raises DiscoveryProviderException."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
        provider_type="tavily",
    )
    query = ResearchQuery(metric_required="Market size")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON")

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(DiscoveryProviderException) as exc:
            await provider.search(query)
        assert "JSON" in str(exc.value)


@pytest.mark.anyio
async def test_04_provider_timeout_raises_unavailable() -> None:
    """Test 4: Request timeout raises DiscoveryProviderUnavailableException."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
        timeout_seconds=2.0,
    )
    query = ResearchQuery(metric_required="EdTech market")

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Connection timed out")):
        with pytest.raises(DiscoveryProviderUnavailableException) as exc:
            await provider.search(query)
        assert "timed out" in str(exc.value).lower()


@pytest.mark.anyio
async def test_05_provider_http_500_error() -> None:
    """Test 5: HTTP 500 server error raises DiscoveryProviderUnavailableException."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(metric_required="EdTech market")

    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(DiscoveryProviderUnavailableException) as exc:
            await provider.search(query)
        assert "502" in str(exc.value)


@pytest.mark.anyio
async def test_06_rate_limit_response_429() -> None:
    """Test 6: HTTP 429 rate limit raises DiscoveryProviderUnavailableException with rate limit message."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(metric_required="EdTech market")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Too Many Requests"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(DiscoveryProviderUnavailableException) as exc:
            await provider.search(query)
        assert "rate limit" in str(exc.value).lower()


@pytest.mark.anyio
async def test_07_missing_api_key_when_required() -> None:
    """Test 7: Missing API key for Tavily/live raises DiscoveryProviderException."""
    with patch.object(settings, "SEARCH_API_KEY", None), patch.object(settings, "TAVILY_API_KEY", None):
        provider = LiveDiscoveryProvider(
            api_url="https://api.tavily.com/search",
            api_key=None,
            provider_type="tavily",
        )
        query = ResearchQuery(metric_required="EdTech market")

        with pytest.raises(DiscoveryProviderException) as exc:
            await provider.search(query)
        assert "TAVILY_API_KEY" in str(exc.value) or "SEARCH_API_KEY" in str(exc.value)


@pytest.mark.anyio
async def test_08_empty_search_results() -> None:
    """Test 8: Empty results array returns an empty list without crashing."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(metric_required="Extremely obscure metric")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    assert results == []


@pytest.mark.anyio
async def test_09_invalid_and_malformed_urls_skipped_safely() -> None:
    """Test 9: Invalid/malformed URLs in provider response are skipped while valid ones are kept."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(metric_required="EdTech market")

    payload_with_bad_urls = {
        "results": [
            {"title": "Bad 1", "url": "not-a-valid-url", "content": "test"},
            {"title": "Bad 2", "url": "ftp://ftp.example.com/file", "content": "test"},
            {"title": "Valid One", "url": "https://example.com/good-page", "content": "good content"},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload_with_bad_urls

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    assert len(results) == 1
    assert results[0].title == "Valid One"
    assert results[0].url == "https://example.com/good-page"


@pytest.mark.anyio
async def test_10_lifecycle_strictly_remains_discovered() -> None:
    """Test 10: Epistemic safety: Discovered sources are strictly tagged DISCOVERED."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(metric_required="Market size")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    for res in results:
        assert res.lifecycle_stage == DiscoveryLifecycleStage.DISCOVERED.value
        assert res.lifecycle_stage != DiscoveryLifecycleStage.VERIFIED.value


@pytest.mark.anyio
async def test_11_query_used_preserved() -> None:
    """Test 11: The exact query string used is attached to each discovered source."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
    )
    query = ResearchQuery(
        metric_required="Annual subscription price",
        geography="India",
        year=2025,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        results = await provider.search(query)

    expected_query = "Annual subscription price India 2025"
    for res in results:
        assert res.query_used == expected_query


def test_12_domain_extraction_and_category_inference() -> None:
    """Test 12: Source category heuristic correctly detects official, academic, analyst, news, and other."""
    assert infer_source_category("education.gov.in") == SourceCategory.OFFICIAL_GOVERNMENT
    assert infer_source_category("censusindia.gov.in") == SourceCategory.OFFICIAL_GOVERNMENT
    assert infer_source_category("iitb.ac.in") == SourceCategory.ACADEMIC_INSTITUTION
    assert infer_source_category("mit.edu") == SourceCategory.ACADEMIC_INSTITUTION
    assert infer_source_category("gartner.com") == SourceCategory.INDUSTRY_ANALYST
    assert infer_source_category("statista.com") == SourceCategory.INDUSTRY_ANALYST
    assert infer_source_category("reuters.com") == SourceCategory.REPUTABLE_NEWS
    assert infer_source_category("bloomberg.com") == SourceCategory.REPUTABLE_NEWS
    assert infer_source_category("sec.gov") == SourceCategory.COMPANY_FILING
    assert infer_source_category("randomblog.xyz") == SourceCategory.OTHER


@pytest.mark.anyio
async def test_13_searxng_and_generic_response_formats() -> None:
    """Test 13: SearXNG GET request format and generic JSON response formats are handled seamlessly."""
    # SearXNG
    searxng_provider = LiveDiscoveryProvider(
        api_url="http://localhost:8080",
        provider_type="searxng",
    )
    query = ResearchQuery(metric_required="Higher education")

    mock_get = MagicMock()
    mock_get.status_code = 200
    mock_get.json.return_value = SAMPLE_SEARXNG_RESPONSE

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_get):
        searxng_results = await searxng_provider.search(query)

    assert len(searxng_results) == 1
    assert searxng_results[0].domain == "mospi.gov.in"
    assert searxng_results[0].category == SourceCategory.OFFICIAL_GOVERNMENT

    # Generic JSON (items / name / link)
    generic_provider = LiveDiscoveryProvider(
        api_url="https://custom-search.api/v1",
        api_key="custom-key",
        provider_type="custom",
    )

    mock_custom = MagicMock()
    mock_custom.status_code = 200
    mock_custom.json.return_value = SAMPLE_GENERIC_RESPONSE

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_custom):
        custom_results = await generic_provider.search(query)

    assert len(custom_results) == 1
    assert custom_results[0].title == "Indian Higher Education Report"
    assert custom_results[0].url == "https://reuters.com/business/education/india-student-surge"
    assert custom_results[0].category == SourceCategory.REPUTABLE_NEWS


def test_14_provider_factory_and_mock_fallback() -> None:
    """Test 14: get_discovery_provider returns appropriate instance based on config/parameters."""
    mock_prov = get_discovery_provider("mock")
    assert isinstance(mock_prov, MockDiscoveryProvider)

    live_prov = get_discovery_provider("live")
    assert isinstance(live_prov, LiveDiscoveryProvider)

    tavily_prov = get_discovery_provider("tavily")
    assert isinstance(tavily_prov, LiveDiscoveryProvider)

    searxng_prov = get_discovery_provider("searxng")
    assert isinstance(searxng_prov, LiveDiscoveryProvider)


@pytest.mark.anyio
async def test_15_api_discover_evidence_endpoint_with_live_provider() -> None:
    """Test 15: POST /api/v1/evidence/discover works end-to-end with live provider dependency."""
    mock_provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="test-key",
        provider_type="tavily",
    )
    mock_service = DiscoveryService(provider=mock_provider)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    app.dependency_overrides[get_discovery_service] = lambda: mock_service
    try:
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post(
                "/api/v1/evidence/discover",
                json={
                    "metric_required": "College students enrollment",
                    "geography": "India",
                    "year": 2025,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_results_found"] == 2
        assert data["sources"][0]["lifecycle_stage"] == "discovered"
    finally:
        app.dependency_overrides.pop(get_discovery_service, None)


def test_16_tavily_api_key_configuration() -> None:
    """Test 16: TAVILY_API_KEY from config/settings is correctly utilized by LiveDiscoveryProvider."""
    with patch.object(settings, "TAVILY_API_KEY", "tvly-test-tavily-config-key"):
        with patch.object(settings, "SEARCH_API_KEY", None):
            prov = LiveDiscoveryProvider(provider_type="tavily")
            assert prov.api_key == "tvly-test-tavily-config-key"
            assert prov.api_url == "https://api.tavily.com/search"


@pytest.mark.anyio
async def test_17_live_provider_failure_does_not_fall_back_to_mock() -> None:
    """Test 17: Live Tavily failure MUST NOT silently fall back to MockDiscoveryProvider."""
    failing_provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-mock-test-key",
        provider_type="tavily",
    )
    service = DiscoveryService(provider=failing_provider)
    query = ResearchQuery(metric_required="India college students", geography="India", year=2025)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        response = await service.discover_sources(query)

    # Must report FAILED status, zero sources, and NOT contain any mock sources
    assert response.status == DiscoveryStatus.FAILED
    assert len(response.sources) == 0
    assert "unavailable" in response.message.lower() or "failed" in response.message.lower()


@pytest.mark.anyio
async def test_18_live_provider_reports_live_research_provider() -> None:
    """Test 18: Orchestrator reports research_provider = 'live' when LiveDiscoveryProvider is active."""
    live_prov = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-test-key",
        provider_type="tavily",
    )
    live_service = DiscoveryService(provider=live_prov)

    from app.services.orchestration_service import OrchestrationService, OrchestrationRequest
    from app.schemas.business import BusinessAnalysis
    orchestrator = OrchestrationService(discovery_service=live_service)

    mock_analysis = BusinessAnalysis(
        business_idea="Coding platform for students in India",
        industry="EdTech",
        product="Coding platform",
        target_customer="Students",
        geography="India",
        business_model="B2C",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    with patch.object(orchestrator.llm_service, "analyze_business_idea", AsyncMock(return_value=mock_analysis)):
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            res = await orchestrator.run(OrchestrationRequest(business_idea="Coding platform for students in India"))

    assert res.research_provider == "live"


@pytest.mark.anyio
async def test_19_missing_api_key_raises_explicit_error() -> None:
    """Test 19: Missing API key produces clear error and does not silently succeed with mock data."""
    with patch.object(settings, "SEARCH_API_KEY", None), patch.object(settings, "TAVILY_API_KEY", None):
        provider = LiveDiscoveryProvider(
            api_url="https://api.tavily.com/search",
            api_key=None,
            provider_type="live",
        )
        query = ResearchQuery(metric_required="Target demographic")

        with pytest.raises(DiscoveryProviderException) as exc:
            await provider.search(query)

        assert "TAVILY_API_KEY" in str(exc.value) or "SEARCH_API_KEY" in str(exc.value)


@pytest.mark.anyio
async def test_20_live_provider_uses_ipv4_transport() -> None:
    """Test 20: LiveDiscoveryProvider initializes AsyncHTTPTransport with IPv4 (local_address='0.0.0.0') binding."""
    provider = LiveDiscoveryProvider(
        api_url="https://api.tavily.com/search",
        api_key="tvly-mock-key-ipv4-test",
        provider_type="tavily",
    )
    query = ResearchQuery(metric_required="EV charging market")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_TAVILY_RESPONSE

    captured_transports: list[httpx.AsyncHTTPTransport] = []
    original_init = httpx.AsyncClient.__init__

    def wrapped_init(self, *args, **kwargs):
        if "transport" in kwargs and isinstance(kwargs["transport"], httpx.AsyncHTTPTransport):
            captured_transports.append(kwargs["transport"])
        return original_init(self, *args, **kwargs)

    with patch.object(httpx.AsyncClient, "__init__", wrapped_init):
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(query)

    assert len(results) == 2
    assert len(captured_transports) >= 1
    # Verify that local_address is bound to IPv4 0.0.0.0
    assert captured_transports[0]._pool._local_address == "0.0.0.0"

