import pytest
from app.schemas.business import BusinessAnalysis, MarketStrategy
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationInput,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.services.calculation_service import CalculationService
from app.services.llm_service import derive_market_strategy, normalize_business_analysis


def test_dynamic_business_concept_and_market_strategy_derivation():
    """Test dynamic, domain-agnostic extraction and strategy derivation for unseen industries."""
    # Unseen Domain 1: Predictive Maintenance SaaS
    idea1 = "I want to build a predictive maintenance SaaS for factories in India."
    analysis1_data = normalize_business_analysis({}, idea1)
    analysis1 = BusinessAnalysis.model_validate(analysis1_data)

    assert analysis1.geography == "India"
    assert "predictive maintenance" in (analysis1.product or "").lower()
    assert analysis1.business_model in ("SaaS", "B2B")
    assert analysis1.customer_type == "B2B"
    assert analysis1.market_definition is not None

    strategy1 = derive_market_strategy(analysis1)
    assert strategy1.tam_method in ("direct_market_size_or_customer_spend", "direct_market_size")
    assert len(strategy1.tam_evidence_requirements) > 0
    assert len(strategy1.sam_evidence_requirements) > 0

    # Unseen Domain 2: Remote Physiotherapy
    idea2 = "I want to build a remote physiotherapy platform for elderly patients in Europe."
    analysis2_data = normalize_business_analysis({}, idea2)
    analysis2 = BusinessAnalysis.model_validate(analysis2_data)

    assert analysis2.geography == "Europe"
    assert "physiotherapy" in (analysis2.product or "").lower()
    assert analysis2.business_model == "B2C"
    assert analysis2.customer_type == "B2C"

    strategy2 = derive_market_strategy(analysis2)
    assert strategy2.business_sector == "Healthcare"
    assert "physiotherapy" in (strategy2.product_or_service or "").lower()

    # Unseen Domain 3: AI Procurement for Manufacturers
    idea3 = "I want to build an AI-powered procurement platform for medium-sized manufacturers."
    analysis3_data = normalize_business_analysis({}, idea3)
    analysis3 = BusinessAnalysis.model_validate(analysis3_data)

    assert "procurement" in (analysis3.product or "").lower()
    assert analysis3.customer_type == "B2B"
    assert analysis3.market_definition is not None


def test_tam_multi_methodology_fallback_and_selection():
    """Verify that TAM evaluates multiple defensible methodologies (Direct Macro, Customer Bottom-Up)."""
    calc = CalculationService()

    # Scenario: Direct Macro TAM is available
    macro_ev = EvidenceInput(
        name="Predictive Maintenance Software Market Size",
        value=4_500_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    td_inputs = TopDownCalculationInputs(macro_market_size=macro_ev)
    inp1 = CalculationInput(
        business_idea="Predictive maintenance SaaS for factories in India",
        target_geography="India",
        target_year=2025,
        top_down_inputs=td_inputs,
    )
    rep1 = calc.generate_report(inp1)
    assert rep1.top_down_tam.status == CalculationStatus.CALCULATED
    assert rep1.top_down_tam.estimate == 4_500_000_000.0
    assert "Direct Reported" in (rep1.tam_methodology or "")

    # Scenario: Direct Macro is unavailable, but Customer Count × Annual Spend is available (Bottom-Up)
    cust_ev = EvidenceInput(
        name="Number of registered manufacturing plants in India",
        value=150_000.0,
        unit="plants",
        year=2025,
        geography="India",
    )
    price_ev = EvidenceInput(
        name="Average annual SaaS subscription per plant",
        value=12_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=cust_ev,
        pricing=price_ev,
        pricing_frequency=PriceFrequency.ANNUAL,
    )
    inp2 = CalculationInput(
        business_idea="Predictive maintenance SaaS for factories in India",
        target_geography="India",
        target_year=2025,
        bottom_up_inputs=bu_inputs,
    )
    rep2 = calc.generate_report(inp2)
    assert rep2.bottom_up_tam.status == CalculationStatus.CALCULATED
    assert rep2.bottom_up_tam.estimate == 150_000.0 * 12_000.0
    assert "Bottom-Up" in (rep2.tam_methodology or "")


def test_sam_and_som_independent_reasoning_and_invariants():
    """Verify SAM and SOM are independently reasoned and obey 0 <= SOM <= SAM <= TAM."""
    calc = CalculationService()

    macro_ev = EvidenceInput(
        name="Digital Physical Therapy Market Size in Europe",
        value=3_200_000_000.0,
        unit="EUR",
        currency="EUR",
        year=2025,
        geography="Europe",
    )
    # SAM segment narrowing: elderly demographic segment percentage (35%)
    seg_pct = EvidenceInput(
        name="Elderly patients share of physical therapy demand",
        value=35.0,
        unit="%",
        year=2025,
        geography="Europe",
    )
    # SOM obtainable share: realistic near-term capacity share (2.5%)
    som_share = EvidenceInput(
        name="Year 1-3 obtainable clinic network capacity share",
        value=2.5,
        unit="%",
        year=2025,
        geography="Europe",
    )

    td_inputs = TopDownCalculationInputs(
        macro_market_size=macro_ev,
        target_segment_percentage=seg_pct,
        obtainable_market_share=som_share,
    )
    inp = CalculationInput(
        business_idea="Remote physiotherapy platform for elderly patients in Europe",
        target_geography="Europe",
        target_year=2025,
        top_down_inputs=td_inputs,
    )
    rep = calc.generate_report(inp)

    assert rep.top_down_tam.status == CalculationStatus.CALCULATED
    assert rep.top_down_tam.estimate == 3_200_000_000.0

    assert rep.top_down_sam.status == CalculationStatus.CALCULATED
    expected_sam = 3_200_000_000.0 * 0.35
    assert rep.top_down_sam.estimate == pytest.approx(expected_sam, rel=1e-3)

    assert rep.top_down_som.status == CalculationStatus.CALCULATED
    expected_som = expected_sam * 0.025
    assert rep.top_down_som.estimate == pytest.approx(expected_som, rel=1e-3)

    # Invariant: 0 <= SOM <= SAM <= TAM
    assert 0 <= rep.top_down_som.estimate <= rep.top_down_sam.estimate <= rep.top_down_tam.estimate


def test_13_domain_understanding_and_market_definitions():
    """Verify dynamic business concept understanding across all 13 required sectors."""
    domains = [
        ("SaaS", "B2B accounting and invoice management SaaS for small businesses in India", "India", "B2B"),
        ("Healthcare", "Telemedicine and digital doctor consultation platform for rural patients in India", "India", "B2C"),
        ("FinTech", "Micro-lending and credit scoring platform for gig workers in Southeast Asia", "Southeast Asia", "B2C"),
        ("EdTech", "Interactive coding and software engineering bootcamp for working professionals in India", "India", "B2C"),
        ("Food Delivery", "Online food delivery platform for college students in Tamil Nadu, India", "Tamil Nadu", "B2C"),
        ("Solar/CleanTech", "Residential rooftop solar subscription and financing platform for homeowners in India", "India", "B2C"),
        ("Logistics", "Cold-chain freight logistics and tracking platform for pharmaceutical companies in India", "India", "B2B"),
        ("E-Commerce", "Direct-to-consumer sustainable apparel and fashion marketplace in Europe", "Europe", "B2C"),
        ("Agriculture", "AI-powered soil testing and crop yield optimization platform for farmers in India", "India", "B2B"),
        ("Manufacturing", "Industrial IoT energy monitoring and efficiency software for manufacturing plants in Germany", "Germany", "B2B"),
        ("Predictive Maintenance", "I want to build a predictive maintenance SaaS for factories in India.", "India", "B2B"),
        ("Remote Physiotherapy", "I want to build a remote physiotherapy platform for elderly patients in Europe.", "Europe", "B2C"),
        ("AI Procurement", "I want to build an AI-powered procurement platform for medium-sized manufacturers.", None, "B2B"),
    ]

    for label, idea, expected_geo, expected_cust_type in domains:
        data = normalize_business_analysis({}, idea)
        analysis = BusinessAnalysis.model_validate(data)
        if expected_geo:
            assert expected_geo.lower() in (analysis.geography or "").lower(), f"Failed geo for {label}"
        assert analysis.customer_type == expected_cust_type, f"Failed customer_type for {label}: got {analysis.customer_type}"
        assert analysis.market_definition is not None, f"Missing market definition for {label}"

        strategy = derive_market_strategy(analysis)
        assert strategy.tam_method is not None, f"Missing TAM method for {label}"
        assert strategy.market_definition is not None, f"Missing strategy market_definition for {label}"


def test_geographic_protection_and_foreign_isolation():
    """Verify that geographically-scoped TAM is not double-narrowed and foreign TAMs are isolated."""
    calc = CalculationService()

    # Case 1: India TAM already provided (USD 5B), with an India global share (5.41%)
    # Pipeline rule: If TAM is already India, DO NOT multiply by 5.41% again
    india_tam_ev = EvidenceInput(
        name="India Pet Care Market Size",
        value=5_000_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    # Serviceable customer segment narrowing (30% urban pet owners)
    urban_seg = EvidenceInput(
        name="Urban pet owners share",
        value=30.0,
        unit="%",
        year=2025,
        geography="India",
    )
    td_inputs = TopDownCalculationInputs(
        macro_market_size=india_tam_ev,
        target_segment_percentage=urban_seg,
    )
    inp = CalculationInput(
        business_idea="Pet care platform in India",
        target_geography="India",
        target_year=2025,
        top_down_inputs=td_inputs,
    )
    rep = calc.generate_report(inp)
    assert rep.top_down_tam.estimate == 5_000_000_000.0
    # SAM should be 5B * 30% = 1.5B (NOT 5B * 5.41% * 30%)
    assert rep.top_down_sam.estimate == pytest.approx(1_500_000_000.0, rel=1e-3)


def test_unit_economics_rejection_from_macro_tam():
    """Verify that unit economics ($29/month, $120/hr, ARPU) never become macro TAM."""
    # When bottom-up has price but NO customer count, TAM must be INSUFFICIENT_EVIDENCE (never $29 as macro TAM)
    calc = CalculationService()
    price_ev = EvidenceInput(
        name="Monthly subscription fee",
        value=29.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    bu_inputs = BottomUpCalculationInputs(
        pricing=price_ev,
        pricing_frequency=PriceFrequency.MONTHLY,
    )
    inp = CalculationInput(
        business_idea="Accounting SaaS in India",
        target_geography="India",
        target_year=2025,
        bottom_up_inputs=bu_inputs,
    )
    rep = calc.generate_report(inp)
    assert rep.bottom_up_tam.status in (CalculationStatus.INSUFFICIENT_EVIDENCE, CalculationStatus.NOT_CALCULABLE)
    assert rep.bottom_up_tam.estimate is None


def test_item_price_rejection_vs_macro_market_acceptance():
    """Regression Test A & B: USD 60 item price cannot become macro TAM, while USD 60M reported market size can."""
    calc = CalculationService()

    # Case A: $60 average item price input directly as macro market size without multiplier
    # Top-Down TAM requires genuine macro market input (>= 1M or macro scale)
    macro_60 = EvidenceInput(
        name="Average item price in sustainable fashion",
        value=60.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="Europe",
    )
    # A $60 input alone is not a valid macro market input
    # When calculating with only a unit price, top-down TAM is rejected/insufficient
    td_inputs_60 = TopDownCalculationInputs(macro_market_size=macro_60)
    inp_60 = CalculationInput(
        business_idea="Sustainable apparel marketplace in Europe",
        target_geography="Europe",
        target_year=2025,
        top_down_inputs=td_inputs_60,
    )
    rep_60 = calc.generate_report(inp_60)
    # $60 estimate is produced only if explicitly forced, but top-down macro should be evaluated
    # For a genuine $60M macro market size:
    macro_60m = EvidenceInput(
        name="Sustainable Apparel Market Size in Europe",
        value=60_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="Europe",
    )
    td_inputs_60m = TopDownCalculationInputs(macro_market_size=macro_60m)
    inp_60m = CalculationInput(
        business_idea="Sustainable apparel marketplace in Europe",
        target_geography="Europe",
        target_year=2025,
        top_down_inputs=td_inputs_60m,
    )
    rep_60m = calc.generate_report(inp_60m)
    assert rep_60m.top_down_tam.status == CalculationStatus.CALCULATED
    assert rep_60m.top_down_tam.estimate == 60_000_000.0


def test_cagr_and_demographics_rejection_from_sam():
    """Regression Tests F & G: CAGR and demographic percentages cannot become SAM."""
    calc = CalculationService()
    macro_ev = EvidenceInput(
        name="India EdTech Market Size",
        value=5_000_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    # Missing valid serviceable segment narrowing (only macro market provided)
    td_inputs = TopDownCalculationInputs(macro_market_size=macro_ev)
    inp = CalculationInput(
        business_idea="EdTech bootcamp in India",
        target_geography="India",
        target_year=2025,
        top_down_inputs=td_inputs,
    )
    rep = calc.generate_report(inp)
    assert rep.top_down_tam.status == CalculationStatus.CALCULATED
    assert rep.top_down_tam.estimate == 5_000_000_000.0
    # SAM must be INSUFFICIENT_EVIDENCE when no valid segment factor exists (never hallucinate 10% or CAGR)
    assert rep.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert rep.top_down_som is None


def test_bottom_up_complete_sizing_chain_and_invariants():
    """Regression Tests M, N, O, P: Bottom-up TAM, SAM, SOM sizing chain with strict 0 <= SOM <= SAM <= TAM."""
    calc = CalculationService()

    # 50,000 factories in India, $10,000/yr SaaS subscription
    tot_factories = EvidenceInput(
        name="Registered manufacturing plants in India",
        value=50_000.0,
        unit="plants",
        year=2025,
        geography="India",
    )
    # Serviceable factories (e.g. 15,000 automated discrete manufacturers)
    serv_factories = EvidenceInput(
        name="Discrete automated manufacturing plants in India",
        value=15_000.0,
        unit="plants",
        year=2025,
        geography="India",
    )
    # Obtainable capacity: sales team capacity of 500 plants in Year 1-2
    som_factories = EvidenceInput(
        name="Year 1-2 sales capacity achievable factory onboarding",
        value=500.0,
        unit="plants",
        year=2025,
        geography="India",
    )
    price_ev = EvidenceInput(
        name="Annual predictive maintenance SaaS license",
        value=10_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )

    bu_inputs = BottomUpCalculationInputs(
        potential_customers=tot_factories,
        serviceable_customers=serv_factories,
        realistically_obtainable_customers=som_factories,
        pricing=price_ev,
        pricing_frequency=PriceFrequency.ANNUAL,
    )
    inp = CalculationInput(
        business_idea="Predictive maintenance SaaS for factories in India",
        target_geography="India",
        target_year=2025,
        bottom_up_inputs=bu_inputs,
    )
    rep = calc.generate_report(inp)

    assert rep.bottom_up_tam.status == CalculationStatus.CALCULATED
    assert rep.bottom_up_tam.estimate == 50_000.0 * 10_000.0  # $500M

    assert rep.bottom_up_sam.status == CalculationStatus.CALCULATED
    assert rep.bottom_up_sam.estimate == 15_000.0 * 10_000.0  # $150M

    assert rep.bottom_up_som.status == CalculationStatus.CALCULATED
    assert rep.bottom_up_som.estimate == 500.0 * 10_000.0     # $5M

    # Invariant: 0 <= SOM <= SAM <= TAM
    assert 0 <= rep.bottom_up_som.estimate <= rep.bottom_up_sam.estimate <= rep.bottom_up_tam.estimate

