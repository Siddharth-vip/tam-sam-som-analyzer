from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.fetching.models import FetchedSource
from app.main import app
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
from app.schemas.orchestration import (
    OrchestrationProgress,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationStage,
    OrchestrationStageStatus,
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
from app.services.orchestration_service import (
    OrchestrationService,
    get_orchestration_service,
)
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
# 17 COMPREHENSIVE ORCHESTRATION TESTS (Phase 4.3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_01_valid_end_to_end_pipeline(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 1: Valid end-to-end pipeline execution calculating TAM, SAM, and SOM."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(
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
    result = await orchestrator.run(request)

    assert result.status == "completed"
    assert result.current_stage == OrchestrationStage.COMPLETED
    assert result.business_analysis is not None
    assert result.business_analysis.geography == "India"
    assert result.evidence_summary.total_discovered >= 2
    assert result.evidence_summary.total_fetched >= 2
    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED
    assert result.tam.estimate == 51600000000.0
    assert result.sam is not None
    assert result.sam.estimate == 7740000000.0
    assert result.som is not None
    assert result.som.estimate == 387000000.0


@pytest.mark.asyncio
async def test_02_invalid_business_idea() -> None:
    """TEST 2: Invalid empty or whitespace business ideas raise validation error."""
    with pytest.raises(ValueError, match="non-empty string"):
        OrchestrationRequest(business_idea="")
    with pytest.raises(ValueError, match="non-empty string"):
        OrchestrationRequest(business_idea="   ")


@pytest.mark.asyncio
async def test_03_ollama_unavailable(
    mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 3: Ollama connection error sets status=failed at analyzing_business stage."""
    failing_llm = MagicMock(spec=OllamaLLMService)
    failing_llm.analyze_business_idea = AsyncMock(side_effect=LLMConnectionError("Ollama connection refused"))

    orchestrator = OrchestrationService(
        llm_service=failing_llm,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(business_idea="Valid business concept")
    result = await orchestrator.run(request)

    assert result.status == "failed"
    assert result.current_stage == OrchestrationStage.FAILED
    assert len(result.errors) >= 1
    assert result.errors[0].stage == OrchestrationStage.ANALYZING_BUSINESS
    assert "Ollama connection refused" in result.errors[0].error_message


@pytest.mark.asyncio
async def test_04_discovery_provider_unavailable(
    mock_llm_service, mock_fetch_service
) -> None:
    """TEST 4: Discovery exception sets status=failed at discovering_evidence stage."""
    failing_discovery = MagicMock(spec=DiscoveryService)
    failing_discovery.discover_sources = AsyncMock(side_effect=Exception("Discovery provider timed out"))

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=failing_discovery,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(business_idea="Valid business concept")
    result = await orchestrator.run(request)

    assert result.status == "failed"
    assert result.current_stage == OrchestrationStage.FAILED
    assert any(e.stage == OrchestrationStage.DISCOVERING_EVIDENCE for e in result.errors)


@pytest.mark.asyncio
async def test_05_fetch_failure(
    mock_llm_service, mock_discovery_service
) -> None:
    """TEST 5: Partial fetch failures continue execution and record warnings."""
    failing_fetcher = MagicMock(spec=SourceFetchService)
    failing_fetcher.fetch_discovered_source = AsyncMock(side_effect=Exception("HTTP 403 Forbidden"))

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=failing_fetcher,
    )
    request = OrchestrationRequest(business_idea="Valid business concept")
    result = await orchestrator.run(request)

    assert result.evidence_summary.total_fetched == 0
    assert any("Failed to fetch source" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_06_extraction_failure(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 6: Extraction parsing errors on documents are caught as warnings."""
    failing_extractor = MagicMock(spec=EvidenceExtractionService)
    failing_extractor.extract_evidence_from_source = MagicMock(side_effect=Exception("Parser buffer overflow"))

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
        extraction_service=failing_extractor,
    )
    request = OrchestrationRequest(business_idea="Valid business concept")
    result = await orchestrator.run(request)

    assert result.evidence_summary.total_extracted_candidates == 0
    assert any("Extraction failed" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_07_invalid_evidence(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 7: Invalid evidence candidates fail structural validation and are excluded."""
    # Candidates with invalid negative value
    bad_candidate = ExtractedEvidenceCandidate(
        metric="students",
        value=-500.0,
        unit="students",
        source_url="https://source.com/doc",
        source_name="Source",
        source_context="Context snippet",
        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
    )
    failing_extractor = MagicMock(spec=EvidenceExtractionService)
    failing_extractor.extract_evidence_from_source = MagicMock(
        return_value=ExtractionResponse(
            source_url="https://source.com/doc",
            candidates=[bad_candidate],
            status=ExtractionStatus.SUCCESS,
        )
    )

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
        extraction_service=failing_extractor,
    )
    request = OrchestrationRequest(business_idea="Valid business concept")
    result = await orchestrator.run(request)

    # Validated count should be 0 because negative value fails validation
    assert result.evidence_summary.total_validated == 0


@pytest.mark.asyncio
async def test_08_insufficient_evidence(mock_llm_service) -> None:
    """TEST 8: Zero discovered sources returns status=insufficient_evidence."""
    empty_discovery = MagicMock(spec=DiscoveryService)
    empty_discovery.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="Niche metric"),
            query_string="Niche metric",
            status=DiscoveryStatus.NO_RESULTS,
            total_results_found=0,
            sources=[],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=empty_discovery,
    )
    request = OrchestrationRequest(business_idea="Ultra-rare niche product")
    result = await orchestrator.run(request)

    assert result.status == "insufficient_evidence"
    assert result.tam is None
    assert any("insufficient evidence" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_09_conflicting_evidence(mock_llm_service) -> None:
    """TEST 9: Contradictory sources are detected in conflict_groups and not averaged."""
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

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=conflicting_discovery,
        fetch_service=conflict_fetcher,
    )
    request = OrchestrationRequest(business_idea="Programming platform for students in India")
    result = await orchestrator.run(request)

    assert len(result.conflict_groups) >= 1
    assert 40000000.0 in result.conflict_groups[0].conflicting_values
    assert 60000000.0 in result.conflict_groups[0].conflicting_values


@pytest.mark.asyncio
async def test_10_verified_evidence_successfully_reaching_calculation(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 10: Verified multi-source evidence passes the Evidence Gate into calculation."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(
        business_idea="Programming platform for students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="annual_subscription_price",
                value=1200.0,
                unit="INR",
                justification="Pricing model",
            )
        ],
    )
    result = await orchestrator.run(request)

    assert result.evidence_summary.total_verified >= 1
    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_11_discovered_evidence_blocked_from_calculation(
    mock_llm_service, mock_discovery_service
) -> None:
    """TEST 11: Unfetched / unvalidated DISCOVERED sources cannot pass the Evidence Gate."""
    empty_fetcher = MagicMock(spec=SourceFetchService)
    empty_fetcher.fetch_discovered_source = AsyncMock(return_value=None)

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=empty_fetcher,
    )
    request = OrchestrationRequest(business_idea="Platform for students in India")
    result = await orchestrator.run(request)

    assert len(result.discovered_sources) >= 1
    assert result.evidence_summary.total_extracted_candidates == 0
    assert result.evidence_summary.total_validated == 0


@pytest.mark.asyncio
async def test_12_som_calculation_blocked_when_market_share_missing(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 12: SOM Safety Rule: SOM is withheld when obtainable market share is not provided."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="annual_subscription_price",
                value=1200.0,
                unit="INR",
                justification="Pricing model",
            )
        ],
    )
    result = await orchestrator.run(request)

    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED
    assert result.som is None or result.som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert any("SOM was withheld under the SOM Safety Rule" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_13_existing_user_assumptions_passed_correctly(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 13: Explicit user assumptions are preserved and applied in calculation inputs."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    assumptions = [
        CalculationAssumption(
            name="annual_price",
            value=2000.0,
            unit="INR",
            justification="Stated subscription fee",
        ),
        CalculationAssumption(
            name="target_cs_segment_pct",
            value=20.0,
            unit="%",
            justification="CS students share",
        ),
        CalculationAssumption(
            name="target_som_share",
            value=10.0,
            unit="%",
            justification="Year 1 penetration estimate",
        ),
    ]
    request = OrchestrationRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=assumptions,
    )
    result = await orchestrator.run(request)

    assert len(result.assumptions) == 3
    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED
    assert result.sam is not None
    assert result.sam.status == CalculationStatus.CALCULATED
    assert result.som is not None
    assert result.som.status == CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_14_stage_progress_and_status_correctness(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 14: All 7 core stages are tracked with completed status and duration in milliseconds."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(business_idea="Programming platform for students in India")
    result = await orchestrator.run(request)

    stages_present = [s.stage for s in result.stages]
    assert OrchestrationStage.ANALYZING_BUSINESS in stages_present
    assert OrchestrationStage.DISCOVERING_EVIDENCE in stages_present
    assert OrchestrationStage.FETCHING_SOURCES in stages_present
    assert OrchestrationStage.EXTRACTING_EVIDENCE in stages_present
    assert OrchestrationStage.VALIDATING_EVIDENCE in stages_present
    assert OrchestrationStage.TRIANGULATING_EVIDENCE in stages_present
    assert OrchestrationStage.CALCULATING_MARKET in stages_present
    assert all(s.status == OrchestrationStageStatus.COMPLETED for s in result.stages)


@pytest.mark.asyncio
async def test_15_final_audit_trail_completeness(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 15: Final result preserves complete auditability: queries, provenance, and durations."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(business_idea="Programming platform for students in India")
    result = await orchestrator.run(request)

    assert result.analysis_id.startswith("mkt_")
    assert result.total_duration_ms is not None
    assert len(result.provenance) >= 1
    assert any("gov.in" in p.source_url for p in result.provenance)
    assert len(result.research_queries) >= 1


def test_16_api_endpoint_success(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 16: POST /api/v1/market/analyze successfully returns HTTP 200 and OrchestrationResult."""
    mock_orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    app.dependency_overrides[get_orchestration_service] = lambda: mock_orchestrator

    try:
        payload = {
            "business_idea": "An online accounting SaaS for Indian SMEs",
            "explicit_assumptions": [
                {
                    "name": "annual_subscription_price",
                    "value": 5000.0,
                    "unit": "INR",
                    "justification": "Subscription pricing",
                }
            ],
        }
        response = client.post("/api/v1/market/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert "status" in data
        assert "stages" in data
        assert len(data["stages"]) == 7
        assert "evidence_summary" in data
    finally:
        app.dependency_overrides.pop(get_orchestration_service, None)


def test_17_api_endpoint_validation_failure() -> None:
    """TEST 17: POST /api/v1/market/analyze rejects invalid input with HTTP 422."""
    response = client.post("/api/v1/market/analyze", json={"business_idea": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_18_top_down_bottom_up_divergence_propagation(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 18: Calculation engine divergence and method comparison are propagated to report."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(
        business_idea="Programming platform for students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="annual_arpu",
                value=1200.0,
                unit="INR",
                justification="Pricing",
            ),
            CalculationAssumption(
                name="top_down_tam_value",
                value=50000000000.0,
                unit="INR",
                justification="Top-down analyst report",
            ),
        ],
    )
    result = await orchestrator.run(request)
    assert result.calculation_report is not None
    assert result.calculation_report.method_comparison is not None
    assert result.tam is not None


@pytest.mark.asyncio
async def test_19_missing_tam_and_sam_evidence_handling(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 19: Missing TAM/SAM evidence results in INSUFFICIENT_EVIDENCE status with explanation."""
    empty_extraction = MagicMock(spec=EvidenceExtractionService)
    empty_extraction.extract_evidence_from_source = MagicMock(
        return_value=ExtractionResponse(
            source_url="https://statistics.gov.in/aishe-2025",
            status=ExtractionStatus.NO_METRICS_FOUND,
            candidates_extracted=0,
            candidates=[],
            message="No metrics found",
        )
    )

    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
        extraction_service=empty_extraction,
    )
    request = OrchestrationRequest(business_idea="Valid concept with no discoverable market stats")
    result = await orchestrator.run(request)

    assert result.status == "insufficient_evidence"
    assert result.tam is not None
    assert result.tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert "insufficient evidence" in result.tam.message.lower()


@pytest.mark.asyncio
async def test_20_pipeline_stage_ordering(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 20: Stage execution strictly follows the deterministic 7-stage sequence."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(business_idea="Programming platform for students in India")
    result = await orchestrator.run(request)

    expected_order = [
        OrchestrationStage.ANALYZING_BUSINESS,
        OrchestrationStage.DISCOVERING_EVIDENCE,
        OrchestrationStage.FETCHING_SOURCES,
        OrchestrationStage.EXTRACTING_EVIDENCE,
        OrchestrationStage.VALIDATING_EVIDENCE,
        OrchestrationStage.TRIANGULATING_EVIDENCE,
        OrchestrationStage.CALCULATING_MARKET,
    ]
    actual_order = [s.stage for s in result.stages]
    assert actual_order == expected_order


@pytest.mark.asyncio
async def test_21_final_report_method_comparison_and_uncertainty(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 21: Full calculation produces uncertainty intervals and audit trail."""
    orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    request = OrchestrationRequest(
        business_idea="An affordable online programming platform for college students in India",
        explicit_assumptions=[
            CalculationAssumption(
                name="annual_arpu",
                value=1200.0,
                unit="INR",
                justification="Pricing",
            ),
            CalculationAssumption(
                name="target_customer_percentage",
                value=18.0,
                unit="%",
                justification="Target CS students segment",
            ),
            CalculationAssumption(
                name="year_1_som_share",
                value=5.0,
                unit="%",
                justification="Year 1 penetration",
            ),
        ],
    )
    result = await orchestrator.run(request)

    assert result.status == "completed"
    assert result.tam.estimate is not None
    assert result.tam.interval is not None
    assert result.tam.interval.lower <= result.tam.estimate <= result.tam.interval.upper
    assert result.sam.estimate is not None
    assert result.som.estimate is not None


def test_22_semantic_research_query_generation(mock_llm_service) -> None:
    """TEST 22: Research query generation produces targeted semantic queries and avoids poor fallbacks."""
    orchestrator = OrchestrationService(llm_service=mock_llm_service)
    analysis = BusinessAnalysis(
        business_idea="I want to build an affordable online programming platform for college students in India",
        product="Affordable online programming platform",
        industry="EdTech / Online Education",
        target_customer="College students",
        geography="India",
        business_model="B2C",
        pricing_model=None,
    )
    request = OrchestrationRequest(business_idea=analysis.business_idea)
    queries = orchestrator._generate_research_queries(analysis, request)

    assert len(queries) == 3
    metric_names = [q.metric_required for q in queries]

    # Demographic query
    assert any("college students" in q.lower() for q in metric_names)
    # Market size query
    assert any("edtech" in q.lower() and "market size" in q.lower() for q in metric_names)
    # Pricing query
    assert any("pricing" in q.lower() or "arpu" in q.lower() for q in metric_names)

    # Must NOT produce nonsensical queries
    assert not any("number of affordable online programming platform" in q.lower() for q in metric_names)
    for q in queries:
        assert q.geography == "India"
        assert q.year == 2025


def test_23_swagger_placeholder_sanitization() -> None:
    """TEST 23: Swagger default/placeholder values ('string', year=0, dummy assumptions) are sanitized."""
    raw_payload = {
        "business_idea": "I want to build an affordable online programming platform for college students in India",
        "geography": "string",
        "year": 0,
        "explicit_assumptions": [
            {
                "name": "string",
                "value": 0,
                "unit": "string",
                "justification": "string",
            }
        ],
    }
    request = OrchestrationRequest.model_validate(raw_payload)

    # Placeholders must be sanitized to None / empty list
    assert request.geography is None
    assert request.year is None
    assert request.explicit_assumptions == []


def test_24_swagger_placeholders_api_execution(
    mock_llm_service, mock_discovery_service, mock_fetch_service
) -> None:
    """TEST 24: API endpoint handles Swagger placeholder values without treating them as real assumptions."""
    mock_orchestrator = OrchestrationService(
        llm_service=mock_llm_service,
        discovery_service=mock_discovery_service,
        fetch_service=mock_fetch_service,
    )
    app.dependency_overrides[get_orchestration_service] = lambda: mock_orchestrator

    try:
        swagger_payload = {
            "business_idea": "I want to build an affordable online programming platform for college students in India",
            "geography": "string",
            "year": 0,
            "max_sources": 5,
            "explicit_assumptions": [
                {
                    "name": "string",
                    "value": 0,
                    "unit": "string",
                    "justification": "string",
                }
            ],
        }
        response = client.post("/api/v1/market/analyze", json=swagger_payload)
        assert response.status_code == 200
        data = response.json()

        # Assumptions should NOT contain the dummy "string" item
        assert len(data["assumptions"]) == 0
        assert data["status"] in ("completed", "insufficient_evidence", "partial")
    finally:
        app.dependency_overrides.pop(get_orchestration_service, None)
