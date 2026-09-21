import pytest
from unittest.mock import AsyncMock, patch

from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.business import (
    BusinessAnalysis,
    BusinessModelAnalysis,
    CompetitorInfo,
    CustomerSegmentItem,
    MarketAttractivenessAssessment,
    MarketGrowthItem,
    MarketTrendItem,
    ValuePropositionAnalysis,
)
from app.schemas.calculation import CalculationReport, CalculationStatus
from app.schemas.pipeline import PipelineRequest, PipelineResult
from app.services.calculation_service import calculate_deterministic_cagr
from app.services.llm_service import OllamaLLMService


# =========================================================================
# 1. Deterministic CAGR & Growth Tests (Phase 16)
# =========================================================================

def test_deterministic_cagr_calculation():
    """Verify exact formula: ((Ending / Beginning) ^ (1 / Years)) - 1."""
    # Example: 100M growing to 200M over 5 years
    cagr = calculate_deterministic_cagr(100.0, 200.0, 5.0)
    assert cagr is not None
    # (2.0 ** 0.2) - 1 ≈ 0.148698 -> rounded to 0.1487
    assert cagr == pytest.approx(0.1487, abs=1e-4)

    # Example: 50M growing to 150M over 6 years
    cagr2 = calculate_deterministic_cagr(50.0, 150.0, 6.0)
    assert cagr2 == pytest.approx(0.2009, abs=1e-4)

    # Example: flat market (0% growth)
    cagr_flat = calculate_deterministic_cagr(100.0, 100.0, 3.0)
    assert cagr_flat == 0.0


def test_deterministic_cagr_boundary_and_invariants():
    """Verify that invalid bounds return None rather than raising exceptions or calculating negative infinity."""
    # Zero or negative beginning value
    assert calculate_deterministic_cagr(0.0, 100.0, 5.0) is None
    assert calculate_deterministic_cagr(-50.0, 100.0, 5.0) is None

    # Negative ending value
    assert calculate_deterministic_cagr(100.0, -10.0, 5.0) is None

    # Zero or negative years
    assert calculate_deterministic_cagr(100.0, 200.0, 0.0) is None
    assert calculate_deterministic_cagr(100.0, 200.0, -2.0) is None

    # None inputs
    assert calculate_deterministic_cagr(None, 200.0, 5.0) is None  # type: ignore
    assert calculate_deterministic_cagr(100.0, None, 5.0) is None  # type: ignore
    assert calculate_deterministic_cagr(100.0, 200.0, None) is None  # type: ignore


# =========================================================================
# 2. Competitor Intelligence & Comparison Matrix (Phase 13 & 14)
# =========================================================================

def test_competitor_info_model_and_defaults():
    """Verify CompetitorInfo defaults to 'Pricing not publicly available' when unprovided."""
    comp = CompetitorInfo(name="TestSaaS Competitor")
    assert comp.name == "TestSaaS Competitor"
    assert comp.pricing == "Pricing not publicly available"
    assert comp.public_pricing == "Pricing not publicly available"
    assert comp.deployment_model == "Cloud SaaS"


@pytest.mark.asyncio
async def test_dynamic_competitor_generation_semantic_fallback():
    """Verify LLM service provides semantic competitors for B2B categories without inventing fake prices."""
    llm = OllamaLLMService(base_url="http://invalid-ollama-host:11434")

    analysis_crm = BusinessAnalysis(
        business_idea="Cloud CRM for Indian SMBs",
        category="CRM & Sales",
        customer_type="SMBs",
        target_country="India",
    )
    with patch.object(llm, "_make_request", side_effect=Exception("Ollama offline")):
        comps = await llm.generate_competitors(analysis_crm)
    assert len(comps) >= 2
    comp_names = [c.name for c in comps]
    assert any("HubSpot" in name or "Zoho" in name for name in comp_names)
    for c in comps:
        assert c.pricing is not None
        assert c.deployment_model == "Cloud SaaS"


# =========================================================================
# 3. Market Trends & Customer Segmentation (Phase 15 & 17)
# =========================================================================

@pytest.mark.asyncio
async def test_dynamic_market_trends_generation():
    """Verify structured market trends contain explanations and impact."""
    llm = OllamaLLMService()
    analysis = BusinessAnalysis(
        business_idea="Automated payroll and attendance SaaS for logistics fleets in India",
        category="HR & Workforce Management",
        customer_type="Fleet Operators",
        target_country="India",
    )
    with patch.object(llm, "_make_request", side_effect=Exception("Ollama offline")):
        trends = await llm.generate_market_trends(analysis)
    assert len(trends) >= 2
    for t in trends:
        assert isinstance(t, MarketTrendItem)
        assert len(t.trend) > 3
        assert len(t.explanation) > 10
        assert t.impact_on_market is not None


@pytest.mark.asyncio
async def test_customer_segmentation_tiers():
    """Verify multi-tier customer segmentation breakdown."""
    llm = OllamaLLMService()
    analysis = BusinessAnalysis(
        business_idea="AI-powered customer support ticketing SaaS for e-commerce brands",
        category="Customer Support & Helpdesk",
        customer_type="E-commerce Brands",
        target_country="United States",
    )
    with patch.object(llm, "_make_request", side_effect=Exception("Ollama offline")):
        segments = await llm.generate_customer_segmentation(analysis)
    assert len(segments) >= 3
    segment_names = [s.segment_name.lower() for s in segments]
    assert any("small" in s or "independent" in s or "smb" in s for s in segment_names)
    assert any("mid-market" in s for s in segment_names)
    assert any("enterprise" in s for s in segment_names)


# =========================================================================
# 4. Value Proposition & Business Model Analysis (Phase 18 & 19)
# =========================================================================

def test_value_proposition_analysis_structure():
    """Verify structured value proposition extraction."""
    llm = OllamaLLMService()
    analysis = BusinessAnalysis(
        business_idea="AI contract review and compliance SaaS for fintech startups",
        category="Legal & Compliance",
        customer_type="FinTech Startups",
        target_country="India",
        primary_problem="High legal fees and slow contract turnaround times",
    )
    vp = llm.generate_value_proposition(analysis)
    assert isinstance(vp, ValuePropositionAnalysis)
    assert len(vp.customer_problem) > 5
    assert len(vp.current_pain_point) > 5
    assert len(vp.product_solution) > 5
    assert len(vp.business_benefit) > 5
    assert len(vp.operational_benefit) > 5
    assert len(vp.differentiation_opportunity) > 5
    assert len(vp.value_proposition_statement) > 10


def test_business_model_analysis_structure():
    """Verify B2B SaaS monetization and business model breakdown."""
    llm = OllamaLLMService()
    analysis = BusinessAnalysis(
        business_idea="Developer API observability and logging platform",
        category="Developer Tools",
        pricing_model="per_seat",
        pricing_basis="per_seat",
        customer_type="Engineering Teams",
        currency="USD",
    )
    bm = llm.generate_business_model_analysis(analysis)
    assert isinstance(bm, BusinessModelAnalysis)
    assert "B2B SaaS" in bm.business_model
    assert "per_seat" in bm.pricing_model
    assert len(bm.possible_expansion_revenue) >= 2


# =========================================================================
# 5. Explainable Market Attractiveness (Phase 20)
# =========================================================================

def test_explainable_market_attractiveness_derivation():
    """Verify transparent 0-10 attractiveness scoring with component factors."""
    pipeline = MarketAnalysisPipeline()
    analysis = BusinessAnalysis(
        business_idea="Modular Cloud ERP for Manufacturing SMEs",
        category="ERP & Business Operations",
        customer_type="Manufacturing SMEs",
        target_country="India",
        clinical_use=False,
    )
    calc_report = CalculationReport(
        business_idea="Modular Cloud ERP for Manufacturing SMEs",
        target_geography="India",
        target_year=2025,
        market_definition="ERP software for SMEs",
        confidence="HIGH",
        all_steps=[],
        all_assumptions=[],
        warnings=[],
    )
    # Mock bottom-up TAM of 600M
    calc_report.bottom_up_tam = type("MockTAM", (), {"estimate": 600_000_000, "status": CalculationStatus.CALCULATED})()  # type: ignore

    competitors = [
        CompetitorInfo(name="SAP Business One"),
        CompetitorInfo(name="Tally Prime"),
    ]

    attr = pipeline._assess_market_attractiveness(analysis, calc_report, competitors)
    assert isinstance(attr, MarketAttractivenessAssessment)
    assert 0.0 <= attr.score <= 10.0
    assert attr.rating in ("HIGH", "MEDIUM", "LOW")
    assert "0 to 10 scale" in attr.scale
    assert "market_size" in attr.component_factors
    assert "competition" in attr.component_factors
    assert len(attr.limitations) >= 2


# =========================================================================
# 6. Complete 22-Section Market Report Generation (Phase 21)
# =========================================================================

@pytest.mark.asyncio
async def test_22_section_report_generation_across_categories():
    """Verify that execute_pipeline outputs all 22 required B2B SaaS report sections."""
    from unittest.mock import MagicMock
    from app.services.discovery_service import DiscoveryService
    from app.services.fetch_service import SourceFetchService
    from app.schemas.discovery import DiscoveryResponse, DiscoveryStatus, DiscoveredSource, SourceCategory, DiscoveryLifecycleStage, ResearchQuery
    from app.fetching.models import FetchedSource

    mock_disc = MagicMock(spec=DiscoveryService)
    mock_disc.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="HR Tech market size", geography="India", year=2025),
            query_string="HR Tech market size India 2025",
            status=DiscoveryStatus.SUCCESS,
            total_results_found=1,
            sources=[
                DiscoveredSource(
                    title="India SaaS Report 2025",
                    url="https://saasreport.in/hr-tech",
                    snippet="India HR Tech market reaches 50000 organizations with 25% adoption.",
                    source_name="India SaaS Association",
                    category=SourceCategory.INDUSTRY_ANALYST,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                )
            ],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )

    mock_fetch = MagicMock(spec=SourceFetchService)
    mock_fetch.fetch_discovered_source = AsyncMock(
        side_effect=lambda src: FetchedSource(
            original_url=src.url,
            final_url=src.url,
            title=src.title,
            source_name=src.source_name,
            content="India HR tech adoption reaches 50000 organizations in 2025 with $1200 average annual pricing.",
            fetch_status="success",
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    )

    pipeline = MarketAnalysisPipeline(
        discovery_service=mock_disc,
        fetch_service=mock_fetch,
    )

    req = PipelineRequest(
        business_idea="AI-powered recruitment and candidate screening SaaS for tech companies in India",
        target_country="India",
        customer_type="Tech Companies",
        pricing_basis="annual_subscription",
        annual_price=120000.0,
        number_of_organizations=50000,
        serviceable_percentage=25.0,
        sales_team_size=5,
        sales_cycle_months=2.0,
    )

    with patch.object(OllamaLLMService, "_make_request", side_effect=Exception("Ollama offline mock")):
        result = await pipeline.execute_pipeline(req)

    assert isinstance(result, PipelineResult)
    assert result.final_report_sections is not None

    sections = result.final_report_sections
    # Verify core 22 section availability
    assert "1_executive_summary" in sections
    assert "2_business_idea" in sections
    assert "3_value_proposition" in sections
    assert "4_b2b_saas_category" in sections
    assert "5_target_customers" in sections
    assert "6_customer_segmentation" in sections
    assert "7_business_model" in sections
    assert "8_market_overview" in sections
    assert "9_market_trends" in sections
    assert "10_market_growth" in sections
    assert "11_tam" in sections
    assert "12_sam" in sections
    assert "13_som" in sections
    assert "14_calculation_trace" in sections
    assert "15_competitor_analysis" in sections
    assert "16_competitor_comparison" in sections
    assert "17_market_attractiveness" in sections
    assert "18_evidence_and_sources" in sections
    assert "19_assumptions" in sections
    assert "20_data_provenance" in sections
    assert "21_limitations" in sections
    assert "22_final_market_analysis_summary" in sections

    # Verify structured models attached to PipelineResult
    assert result.competitor_comparison is not None
    assert len(result.competitor_comparison) > 0
    assert result.market_trends is not None
    assert result.market_growth is not None
    assert result.customer_segmentation is not None
    assert result.value_proposition_analysis is not None
    assert result.business_model_analysis is not None


# =========================================================================
# 7. Production Hardening & Safe Error Handling (Phase 24)
# =========================================================================

@pytest.mark.asyncio
async def test_pipeline_som_withholding_when_capacity_missing():
    """Verify that when SOM capacity operands are absent, SOM is cleanly withheld with INSUFFICIENT_EVIDENCE."""
    from unittest.mock import MagicMock
    from app.services.discovery_service import DiscoveryService
    from app.services.fetch_service import SourceFetchService
    from app.schemas.discovery import DiscoveryResponse, DiscoveryStatus, DiscoveredSource, SourceCategory, DiscoveryLifecycleStage, ResearchQuery
    from app.fetching.models import FetchedSource

    mock_disc = MagicMock(spec=DiscoveryService)
    mock_disc.discover_sources = AsyncMock(
        return_value=DiscoveryResponse(
            query=ResearchQuery(metric_required="Cybersecurity organizations", geography="India", year=2025),
            query_string="Cybersecurity organizations India 2025",
            status=DiscoveryStatus.SUCCESS,
            total_results_found=1,
            sources=[
                DiscoveredSource(
                    title="Cybersecurity Report",
                    url="https://sec.org",
                    snippet="Cybersecurity scanner for Indian SMEs.",
                    source_name="SecOrg",
                    category=SourceCategory.INDUSTRY_ANALYST,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                )
            ],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )
    )

    mock_fetch = MagicMock(spec=SourceFetchService)
    mock_fetch.fetch_discovered_source = AsyncMock(
        side_effect=lambda src: FetchedSource(
            original_url=src.url,
            final_url=src.url,
            title=src.title,
            source_name=src.source_name,
            content="20000 SMEs in India require automated vulnerability scanning.",
            fetch_status="success",
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    )

    pipeline = MarketAnalysisPipeline(
        discovery_service=mock_disc,
        fetch_service=mock_fetch,
    )

    req = PipelineRequest(
        business_idea="Cybersecurity vulnerability scanner for Indian SMEs",
        target_country="India",
        customer_type="SMEs",
        pricing_basis="annual_subscription",
        annual_price=50000.0,
        number_of_organizations=20000,
        # No sales_team_size or capacity provided!
    )

    with patch.object(OllamaLLMService, "_make_request", side_effect=Exception("Ollama offline mock")):
        result = await pipeline.execute_pipeline(req)

    assert result.tam is not None
    assert result.tam.status == CalculationStatus.CALCULATED
    assert result.som is not None
    assert result.som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert result.som.estimate is None

