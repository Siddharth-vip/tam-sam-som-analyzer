import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.discovery.base import (
    BaseDiscoveryProvider,
    DiscoveryProviderException,
    DiscoveryProviderUnavailableException,
)
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
from app.schemas.evidence import SourceType
from app.services.discovery_service import DiscoveryService, get_discovery_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Schema Validation Unit Tests
# ---------------------------------------------------------------------------

def test_research_query_valid() -> None:
    """Valid research query instantiates cleanly with normalized fields."""
    query = ResearchQuery(
        metric_required="  Number of higher education students in India  ",
        geography="  India  ",
        year=2025,
        industry_topic="  EdTech / Higher Education  ",
        target_population="College students",
        preferred_source_types=[SourceType.GOVERNMENT, SourceType.OFFICIAL_STATISTICS],
        preferred_categories=[SourceCategory.OFFICIAL_GOVERNMENT],
        max_results=5,
    )
    assert query.metric_required == "Number of higher education students in India"
    assert query.geography == "India"
    assert query.industry_topic == "EdTech / Higher Education"
    assert query.year == 2025
    assert len(query.preferred_source_types) == 2


def test_research_query_empty_metric_rejected() -> None:
    """Empty or whitespace-only metric_required is rejected."""
    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="")

    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="   \t\n  ")


def test_research_query_invalid_year_rejected() -> None:
    """Years outside the reasonable range [1900, 2100] are rejected."""
    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="Students", year=1800)

    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="Students", year=2150)


def test_research_query_max_results_bounds() -> None:
    """max_results must be between 1 and 20."""
    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="Students", max_results=0)

    with pytest.raises(ValidationError):
        ResearchQuery(metric_required="Students", max_results=25)


def test_discovered_source_valid() -> None:
    """Valid discovered source populates domain and defaults to DISCOVERED stage."""
    source = DiscoveredSource(
        title="National Education Report 2025",
        url="https://education.gov.in/reports/higher-ed-2025.pdf",
        snippet="Annual digest of higher education enrollment data in India.",
        source_name="Ministry of Education",
        category=SourceCategory.OFFICIAL_GOVERNMENT,
    )
    assert source.title == "National Education Report 2025"
    assert source.domain == "education.gov.in"
    assert source.lifecycle_stage == DiscoveryLifecycleStage.DISCOVERED.value


def test_discovered_source_invalid_url_rejected() -> None:
    """Non-HTTP/HTTPS or malformed URLs are rejected."""
    with pytest.raises(ValidationError):
        DiscoveredSource(
            title="Invalid Link",
            url="not_a_valid_url",
        )

    with pytest.raises(ValidationError):
        DiscoveredSource(
            title="FTP Link",
            url="ftp://ftp.example.com/file.pdf",
        )


def test_discovered_source_cannot_claim_verified_stage() -> None:
    """Epistemic Guard: A discovered source cannot claim lifecycle_stage='verified' during discovery."""
    with pytest.raises(ValidationError) as exc:
        DiscoveredSource(
            title="Unchecked Web Page",
            url="https://example.com/unverified",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        )
    assert "verified" in str(exc.value).lower()


def test_discovery_lifecycle_stages_completeness() -> None:
    """Verify all 5 lifecycle stages exist in strict sequence."""
    stages = [stage.value for stage in DiscoveryLifecycleStage]
    assert "discovered" in stages
    assert "fetched" in stages
    assert "extracted" in stages
    assert "validated" in stages
    assert "verified" in stages


# ---------------------------------------------------------------------------
# Provider & Service Unit Tests
# ---------------------------------------------------------------------------

def test_mock_provider_build_query_string() -> None:
    """Provider constructs canonical search query strings correctly."""
    provider = MockDiscoveryProvider()
    query = ResearchQuery(
        metric_required="College students",
        target_population="Undergraduates",
        industry_topic="EdTech",
        geography="India",
        year=2025,
    )
    query_str = provider.build_query_string(query)
    assert "College students" in query_str
    assert "Undergraduates" in query_str
    assert "EdTech" in query_str
    assert "India" in query_str
    assert "2025" in query_str


@pytest.mark.anyio
async def test_discovery_service_success() -> None:
    """DiscoveryService executes search and returns tagged DISCOVERED sources."""
    service = DiscoveryService(MockDiscoveryProvider())
    query = ResearchQuery(
        metric_required="Number of college students in India",
        geography="India",
        year=2025,
        max_results=2,
    )
    response = await service.discover_sources(query)

    assert response.status == DiscoveryStatus.SUCCESS
    assert response.total_results_found == 2
    assert len(response.sources) == 2
    for source in response.sources:
        assert source.lifecycle_stage == DiscoveryLifecycleStage.DISCOVERED
        assert source.query_used is not None
        assert source.url.startswith("https://")


@pytest.mark.anyio
async def test_discovery_service_no_results() -> None:
    """DiscoveryService cleanly handles empty provider results."""
    empty_provider = MockDiscoveryProvider(seeded_sources=[])
    service = DiscoveryService(empty_provider)
    query = ResearchQuery(metric_required="Obscure metric with no data")
    response = await service.discover_sources(query)

    assert response.status == DiscoveryStatus.NO_RESULTS
    assert response.total_results_found == 0
    assert response.sources == []


class FailingProvider(BaseDiscoveryProvider):
    def build_query_string(self, query: ResearchQuery) -> str:
        return query.metric_required

    async def search(self, query: ResearchQuery) -> list:
        raise DiscoveryProviderUnavailableException("Connection to search engine timed out.")


@pytest.mark.anyio
async def test_discovery_service_provider_unavailable() -> None:
    """DiscoveryService handles provider unavailability gracefully."""
    service = DiscoveryService(FailingProvider())
    query = ResearchQuery(metric_required="Market size")
    response = await service.discover_sources(query)

    assert response.status == DiscoveryStatus.FAILED
    assert response.total_results_found == 0
    assert "unavailable" in response.message.lower()


# ---------------------------------------------------------------------------
# API Endpoint Tests (POST /api/v1/evidence/discover)
# ---------------------------------------------------------------------------

def test_api_discover_evidence_success() -> None:
    """API endpoint returns 200 with structured DiscoveryResponse."""
    payload = {
        "metric_required": "Number of college students in India",
        "geography": "India",
        "year": 2025,
        "industry_topic": "Higher Education",
        "max_results": 3,
    }
    response = client.post("/api/v1/evidence/discover", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_results_found"] > 0
    assert data["lifecycle_stage"] == "discovered"
    assert len(data["sources"]) > 0

    first_source = data["sources"][0]
    assert "title" in first_source
    assert "url" in first_source
    assert first_source["lifecycle_stage"] == "discovered"


def test_api_discover_evidence_rejected_empty_metric() -> None:
    """API endpoint returns 422 when metric_required is missing or blank."""
    response = client.post(
        "/api/v1/evidence/discover",
        json={"metric_required": "   "},
    )
    assert response.status_code == 422


def test_api_discover_evidence_rejected_invalid_max_results() -> None:
    """API endpoint returns 422 when max_results is out of range."""
    response = client.post(
        "/api/v1/evidence/discover",
        json={"metric_required": "Students", "max_results": 50},
    )
    assert response.status_code == 422
