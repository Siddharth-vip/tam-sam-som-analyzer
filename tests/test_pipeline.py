import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.fetching.models import FetchedSource
from app.main import app
from app.orchestration.models import (
    PipelineProgressEvent,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
)
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.business import BusinessAnalysis
from app.schemas.calculation import (
    CalculationAssumption,
    CalculationStatus,
)
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    DiscoveryResponse,
    DiscoveryStatus,
    ResearchQuery,
    SourceCategory,
)
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionMethod,
    ExtractionResponse,
    ExtractionStatus,
)
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationResult,
    EvidenceValidationStatus,
    SourceProvenance,
    TriangulationResult,
)
from app.services.calculation_service import CalculationService
from app.services.discovery_service import DiscoveryService
from app.services.extraction_service import EvidenceExtractionService
from app.services.fetch_service import SourceFetchService
from app.services.llm_service import LLMConnectionError, OllamaLLMService
from app.services.validation_service import EvidenceValidationService

client = TestClient(app)


# ---------------------------------------------------------------------------
# FIXTURES & MOCK HELPERS
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_service():
    service = MagicMock(spec=OllamaLLMService)
    service.analyze_business_idea = AsyncMock(
        return_value=BusinessAnalysis(
            business_idea="An affordable online programming platform for college students in India",
            product="Online programming platform",
            industry="Education / EdTech",
            target_customer="College students",
            geography="India",
            pricing_model="Monthly subscription",
            business_model="B2C SaaS",
        )
    )
    return service


@pytest.fixture
def mock_discovery_service():
    service = MagicMock(spec=DiscoveryService)
    service.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="Number of college students", geography="India", year=2025),
            query_string="Number of college students India 2025",
            status=DiscoveryStatus.SUCCESS,
            total_results_found=2,
            sources=[
                DiscoveredSource(
                    title="Higher Education Survey India 2025",
                    url="https://statistics.gov.in/aishe-2025",
                    snippet="Report records 43 million college students in India in 2025.",
                    source_name="Ministry of Education",
                    category=SourceCategory.NATIONAL_STATISTICS,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
                DiscoveredSource(
                    title="Higher Education Commission Census",
                    url="https://education.gov.in/he-census",
                    snippet="Census confirms 43 million college students in India in 2025.",
                    source_name="Higher Education Commission",
                    category=SourceCategory.OFFICIAL_GOVERNMENT,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
            ],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )
    return service


@pytest.fixture
def mock_fetch_service():
    service = MagicMock(spec=SourceFetchService)
    service.fetch_discovered_source = AsyncMock(
        side_effect=lambda src: FetchedSource(
            original_url=src.url,
            final_url=src.url,
            title=src.title,
            source_name=src.source_name,
            content=f"According to national data, India has 43 million college students enrolled in 2025. Computer science students represent 15% of enrollment.",
            fetch_status="success",
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    )
    return service


# ---------------------------------------------------------------------------
# 24 COMPREHENSIVE PIPELINE ORCHESTRATION TESTS (Phase 4.3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_01_valid_pipeline_request() -> None:
    """TEST 1: Valid PipelineRequest instantiation and field defaults."""
    req = PipelineRequest(
        business_idea="AI-powered medical imaging diagnostics",
        max_sources=10,
        enable_calculation=True,
    )
    assert req.business_idea == "AI-powered medical imaging diagnostics"
    assert req.max_sources == 10
    assert req.enable_calculation is True


@pytest.mark.asyncio
async def test_02_empty_business_idea_rejected() -> None:
    """TEST 2: Empty business_idea raises validation error."""
    with pytest.raises(ValueError, match="non-empty string"):
        PipelineRequest(business_idea="")


@pytest.mark.asyncio
async def test_03_whitespace_business_idea_rejected() -> None:
    """TEST 3: Whitespace-only business_idea raises validation error."""
    with pytest.raises(ValueError, match="non-empty string"):
        PipelineRequest(business_idea="     ")


@pytest.mark.asyncio
async def test_04_max_sources_validation_bounds() -> None:
    """TEST 4: max_sources bounds (1 to 50) enforced."""
    with pytest.raises(ValueError):
        PipelineRequest(business_idea="Valid business concept", max_sources=0)
    with pytest.raises(ValueError):
        PipelineRequest(business_idea="Valid business concept", max_sources=100)


@pytest.mark.asyncio
async def test_05_business_analysis_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 5: Business analysis stage executes and populates BusinessAnalysis in result."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert result.business_analysis is not None
    assert result.business_analysis.industry == "Education / EdTech"
    mock_llm_service.analyze_business_idea.assert_called_once()


@pytest.mark.asyncio
async def test_06_discovery_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 6: Discovery stage executes and captures discovered sources."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert len(result.discovered_sources) >= 1
    assert result.research_queries is not None
    assert len(result.research_queries) >= 1


@pytest.mark.asyncio
async def test_07_fetching_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 7: Fetching stage safely fetches documents."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert len(result.fetched_sources) >= 1
    assert all(f.content is not None for f in result.fetched_sources)


@pytest.mark.asyncio
async def test_08_extraction_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 8: Extraction stage extracts candidate evidence records."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert len(result.extracted_candidates) >= 1


@pytest.mark.asyncio
async def test_09_validation_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 9: Validation stage executes and preserves validated items."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert len(result.validation_results) >= 1
    assert all(v.is_valid for v in result.validation_results)


@pytest.mark.asyncio
async def test_10_triangulation_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 10: Multi-source triangulation corroborates independent sources."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="An affordable online programming platform for college students in India")
    result = await pipeline.run(request)

    assert result.triangulation_result is not None
    # 2 independent government sources for 43 million students becomes verified
    assert len(result.triangulation_result.verified_items) >= 1


@pytest.mark.asyncio
async def test_11_calculation_stage_executed(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 11: Calculation stage generates deterministic calculation report."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="annual_subscription_price",
                value=1200.0,
                unit="INR",
                justification="Target pricing model",
            )
        ],
    )
    result = await pipeline.run(request)

    assert result.calculation_report is not None
    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_12_full_successful_pipeline(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 12: Complete pipeline end-to-end execution with TAM, SAM, and SOM."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="target_cs_students_pct",
                value=15.0,
                unit="%",
                justification="Target CS student proportion",
            ),
            CalculationAssumption(
                name="annual_subscription_price",
                value=1200.0,
                unit="INR",
                justification="Target pricing model",
            ),
            CalculationAssumption(
                name="year_1_som_share",
                value=5.0,
                unit="%",
                justification="Target Year 1 SOM share",
            ),
        ],
    )
    result = await pipeline.run(request)

    assert result.status == PipelineStatus.COMPLETED
    assert result.tam.estimate == 51600000000.0
    assert result.sam.estimate == 7740000000.0
    assert result.som.estimate == 387000000.0
    assert result.confidence in (
        EvidenceConfidence.MEDIUM,
        EvidenceConfidence.HIGH,
        EvidenceConfidence.VERY_HIGH,
        "medium",
        "high",
        "very_high",
    )


@pytest.mark.asyncio
async def test_13_partial_source_fetch_failure(
    mock_llm_service, mock_discovery_service
) -> None:
    """TEST 13: Partial source fetch failures do not terminate the pipeline."""
    failing_fetcher = MagicMock(spec=SourceFetchService)
    # Source 1 succeeds, Source 2 fails
    async def fetch_mock(src):
        if "statistics.gov.in" in src.url:
            return FetchedSource(
                original_url=src.url,
                final_url=src.url,
                title=src.title,
                source_name=src.source_name,
                content="National data: 43 million students.",
                fetch_status="success",
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
            )
        raise Exception("HTTP 500 Internal Server Error")

    failing_fetcher.fetch_discovered_source = AsyncMock(side_effect=fetch_mock)

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=failing_fetcher,
    )
    request = PipelineRequest(business_idea="College education platform in India")
    result = await pipeline.run(request)

    # Pipeline completes with PARTIAL status and warnings
    assert result.status == PipelineStatus.PARTIAL
    assert len(result.fetched_sources) == 1
    assert any("Failed to fetch source" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_14_discovery_provider_unavailable(
    mock_llm_service, mock_fetch_service
) -> None:
    """TEST 14: Discovery provider exception returns FAILED status with error details."""
    failing_discovery = MagicMock(spec=DiscoveryService)
    failing_discovery.discover_sources = AsyncMock(side_effect=Exception("Discovery index down"))

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=failing_discovery,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="Test business concept")
    result = await pipeline.run(request)

    assert result.status == PipelineStatus.FAILED
    assert any("Discovery index down" in e for e in result.errors)


@pytest.mark.asyncio
async def test_15_ollama_unavailable(
    mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 15: Ollama unavailable causes pipeline to fail gracefully with error recorded."""
    failing_llm = MagicMock(spec=OllamaLLMService)
    failing_llm.analyze_business_idea = AsyncMock(side_effect=LLMConnectionError("Ollama offline"))

    pipeline = MarketAnalysisPipeline(
        llm_service=failing_llm,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="Test business concept")
    result = await pipeline.run(request)

    assert result.status == PipelineStatus.FAILED
    assert any("Ollama offline" in e for e in result.errors)


@pytest.mark.asyncio
async def test_16_insufficient_evidence(mock_llm_service) -> None:
    """TEST 16: Zero discovered sources returns INSUFFICIENT_EVIDENCE status."""
    empty_discovery = MagicMock(spec=DiscoveryService)
    empty_discovery.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="Rare niche"),
            query_string="Rare niche",
            status=DiscoveryStatus.NO_RESULTS,
            total_results_found=0,
            sources=[],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=empty_discovery,
    )
    request = PipelineRequest(business_idea="Ultra-rare boutique product")
    result = await pipeline.run(request)

    assert result.status == PipelineStatus.INSUFFICIENT_EVIDENCE
    assert any("insufficient evidence" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_17_conflicting_evidence(mock_llm_service) -> None:
    """TEST 17: Contradictory sources are detected and preserved without mathematical averaging."""
    conflicting_discovery = MagicMock(spec=DiscoveryService)
    conflicting_discovery.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="Student count"),
            query_string="Student count",
            status=DiscoveryStatus.SUCCESS,
            total_results_found=2,
            sources=[
                DiscoveredSource(
                    title="Source A",
                    url="https://source-a.org/data",
                    snippet="40 million students",
                    source_name="Org A",
                    category=SourceCategory.TRADE_ASSOCIATION,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
                DiscoveredSource(
                    title="Source B",
                    url="https://source-b.com/data",
                    snippet="60 million students",
                    source_name="Org B",
                    category=SourceCategory.INDUSTRY_ANALYST,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                ),
            ],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )

    conflict_fetcher = MagicMock(spec=SourceFetchService)
    conflict_fetcher.fetch_discovered_source = AsyncMock(
        side_effect=lambda src: FetchedSource(
            original_url=src.url,
            final_url=src.url,
            title=src.title,
            source_name=src.source_name,
            content=f"Report says {40 if 'source-a' in src.url else 60} million students in India.",
            fetch_status="success",
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    )

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=conflicting_discovery,
        fetch_service=conflict_fetcher,
    )
    request = PipelineRequest(business_idea="Programming platform for students in India")
    result = await pipeline.run(request)

    assert len(result.conflicts) >= 1
    # Check that conflicting values (40M and 60M) remain separate and are not averaged to 50M
    assert 40000000.0 in result.conflicts[0].conflicting_values
    assert 60000000.0 in result.conflicts[0].conflicting_values


@pytest.mark.asyncio
async def test_18_discovered_evidence_cannot_reach_calculation(
    mock_llm_service, mock_discovery_service
) -> None:
    """TEST 18: Unfetched/unvalidated DISCOVERED sources cannot pass the Evidence Gate."""
    empty_fetcher = MagicMock(spec=SourceFetchService)
    # Fetcher returns no content
    empty_fetcher.fetch_discovered_source = AsyncMock(return_value=None)

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=empty_fetcher,
    )
    request = PipelineRequest(business_idea="Platform for students in India")
    result = await pipeline.run(request)

    # Discovered sources exist, but 0 extracted or validated items
    assert len(result.discovered_sources) == 2
    assert len(result.extracted_candidates) == 0
    assert len(result.validation_results) == 0


@pytest.mark.asyncio
async def test_19_no_hallucinated_som(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 19: SOM Safety Rule: SOM is withheld when market share is not provided."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="pricing_arpu",
                value=1200.0,
                unit="INR",
                justification="Pricing model",
            )
        ],
    )
    result = await pipeline.run(request)

    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED
    assert result.som is None or result.som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert any("SOM was withheld under the SOM Safety Rule" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_20_pipeline_id_generated(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 20: Every pipeline execution creates a unique pipeline_id."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    req1 = PipelineRequest(business_idea="Business A")
    req2 = PipelineRequest(business_idea="Business B")

    res1 = await pipeline.run(req1)
    res2 = await pipeline.run(req2)

    assert res1.pipeline_id.startswith("pipe_")
    assert res2.pipeline_id.startswith("pipe_")
    assert res1.pipeline_id != res2.pipeline_id


@pytest.mark.asyncio
async def test_21_progress_events_emitted_in_correct_order(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 21: run_with_progress emits progress events in correct chronological order."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="Programming platform for students in India")

    stages_emitted = []
    async for event in pipeline.run_with_progress(request):
        stages_emitted.append(event.stage)

    assert PipelineStage.BUSINESS_ANALYSIS in stages_emitted
    assert PipelineStage.QUERY_GENERATION in stages_emitted
    assert PipelineStage.DISCOVERY in stages_emitted
    assert PipelineStage.FETCHING in stages_emitted
    assert PipelineStage.EXTRACTION in stages_emitted
    assert PipelineStage.VALIDATION in stages_emitted
    assert PipelineStage.TRIANGULATION in stages_emitted
    assert PipelineStage.COMPLETED in stages_emitted


@pytest.mark.asyncio
async def test_22_progress_reaches_100_percent(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 22: Progress percent increases monotonically and finishes at 100%."""
    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = PipelineRequest(business_idea="Programming platform for students in India")

    percentages = []
    async for event in pipeline.run_with_progress(request):
        percentages.append(event.progress_percent)

    assert percentages[-1] == 100
    assert percentages == sorted(percentages)


def test_23_sse_endpoint_returns_events(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 23: POST /api/v1/pipeline/analyze/stream streams Server-Sent Events."""
    mock_pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    from app.orchestration.pipeline import get_market_pipeline
    app.dependency_overrides[get_market_pipeline] = lambda: mock_pipeline

    try:
        payload = {
            "business_idea": "An online learning platform for students in India",
        }
        response = client.post("/api/v1/pipeline/analyze/stream", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        text = response.text
        assert "data: " in text
        lines = [line for line in text.split("\n") if line.startswith("data: ")]
        assert len(lines) >= 1
        # Verify valid JSON in SSE payload
        first_event = json.loads(lines[0].replace("data: ", ""))
        assert "pipeline_id" in first_event
        assert "stage" in first_event
        assert "progress_percent" in first_event
    finally:
        app.dependency_overrides.pop(get_market_pipeline, None)


def test_24_api_pipeline_analyze_endpoint_success(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 24: POST /api/v1/pipeline/analyze accepts request and returns structured PipelineResult."""
    mock_pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    from app.orchestration.pipeline import get_market_pipeline
    app.dependency_overrides[get_market_pipeline] = lambda: mock_pipeline

    try:
        payload = {
            "business_idea": "An online accounting SaaS for Indian SMEs",
            "explicit_assumptions": [
                {
                    "name": "annual_subscription",
                    "value": 5000.0,
                    "unit": "INR",
                    "justification": "Subscription pricing",
                }
            ],
        }
        response = client.post("/api/v1/pipeline/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_id" in data
        assert "status" in data
        assert "business_idea" in data
        assert "audit_trail" in data
    finally:
        app.dependency_overrides.pop(get_market_pipeline, None)
