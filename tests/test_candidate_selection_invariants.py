"""Comprehensive regression test suite for market-size candidate selection,

evidence classification, and calculation input invariants.

Invariants tested:
1. $29.5 per-customer / per-unit value incorrectly becoming TAM lower bound.
2. Foreign-country market value becoming a target-country TAM candidate.
3. Global-to-India percentage double narrowing.
4. CAGR / growth rate being used as SAM.
5. Demographic percentage (e.g. age/gender or species split) being used as SAM.
6. Physical-product share (e.g. pet food 35%) being used as SAM for a service platform.
7. Valid customer/service segment percentage producing SAM.
8. Missing SAM evidence producing INSUFFICIENT_EVIDENCE.
9. Missing SOM evidence producing INSUFFICIENT_EVIDENCE.
10. Valid obtainable-share evidence producing SOM (0 <= SOM <= SAM <= TAM).
"""

import pytest
from app.schemas.calculation import (
    CalculationInput,
    CalculationStatus,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate, MarketMetricType
from app.schemas.pipeline import PipelineRequest
from app.schemas.validation import EvidenceValidationResult
from app.services.calculation_service import CalculationService
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService
from app.orchestration.pipeline import MarketAnalysisPipeline


# ---------------------------------------------------------------------------
# Test 1: $29.5 per-customer / per-unit value rejected as TAM / TAM lower bound
# ---------------------------------------------------------------------------
def test_invariant_1_unit_economics_rejected_as_tam_lower_bound():
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    s1 = "The India pet care market reached USD 14.80 billion in 2025."
    s2 = "Average spending is $29.5 per customer across veterinary and grooming services in 2025."

    c1 = extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com/pet-india")
    c2 = extractor.extract_candidates_from_sentence(s2, "https://petcareinsights.com/spend")

    # Ensure $29.5 is classified as average_price/unit spend, NOT market_size
    cand_295 = next((c for c in c2 if c.value == 29.5), None)
    assert cand_295 is not None
    assert cand_295.metric_type in (MarketMetricType.AVERAGE_PRICE, MarketMetricType.ANNUAL_SPEND, MarketMetricType.SUBSCRIPTION_PRICE)
    assert cand_295.metric_type != MarketMetricType.MARKET_SIZE

    tri_res = validator.triangulate_evidence(c1 + c2)
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.macro_market_size is not None
    macro = calc_input.top_down_inputs.macro_market_size
    assert macro.value == 14_800_000_000.0

    # Range bounds must never contain 29.5
    assert macro.range_min != 29.5
    if macro.range_min is not None:
        assert macro.range_min >= 1_000_000.0


# ---------------------------------------------------------------------------
# Test 2: Foreign-country market value rejected as target-country TAM candidate
# ---------------------------------------------------------------------------
def test_invariant_2_foreign_country_market_rejected_as_target_country_tam():
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    sentence = "India pet care is valued at USD 4,300 million in 2025, trailing China's USD 43,400 million."
    cands = extractor.extract_candidates_from_sentence(sentence, "https://kenresearch.com/report")

    # China's 43.4B candidate must isolate to China, India's 4.3B to India
    cand_china = next((c for c in cands if c.value == 43_400_000_000.0), None)
    assert cand_china is not None
    assert cand_china.geography == "China"

    cand_india = next((c for c in cands if c.value == 4_300_000_000.0), None)
    assert cand_india is not None
    assert cand_india.geography == "India"

    tri_res = validator.triangulate_evidence(cands)
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )
    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    macro = calc_input.top_down_inputs.macro_market_size
    assert macro.geography == "India"
    assert macro.value == 4_300_000_000.0
    # Range max must not be China's 43.4B
    if macro.range_max is not None:
        assert macro.range_max != 43_400_000_000.0


# ---------------------------------------------------------------------------
# Test 3: Global-to-India percentage double narrowing rejected
# ---------------------------------------------------------------------------
def test_invariant_3_global_to_india_percentage_not_double_narrowing():
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    india_tam = EvidenceInput(
        name="India pet care market revenue",
        value=14_800_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    global_share_pct = EvidenceInput(
        name="India share of global market",
        value=5.41,
        unit="%",
        geography="India",
    )

    req = PipelineRequest(
        business_idea="Online pet-care platform in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    # When TAM is already India, 5.41% must not be applied as geo_pct
    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=[
            EvidenceValidationResult(
                candidate_id="c_tam",
                metric="India pet care market revenue",
                value=14_800_000_000.0,
                unit="USD",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The India pet care market revenue reached USD 14.80 billion in 2025.",
            ),
            EvidenceValidationResult(
                candidate_id="c_share",
                metric="India share of the global market",
                value=5.41,
                unit="%",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="India represents 5.41% of the global market.",
            ),
        ],
        request=req,
    )

    assert calc_input.top_down_inputs.serviceable_geography_percentage is None
    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.estimate == 14_800_000_000.0
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None


# ---------------------------------------------------------------------------
# Test 4: CAGR / growth rate rejected as SAM narrowing factor
# ---------------------------------------------------------------------------
def test_invariant_4_cagr_growth_rejected_as_sam():
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    req = PipelineRequest(
        business_idea="Online tutoring platform in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=[
            EvidenceValidationResult(
                candidate_id="c_tam",
                metric="India tutoring market size",
                value=5_000_000_000.0,
                unit="USD",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The India tutoring market size was USD 5.0 Billion in 2025.",
            ),
            EvidenceValidationResult(
                candidate_id="c_cagr",
                metric="Tutoring market CAGR",
                value=16.8,
                unit="%",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The tutoring market in India is projected to grow at a CAGR of 16.8% through 2030.",
            ),
        ],
        request=req,
    )

    assert calc_input.top_down_inputs.target_segment_percentage is None
    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None


# ---------------------------------------------------------------------------
# Test 5: Demographic / species percentage rejected as SAM
# ---------------------------------------------------------------------------
def test_invariant_5_demographic_or_species_split_rejected_as_sam():
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    req = PipelineRequest(
        business_idea="Online pet care services platform in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=[
            EvidenceValidationResult(
                candidate_id="c_tam",
                metric="India pet care services market",
                value=2_500_000_000.0,
                unit="USD",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The India pet care services market reached USD 2.5 Billion in 2025.",
            ),
            EvidenceValidationResult(
                candidate_id="c_species",
                metric="Dogs vs cats population share",
                value=68.0,
                unit="%",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="In India, dogs dominate the pet population, followed by cats making up the rest.",
            ),
        ],
        request=req,
    )

    assert calc_input.top_down_inputs.target_segment_percentage is None
    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None


# ---------------------------------------------------------------------------
# Test 6: Physical-product share rejected as SAM for service platform
# ---------------------------------------------------------------------------
def test_invariant_6_physical_product_share_rejected_as_sam_for_service_platform():
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    req = PipelineRequest(
        business_idea="Online pet-care platform connecting pet owners with veterinarians and groomers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=[
            EvidenceValidationResult(
                candidate_id="c_tam",
                metric="India pet care market",
                value=14_800_000_000.0,
                unit="USD",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The India pet care market reached USD 14.80 billion in 2025.",
            ),
            EvidenceValidationResult(
                candidate_id="c_food",
                metric="Pet food segment share",
                value=35.0,
                unit="%",
                geography="India",
                year=2024,
                source_url="https://source2.com",
                source_context="North India accounted for a whopping 35% of the pet food market share in 2024.",
            ),
        ],
        request=req,
    )

    assert calc_input.top_down_inputs.target_segment_percentage is None
    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None


# ---------------------------------------------------------------------------
# Test 7: Valid customer / service segment percentage producing SAM
# ---------------------------------------------------------------------------
def test_invariant_7_valid_service_segment_percentage_produces_sam():
    pipeline = MarketAnalysisPipeline()
    calc_service = CalculationService()

    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=[
            EvidenceValidationResult(
                candidate_id="c_tam",
                metric="India pet care market size",
                value=14_800_000_000.0,
                unit="USD",
                geography="India",
                year=2025,
                source_url="https://source1.com",
                source_context="The India pet care market size was USD 14.80 billion in 2025.",
            ),
            EvidenceValidationResult(
                candidate_id="c_segment",
                metric="Pet care service transactions segment share",
                value=51.1,
                unit="%",
                geography="India",
                year=2025,
                source_url="https://source3.com",
                source_context="Pet care service transactions in India represent 51.1% of the overall market addressable by booking platforms.",
            ),
        ],
        request=req,
    )

    assert calc_input.top_down_inputs.target_segment_percentage is not None
    assert calc_input.top_down_inputs.target_segment_percentage.value == 51.1

    report = calc_service.generate_report(calc_input)
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    expected_sam = 14_800_000_000.0 * 0.511  # $7,562,800,000.0
    assert pytest.approx(report.top_down_sam.estimate, rel=1e-3) == expected_sam
    assert 0 <= report.top_down_sam.estimate <= report.top_down_tam.estimate


# ---------------------------------------------------------------------------
# Test 8: Missing SAM evidence producing INSUFFICIENT_EVIDENCE
# ---------------------------------------------------------------------------
def test_invariant_8_missing_sam_evidence_produces_insufficient_evidence():
    calc_service = CalculationService()

    tam_ev = EvidenceInput(
        name="India pet care market",
        value=14_800_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(macro_market_size=tam_ev),
        target_geography="India",
        target_year=2025,
    )

    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 14_800_000_000.0
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None


# ---------------------------------------------------------------------------
# Test 9: Missing SOM evidence producing INSUFFICIENT_EVIDENCE
# ---------------------------------------------------------------------------
def test_invariant_9_missing_som_evidence_produces_insufficient_evidence():
    calc_service = CalculationService()

    tam_ev = EvidenceInput(
        name="India pet care market",
        value=14_800_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    sam_seg = EvidenceInput(
        name="Service transactions segment",
        value=51.1,
        unit="%",
        geography="India",
    )

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=tam_ev,
            target_segment_percentage=sam_seg,
            obtainable_market_share=None,  # Missing SOM share
        ),
        target_geography="India",
        target_year=2025,
    )

    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_som.estimate is None


# ---------------------------------------------------------------------------
# Test 10: Valid obtainable-share evidence producing SOM (0 <= SOM <= SAM <= TAM)
# ---------------------------------------------------------------------------
def test_invariant_10_valid_obtainable_share_produces_som_with_funnel_invariants():
    calc_service = CalculationService()

    tam_ev = EvidenceInput(
        name="India pet care market",
        value=14_800_000_000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
    )
    sam_seg = EvidenceInput(
        name="Service transactions segment",
        value=51.1,
        unit="%",
        geography="India",
    )
    som_share = EvidenceInput(
        name="Year 3 platform obtainable market share",
        value=2.5,
        unit="%",
        geography="India",
    )

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=tam_ev,
            target_segment_percentage=sam_seg,
            obtainable_market_share=som_share,
        ),
        target_geography="India",
        target_year=2025,
    )

    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    assert report.top_down_som.status == CalculationStatus.CALCULATED

    tam_val = report.top_down_tam.estimate
    sam_val = report.top_down_sam.estimate
    som_val = report.top_down_som.estimate

    expected_sam = 14_800_000_000.0 * 0.511
    expected_som = expected_sam * 0.025  # 2.5% of SAM = $189,070,000.0

    assert pytest.approx(tam_val, rel=1e-3) == 14_800_000_000.0
    assert pytest.approx(sam_val, rel=1e-3) == expected_sam
    assert pytest.approx(som_val, rel=1e-3) == expected_som

    # Strict Funnel Invariant: 0 <= SOM <= SAM <= TAM
    assert 0 <= som_val <= sam_val <= tam_val
