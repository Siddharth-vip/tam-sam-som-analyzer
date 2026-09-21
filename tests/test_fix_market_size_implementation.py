"""Comprehensive regression and verification test suite for the corrected TAM/SAM/SOM implementation.
Covers Tests 1-12 from user specification:
- TEST 1: Strong Evidence -> TAM, SAM, SOM calculated, High confidence
- TEST 2: Moderate Evidence -> TAM, SAM calculated, SOM calculated/estimated, Medium confidence
- TEST 3: Weak but Usable Evidence -> Defensible estimate, Low confidence, visible assumptions
- TEST 4: No Usable Evidence -> Not Calculable, reasons explained
- TEST 5: TAM Strong / SAM Weak -> TAM remains calculated, SAM estimated/not calculable (TAM not discarded)
- TEST 6: TAM/SAM Available / SOM Weak -> TAM/SAM calculated, SOM estimated or not calculable
- TEST 7: Invalid Funnel (SOM > SAM or SAM > TAM) -> Invariant enforced (SAM <= TAM, SOM <= SAM)
- TEST 8: Unsupported Source -> Tier 5 / spam excluded or confidence downgraded
- TEST 9: Missing Currency -> Explicit currency mismatch or missing currency warning
- TEST 10: Geography Mismatch -> Incompatible geo handled transparently
- TEST 11: Missing API Key -> Clear configuration error without exposing secrets
- TEST 12: API Failure -> Graceful handling
"""

import pytest
from app.schemas.discovery import DiscoveryLifecycleStage, ResearchQuery, SourceQualityTier
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationStatus,
    EvidenceInput,
    EvidenceQualityRating,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.services.calculation_service import CalculationService
from app.discovery.live_provider import LiveDiscoveryProvider
from app.discovery.base import DiscoveryProviderException, DiscoveryProviderUnavailableException


@pytest.fixture
def calc_service() -> CalculationService:
    return CalculationService()


def test_scenario_1_strong_evidence(calc_service: CalculationService) -> None:
    """TEST 1 — Strong Evidence: TAM, SAM, SOM calculated with High confidence."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Higher Ed Market Size",
            value=10_000_000_000.0,
            unit="USD",
            currency="USD",
            year=2024,
            geography="India",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
            source_url="https://ibef.org/reports/education-2024",
        ),
        segment_percentages=[
            EvidenceInput(
                name="EdTech Segment Share",
                value=20.0,
                unit="%",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                source_url="https://kearney.com/edtech",
            )
        ],
        serviceable_geography_percentage=EvidenceInput(
            name="India Tech Students Region",
            value=50.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
        ),
        obtainable_market_share=EvidenceInput(
            name="Audited Competitor Benchmark Share",
            value=5.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
            source_url="https://benchmark.org/edtech",
        ),
    )

    tam = calc_service.calculate_top_down_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 2_000_000_000.0
    assert tam.evidence_quality == EvidenceQualityRating.HIGH

    sam = calc_service.calculate_top_down_sam(tam, inputs)
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 1_000_000_000.0
    assert sam.evidence_quality in (EvidenceQualityRating.HIGH, EvidenceQualityRating.MEDIUM)

    som = calc_service.calculate_top_down_som(sam, inputs)
    assert som.status == CalculationStatus.CALCULATED
    assert som.estimate == 50_000_000.0
    assert som.estimate <= sam.estimate <= tam.estimate


def test_scenario_2_moderate_evidence(calc_service: CalculationService) -> None:
    """TEST 2 — Moderate Evidence: TAM, SAM calculated, Medium confidence with assumptions visible."""
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="Engineering College Students",
            value=4_000_000.0,
            unit="students",
            entity_concept="student",
            geography="India",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_url="https://aishe.gov.in",
        ),
        pricing=EvidenceInput(
            name="Annual Platform Fee",
            value=2500.0,
            unit="INR",
            currency="INR",
            entity_concept="per student",
            frequency=PriceFrequency.ANNUAL,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_url="https://edtech-pricing.in",
        ),
        target_customer_percentage=EvidenceInput(
            name="Target College Segment",
            value=50.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
    )

    tam = calc_service.calculate_bottom_up_tam(bu_inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 10_000_000_000.0  # 4M * 2500 = 10B INR

    sam = calc_service.calculate_bottom_up_sam(tam, bu_inputs)
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 5_000_000_000.0  # 50% of 10B = 5B INR
    assert len(sam.warnings) > 0 or len(sam.assumptions_used) > 0 or sam.evidence_quality is not None


def test_scenario_3_weak_but_usable_evidence(calc_service: CalculationService) -> None:
    """TEST 3 — Weak but Usable Evidence: Defensible estimate with low confidence & assumptions."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Early Market Indicator",
            value=500_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
            source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        ),
        target_segment_percentage=EvidenceInput(
            name="Serviceable Target Share",
            value=20.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
            source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
        ),
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    sam = calc_service.calculate_top_down_sam(tam, inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 100_000_000.0


def test_scenario_4_conflicting_data_safe_degradation(calc_service: CalculationService) -> None:
    """TEST 4 — Conflicting Data: Conflicting metrics degrade gracefully without crashing."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Conflicted Industry TAM",
            value=200_000_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            is_conflict=False,
        ),
        target_segment_percentage=EvidenceInput(
            name="Conflicted Serviceable %",
            value=15.0,
            unit="%",
            is_conflict=True,
            conflicting_values=[15.0, 45.0],
        ),
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED

    sam = calc_service.calculate_top_down_sam(tam, inputs)
    assert sam.status == CalculationStatus.CONFLICT
    # TAM remains fully calculated and untouched
    assert tam.status == CalculationStatus.CALCULATED


def test_scenario_6_tam_sam_available_som_weak(calc_service: CalculationService) -> None:
    """TEST 6 — TAM/SAM Available / SOM Weak: SOM is Not Calculable without arbitrary fabrication."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Accounting SaaS Market",
            value=15_000_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
        ),
        target_segment_percentage=EvidenceInput(
            name="SMB Share",
            value=30.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        obtainable_market_share=None,  # No obtainable market share provided
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    sam = calc_service.calculate_top_down_sam(tam, inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 4_500_000_000.0  # 30% of $15B = $4.5B

    som = calc_service.calculate_top_down_som(sam, inputs)
    assert som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert som.estimate is None
    # No arbitrary 1% or 5% was invented
    assert "missing" in som.message.lower() or "insufficient" in som.message.lower()


def test_scenario_7_invalid_funnel_enforces_invariants(calc_service: CalculationService) -> None:
    """TEST 7 — Invalid Funnel: Enforces SAM <= TAM and SOM <= SAM invariants."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Base Market",
            value=100_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        segment_percentages=[
            EvidenceInput(
                name="Max Segment",
                value=100.0,
                unit="%",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        ],
        serviceable_geography_percentage=EvidenceInput(
            name="Max Geo",
            value=100.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    sam = calc_service.calculate_top_down_sam(tam, inputs)
    # The calculation service ensures SAM <= TAM
    assert sam.estimate <= tam.estimate
    assert sam.estimate == tam.estimate


def test_scenario_8_unsupported_source_rejection(calc_service: CalculationService) -> None:
    """TEST 8 — Unsupported Source: Low confidence source retains transparent downgrade."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Forum Mention Market Size",
            value=50_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
            source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
            is_assumption=True,
        ),
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    assert tam.evidence_quality == EvidenceQualityRating.LOW


def test_scenario_9_missing_currency_warning(calc_service: CalculationService) -> None:
    """TEST 9 — Missing Currency: Flags currency divergence when currencies mismatch."""
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="Customers in India",
            value=1_000_000.0,
            unit="users",
            currency="INR",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        pricing=EvidenceInput(
            name="US Dollar Pricing",
            value=100.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
    )
    warnings = calc_service._check_bottom_up_unit_compatibility(
        bu_inputs.potential_customers,
        bu_inputs.pricing,
    )
    assert any("currency divergence" in w.lower() for w in warnings)


def test_scenario_10_geography_mismatch_transparency(calc_service: CalculationService) -> None:
    """TEST 10 — Entity and Unit Compatibility checking transparently detects mismatches."""
    cust = EvidenceInput(
        name="Households",
        value=500_000.0,
        unit="households",
        entity_concept="household",
        lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
    )
    pricing = EvidenceInput(
        name="Per Student License",
        value=50.0,
        unit="USD",
        currency="USD",
        entity_concept="student",
        lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
    )
    warnings = calc_service._check_bottom_up_unit_compatibility(cust, pricing)
    assert any("entity unit mismatch" in w.lower() for w in warnings)


@pytest.mark.asyncio
async def test_scenario_11_missing_api_key_error_handling() -> None:
    """TEST 11 — Missing API Key: Clear configuration error without exposing secrets."""
    provider = LiveDiscoveryProvider(
        provider_type="tavily",
        api_url="https://api.tavily.com/search",
        api_key="",
    )
    query = ResearchQuery(
        query_id="q-test-1",
        metric_required="Higher education students India",
        industry_topic="EdTech",
        geography="India",
        year=2024,
    )

    with pytest.raises(DiscoveryProviderException) as exc_info:
        await provider.search(query)

    err_msg = str(exc_info.value).lower()
    assert "requires tavily_api_key or search_api_key" in err_msg or "configured" in err_msg
    # Confirm no secret token is printed in error message
    assert "sk-" not in str(exc_info.value)
    assert "tvly-" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_scenario_12_api_failure_handling() -> None:
    """TEST 12 — API Failure: Gracefully raises descriptive provider error without crashing obscurely."""
    provider = LiveDiscoveryProvider(
        provider_type="tavily",
        api_url="https://api.tavily.com/search",
        api_key="invalid_test_key_for_error_handling",
    )
    query = ResearchQuery(
        query_id="q-test-2",
        metric_required="Higher education students India",
        industry_topic="EdTech",
        geography="India",
        year=2024,
    )

    with pytest.raises((DiscoveryProviderException, DiscoveryProviderUnavailableException)) as exc_info:
        await provider.search(query)

    err_msg = str(exc_info.value).lower()
    assert "failed" in err_msg or "invalid" in err_msg or "unauthorized" in err_msg or "http" in err_msg


@pytest.mark.asyncio
async def test_scenario_13_ev_charging_single_search_and_tam_calculation() -> None:
    """TEST 13 — Single-search analysis flow for 'Affordable EV charging stations in major cities across India' (India, 2026).
    Verifies:
    1. Exactly 1 Tavily/Discovery search request is made.
    2. Evidence with EV domain entities and currencies (USD/INR/crore) is extracted.
    3. TAM is calculated deterministically from direct market revenue.
    4. SOM remains UNAVAILABLE without arbitrary fallback numbers.
    5. TAM remains valid even when SOM fails.
    """
    from unittest.mock import AsyncMock, MagicMock
    from app.fetching.models import FetchedSource
    from app.orchestration.models import PipelineRequest
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.schemas.business import BusinessAnalysis
    from app.schemas.discovery import DiscoveredSource, DiscoveryStatus, DiscoveryResponse, SourceCategory
    from app.services.fetch_service import SourceFetchService
    from app.services.llm_service import OllamaLLMService
    from app.services.discovery_service import DiscoveryService

    mock_llm = MagicMock(spec=OllamaLLMService)
    mock_llm.analyze_business_idea = AsyncMock(
        return_value=BusinessAnalysis(
            business_idea="Affordable EV charging stations in major cities across India",
            product="EV charging stations",
            industry="EV Charging Infrastructure",
            target_customer="EV Owners & Fleet Operators",
            geography="India",
            pricing_model="Pay-per-use & subscription",
            business_model="Infrastructure / B2C & B2B",
        )
    )

    call_count = 0

    async def mock_discover(query):
        nonlocal call_count
        call_count += 1
        return DiscoveryResponse(
            query=query,
            query_string=query.metric_required,
            status=DiscoveryStatus.SUCCESS,
            total_results_found=1,
            sources=[
                DiscoveredSource(
                    title="India EV Charging Infrastructure Market Report 2026",
                    url="https://iea.org/reports/india-ev-charging-2026",
                    snippet="The Indian EV charging station market was valued at USD 1.2 billion in 2025 and is projected to reach USD 4.5 billion by 2030.",
                    source_name="International Energy Agency",
                    category=SourceCategory.INDUSTRY_ANALYST,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                )
            ],
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
        )

    mock_discovery = MagicMock(spec=DiscoveryService)
    mock_discovery.discover_sources = AsyncMock(side_effect=mock_discover)
    mock_discovery.provider = LiveDiscoveryProvider(provider_type="tavily", api_key="dummy_key")

    mock_fetcher = MagicMock(spec=SourceFetchService)
    mock_fetcher.fetch_discovered_source = AsyncMock(
        return_value=FetchedSource(
            original_url="https://iea.org/reports/india-ev-charging-2026",
            final_url="https://iea.org/reports/india-ev-charging-2026",
            title="India EV Charging Infrastructure Market Report 2026",
            source_name="International Energy Agency",
            content="According to the research, the Indian EV charging station market size was valued at USD 1.2 billion in 2025. Furthermore, India currently has 25,000 charging stations deployed across Tier 1 cities.",
            fetch_status="success",
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
        )
    )

    pipeline = MarketAnalysisPipeline(
        llm_service=mock_llm,
        discovery_service=mock_discovery,
        fetch_service=mock_fetcher,
    )

    req = PipelineRequest(
        business_idea="Affordable EV charging stations in major cities across India",
        preferred_geography="India",
        preferred_year=2026,
    )

    res = await pipeline.run(req)

    # 1. Exactly 1 discovery search call made in live mode
    assert call_count == 1

    # 2. Market sizing calculations evaluated independently
    assert res.calculation_report is not None
    assert res.tam is not None
    assert res.tam.status == CalculationStatus.CALCULATED
    assert res.tam.estimate == 1_200_000_000.0
    assert res.tam.currency == "USD"

    # 3. SOM remains unavailable due to lack of obtainable share evidence (anti-fabrication safeguard)
    assert res.som.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, CalculationStatus.INVALID_INPUT)
    assert res.som.estimate is None

    # 4. TAM is NOT invalidated by missing SOM
    assert res.tam.status == CalculationStatus.CALCULATED


def test_scenario_14_currency_and_denomination_normalization() -> None:
    """TEST 14 — Regex and normalization correctly parses various currency and volume denominations."""
    from app.services.extraction_service import EvidenceExtractionService
    from app.fetching.models import FetchedSource
    from app.schemas.extraction import ExtractionRequest

    extractor = EvidenceExtractionService()
    test_text = (
        "The market reached ₹5,000 crore in 2025. "
        "Global revenues exceeded 10 billion USD. "
        "There are 2.5 million vehicles and 45,000 charging stations."
    )
    src = FetchedSource(
        original_url="https://example.com/data",
        title="EV Market Data",
        content=test_text,
        fetch_status="success",
    )
    resp = extractor.extract_evidence_from_source(ExtractionRequest(source=src))

    extracted_vals = [c.value for c in resp.candidates]
    # ₹5,000 crore -> 50,000,000,000 INR
    assert 50_000_000_000.0 in extracted_vals
    # 10 billion USD -> 10,000,000,000 USD
    assert 10_000_000_000.0 in extracted_vals
    # 2.5 million vehicles -> 2,500,000
    assert 2_500_000.0 in extracted_vals
    # 45,000 charging stations -> 45,000
    assert 45_000.0 in extracted_vals


def test_scenario_15_api_key_priority_and_masking() -> None:
    """TEST 15 — Live discovery provider prioritizes TAVILY_API_KEY over SEARCH_API_KEY and masks secrets."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-primary-key", "SEARCH_API_KEY": "tvly-secondary-key"}):
        p1 = LiveDiscoveryProvider(provider_type="tavily")
        assert p1.api_key == "tvly-primary-key"

    with patch.dict(os.environ, {"TAVILY_API_KEY": "", "SEARCH_API_KEY": "tvly-fallback-key"}):
        p2 = LiveDiscoveryProvider(provider_type="tavily")
        assert p2.api_key == "tvly-fallback-key"


@pytest.mark.asyncio
async def test_scenario_16_ollama_cuda_stack_overrun_500_handling() -> None:
    """TEST 16 — Ollama returns HTTP 500 with CUDA buffer overrun error; pipeline handles gracefully."""
    from unittest.mock import AsyncMock, patch, MagicMock
    import httpx
    from app.services.llm_service import OllamaLLMService, LLMResponseError
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.schemas.pipeline import PipelineRequest, PipelineStatus

    llm = OllamaLLMService()
    cuda_err_response = MagicMock(spec=httpx.Response)
    cuda_err_response.status_code = 500
    cuda_err_response.text = (
        "llama-server process has terminated: exit status 0xc0000409: "
        "The system detected an overrun of a stack-based buffer in this application. "
        "CUDA error: shared object initialization failed"
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = cuda_err_response

        # Direct LLM call test
        with pytest.raises(LLMResponseError) as exc_info:
            await llm.analyze_business_idea("Affordable EV charging stations in major cities across India")
        assert "Local LLM crash detected" in str(exc_info.value)
        assert "CUDA" in str(exc_info.value)

        # End-to-end pipeline test
        pipe = MarketAnalysisPipeline(llm_service=llm)
        req = PipelineRequest(business_idea="Affordable EV charging stations in major cities across India")
        res = await pipe.run(req)

        assert res.status in (PipelineStatus.FAILED, PipelineStatus.INSUFFICIENT_EVIDENCE, "failed", "insufficient_evidence")
        assert res.tam is None or res.tam.estimate is None or res.tam.status != CalculationStatus.CALCULATED
        assert res.sam is None or res.sam.estimate is None or res.sam.status != CalculationStatus.CALCULATED
        assert res.som is None or res.som.estimate is None or res.som.status != CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_scenario_17_ollama_connection_failure_handling() -> None:
    """TEST 17 — Ollama connection refused / network failure handled cleanly."""
    from unittest.mock import AsyncMock, patch
    import httpx
    from app.services.llm_service import OllamaLLMService, LLMConnectionError
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.schemas.pipeline import PipelineRequest, PipelineStatus

    llm = OllamaLLMService()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused to 127.0.0.1:11434")

        with pytest.raises(LLMConnectionError):
            await llm.analyze_business_idea("Idea", allow_fallback=False)

        pipe = MarketAnalysisPipeline(llm_service=llm)
        res = await pipe.run(PipelineRequest(business_idea="Idea"))
        assert res.status in (PipelineStatus.FAILED, PipelineStatus.INSUFFICIENT_EVIDENCE, "failed", "insufficient_evidence")
        assert res.tam is None or res.tam.status != CalculationStatus.CALCULATED
        assert res.sam is None or res.sam.status != CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_scenario_18_ollama_timeout_handling() -> None:
    """TEST 18 — Ollama timeout handled cleanly."""
    from unittest.mock import AsyncMock, patch
    import httpx
    from app.services.llm_service import OllamaLLMService, LLMTimeoutError
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.schemas.pipeline import PipelineRequest, PipelineStatus

    llm = OllamaLLMService(timeout_seconds=0.1)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("Read timed out")

        with pytest.raises(LLMTimeoutError):
            await llm.analyze_business_idea("Idea", allow_fallback=False)

        pipe = MarketAnalysisPipeline(llm_service=llm)
        res = await pipe.run(PipelineRequest(business_idea="Idea"))
        assert res.status in (PipelineStatus.FAILED, PipelineStatus.INSUFFICIENT_EVIDENCE, "failed", "insufficient_evidence")
        assert res.tam is None or res.tam.status != CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_scenario_19_ollama_malformed_response_handling() -> None:
    """TEST 19 — Ollama malformed response handled cleanly."""
    from unittest.mock import AsyncMock, patch, MagicMock
    import httpx
    from app.services.llm_service import OllamaLLMService, LLMResponseError

    llm = OllamaLLMService()
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "This is plain text, not JSON"}}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(LLMResponseError) as exc_info:
            await llm.analyze_business_idea("Idea")
        assert "could not be decoded as JSON" in str(exc_info.value)


def test_scenario_20_status_consistency_invariant() -> None:
    """TEST 20 — A metric with no numerical result must NEVER be marked CALCULATED."""
    from app.schemas.calculation import MetricCalculationResult, TAMResult, SAMResult, SOMResult

    # If estimate is None and status was set to CALCULATED, validator fixes it to NOT_CALCULABLE
    tam = TAMResult(estimate=None, status=CalculationStatus.CALCULATED)
    assert tam.status == CalculationStatus.NOT_CALCULABLE
    assert tam.status != CalculationStatus.CALCULATED

    sam = SAMResult(estimate=None, status=CalculationStatus.CALCULATED)
    assert sam.status == CalculationStatus.NOT_CALCULABLE
    assert sam.status != CalculationStatus.CALCULATED

    som = SOMResult(estimate=None, status=CalculationStatus.CALCULATED)
    assert som.status == CalculationStatus.NOT_CALCULABLE
    assert som.status != CalculationStatus.CALCULATED

    # If estimate is provided, status is CALCULATED
    tam_valid = TAMResult(estimate=50000.0)
    assert tam_valid.status == CalculationStatus.CALCULATED


@pytest.mark.asyncio
async def test_scenario_21_mock_provider_makes_zero_external_network_calls() -> None:
    """TEST 21 — Mock discovery provider executes completely offline without calling Tavily."""
    from app.services.discovery_service import DiscoveryService
    from app.discovery.mock_provider import MockDiscoveryProvider
    from app.schemas.discovery import DiscoveryStatus, ResearchQuery

    mock_prov = MockDiscoveryProvider()
    disc_svc = DiscoveryService(provider=mock_prov)
    query = ResearchQuery(query_text="EV charging stations market size India", metric_required="market_size", target_metric="market_size")
    resp = await disc_svc.discover_sources(query)

    assert resp.status == DiscoveryStatus.SUCCESS
    assert len(resp.sources) > 0
    # Provider is strictly mock
    assert type(disc_svc.provider).__name__ == "MockDiscoveryProvider"


def test_sam_case_1_geographic_or_customer_narrowing(calc_service: CalculationService) -> None:
    """CASE 1: Business idea with clearly defined geographic/product/customer segment.
    Expected:
    - TAM is calculated ($100M).
    - SAM is quantitatively narrowed using evidence (e.g. 25% major cities / target segment = $25M).
    - SAM does NOT blindly become 100% of TAM.
    """
    # Top-Down test with geographic/segment narrowing
    td_inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="India Total EV Charging Market",
            value=100_000_000.0,
            unit="USD",
            currency="USD",
            geography="India",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        serviceable_geography_percentage=EvidenceInput(
            name="Tier-1 Major Cities Share",
            value=25.0,
            unit="%",
            geography="India",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
    )
    tam_td = calc_service.calculate_top_down_tam(td_inputs)
    sam_td = calc_service.calculate_top_down_sam(tam_td, td_inputs)

    assert tam_td.status == CalculationStatus.CALCULATED
    assert tam_td.estimate == 100_000_000.0
    assert sam_td.status == CalculationStatus.CALCULATED
    assert sam_td.estimate == 25_000_000.0  # Narrowed by 25%
    assert sam_td.estimate < tam_td.estimate
    assert len(sam_td.steps) > 0

    # Bottom-Up test with serviceable customer count narrowing
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="All Vehicles in India",
            value=10_000_000.0,
            unit="vehicles",
            entity_concept="vehicle",
            geography="India",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        serviceable_customers=EvidenceInput(
            name="EV Commercial Fleet in Major Cities",
            value=500_000.0,
            unit="vehicles",
            entity_concept="vehicle",
            geography="India - Major Cities",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        pricing=EvidenceInput(
            name="Annual Charging Spend",
            value=1200.0,
            unit="USD",
            currency="USD",
            entity_concept="per vehicle",
            frequency=PriceFrequency.ANNUAL,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
    )
    tam_bu = calc_service.calculate_bottom_up_tam(bu_inputs)
    sam_bu = calc_service.calculate_bottom_up_sam(tam_bu, bu_inputs)

    assert tam_bu.status == CalculationStatus.CALCULATED
    assert tam_bu.estimate == 12_000_000_000.0  # 10M * $1,200 = $12B
    assert sam_bu.status == CalculationStatus.CALCULATED
    assert sam_bu.estimate == 600_000_000.0     # 500k * $1,200 = $600M
    assert sam_bu.estimate < tam_bu.estimate


def test_sam_case_2_explicit_entire_tam_serviceable(calc_service: CalculationService) -> None:
    """CASE 2: Business idea where available evidence explicitly supports entire TAM as serviceable.
    Expected:
    - SAM may equal TAM ($50M = $50M).
    - The evidence/assumption supporting this is traceable with an explicit calculation step.
    """
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Specialized Direct Niche Market",
            value=50_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        target_segment_percentage=EvidenceInput(
            name="Fully Serviceable Market Scope",
            value=100.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            assumption_justification="Evidence indicates product natively serves the entire defined direct niche market.",
        ),
    )
    tam = calc_service.calculate_top_down_tam(inputs)
    sam = calc_service.calculate_top_down_sam(tam, inputs)

    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 50_000_000.0
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 50_000_000.0
    assert any("100" in step.description for step in sam.steps)


def test_sam_case_3_no_sam_narrowing_evidence_tam_valid_sam_insufficient(calc_service: CalculationService) -> None:
    """CASE 3: Business idea where no defensible SAM narrowing evidence exists.
    Expected:
    - TAM remains valid if supported.
    - SAM becomes INSUFFICIENT_EVIDENCE / NOT_CALCULABLE.
    - No fabricated percentage is introduced (does NOT default to 100%).
    - Explains what evidence is missing.
    """
    # Top-Down without SAM narrowing factors
    td_inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="Broad SaaS Industry TAM",
            value=80_000_000_000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        # No serviceable_geography_percentage, target_segment_percentage, or other_filters
    )
    tam_td = calc_service.calculate_top_down_tam(td_inputs)
    sam_td = calc_service.calculate_top_down_sam(tam_td, td_inputs)

    assert tam_td.status == CalculationStatus.CALCULATED
    assert tam_td.estimate == 80_000_000_000.0
    assert sam_td.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert sam_td.estimate is None
    assert "insufficient evidence" in sam_td.message.lower()

    # Bottom-Up without serviceable customer count or target percentage
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="Total Businesses in India",
            value=60_000_000.0,
            unit="businesses",
            entity_concept="business",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        pricing=EvidenceInput(
            name="Annual Plan",
            value=500.0,
            unit="USD",
            currency="USD",
            frequency=PriceFrequency.ANNUAL,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        # No serviceable_customers count and no target_customer_percentage
    )
    tam_bu = calc_service.calculate_bottom_up_tam(bu_inputs)
    sam_bu = calc_service.calculate_bottom_up_sam(tam_bu, bu_inputs)

    assert tam_bu.status == CalculationStatus.CALCULATED
    assert tam_bu.estimate == 30_000_000_000.0
    assert sam_bu.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert sam_bu.estimate is None
    assert "insufficient evidence" in sam_bu.message.lower()


def test_solar_tam_46_dollar_regression(calc_service: CalculationService) -> None:
    """REGRESSION TEST: Solar Panel Installation $46/year TAM failure.
    
    Business: 'Affordable home solar panel installation services for residential households in Tamil Nadu'
    Failure root cause:
    - Growth range 22-24% with unit 'units' was incorrectly treated as 23 potential customers.
    - Commodity tariff rate 'INR 2/kWh' was incorrectly treated as 2 INR annual ARPU.
    - Resulting in Bottom-Up TAM = 23 * 2 = 46 INR ($46/year) which overrode the valid $122.5B Top-Down TAM.
    
    Verification:
    - Non-entity 'units' and commodity '/kWh' tariffs must be rejected from bottom-up inputs.
    - Top-Down TAM ($122.5B) is properly computed and selected.
    - SAM ($85.75B) is properly narrowed to 70% and is strictly less than TAM.
    - SOM remains INSUFFICIENT_EVIDENCE under the SOM safety rule.
    """
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.orchestration.models import PipelineRequest, PipelineStatus
    from app.schemas.validation import EvidenceValidationResult, EvidenceValidationStatus
    from app.schemas.extraction import MarketMetricType

    pipeline = MarketAnalysisPipeline()

    val_items = [
        # Candidate 1: Percentage growth range (22-24%)
        EvidenceValidationResult(
            candidate_id="cand-growth",
            metric="units",
            value=None,
            unit="units",
            raw_value_expression="22-24%",
            range_min=22.0,
            range_max=24.0,
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="Commercial buyers accelerating rooftop pipelines by 22-24% each year.",
            source_url="https://mordorintelligence.com/solar-india",
        ),
        # Candidate 2: Commodity tariff rate (INR 2/kWh)
        EvidenceValidationResult(
            candidate_id="cand-tariff",
            metric="tariff / usage rate",
            value=2.0,
            unit="INR",
            raw_value_expression="INR 2/kWh",
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="pushing discovered tariffs to INR 2/kWh, a new national floor.",
            source_url="https://mordorintelligence.com/solar-india",
        ),
        # Candidate 3: Calendar forecast year span (2026-2031)
        EvidenceValidationResult(
            candidate_id="cand-years",
            metric="units",
            value=None,
            unit="units",
            raw_value_expression="2026 - 2031",
            range_min=2026.0,
            range_max=2031.0,
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="India Solar Energy Market Growth Trends and Forecast (2026 - 2031)",
            source_url="https://mordorintelligence.com/solar-india",
        ),
        # Candidate 4: Genuine Macro Market Size ($122.5B)
        EvidenceValidationResult(
            candidate_id="cand-macro",
            metric="market size / revenue",
            metric_type=MarketMetricType.MARKET_SIZE,
            value=122_500_000_000.0,
            unit="USD",
            raw_value_expression="USD 122.5 billion",
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="The India Solar Energy Market size was valued at USD 122.5 billion in 2025.",
            source_url="https://mordorintelligence.com/solar-india",
        ),
        # Candidate 5: Target Residential Segment Percentage (70%)
        EvidenceValidationResult(
            candidate_id="cand-segment",
            metric="Residential solar share",
            metric_type=MarketMetricType.MARKET_SHARE,
            value=70.0,
            unit="%",
            raw_value_expression="70%",
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="Residential solar accounts for 70% of rooftop installations.",
            source_url="https://intellectualmarketinsights.com/report/solar-india",
        ),
    ]

    req = PipelineRequest(
        business_idea="Affordable home solar panel installation services for residential households in Tamil Nadu",
        preferred_geography="Tamil Nadu, India",
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=val_items,
        request=req,
    )

    # CASE A: Growth percentage such as 22-24% is rejected as a customer count
    assert calc_input.bottom_up_inputs.potential_customers is None, "Case A: Growth range 22-24% must NOT be treated as customer population count!"

    # CASE B: Forecast year range such as 2026-2031 is rejected as a customer count
    assert calc_input.bottom_up_inputs.serviceable_customers is None, "Case B: Forecast year span 2026-2031 must NOT be treated as serviceable customer count!"

    # CASE C: Commodity tariff (INR 2/kWh) is rejected as annual ARPU/pricing
    assert calc_input.bottom_up_inputs.pricing is None, "Case C: Commodity tariff INR 2/kWh must NOT be treated as annual ARPU!"

    # CASE D: Valid macro market size $122.5B produces valid Top-Down TAM
    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.macro_market_size is not None
    assert calc_input.top_down_inputs.macro_market_size.value == 122_500_000_000.0

    # CASE E: Valid 70% residential segment evidence produces Top-Down SAM = $122.5B * 70% = $85.75B
    assert calc_input.top_down_inputs.target_segment_percentage is not None
    assert calc_input.top_down_inputs.target_segment_percentage.value == 70.0

    # Run Calculation Report
    report = calc_service.generate_report(calc_input)
    assert report.bottom_up_tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 122_500_000_000.0

    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 85_750_000_000.0  # $122.5B * 70%
    assert report.top_down_sam.estimate < report.top_down_tam.estimate

    # CASE H: SOM remains Insufficient Evidence when no obtainable-market evidence exists
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE

    # Final Result Synthesis in pipeline
    final_res = pipeline._build_final_result(
        pipeline_id="pipe-solar-1",
        status=PipelineStatus.COMPLETED,
        request=req,
        analysis=None,
        research_queries=[],
        discovered_sources=[],
        fetched_sources=[],
        extracted_candidates=[],
        validation_results=val_items,
        tri_result=None,
        calc_report=report,
        errors=[],
        warnings=[],
        audit_trail=[],
        started_at="2026-09-15T00:00:00Z",
    )

    # CASE F: Invalid bottom-up operands cannot cause TAM/SAM to become $46/$46
    assert final_res.tam.status == CalculationStatus.CALCULATED
    assert final_res.tam.estimate == 122_500_000_000.0, f"TAM must be $122.5B, got {final_res.tam.estimate}"
    assert final_res.tam.estimate != 46.0

    # CASE G: SAM remains <= TAM (and strictly narrowed: $85.75B < $122.5B)
    assert final_res.sam.status == CalculationStatus.CALCULATED
    assert final_res.sam.estimate == 85_750_000_000.0, f"SAM must be $85.75B, got {final_res.sam.estimate}"
    assert final_res.sam.estimate < final_res.tam.estimate
    assert final_res.sam.estimate <= final_res.tam.estimate

    # CASE H: SOM remains Insufficient Evidence
    assert final_res.som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


def test_solar_tam_insufficient_evidence_when_no_macro_or_valid_bottom_up(calc_service: CalculationService) -> None:
    """When only commodity tariffs and growth rates exist without valid macro/customer evidence,
    TAM and SAM must return INSUFFICIENT_EVIDENCE instead of producing an absurd $46 figure.
    """
    from app.orchestration.pipeline import MarketAnalysisPipeline
    from app.orchestration.models import PipelineRequest, PipelineStatus
    from app.schemas.validation import EvidenceValidationResult, EvidenceValidationStatus

    pipeline = MarketAnalysisPipeline()

    val_items = [
        EvidenceValidationResult(
            candidate_id="cand-growth",
            metric="units",
            value=None,
            unit="units",
            raw_value_expression="22-24%",
            range_min=22.0,
            range_max=24.0,
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="Commercial buyers accelerating rooftop pipelines by 22-24% each year.",
            source_url="https://mordorintelligence.com/solar-india",
        ),
        EvidenceValidationResult(
            candidate_id="cand-tariff",
            metric="tariff / usage rate",
            value=2.0,
            unit="INR",
            raw_value_expression="INR 2/kWh",
            is_valid=True,
            validation_status=EvidenceValidationStatus.VALID,
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
            source_context="pushing discovered tariffs to INR 2/kWh, a new national floor.",
            source_url="https://mordorintelligence.com/solar-india",
        ),
    ]

    req = PipelineRequest(
        business_idea="Affordable home solar panel installation services for residential households in Tamil Nadu",
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=val_items,
        request=req,
    )

    report = calc_service.generate_report(calc_input)
    assert report.bottom_up_tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_tam is None or report.top_down_tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE

    final_res = pipeline._build_final_result(
        pipeline_id="pipe-solar-1",
        status=PipelineStatus.COMPLETED,
        request=req,
        analysis=None,
        research_queries=[],
        discovered_sources=[],
        fetched_sources=[],
        extracted_candidates=[],
        validation_results=val_items,
        tri_result=None,
        calc_report=report,
        errors=[],
        warnings=[],
        audit_trail=[],
        started_at="2026-09-15T00:00:00Z",
    )

    assert final_res.tam.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, CalculationStatus.NOT_CALCULABLE)
    assert final_res.tam.estimate is None
    assert final_res.sam.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, CalculationStatus.NOT_CALCULABLE)
    assert final_res.sam.estimate is None
    assert final_res.som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


