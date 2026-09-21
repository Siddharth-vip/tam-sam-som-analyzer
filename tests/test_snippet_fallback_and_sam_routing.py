import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.fetching.models import FetchedSource, FetchStatus
from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveredSource, DiscoveryLifecycleStage, SourceQualityTier, SourceCategory, DiscoveryResponse, ResearchQuery, DiscoveryStatus
from app.schemas.extraction import ExtractionRequest, MarketMetricType
from app.schemas.pipeline import PipelineRequest
from app.services.fetch_service import SourceFetchService
from app.services.extraction_service import EvidenceExtractionService
from app.orchestration.pipeline import MarketAnalysisPipeline


@pytest.mark.asyncio
async def test_403_with_snippet_falls_back_to_snippet_content():
    """TEST 1: When HTTP fetch returns 403 and source.snippet exists, use snippet as fallback content."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch.return_value = FetchedSource(
        original_url="https://www.fortunebusinessinsights.com/pet-care-market-104749",
        fetch_status=FetchStatus.FETCH_FAILED,
        http_status=403,
        error_message="HTTP request failed with status code 403.",
    )

    fetch_service = SourceFetchService(fetcher=mock_fetcher)
    discovered = DiscoveredSource(
        title="Pet Care Market Report",
        url="https://www.fortunebusinessinsights.com/pet-care-market-104749",
        domain="www.fortunebusinessinsights.com",
        snippet="India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market.",
        category=SourceCategory.FINANCIAL_MARKET_RESEARCH,
        source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
    )

    result = await fetch_service.fetch_discovered_source(discovered)

    assert result.fetch_status == FetchStatus.SNIPPET_FALLBACK
    assert result.content is not None
    assert "5.41% of the global market" in result.content
    assert result.http_status == 403
    assert result.original_url == discovered.url
    assert "fortunebusinessinsights.com" in result.domain


@pytest.mark.asyncio
async def test_timeout_with_snippet_falls_back():
    """TEST 2: When HTTP fetch times out and snippet exists, snippet fallback occurs."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch.return_value = FetchedSource(
        original_url="https://dataintelo.com/report/global-pet-care-service-market",
        fetch_status=FetchStatus.TIMEOUT,
        error_message="Request timed out after 10.0 seconds.",
    )

    fetch_service = SourceFetchService(fetcher=mock_fetcher)
    discovered = DiscoveredSource(
        title="Pet Care Service Market Research",
        url="https://dataintelo.com/report/global-pet-care-service-market",
        domain="dataintelo.com",
        snippet="Online booking platforms captured 51.1% of pet care service transactions in 2025.",
        category=SourceCategory.OTHER,
        source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
    )

    result = await fetch_service.fetch_discovered_source(discovered)

    assert result.fetch_status == FetchStatus.SNIPPET_FALLBACK
    assert result.content == "Online booking platforms captured 51.1% of pet care service transactions in 2025."


@pytest.mark.asyncio
async def test_403_with_empty_snippet_remains_failed():
    """TEST 3: When HTTP fetch returns 403 and snippet is None or empty, source remains failed with no content."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch.return_value = FetchedSource(
        original_url="https://example.com/blocked-no-snippet",
        fetch_status=FetchStatus.FETCH_FAILED,
        http_status=403,
        error_message="HTTP request failed with status code 403.",
    )

    fetch_service = SourceFetchService(fetcher=mock_fetcher)
    discovered = DiscoveredSource(
        title="Blocked Page",
        url="https://example.com/blocked-no-snippet",
        domain="example.com",
        snippet="",  # empty snippet
        category=SourceCategory.OTHER,
        source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
    )

    result = await fetch_service.fetch_discovered_source(discovered)

    assert result.fetch_status == FetchStatus.FETCH_FAILED
    assert result.content is None or result.content == ""


def test_extraction_identifies_geographic_percentage_from_snippet():
    """TEST 4: Extraction extracts 5.41% as MARKET_SHARE candidate for India."""
    extraction_service = EvidenceExtractionService()
    snippet = "India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market."
    source = FetchedSource(
        original_url="https://www.fortunebusinessinsights.com/pet-care-market-104749",
        title="Pet Care Market Report",
        source_name="Fortune Business Insights",
        fetch_status=FetchStatus.SNIPPET_FALLBACK,
        content=snippet,
        content_length_bytes=len(snippet),
        http_status=403,
    )

    resp = extraction_service.extract_evidence_from_source(ExtractionRequest(source=source))
    assert resp.candidates is not None
    assert len(resp.candidates) >= 2

    # Find the 5.41% candidate
    pct_candidates = [c for c in resp.candidates if c.unit == "%" and c.value == 5.41]
    assert len(pct_candidates) == 1
    pct_cand = pct_candidates[0]
    assert pct_cand.value == 5.41
    assert pct_cand.metric_type == MarketMetricType.MARKET_SHARE
    assert pct_cand.geography == "India"
    assert pct_cand.year == 2025


@pytest.mark.asyncio
async def test_end_to_end_sam_derived_from_global_tam_and_snippet_percentage():
    """TEST 5: End-to-end pipeline routes 5.41% geographic share to SAM: $29.5B * 5.41% = $1.59595B."""
    pipeline = MarketAnalysisPipeline()

    # 1. Global pet care services market: $29.5B USD in 2025
    doc_global = FetchedSource(
        original_url="https://www.wiseguyreports.com/reports/pet-care-services-market",
        title="Global Pet Care Services Market",
        source_name="Wise Guy Reports",
        fetch_status=FetchStatus.SUCCESS,
        content="The Global Pet Care Services Market was valued at USD 29.5 Billion in 2025.",
        content_length_bytes=100,
        http_status=200,
    )

    # 2. Fortune Business Insights: 403 fallback with 5.41% India share of global market
    doc_india_snippet = FetchedSource(
        original_url="https://www.fortunebusinessinsights.com/pet-care-market-104749",
        title="Pet Care Market Report",
        source_name="Fortune Business Insights",
        fetch_status=FetchStatus.SNIPPET_FALLBACK,
        content="India represents roughly 5.41% of the global market in 2025.",
        content_length_bytes=65,
        http_status=403,
    )

    # Mock fetch service
    pipeline.fetch_service.fetch_discovered_source = AsyncMock(side_effect=[doc_global, doc_india_snippet])
    
    # Mock LLM analysis
    mock_biz = BusinessAnalysis(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        product="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers",
        target_customer="Pet owners",
        geography="India",
        business_model="B2C",
        customer_problem="Finding verified pet care providers",
        value_proposition="Verified veterinarians and groomers",
    )
    pipeline.llm_service.analyze_business_idea = AsyncMock(return_value=mock_biz)
    pipeline.llm_service.generate_competitors = AsyncMock(return_value=[])

    request = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
        max_sources=2,
    )

    with patch.object(pipeline.discovery_service, "discover_sources") as mock_disc:
        rq = ResearchQuery(metric_required="pet care market size", geography="India", year=2025)
        mock_disc.return_value = DiscoveryResponse(
            query=rq,
            query_string="pet care market size India 2025",
            status=DiscoveryStatus.SUCCESS,
            total_results_found=2,
            sources=[
                DiscoveredSource(
                    title=doc_global.title,
                    url=doc_global.original_url,
                    domain="www.wiseguyreports.com",
                    snippet=doc_global.content,
                    category=SourceCategory.FINANCIAL_MARKET_RESEARCH,
                    source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
                DiscoveredSource(
                    title=doc_india_snippet.title,
                    url=doc_india_snippet.original_url,
                    domain="www.fortunebusinessinsights.com",
                    snippet=doc_india_snippet.content,
                    category=SourceCategory.FINANCIAL_MARKET_RESEARCH,
                    source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
            ],
        )

        result = await pipeline.run(request)

        assert result.status == "completed"
        assert result.tam is not None
        assert result.tam.status == "calculated"
        assert result.tam.estimate == 29_500_000_000.0  # $29.5B

        # SAM must be calculated via TAM * 5.41%
        assert result.sam is not None
        assert result.sam.status == "calculated"
        # 29.5B * 0.0541 = 1,595,950,000.0
        assert abs(result.sam.estimate - 1_595_950_000.0) < 1000.0
        assert result.sam.estimate <= result.tam.estimate
        assert result.sam.estimate != result.tam.estimate

        # TEST 6: SOM must remain INSUFFICIENT_EVIDENCE under the SOM safety rule
        assert result.som is not None
        assert result.som.status == "insufficient_evidence"
        assert result.som.estimate is None


def test_previous_customer_pricing_regression_protections():
    """TEST 7: Growth rates, years, and tariffs are NOT misidentified as customer counts/pricing."""
    extraction_service = EvidenceExtractionService()
    
    # 1. Growth percentage is GROWTH_RATE, not customer count
    text_growth = "The solar panel market is experiencing 22-24% annual growth across residential installations."
    doc_growth = FetchedSource(
        original_url="https://example.com/growth",
        fetch_status=FetchStatus.SUCCESS,
        content=text_growth,
        content_length_bytes=len(text_growth),
    )
    resp_growth = extraction_service.extract_evidence_from_source(ExtractionRequest(source=doc_growth))
    for c in resp_growth.candidates:
        assert c.metric_type != MarketMetricType.CUSTOMER_COUNT
        assert c.metric_type != MarketMetricType.POPULATION

    # 2. Tariff is tariff / usage rate, not annual customer pricing
    text_tariff = "Solar energy feed-in tariff is set at INR 2/kWh in Tamil Nadu."
    doc_tariff = FetchedSource(
        original_url="https://example.com/tariff",
        fetch_status=FetchStatus.SUCCESS,
        content=text_tariff,
        content_length_bytes=len(text_tariff),
    )
    resp_tariff = extraction_service.extract_evidence_from_source(ExtractionRequest(source=doc_tariff))
    for c in resp_tariff.candidates:
        assert c.metric != "annual pricing / ARPU"
        assert c.metric_type != MarketMetricType.AVERAGE_PRICE


@pytest.mark.asyncio
async def test_successful_fetches_behave_normally():
    """TEST 8: Sources fetched with HTTP 200 retain SUCCESS status and full body content."""
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch.return_value = FetchedSource(
        original_url="https://example.com/report",
        fetch_status=FetchStatus.SUCCESS,
        http_status=200,
        content="Full page content here about the market.",
        content_length_bytes=40,
    )

    fetch_service = SourceFetchService(fetcher=mock_fetcher)
    discovered = DiscoveredSource(
        title="Report",
        url="https://example.com/report",
        domain="example.com",
        snippet="Short snippet",
        category=SourceCategory.OTHER,
        source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
    )

    result = await fetch_service.fetch_discovered_source(discovered)

    assert result.fetch_status == FetchStatus.SUCCESS
    assert result.content == "Full page content here about the market."
    assert result.http_status == 200
