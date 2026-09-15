"""Comprehensive 22-Failure-Mode Regression and Multi-Domain Isolation Test Suite.

Verifies end-to-end correctness of TAM, SAM, SOM candidate extraction, semantic routing,
geographic isolation, range construction, anti-double-narrowing, SOM safety, and run isolation.
"""

import pytest
from app.schemas.calculation import (
    CalculationInput,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
    BottomUpCalculationInputs,
)
from app.schemas.discovery import SourceQualityTier
from app.schemas.extraction import MarketMetricType, ExtractedEvidenceCandidate
from app.schemas.pipeline import PipelineRequest
from app.services.calculation_service import CalculationService
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService
from app.orchestration.pipeline import MarketAnalysisPipeline


# ==============================================================================
# 1. TAM Candidate Failure Modes (1, 2, 3, 4, 5, 17, 18, 20)
# ==============================================================================

def test_01_per_unit_spending_cannot_become_tam():
    """Failure Mode 1: Per-unit spend cannot be classified as macro market size."""
    extractor = EvidenceExtractionService()
    sentence = "The annual software subscription costs USD 450 per developer in 2025."
    candidates = extractor.extract_candidates_from_sentence(sentence, "https://techreport.com")
    cand = next((c for c in candidates if c.value == 450.0), None)
    assert cand is not None
    assert cand.metric_type in (MarketMetricType.AVERAGE_PRICE, MarketMetricType.SUBSCRIPTION_PRICE)
    assert cand.metric_type != MarketMetricType.MARKET_SIZE


def test_02_per_pet_spending_cannot_become_tam():
    """Failure Mode 2: Per-companion pet spending cannot be classified as macro market size."""
    extractor = EvidenceExtractionService()
    sentence = "Modeled annual expenditure rises from USD 93.7 per companion pet in 2025 to USD 167.0 by 2032."
    candidates = extractor.extract_candidates_from_sentence(sentence, "https://kenresearch.com/report")
    cand = next((c for c in candidates if c.value == 93.7), None)
    assert cand is not None
    assert cand.metric_type in (MarketMetricType.AVERAGE_PRICE, MarketMetricType.SUBSCRIPTION_PRICE, MarketMetricType.ANNUAL_SPEND)
    assert cand.metric_type != MarketMetricType.MARKET_SIZE
    assert cand.metric != "market size / revenue"


def test_03_arpu_cannot_become_tam():
    """Failure Mode 3: Annual ARPU / pricing cannot enter Top-Down macro TAM."""
    extractor = EvidenceExtractionService()
    sentence = "Average revenue per user (ARPU) is estimated at $120 annually in India."
    candidates = extractor.extract_candidates_from_sentence(sentence, "https://statista.com")
    cand = next((c for c in candidates if c.value == 120.0), None)
    assert cand is not None
    assert cand.metric_type in (MarketMetricType.AVERAGE_PRICE, MarketMetricType.SUBSCRIPTION_PRICE)


def test_04_china_value_cannot_inherit_india_geography():
    """Failure Mode 4: Peer country numbers must retain their proximate geography."""
    extractor = EvidenceExtractionService()
    sentence = "India ranks 2nd among selected peers at USD 4,300 million in 2025, trailing China's USD 43,400 million."
    candidates = extractor.extract_candidates_from_sentence(sentence, "https://kenresearch.com")

    china_cand = next((c for c in candidates if c.value == 43400000000.0), None)
    assert china_cand is not None
    assert china_cand.geography == "China"
    assert china_cand.geography != "India"

    india_cand = next((c for c in candidates if c.value == 4300000000.0), None)
    assert india_cand is not None
    assert india_cand.geography == "India"


def test_05_foreign_country_market_values_cannot_enter_india_tam_range():
    """Failure Mode 5: China / foreign values cannot pollute India TAM candidate bounds."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    s1 = "The India pet care products market size increased from USD 8.6 Billion in 2025 to USD 9.2 Billion in 2026."
    s2 = "India ranks 2nd at USD 4,300 million in 2025, trailing China's USD 43,400 million."
    cands = (
        extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com")
        + extractor.extract_candidates_from_sentence(s2, "https://kenresearch.com")
    )
    tri_res = validator.triangulate_evidence(cands)

    req = PipelineRequest(
        business_idea="Pet care services in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is not None
    macro_input = calc_input.top_down_inputs.macro_market_size
    assert macro_input is not None
    if macro_input.range_max is not None:
        assert macro_input.range_max <= 15_000_000_000.0  # Must NEVER be China's $43.4B


def test_17_tam_range_cannot_use_unrelated_numerical_candidates():
    """Failure Mode 17: Triangulation and range bounds exclude micro and unrelated values."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    s1 = "The India pet care products market size reached USD 8.6 Billion in 2025."
    s2 = "Modeled annual expenditure rises from USD 93.7 per companion pet in 2025."
    cands = (
        extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com")
        + extractor.extract_candidates_from_sentence(s2, "https://kenresearch.com")
    )
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    macro_input = calc_input.top_down_inputs.macro_market_size
    assert macro_input is not None
    assert macro_input.value == 8600000000.0
    if macro_input.range_min is not None:
        assert macro_input.range_min >= 1_000_000.0
        assert macro_input.range_min != 93.7


def test_23_unit_spend_29_5_cannot_become_tam_lower_bound():
    """Specific Test: $29.5 per-customer/per-unit value cannot become TAM lower bound."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    s1 = "The India pet care market reached USD 8.6 Billion in 2025."
    s2 = "Average expenditure per pet is USD 29.5 annually."
    cands = (
        extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com")
        + extractor.extract_candidates_from_sentence(s2, "https://survey.com")
    )
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    macro_input = calc_input.top_down_inputs.macro_market_size
    assert macro_input is not None
    assert macro_input.value == 8600000000.0
    assert macro_input.range_min != 29.5
    if macro_input.range_min is not None:
        assert macro_input.range_min >= 1_000_000.0


def test_18_single_valid_tam_candidate_does_not_produce_fake_range():
    """Failure Mode 18: A single valid TAM candidate without conflicts has clean interval bounds."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(
        name="market size / revenue",
        value=8600000000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
        source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
    )
    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(macro_market_size=tam_ev),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam is not None
    assert report.top_down_tam.estimate == 8600000000.0
    assert report.top_down_tam.interval.lower == 8600000000.0
    assert report.top_down_tam.interval.upper == 8600000000.0


def test_20_bottom_up_unit_economics_remain_separate_from_macro_tam():
    """Failure Mode 20: Unit economics pricing produces bottom-up sizing, not macro TAM."""
    calc_service = CalculationService()
    cust_ev = EvidenceInput(
        name="college students",
        value=40000000.0,
        unit="students",
        year=2025,
        geography="India",
    )
    price_ev = EvidenceInput(
        name="annual tuition / ARPU",
        value=500.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    calc_input = CalculationInput(
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=cust_ev,
            pricing=price_ev,
            pricing_frequency=PriceFrequency.ANNUAL,
        ),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.bottom_up_tam is not None
    assert report.bottom_up_tam.estimate == 20000000000.0  # 40M * $500 = $20B
    assert report.top_down_tam is None or report.top_down_tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 2. SAM Candidate & Percentage Failure Modes (6, 7, 8, 9, 10, 11, 12, 13, 14)
# ==============================================================================

def test_06_cagr_cannot_become_sam_percentage():
    """Failure Mode 6: Industry CAGR cannot be used as SAM percentage."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "The Indian pet care market will grow at a CAGR of 14.88% from 2025 to 2030."
    cands = extractor.extract_candidates_from_sentence(s, "https://imarcgroup.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care platform in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_07_growth_percentage_cannot_become_sam_percentage():
    """Failure Mode 7: YoY growth percentage cannot be used as SAM percentage."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "Revenues increased by 22.5% year-on-year across major cities."
    cands = extractor.extract_candidates_from_sentence(s, "https://news.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_08_discount_cannot_become_sam_percentage():
    """Failure Mode 8: Promotional store discount (e.g. Save 35%) cannot become SAM percentage."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "Buy pet care packages today and save 35% on all grooming sessions."
    cands = extractor.extract_candidates_from_sentence(s, "https://petstore.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_09_demographic_percentage_cannot_become_sam_percentage():
    """Failure Mode 9: Species / biological breakdown (70% dogs) cannot become service SAM percentage."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "In India, dogs dominate pet ownership making up 70% of companion animals."
    cands = extractor.extract_candidates_from_sentence(s, "https://petresearch.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care platform in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_10_physical_product_share_cannot_narrow_service_market():
    """Failure Mode 10: Pet food share (65%) cannot narrow a veterinary/grooming service platform."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "Pet food accounts for 65.00% of the overall market spending in India."
    cands = extractor.extract_candidates_from_sentence(s, "https://imarcgroup.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_11_global_to_india_share_cannot_be_applied_to_india_scoped_tam():
    """Failure Mode 11: India 5.41% share of global TAM must not narrow an already India-scoped TAM."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s1 = "The India pet care products market size increased from USD 8.6 Billion in 2025 to USD 9.2 Billion in 2026."
    s2 = "India represents 5.41% of the global pet care market."
    cands = (
        extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com")
        + extractor.extract_candidates_from_sentence(s2, "https://fortunebusiness.com")
    )
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    # TAM is India ($8.6B), so serviceable_geography_percentage MUST be suppressed
    assert calc_input.top_down_inputs.macro_market_size.geography == "India"
    assert calc_input.top_down_inputs.serviceable_geography_percentage is None


def test_12_generic_fallback_metric_name_cannot_qualify_as_segment():
    """Failure Mode 12: Generic fallback metric name 'market share / segment percentage' does not qualify without context."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s = "The market share of 45.0% was recorded."
    cands = extractor.extract_candidates_from_sentence(s, "https://generic.com")
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(business_idea="Tutoring platform in India", preferred_geography="India", preferred_year=2025)
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is None or calc_input.top_down_inputs.target_segment_percentage is None


def test_13_valid_target_segment_percentage_can_qualify():
    """Failure Mode 13: Legitimate, topic-aligned target segment percentage qualifies for SAM."""
    pipeline = MarketAnalysisPipeline()
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()

    s1 = "The Indian education tutoring market is valued at USD 10.0 Billion in 2025."
    s2 = "High-school students represent a target segment accounting for 35.0% of tutoring demand in India."
    cands = (
        extractor.extract_candidates_from_sentence(s1, "https://education.gov.in")
        + extractor.extract_candidates_from_sentence(s2, "https://research.edu")
    )
    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online home tutoring services for high-school students in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.target_segment_percentage is not None
    assert calc_input.top_down_inputs.target_segment_percentage.value == 35.0

    calc_service = CalculationService()
    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 3500000000.0  # 10B * 35% = $3.5B


def test_14_sam_cannot_exceed_tam():
    """Failure Mode 14: SAM estimate and interval bounds must never exceed TAM."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(name="market size", value=10000000000.0, unit="USD", currency="USD", year=2025, geography="India")
    seg_ev = EvidenceInput(name="service segment", value=40.0, unit="%", year=2025, geography="India")

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=tam_ev,
            target_segment_percentage=seg_ev,
        ),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.estimate <= report.top_down_tam.estimate
    assert report.top_down_sam.estimate == 4000000000.0


# ==============================================================================
# 3. SOM Safety & Calculation Failure Modes (15, 16)
# ==============================================================================

def test_15_som_cannot_exceed_sam():
    """Failure Mode 15: SOM must never exceed SAM."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(name="market size", value=10000000000.0, unit="USD", currency="USD", year=2025, geography="India")
    seg_ev = EvidenceInput(name="service segment", value=50.0, unit="%", year=2025, geography="India")
    som_ev = EvidenceInput(name="obtainable share", value=5.0, unit="%", year=2025, geography="India")

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=tam_ev,
            target_segment_percentage=seg_ev,
            obtainable_market_share=som_ev,
        ),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.top_down_som.status == CalculationStatus.CALCULATED
    assert report.top_down_som.estimate <= report.top_down_sam.estimate
    assert report.top_down_som.estimate == 250000000.0  # $5B * 5% = $250M


def test_16_som_cannot_be_fabricated():
    """Failure Mode 16: When obtainable share evidence is absent, SOM is strictly INSUFFICIENT_EVIDENCE."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(name="market size", value=8600000000.0, unit="USD", currency="USD", year=2025, geography="India")
    seg_ev = EvidenceInput(name="service segment", value=20.0, unit="%", year=2025, geography="India")

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=tam_ev,
            target_segment_percentage=seg_ev,
            obtainable_market_share=None,
        ),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_som.estimate is None


# ==============================================================================
# 4. Run Isolation, Provenance & Traceability (19, 21, 22)
# ==============================================================================

def test_19_cross_run_evidence_isolation():
    """Failure Mode 19: Run 2 (Tutoring) cannot inherit evidence or candidates from Run 1 (Pet Care)."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    # Run 1: Pet Care
    pet_text = "The India pet care products market size increased from USD 8.6 Billion in 2025 to USD 9.2 Billion in 2026."
    pet_cands = extractor.extract_candidates_from_sentence(pet_text, "https://imarcgroup.com")
    pet_tri = validator.triangulate_evidence(pet_cands)
    req1 = PipelineRequest(business_idea="Pet care in India", preferred_geography="India", preferred_year=2025)
    calc_input1 = pipeline._build_calculation_inputs(None, pet_tri.validated_items, req1)
    assert calc_input1.top_down_inputs.macro_market_size.value == 8600000000.0

    # Run 2: Tutoring (Fresh run with tutoring evidence only)
    tutor_text = "The India home tutoring market is estimated at USD 4.5 Billion in 2025."
    tutor_cands = extractor.extract_candidates_from_sentence(tutor_text, "https://education.in")
    tutor_tri = validator.triangulate_evidence(tutor_cands)
    req2 = PipelineRequest(business_idea="Tutoring services in India", preferred_geography="India", preferred_year=2025)
    calc_input2 = pipeline._build_calculation_inputs(None, tutor_tri.validated_items, req2)

    assert calc_input2.top_down_inputs.macro_market_size.value == 4500000000.0
    assert calc_input2.top_down_inputs.macro_market_size.value != 8600000000.0


def test_21_top_down_and_bottom_up_results_separately_traceable():
    """Failure Mode 21: Top-down and bottom-up sizing have distinct steps and divergence analysis."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(name="macro market", value=10000000000.0, unit="USD", currency="USD", year=2025, geography="India")
    cust_ev = EvidenceInput(name="users", value=10000000.0, unit="users", year=2025, geography="India")
    price_ev = EvidenceInput(name="subscription", value=800.0, unit="USD", currency="USD", year=2025, geography="India")

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(macro_market_size=tam_ev),
        bottom_up_inputs=BottomUpCalculationInputs(potential_customers=cust_ev, pricing=price_ev),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.estimate == 10000000000.0
    assert report.bottom_up_tam.estimate == 8000000000.0
    assert report.method_comparison is not None
    assert report.method_comparison.top_down_estimate == 10000000000.0
    assert report.method_comparison.bottom_up_estimate == 8000000000.0
    assert len(report.top_down_tam.steps) >= 1
    assert len(report.bottom_up_tam.steps) >= 1


def test_22_frontend_payload_structure():
    """Failure Mode 22: Calculation report produces valid structured output matching frontend types."""
    calc_service = CalculationService()
    tam_ev = EvidenceInput(
        name="market size / revenue",
        value=8600000000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
        range_min=4300000000.0,
        range_max=9200000000.0,
    )
    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(macro_market_size=tam_ev),
        target_geography="India",
        target_year=2025,
    )
    report = calc_service.generate_report(calc_input)
    dict_report = report.model_dump()
    assert "top_down_tam" in dict_report
    assert "top_down_sam" in dict_report
    assert dict_report["top_down_tam"]["estimate"] == 8600000000.0
    assert dict_report["top_down_sam"]["status"] == "insufficient_evidence"
    assert dict_report["top_down_som"] is None or dict_report["top_down_som"]["status"] == "insufficient_evidence"


# ==============================================================================
# 5. Multi-Domain Scenario Tests (Pet Care, Tutoring, Food Delivery, Solar)
# ==============================================================================

def test_scenario_a_pet_care_india():
    """TEST A: Pet Care / India — TAM=$8.6B, SAM=insufficient_evidence, SOM=insufficient_evidence."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    s1 = "The India pet care products market size increased from USD 8.6 Billion in 2025 to USD 9.2 Billion in 2026."
    s2 = "Modeled annual expenditure rises from USD 93.7 per companion pet in 2025."
    s3 = "India ranks 2nd at USD 4,300 million in 2025, trailing China's USD 43,400 million."
    s4 = "Pet food accounts for 65% of the market."
    s5 = "India represents 5.41% of the global pet care market."

    cands = []
    for s in (s1, s2, s3, s4, s5):
        cands.extend(extractor.extract_candidates_from_sentence(s, "https://report.com"))

    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    report = calc_service.generate_report(calc_input)

    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 8600000000.0
    assert report.top_down_tam.interval.lower >= 1_000_000.0
    assert report.top_down_tam.interval.lower != 93.7
    assert report.top_down_tam.interval.upper <= 15_000_000_000.0
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_som is None or report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


def test_scenario_b_online_tutoring_india():
    """TEST B: Online Tutoring / India — Clean tutoring market size and high school segment."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    s1 = "The India tutoring market size was valued at USD 10.0 Billion in 2025."
    s2 = "High-school students represent a target segment accounting for 30.0% of tutoring demand in India."
    s3 = "Urbanization rate in India is 36.0%."

    cands = []
    for s in (s1, s2, s3):
        cands.extend(extractor.extract_candidates_from_sentence(s, "https://education.gov.in"))

    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online platform for affordable home tutoring services for high-school students in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    report = calc_service.generate_report(calc_input)

    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 10000000000.0
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 3000000000.0
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


def test_scenario_c_food_delivery_tamil_nadu():
    """TEST C: Food Delivery / Tamil Nadu — Identifies regional food delivery market & college segment."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    s1 = "The online food delivery market in Tamil Nadu reached USD 1,500 million in 2025."
    s2 = "College students represent 25.0% of online food delivery orders across major cities."
    s3 = "Tamil Nadu urbanization rate is 48%."

    cands = []
    for s in (s1, s2, s3):
        cands.extend(extractor.extract_candidates_from_sentence(s, "https://statista.com"))

    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online food delivery platform for college students in Tamil Nadu, India",
        preferred_geography="Tamil Nadu",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    report = calc_service.generate_report(calc_input)

    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 1500000000.0
    assert report.top_down_tam.geography == "Tamil Nadu"
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 375000000.0  # 1.5B * 25% = $375M
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


def test_scenario_d_residential_solar_india():
    """TEST D: Residential Solar / India — Sizing for rooftop solar and residential segment."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    s1 = "The India solar power market size was valued at USD 12.0 Billion in 2025."
    s2 = "The residential rooftop segment accounts for 20.0% of solar installations."
    s3 = "Solar cell import tariffs were 25%."

    cands = []
    for s in (s1, s2, s3):
        cands.extend(extractor.extract_candidates_from_sentence(s, "https://mnre.gov.in"))

    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Rooftop solar installation and financing platform for residential homeowners in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)
    report = calc_service.generate_report(calc_input)

    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 12000000000.0
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 2400000000.0  # 12B * 20% = $2.4B
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE


def test_malformed_percentage_and_jump_from_do_not_crash_pipeline():
    """Regression test: Malformed candidate with out-of-bounds percentage or 'jump from' does not crash market calculation."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    s1 = "The India apparel market is valued at USD 1,200 million in 2025."
    s2 = "Sustainable apparel represents a target segment accounting for 25.0% of apparel sales in India."
    s3 = "Consumer demand saw a jump from 128 to 150 million users."

    cands = []
    for s in (s1, s2, s3):
        cands.extend(extractor.extract_candidates_from_sentence(s, "https://apparel-market-research.com"))

    # Also deliberately inject a malformed candidate with an invalid percentage
    malformed_cand = ExtractedEvidenceCandidate(
        metric="jump from",
        value=128.0,
        unit="%",
        geography="India",
        year=2025,
        source_url="https://bad-source.com",
        source_context="There was a jump from 128% in metrics.",
    )
    cands.append(malformed_cand)
    tri_items = validator.triangulate_evidence(cands).validated_items

    req = PipelineRequest(
        business_idea="Direct-to-consumer sustainable apparel marketplace for environmentally conscious consumers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    # Pipeline _build_calculation_inputs should safely filter out/sanitize the malformed item without raising ValidationError
    calc_input = pipeline._build_calculation_inputs(None, tri_items, req)
    report = calc_service.generate_report(calc_input)

    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 1200000000.0  # $1.2B
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.estimate == 300000000.0   # $1.2B * 25% = $300M

