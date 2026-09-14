import pytest
from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationResult,
    EvidenceValidationStatus,
    MarketScopeType,
)
from app.schemas.calculation import (
    EvidenceInput,
    TopDownCalculationInputs,
    BottomUpCalculationInputs,
    PriceFrequency,
    CalculationStatus,
)
from app.services.validation_service import EvidenceValidationService
from app.services.calculation_service import CalculationService

validation_service = EvidenceValidationService()
calc_service = CalculationService()

SAMPLE_ANALYSIS = BusinessAnalysis(
    business_idea="Affordable online programming platform for college students in India",
    industry="Education / EdTech / Online Learning",
    product="Online Programming Platform / Coding Education",
    target_customer="College Students / Undergraduates in India",
    geography="India",
    business_model="B2C / Subscription",
    pricing_model="Affordable Monthly/Annual Subscription",
)


def test_parent_market_scope_classification() -> None:
    """Test that broad parent macro industry claims ($313B total education) are classified as Parent market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_parent_1",
        metric="Total Indian Education Sector Market Size",
        value=313_000_000_000.0,
        unit="USD",
        year=2024,
        geography="India",
        source_context="The total Indian education market is estimated at $313 billion across all K-12, higher education, and brick-and-mortar institutions.",
        source_url="https://ibef.org/industry/education-sector-india.aspx",
        source_name="IBEF Education Sector Report",
        metric_type="market_size",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.PARENT_MARKET.value
    assert "parent" in val_res.market_scope_explanation.lower()
    assert val_res.relevance_breakdown is not None
    assert val_res.relevance_breakdown.market_scope == MarketScopeType.PARENT_MARKET.value
    assert "parent" in val_res.relevance_breakdown.market_scope_explanation.lower()


def test_addressable_market_scope_classification() -> None:
    """Test that specific product-market claims (Online coding platform TAM) are classified as Addressable market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_tam_1",
        metric="India Online Coding and Developer Education TAM",
        value=2_500_000_000.0,
        unit="USD",
        year=2024,
        geography="India",
        source_context="The total addressable market for online programming courses and coding bootcamps in India reached $2.5 billion in 2024.",
        source_url="https://nasscom.in/coding-education-tam-2024",
        source_name="NASSCOM Tech Skills Report",
        metric_type="market_size",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.ADDRESSABLE_MARKET.value
    assert "addressable" in val_res.market_scope_explanation.lower()


def test_serviceable_market_scope_classification() -> None:
    """Test that target customer segment evidence is classified as Serviceable market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_sam_1",
        metric="College Student Higher Education Coding Segment SAM",
        value=650_000_000.0,
        unit="USD",
        year=2024,
        geography="India",
        source_context="Serviceable addressable market for college undergraduates and university students subscribing to coding platforms is $650M.",
        source_url="https://research.org/sam-college-coding",
        source_name="Higher Ed Research Insights",
        metric_type="market_size",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.SERVICEABLE_MARKET.value
    assert "serviceable" in val_res.market_scope_explanation.lower()


def test_obtainable_market_scope_classification() -> None:
    """Test that market share / SOM evidence is classified as Obtainable market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_som_1",
        metric="Obtainable Initial Year Market Share (SOM)",
        value=3.5,
        unit="%",
        year=2024,
        geography="India",
        source_context="Early-stage edtech entrants realistically capture 3.5% obtainable market share within the first 24 months.",
        source_url="https://venturecap.org/benchmarks/edtech-som-capture",
        source_name="EdTech Benchmark Report",
        metric_type="market_share",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.OBTAINABLE_MARKET.value
    assert "obtainable" in val_res.market_scope_explanation.lower()


def test_adjacent_market_scope_classification_foreign_geography() -> None:
    """Test that evidence from a different geography is classified as Adjacent market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_adj_1",
        metric="US Coding Bootcamp Market Size",
        value=3_200_000_000.0,
        unit="USD",
        year=2024,
        geography="United States",
        source_context="The United States online coding education market was valued at $3.2 billion.",
        source_url="https://usmarket.org/coding-education",
        source_name="US Market Research",
        metric_type="market_size",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.ADJACENT_MARKET.value
    assert "adjacent" in val_res.market_scope_explanation.lower()


def test_unrelated_market_scope_classification() -> None:
    """Test that completely unrelated industry evidence is classified as Unrelated market."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_unrelated_1",
        metric="Global Steel Manufacturing Production",
        value=850_000_000_000.0,
        unit="USD",
        year=2024,
        geography="Global",
        source_context="The global crude steel and alloy manufacturing market size reached $850 billion in 2024.",
        source_url="https://worldsteel.org/statistics/annual-2024",
        source_name="World Steel Association",
        metric_type="market_size",
    )

    val_res = validation_service.validate_candidate(candidate, SAMPLE_ANALYSIS)
    
    assert val_res.market_scope == MarketScopeType.UNRELATED_MARKET.value
    assert not val_res.is_valid
    assert val_res.rejection_reason is not None


def test_parent_market_warning_in_top_down_tam() -> None:
    """Test that Top-Down TAM warns if an unsegmented parent market figure is used."""
    macro_input = EvidenceInput(
        name="Total Indian Education Sector",
        value=313_000_000_000.0,
        unit="USD",
        currency="USD",
        year=2024,
        geography="India",
        market_scope=MarketScopeType.PARENT_MARKET.value,
        market_scope_explanation="Parent market: Aggregate Indian education sector encompassing K-12, higher ed, and offline infrastructure.",
    )

    td_inputs = TopDownCalculationInputs(
        macro_market_size=macro_input,
        segment_percentages=[],  # No narrowing percentages supplied
    )

    tam_res = calc_service.calculate_top_down_tam(td_inputs)
    
    assert tam_res.status == CalculationStatus.CALCULATED
    assert any("Parent-market warning" in w for w in tam_res.warnings)
    assert tam_res.market_scope == "Addressable market"
    assert tam_res.market_scope_explanation is not None


def test_explicit_market_scope_on_all_calculation_results() -> None:
    """Test that TAM, SAM, and SOM calculation results (both Top-Down and Bottom-Up) include explicit scope & explanation."""
    # 1. Top-Down
    macro_input = EvidenceInput(
        name="India Online Developer Education TAM",
        value=2_000_000_000.0,
        unit="USD",
        currency="USD",
        year=2024,
        geography="India",
        market_scope=MarketScopeType.ADDRESSABLE_MARKET.value,
    )
    seg_pct = EvidenceInput(
        name="Higher Education Segment Share",
        value=35.0,
        unit="%",
        market_scope=MarketScopeType.SERVICEABLE_MARKET.value,
    )
    som_share = EvidenceInput(
        name="Obtainable Target Share",
        value=5.0,
        unit="%",
        market_scope=MarketScopeType.OBTAINABLE_MARKET.value,
    )

    td_inputs = TopDownCalculationInputs(
        macro_market_size=macro_input,
        target_segment_percentage=seg_pct,
        obtainable_market_share=som_share,
    )

    td_tam = calc_service.calculate_top_down_tam(td_inputs)
    td_sam = calc_service.calculate_top_down_sam(td_tam, td_inputs)
    td_som = calc_service.calculate_top_down_som(td_sam, td_inputs)

    assert td_tam.market_scope == "Addressable market"
    assert "TAM" in td_tam.market_scope_explanation or "Addressable" in td_tam.market_scope_explanation
    assert td_sam.market_scope == "Serviceable market"
    assert "SAM" in td_sam.market_scope_explanation or "Serviceable" in td_sam.market_scope_explanation
    assert td_som.market_scope == "Obtainable market"
    assert "SOM" in td_som.market_scope_explanation or "Obtainable" in td_som.market_scope_explanation

    # 2. Bottom-Up
    cust_input = EvidenceInput(
        name="College Students in India",
        value=40_000_000.0,
        unit="students",
        year=2024,
        geography="India",
        market_scope=MarketScopeType.ADDRESSABLE_MARKET.value,
    )
    target_pct = EvidenceInput(
        name="Engineering and Computer Science Undergrads",
        value=10.0,
        unit="%",
        market_scope=MarketScopeType.SERVICEABLE_MARKET.value,
    )
    price_input = EvidenceInput(
        name="Annual Coding Platform Subscription",
        value=50.0,
        unit="USD",
        currency="USD",
        year=2024,
    )
    obt_cust = EvidenceInput(
        name="Realistic First Year Enrolled Students",
        value=100_000.0,
        unit="students",
        market_scope=MarketScopeType.OBTAINABLE_MARKET.value,
    )

    bu_inputs = BottomUpCalculationInputs(
        potential_customers=cust_input,
        pricing=price_input,
        pricing_frequency=PriceFrequency.ANNUAL,
        target_customer_percentage=target_pct,
        realistically_obtainable_customers=obt_cust,
    )

    bu_tam = calc_service.calculate_bottom_up_tam(bu_inputs)
    bu_sam = calc_service.calculate_bottom_up_sam(bu_tam, bu_inputs)
    bu_som = calc_service.calculate_bottom_up_som(bu_sam, bu_inputs)

    assert bu_tam.market_scope == "Addressable market"
    assert bu_tam.market_scope_explanation is not None
    assert bu_sam.market_scope == "Serviceable market"
    assert bu_sam.market_scope_explanation is not None
    assert bu_som.market_scope == "Obtainable market"
    assert bu_som.market_scope_explanation is not None
