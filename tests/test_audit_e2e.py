import math
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx

from app.fetching.http_fetcher import HttpSourceFetcher
from app.fetching.models import FetchedSource, FetchRequest, FetchStatus
from app.main import app
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.business import BusinessAnalysis
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationStatus,
    DivergenceSeverity,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    DiscoveryResponse,
    ResearchQuery,
    SourceCategory,
)
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionMethod,
    ExtractionRequest,
    ExtractionStatus,
)
from app.schemas.orchestration import OrchestrationRequest
from app.schemas.pipeline import PipelineRequest
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationStatus,
    TriangulationRequest,
)
from app.services.calculation_service import CalculationService
from app.services.discovery_service import DiscoveryService
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService

client = TestClient(app)


# ===========================================================================
# PHASE 2 & 7: API Contract Flexibility for Triangulation
# ===========================================================================

def test_api_triangulation_with_singular_candidate_payload() -> None:
    """Verify triangulation endpoint accepts singular {'candidate': {...}} payload without 422 error."""
    payload = {
        "candidate": {
            "metric": "working professionals",
            "value": 1500000.0,
            "unit": "people",
            "geography": "Chennai",
            "year": 2025,
            "source_name": "Tamil Nadu Statistical Bureau",
            "source_url": "https://statistics.tn.gov.in/labour-force-chennai",
            "source_context": "Chennai has 1.5 million working professionals employed in the IT and services sector in 2025.",
        }
    }

    response = client.post("/api/v1/evidence/triangulate", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["total_candidates_processed"] == 1
    assert len(data["validated_items"]) == 1
    item = data["validated_items"][0]
    assert item["metric"] == "working professionals"
    assert item["value"] == 1500000.0
    assert item["lifecycle_stage"] == "validated"
    assert item["corroborating_source_count"] == 1


def test_api_triangulation_with_raw_list_payload() -> None:
    """Verify triangulation endpoint accepts raw list [{...}, {...}] payload."""
    payload = [
        {
            "metric": "working professionals",
            "value": 1500000.0,
            "unit": "people",
            "geography": "Chennai",
            "year": 2025,
            "source_name": "Source 1",
            "source_url": "https://statistics.tn.gov.in/report1",
            "source_context": "1.5 million working professionals in Chennai in 2025.",
        },
        {
            "metric": "working professionals",
            "value": 1500000.0,
            "unit": "people",
            "geography": "Chennai",
            "year": 2025,
            "source_name": "Source 2",
            "source_url": "https://mospi.gov.in/report2",
            "source_context": "National stats confirm 1.5 million working professionals in Chennai in 2025.",
        },
    ]

    response = client.post("/api/v1/evidence/triangulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates_processed"] == 2
    assert len(data["verified_items"]) == 1
    assert data["verified_items"][0]["lifecycle_stage"] == "verified"
    assert data["verified_items"][0]["corroborating_source_count"] == 2


# ===========================================================================
# PHASE 4: Evidence Fetching & Redirect / Content Drift Handling
# ===========================================================================

@pytest.mark.asyncio
async def test_fetching_handles_cross_domain_redirect_and_unrelated_content() -> None:
    """Verify that when a source URL redirects across domains (e.g. research-institute.org -> ubercloud.com.au),

    the fetcher correctly records final_url, detects cross-domain redirect, updates domain to the actual
    target, extracts the actual page content and title rather than blindly trusting the claimed metadata.
    """
    fetcher = HttpSourceFetcher()

    fake_html = """
    <html>
    <head><title>Ubercloud - High Performance Cloud Solutions</title></head>
    <body>
        <h1>Cloud Computing Infrastructure</h1>
        <p>We provide HPC cloud software solutions for CAE simulation and cloud HPC engineering.</p>
    </body>
    </html>
    """

    # Mock HTTP response with cross-domain redirect
    mock_response = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        text=fake_html,
        request=httpx.Request("GET", "https://ubercloud.com.au/"),
    )

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response

        fetched = await fetcher.fetch(
            url="https://research-institute.org/reports/market-analysis",
            title="Healthy Meal Delivery / Food Service Annual Market & Industry Report",
            source_name="Global Economic & Industry Research Institute",
        )

        assert fetched.fetch_status == FetchStatus.SUCCESS
        assert fetched.original_url == "https://research-institute.org/reports/market-analysis"
        assert fetched.final_url == "https://ubercloud.com.au/"
        assert fetched.domain == "ubercloud.com.au"
        assert fetched.is_cross_domain_redirect is True
        assert fetched.is_redirected is True
        # Title updated to reflect actual fetched page, not claimed meal delivery report
        assert "Ubercloud" in fetched.title
        assert fetched.source_name is None  # Does not falsely attribute ubercloud content to Research Institute

        # Test extraction on this unrelated content
        extractor = EvidenceExtractionService()
        extract_req = ExtractionRequest(source=fetched)
        extract_resp = extractor.extract_evidence_from_source(extract_req)

        # Zero market metrics extracted from unrelated tech content
        assert extract_resp.status == ExtractionStatus.NO_METRICS_FOUND
        assert len(extract_resp.candidates) == 0
        assert extract_resp.total_candidates_found == 0


# ===========================================================================
# PHASE 5: Evidence Extraction - Real Numbers vs Zero Candidates
# ===========================================================================

def test_evidence_extraction_numerical_and_zero_handling() -> None:
    """Verify extraction finds numbers, units, geography, year without hallucination,

    and returns NO_METRICS_FOUND when no quantitative facts exist.
    """
    extractor = EvidenceExtractionService()

    # Case A: Real numerical market evidence for Chennai Food Service
    source_a = FetchedSource(
        original_url="https://statistics.tn.gov.in/chennai-labour-2025",
        fetch_status=FetchStatus.SUCCESS,
        content="In 2025, Chennai has 1.8 million working professionals across tech and financial parks.",
    )
    resp_a = extractor.extract_evidence_from_source(ExtractionRequest(source=source_a))
    assert resp_a.status == ExtractionStatus.SUCCESS
    assert resp_a.total_candidates_found >= 1
    cand = resp_a.candidates[0]
    assert cand.value == 1800000.0
    assert cand.geography == "Chennai"
    assert cand.year == 2025
    assert cand.unit == "professionals"

    # Case B: Source with no numerical metrics
    source_b = FetchedSource(
        original_url="https://example.com/opinion-blog",
        fetch_status=FetchStatus.SUCCESS,
        content="Healthy eating is becoming increasingly popular in urban areas as people care more about nutrition.",
    )
    resp_b = extractor.extract_evidence_from_source(ExtractionRequest(source=source_b))
    assert resp_b.status == ExtractionStatus.NO_METRICS_FOUND
    assert resp_b.total_candidates_found == 0
    assert len(resp_b.candidates) == 0


# ===========================================================================
# PHASE 8 & 9: TAM/SAM/SOM Calculation Mathematics & Invariants
# ===========================================================================

def test_calculation_mathematics_top_down_and_bottom_up() -> None:
    """Verify calculation engine computes exact Top-Down and Bottom-Up formulas,

    enforces SAM <= TAM and SOM <= SAM, propagates uncertainty, and compares divergence.
    """
    calc_service = CalculationService()

    # Top-Down Setup:
    # Macro: 100,000,000 INR (range 90M - 110M)
    # Segment: 50% (range 45% - 55%) -> TAM = 50,000,000 INR (range 40.5M - 60.5M)
    # Serviceable Geography: 40% (range 35% - 45%) -> SAM = 20,000,000 INR (range 14.175M - 27.225M)
    # Obtainable Market Share: 5% (range 4% - 6%) -> SOM = 1,000,000 INR (range 0.567M - 1.6335M)
    top_down_input = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Chennai Food Service Macro Spend",
            value=100000000.0,
            range_min=90000000.0,
            range_max=110000000.0,
            unit="INR",
            currency="INR",
            year=2025,
            geography="Chennai",
            lifecycle_stage="validated",
        ),
        segment_percentages=[
            EvidenceInput(
                name="Healthy Meal Delivery Share",
                value=50.0,
                range_min=45.0,
                range_max=55.0,
                unit="%",
                lifecycle_stage="validated",
            )
        ],
        serviceable_geography_percentage=EvidenceInput(
            name="IT Corridors / Central Chennai Share",
            value=40.0,
            range_min=35.0,
            range_max=45.0,
            unit="%",
            lifecycle_stage="validated",
        ),
        obtainable_market_share=EvidenceInput(
            name="Target Market Share",
            value=5.0,
            range_min=4.0,
            range_max=6.0,
            unit="%",
            lifecycle_stage="validated",
            is_assumption=True,
            assumption_justification="Year 2 local market penetration target",
        ),
    )

    # Bottom-Up Setup:
    # Potential Customers: 200,000 professionals in target IT corridors (range 180k - 220k)
    # Pricing: 2,500 INR / month (range 2,200 - 2,800) -> 30,000 INR / year
    # TAM = 200,000 * 30,000 = 6,000,000,000 INR (or 6 Billion INR)
    # Serviceable Customers: 50,000 professionals (range 45k - 55k) -> SAM = 1,500,000,000 INR
    # Realistically Obtainable Customers: 2,500 subscribers -> SOM = 75,000,000 INR
    bottom_up_input = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="Target Working Professionals in Chennai",
            value=200000.0,
            range_min=180000.0,
            range_max=220000.0,
            unit="professionals",
            year=2025,
            geography="Chennai",
            lifecycle_stage="validated",
        ),
        pricing=EvidenceInput(
            name="Monthly Meal Subscription Price",
            value=2500.0,
            range_min=2200.0,
            range_max=2800.0,
            unit="INR",
            currency="INR",
            year=2025,
            lifecycle_stage="validated",
        ),
        pricing_frequency=PriceFrequency.MONTHLY,
        serviceable_customers=EvidenceInput(
            name="Active Daily Tiffin/Meal Buyers",
            value=50000.0,
            range_min=45000.0,
            range_max=55000.0,
            unit="professionals",
            lifecycle_stage="validated",
        ),
        realistically_obtainable_customers=EvidenceInput(
            name="Year 1 Target Kitchen Capacity Customers",
            value=2500.0,
            range_min=2000.0,
            range_max=3000.0,
            unit="subscribers",
            lifecycle_stage="validated",
            is_assumption=True,
            assumption_justification="Initial central kitchen capacity",
        ),
    )

    req = CalculationInput(
        business_idea="Healthy Meal Delivery in Chennai",
        target_geography="Chennai",
        target_year=2025,
        top_down_inputs=top_down_input,
        bottom_up_inputs=bottom_up_input,
    )

    report = calc_service.generate_report(req)

    assert report.status == CalculationStatus.CALCULATED
    # Top-Down Invariants
    assert report.top_down_tam is not None and report.top_down_tam.estimate == 50000000.0
    assert report.top_down_tam.interval.lower == pytest.approx(40500000.0)
    assert report.top_down_tam.interval.upper == pytest.approx(60500000.0)

    assert report.top_down_sam is not None and report.top_down_sam.estimate == 20000000.0
    assert report.top_down_sam.estimate <= report.top_down_tam.estimate

    assert report.top_down_som is not None and report.top_down_som.estimate == 1000000.0
    assert report.top_down_som.estimate <= report.top_down_sam.estimate

    # Bottom-Up Invariants
    assert report.bottom_up_tam is not None and report.bottom_up_tam.estimate == 6000000000.0
    assert report.bottom_up_sam is not None and report.bottom_up_sam.estimate == 1500000000.0
    assert report.bottom_up_sam.estimate <= report.bottom_up_tam.estimate

    assert report.bottom_up_som is not None and report.bottom_up_som.estimate == 75000000.0
    assert report.bottom_up_som.estimate <= report.bottom_up_sam.estimate

    # Method Comparison
    assert report.method_comparison is not None
    assert report.method_comparison.top_down_tam == 50000000.0
    assert report.method_comparison.bottom_up_tam == 6000000000.0
    assert report.method_comparison.divergence_severity == DivergenceSeverity.SEVERE_DIVERGENCE
    assert "SEVERE DIVERGENCE" in report.method_comparison.explanation


# ===========================================================================
# PHASE 12: Negative Testing & Safety Guards
# ===========================================================================

def test_calculation_rejects_discovered_only_evidence() -> None:
    """Epistemic Guard: Calculation inputs must reject DISCOVERED lifecycle stage evidence."""
    with pytest.raises(Exception) as exc_info:
        EvidenceInput(
            name="Unverified Discovered Stat",
            value=1000000.0,
            unit="USD",
            lifecycle_stage="discovered",  # Discovered evidence strictly blocked
        )
    assert "cannot be used as a numerical calculation input" in str(exc_info.value)


def test_som_safety_rule_blocks_calculation_without_market_share() -> None:
    """SOM Safety Rule: Missing market share or obtainable customers results in INSUFFICIENT_EVIDENCE."""
    calc_service = CalculationService()
    top_down_no_som = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Macro Food Market",
            value=10000000.0,
            unit="INR",
            lifecycle_stage="validated",
        ),
        serviceable_geography_percentage=EvidenceInput(
            name="City Geo Share",
            value=50.0,
            unit="%",
            lifecycle_stage="validated",
        ),
        # obtainable_market_share is None
    )

    tam = calc_service.calculate_top_down_tam(top_down_no_som)
    sam = calc_service.calculate_top_down_sam(tam, top_down_no_som)
    som = calc_service.calculate_top_down_som(sam, top_down_no_som)

    assert som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert som.estimate is None
    assert "SOM safety rule strictly forbids arbitrary market share percentages" in som.message


# ===========================================================================
# PHASE 13: Full End-to-End Test (Chennai Healthy Meal Delivery)
# ===========================================================================

@pytest.mark.asyncio
async def test_full_realistic_pipeline_e2e_chennai_meal_delivery() -> None:
    """Execute complete end-to-end pipeline:

    Idea: 'Healthy Meal Delivery service for working professionals in Chennai 2025'
    Stages: Business Analysis -> Query Gen -> Discovery -> Fetch -> Extract -> Validate -> Triangulate -> Calculate.
    """
    mock_llm = AsyncMock()
    mock_llm.analyze_business_idea.return_value = BusinessAnalysis(
        business_idea="Healthy Meal Delivery service for working professionals in Chennai 2025",
        industry="Food & Beverage / Health Food Delivery",
        product="Healthy subscription meal delivery service",
        target_customer="Working professionals in tech and corporate offices",
        geography="Chennai",
        business_model="B2C Subscription",
        pricing_model="Monthly subscription",
        customer_problem="Lack of healthy, hygienic, timely daily lunch and dinner options for busy professionals",
        value_proposition="Nutritious chef-prepared balanced daily meals delivered directly to offices and apartments",
    )

    # Mock discovery returning 2 independent sources
    mock_discovery = AsyncMock()
    mock_query = ResearchQuery(
        metric_required="working professionals",
        geography="Chennai",
        year=2025,
    )
    mock_discovery.discover_sources.return_value = DiscoveryResponse(
        query=mock_query,
        query_string="working professionals Chennai 2025",
        total_sources_found=2,
        sources=[
            DiscoveredSource(
                title="Chennai Labour & Employment Statistical Report 2025",
                url="https://statistics.tn.gov.in/reports/chennai-employment-2025",
                snippet="Chennai urban agglomeration has 1.8 million formal working professionals in 2025.",
                source_name="State Statistical Department",
                category=SourceCategory.OFFICIAL_GOVERNMENT,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            ),
            DiscoveredSource(
                title="Tamil Nadu Economic & Workforce Survey 2025",
                url="https://tn.gov.in/workforce-survey-2025",
                snippet="The formal service and IT sector in Chennai employs 1.8 million working professionals in 2025.",
                source_name="Department of Planning and Economics",
                category=SourceCategory.OFFICIAL_GOVERNMENT,
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            ),
        ],
    )

    # Mock fetcher returning real text
    mock_fetcher = AsyncMock()

    async def mock_fetch_impl(source_or_req) -> FetchedSource:
        url = source_or_req.url
        title = source_or_req.title
        source_name = source_or_req.source_name
        if "statistics.tn.gov.in" in url:
            return FetchedSource(
                original_url=url,
                title=title,
                source_name=source_name,
                fetch_status=FetchStatus.SUCCESS,
                content="Official data confirms 1.8 million working professionals in Chennai in 2025.",
            )
        return FetchedSource(
            original_url=url,
            title=title,
            source_name=source_name,
            fetch_status=FetchStatus.SUCCESS,
            content="According to state surveys, 1.8 million working professionals are active in Chennai in 2025.",
        )

    mock_fetcher.fetch.side_effect = mock_fetch_impl
    mock_fetcher.fetch_source.side_effect = mock_fetch_impl
    mock_fetcher.fetch_discovered_source.side_effect = mock_fetch_impl

    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    calc_service = CalculationService()

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm,
        discovery_service=mock_discovery,
        fetch_service=mock_fetcher,
        extraction_service=extractor,
        validation_service=validator,
        calculation_service=calc_service,
    )

    pipeline_req = PipelineRequest(
        business_idea="Healthy Meal Delivery service for working professionals in Chennai 2025",
        target_geography="Chennai",
        target_year=2025,
        assumptions=[
            CalculationAssumption(
                name="Monthly Meal Subscription Pricing",
                value=3000.0,
                unit="INR",
                justification="Average pricing for healthy daily tiffin meal subscription in Chennai",
            ),
            CalculationAssumption(
                name="Target Professional Segment Share",
                value=20.0,
                unit="%",
                justification="Estimated 20% of IT corridor professionals order daily healthy meals",
            ),
            CalculationAssumption(
                name="Obtainable Market Share",
                value=2.0,
                unit="%",
                justification="Realistic Year 1-2 kitchen capacity capture (3,600 users)",
            ),
        ],
    )

    result = await pipeline.run(pipeline_req)

    assert result.status == "completed"
    assert result.business_analysis is not None
    assert result.business_analysis.geography == "Chennai"
    assert len(result.discovered_sources) == 2
    assert len(result.fetched_sources) == 2
    assert len(result.extracted_candidates) >= 2

    # Verify multi-source triangulation verified the 1.8M metric
    assert result.triangulation_result is not None
    assert len(result.triangulation_result.verified_items) >= 1
    verified_stat = result.triangulation_result.verified_items[0]
    assert verified_stat.value == 1800000.0
    assert verified_stat.lifecycle_stage == "verified"
    assert verified_stat.corroborating_source_count == 2

    # Verify calculation report generated
    assert result.calculation_report is not None
    assert result.calculation_report.status == CalculationStatus.CALCULATED
    assert result.calculation_report.bottom_up_tam is not None
    # TAM = 1.8M professionals * 3,000 INR = 5,400,000,000 INR (5.4 Billion INR)
    assert result.calculation_report.bottom_up_tam.estimate == pytest.approx(5400000000.0)

    # SAM = 1.8M * 20% * 3,000 = 360,000 * 3,000 = 1,080,000,000 INR (1.08 Billion INR)
    assert result.calculation_report.bottom_up_sam is not None
    assert result.calculation_report.bottom_up_sam.estimate == pytest.approx(1080000000.0)

    # SOM = 360,000 * 2% * 3,000 = 7,200 * 3,000 = 21,600,000 INR (21.6 Million INR)
    assert result.calculation_report.bottom_up_som is not None
    assert result.calculation_report.bottom_up_som.estimate == pytest.approx(21600000.0)

    # Confidence check: verified evidence + assumptions
    assert result.calculation_report.confidence in ("high", "very_high", "medium")
    assert len(result.calculation_report.all_steps) >= 3
