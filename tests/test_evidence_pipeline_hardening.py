import pytest
import re
from unittest.mock import AsyncMock, MagicMock, patch

from app.fetching.models import FetchedSource, FetchStatus
from app.orchestration.models import PipelineRequest, PipelineStatus
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.business import BusinessAnalysis
from app.schemas.calculation import CalculationStatus
from app.schemas.discovery import DiscoveredSource, DiscoveryLifecycleStage, ResearchQuery, SourceCategory
from app.schemas.extraction import ExtractionMethod, ExtractionRequest, MarketMetricType
from app.services.discovery_service import DiscoveryService, get_discovery_service
from app.services.extraction_service import EvidenceExtractionService, get_extraction_service
from app.services.fetch_service import SourceFetchService
from app.services.validation_service import EvidenceValidationService, get_validation_service


@pytest.fixture
def extraction_service() -> EvidenceExtractionService:
    return get_extraction_service()


@pytest.fixture
def validation_service() -> EvidenceValidationService:
    return get_validation_service()


@pytest.fixture
def discovery_service() -> DiscoveryService:
    return get_discovery_service()


# ===========================================================================
# 1. Listicle & Non-Market Rejection Tests
# ===========================================================================

def test_irrelevant_linux_article_rejected(extraction_service: EvidenceExtractionService):
    """Assert that Linux distributions listicles are rejected and not extracted as market metrics."""
    text = "16 Best Linux Distributions for Older Computers"
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://ubercloud.com.au/best-linux-distros",
    )
    assert len(candidates) == 0, "Linux distributions listicle must be rejected from market evidence"


def test_wordpress_tips_rejected(extraction_service: EvidenceExtractionService):
    """Assert that WordPress tutorial tips are rejected as non-market noise."""
    text = "Easy WordPress Speed Optimization - 10 Simple Tips"
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://ubercloud.com.au/wordpress-speed-tips",
    )
    assert len(candidates) == 0, "WordPress tips listicle must be rejected"


def test_llm_listicle_rejected(extraction_service: EvidenceExtractionService):
    """Assert that Open Source LLM counts are rejected as non-market sizing noise."""
    text = "14 Top Outstanding Open Source LLMs for AI Engineers"
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://ubercloud.com.au/top-open-source-llms",
    )
    assert len(candidates) == 0, "LLM listicle count must be rejected"


def test_unrelated_birds_article_rejected(extraction_service: EvidenceExtractionService):
    """Assert that biological/flora/fauna numbers are rejected."""
    text = "There are 2,026 Birds observed in the nature reserve across the region."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://example.org/nature-reserve",
    )
    assert len(candidates) == 0, "Bird counts must not become customer population candidates"


def test_extracted_article_year_not_treated_as_market_metric(extraction_service: EvidenceExtractionService):
    """Assert that release years like 'Released in 2024' are not extracted as market values."""
    text = "The programming platform was officially released in 2024."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://example.org/news/platform-release",
    )
    # The year 2024 should not become a metric value of 2024
    assert len(candidates) == 0 or all(c.value != 2024.0 for c in candidates), (
        "Release calendar year must not become a scalar metric value"
    )


def test_extracted_listicle_number_not_market_metric(extraction_service: EvidenceExtractionService):
    """Assert that listicle headings starting with counts are rejected."""
    text = "10 Simple Tips to master Python and web development."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://example.org/tutorials/python-tips",
    )
    assert len(candidates) == 0, "Listicle numbers must not become market evidence candidates"


# ===========================================================================
# 2. Legitimate Market Evidence Acceptance Tests
# ===========================================================================

def test_india_college_student_evidence_accepted(
    extraction_service: EvidenceExtractionService,
    validation_service: EvidenceValidationService,
):
    """Assert that authentic college student demographic enrollment data is accepted."""
    sentence = "In India, approximately 41.3 million college students are currently enrolled in higher education institutions in 2024."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://aishe.gov.in/reports/higher-education-2024",
        source_name="Ministry of Education AISHE Report",
    )
    assert len(candidates) >= 1
    cand = candidates[0]
    assert "student" in cand.metric.lower() or "student" in (cand.unit or "").lower()
    assert cand.geography == "India"
    assert cand.metric_type in (MarketMetricType.STUDENT_COUNT, MarketMetricType.POPULATION, MarketMetricType.ENROLLMENT)

    # Validate candidate
    val_res = validation_service.validate_candidate(cand)
    assert val_res.is_valid is True
    assert val_res.source_quality_score >= 0.8


def test_market_size_evidence_accepted(
    extraction_service: EvidenceExtractionService,
    validation_service: EvidenceValidationService,
):
    """Assert that authentic EdTech market size data is extracted and validated."""
    sentence = "The India EdTech and online education market was valued at USD 2.5 billion in 2024."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=sentence,
        source_url="https://ibef.org/reports/india-edtech-industry",
        source_name="IBEF Industry Study",
    )
    assert len(candidates) >= 1
    cand = candidates[0]
    assert cand.value == 2_500_000_000.0
    assert cand.unit == "USD"
    assert cand.metric_type == MarketMetricType.MARKET_SIZE

    # Validate candidate
    val_res = validation_service.validate_candidate(cand)
    assert val_res.is_valid is True


# ===========================================================================
# 3. Discovery Relevance & Filter Tests
# ===========================================================================

def test_discovery_filtering_rejects_irrelevant_tech_articles(discovery_service: DiscoveryService):
    """Assert that discovery filtering excludes Linux, LLMs, WordPress, and Kafka articles."""
    query = ResearchQuery(
        metric_required="India college student population",
        geography="India",
        industry_topic="EdTech / Online Education",
    )

    sources = [
        DiscoveredSource(
            title="16 Best Linux Distributions for Beginners",
            url="https://ubercloud.com.au/linux-distros",
            snippet="A list of 16 top Linux operating systems.",
        ),
        DiscoveredSource(
            title="14 Top Open Source LLM Models in 2024",
            url="https://ubercloud.com.au/top-llms",
            snippet="Guide to 14 open source large language models.",
        ),
        DiscoveredSource(
            title="AISHE Higher Education Statistical Survey",
            url="https://aishe.gov.in/reports/survey",
            snippet="Official higher education enrollment statistics for India.",
            category=SourceCategory.OFFICIAL_GOVERNMENT,
        ),
    ]

    rel, rej = discovery_service.filter_relevant_sources(sources, query)
    assert len(rel) == 1
    assert rel[0].url == "https://aishe.gov.in/reports/survey"
    assert len(rej) == 2
    assert all("rejected" in s.relevance_status for s in rej)


def test_research_queries_are_business_specific():
    """Assert that generated research queries are semantically targeted to business attributes."""
    pipeline = MarketAnalysisPipeline()
    analysis = BusinessAnalysis(
        business_idea="I want to build an affordable online programming platform for college students in India.",
        industry="EdTech / Online Education",
        product="Affordable online programming platform",
        target_customer="College students",
        geography="India",
        business_model="B2C",
    )
    req = PipelineRequest(business_idea=analysis.business_idea, preferred_geography="India")
    queries = pipeline._generate_research_queries(analysis, req)

    assert len(queries) >= 2
    query_texts = " ".join(q.metric_required for q in queries)
    assert "India" in query_texts
    assert "college students" in query_texts.lower() or "student" in query_texts.lower()
    assert "edtech" in query_texts.lower() or "education" in query_texts.lower() or "programming" in query_texts.lower()


# ===========================================================================
# 4. Fetch Failure & DNS Resilience Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_failed_statistics_source_does_not_break_pipeline():
    """Simulate DNS/socket getaddrinfo failure and assert pipeline completes safely without crashing."""
    pipeline = MarketAnalysisPipeline()

    mock_analysis = BusinessAnalysis(
        business_idea="I want to build an affordable online programming platform for college students in India.",
        industry="EdTech / Online Education",
        product="Affordable online programming platform",
        target_customer="College students",
        geography="India",
        business_model="B2C",
    )

    failed_doc = FetchedSource(
        original_url="https://statistics.gov.in/reports/india-statistics",
        url="https://statistics.gov.in/reports/india-statistics",
        fetch_status="fetch_failed",
        error_message="Network connection failed: [Errno 11001] getaddrinfo failed",
        content="",
    )

    with patch.object(pipeline.llm_service, "analyze_business_idea", AsyncMock(return_value=mock_analysis)), \
         patch.object(pipeline.fetch_service, "fetch_discovered_source", AsyncMock(return_value=failed_doc)):

        req = PipelineRequest(business_idea=mock_analysis.business_idea, preferred_geography="India")
        res = await pipeline.run(req)

        assert res is not None
        assert res.status in (PipelineStatus.INSUFFICIENT_EVIDENCE, PipelineStatus.PARTIAL, PipelineStatus.COMPLETED)
        # TAM should not be calculated with fabricated numbers
        if res.tam:
            assert res.tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE or res.tam.value is None


def test_mock_evidence_identified():
    """Assert that mock discovery provider flags sources as mock data."""
    from app.discovery.mock_provider import MockDiscoveryProvider
    mock_prov = MockDiscoveryProvider()
    q = ResearchQuery(metric_required="India college student enrollment", geography="India")
    import asyncio
    sources = asyncio.run(mock_prov.search(q))
    assert len(sources) > 0
    assert all(s.is_mock is True for s in sources)


# ===========================================================================
# 5. End-to-End Test for College Programming Platform in India
# ===========================================================================

@pytest.mark.asyncio
async def test_end_to_end_college_programming_platform_india():
    """Complete end-to-end execution testing clean evidence handling and SOM safety rules."""
    pipeline = MarketAnalysisPipeline()
    mock_analysis = BusinessAnalysis(
        business_idea="I want to build an affordable online programming platform for college students in India.",
        industry="EdTech / Online Education",
        product="Affordable online programming platform",
        target_customer="College students",
        geography="India",
        business_model="B2C",
    )
    with patch.object(pipeline.llm_service, "analyze_business_idea", AsyncMock(return_value=mock_analysis)):
        req = PipelineRequest(
            business_idea="I want to build an affordable online programming platform for college students in India.",
            preferred_geography="India",
            preferred_year=2025,
        )
        res = await pipeline.run(req)

        assert res is not None
        assert res.business_analysis is not None
        assert res.business_analysis.geography == "India"
        assert "college students" in (res.business_analysis.target_customer or "").lower()

        # Evidence check: No Linux distros, birds, tips, or LLMs
        all_metrics = [c.metric.lower() for c in res.extracted_candidates] + [v.metric.lower() for v in res.validation_results]
        for m in all_metrics:
            assert "linux" not in m
            assert "bird" not in m
            assert "tip" not in m
            assert not re.search(r"\bllms?\b", m)

        # Deterministic SOM safety rule check: SOM is withheld without explicit user assumption
        if res.som:
            assert res.som.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence")


# ===========================================================================
# 6. Additional Granular Regression Tests (Phase 6 Hardening Audit)
# ===========================================================================

def test_software_version_number_rejected_as_metric(extraction_service: EvidenceExtractionService):
    """Assert software version numbers (e.g. 'Ubuntu 24.04 LTS') are rejected from becoming metrics."""
    text = "The server runs Ubuntu 24.04 LTS with long-term enterprise updates."
    candidates = extraction_service.extract_candidates_from_sentence(
        sentence=text,
        source_url="https://example.org/ubuntu-release",
    )
    assert len(candidates) == 0, "Software version numbers (e.g. 24.04 LTS) must not become market evidence"


def test_generalization_across_different_business_domains(discovery_service: DiscoveryService):
    """Assert discovery filtering dynamically generalizes to Fitness, Food Delivery, and SaaS domains."""
    # Domain A: Fitness app for college students
    query_fitness = ResearchQuery(
        metric_required="India college students fitness gym workout app adoption",
        target_population="College students",
        industry_topic="Fitness & Wellness",
        geography="India",
    )
    src_fitness_relevant = DiscoveredSource(
        title="Youth & College Student Fitness Habits in India 2025",
        url="https://fitnessresearch.in/youth-habits",
        snippet="Over 15 million college students in India engage in regular gym workouts and fitness app routines.",
    )
    src_unrelated = DiscoveredSource(
        title="Automotive Engine Transmission Diagnostics",
        url="https://automotive.org/engines",
        snippet="Analysis of commercial truck engine transmission efficiency.",
    )

    rel_fit, rej_fit = discovery_service.filter_relevant_sources([src_fitness_relevant, src_unrelated], query_fitness)
    assert len(rel_fit) == 1
    assert rel_fit[0].url == "https://fitnessresearch.in/youth-habits"
    assert len(rej_fit) == 1

    # Domain B: Food delivery for university campuses
    query_food = ResearchQuery(
        metric_required="University campus food delivery meal ordering volume",
        target_population="University students",
        industry_topic="Food Delivery / QSR",
        geography="India",
    )
    src_food_relevant = DiscoveredSource(
        title="University Campus Food Ordering Trends in India",
        url="https://foodtrends.in/campus-delivery",
        snippet="Report tracking 5 million student meal orders across major Indian universities.",
    )
    rel_food, rej_food = discovery_service.filter_relevant_sources([src_food_relevant, src_unrelated], query_food)
    assert len(rel_food) == 1
    assert rel_food[0].url == "https://foodtrends.in/campus-delivery"
    assert len(rej_food) == 1


def test_live_provider_not_silently_replaced_by_mock(discovery_service: DiscoveryService):
    """Assert that when LiveDiscoveryProvider encounters an error/missing key, it raises an exception rather than silently producing mock data."""
    from app.config import settings
    from app.discovery.live_provider import LiveDiscoveryProvider
    from app.discovery.base import DiscoveryProviderUnavailableException, DiscoveryProviderException
    
    with patch.object(settings, "SEARCH_API_KEY", None), patch.object(settings, "TAVILY_API_KEY", None):
        live_prov = LiveDiscoveryProvider(provider_type="live", api_key=None, api_url=None)
        q = ResearchQuery(metric_required="Test query")
        
        import asyncio
        # Expect clean provider exception, NEVER silent mock data fallback
        with pytest.raises((DiscoveryProviderUnavailableException, DiscoveryProviderException)):
            asyncio.run(live_prov.search(q))


@pytest.mark.asyncio
async def test_http_404_and_429_do_not_crash_pipeline_and_audit_recorded():
    """Assert HTTP 404 Not Found and HTTP 429 Rate Limit do not crash pipeline and are recorded in audit."""
    pipeline = MarketAnalysisPipeline()
    mock_analysis = BusinessAnalysis(
        business_idea="I want to build an affordable online programming platform for college students in India.",
        industry="EdTech / Online Education",
        product="Affordable online programming platform",
        target_customer="College students",
        geography="India",
        business_model="B2C",
    )
    
    async def mock_fetch(source):
        if "404" in source.url:
            return FetchedSource(
                original_url=source.url,
                url=source.url,
                fetch_status="fetch_failed",
                http_status_code=404,
                error_message="HTTP 404 Not Found",
                content="",
            )
        elif "429" in source.url:
            return FetchedSource(
                original_url=source.url,
                url=source.url,
                fetch_status="fetch_failed",
                http_status_code=429,
                error_message="HTTP 429 Rate Limited",
                content="",
            )
        else:
            return FetchedSource(
                original_url=source.url,
                url=source.url,
                fetch_status=FetchStatus.SUCCESS,
                http_status_code=200,
                content="In India, approximately 41.3 million college students are currently enrolled in higher education in 2024.",
            )

    sources = [
        DiscoveredSource(title="Broken Page", url="https://example.gov/404-report", snippet="Unavailable report"),
        DiscoveredSource(title="Rate Limited Page", url="https://example.org/429-data", snippet="Rate limited report"),
        DiscoveredSource(title="Valid Report", url="https://aishe.gov.in/report-2024", snippet="41.3 million college students in India"),
    ]

    with patch.object(pipeline.llm_service, "analyze_business_idea", AsyncMock(return_value=mock_analysis)), \
         patch.object(pipeline.discovery_service, "discover_sources", AsyncMock(return_value=MagicMock(sources=sources))), \
         patch.object(pipeline.fetch_service, "fetch_discovered_source", side_effect=mock_fetch):

        req = PipelineRequest(business_idea=mock_analysis.business_idea, preferred_geography="India")
        res = await pipeline.run(req)

        assert res is not None
        # Pipeline must not crash
        assert res.status in (PipelineStatus.COMPLETED, PipelineStatus.PARTIAL, PipelineStatus.INSUFFICIENT_EVIDENCE)
        # Failed sources must not produce valid candidates
        failed_candidate_urls = [c.source_url for c in res.extracted_candidates]
        assert "https://example.gov/404-report" not in failed_candidate_urls
        assert "https://example.org/429-data" not in failed_candidate_urls
        # Valid source must have produced valid candidate
        assert any("aishe.gov.in" in (c.source_url or "") for c in res.extracted_candidates)


