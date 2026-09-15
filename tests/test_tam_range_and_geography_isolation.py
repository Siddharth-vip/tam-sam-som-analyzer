"""Regression tests for TAM range accuracy, unit-economics classification, and proximate geography isolation."""

import pytest
from app.schemas.calculation import CalculationInput, CalculationStatus, EvidenceInput
from app.schemas.discovery import SourceQualityTier
from app.schemas.extraction import MarketMetricType
from app.schemas.pipeline import PipelineRequest
from app.services.calculation_service import CalculationService
from app.services.extraction_service import EvidenceExtractionService
from app.services.orchestration_service import OrchestrationService
from app.services.validation_service import EvidenceValidationService
from app.orchestration.pipeline import MarketAnalysisPipeline


def test_per_companion_pet_spending_not_macro_tam():
    """TEST A: 'USD 93.7 per companion pet' is classified as unit economics (pricing/ARPU), NOT macro market size."""
    extractor = EvidenceExtractionService()
    sentence = "Modeled annual expenditure rises from USD 93.7 per companion pet in 2025 to USD 167.0 by 2032."
    candidates = extractor.extract_candidates_from_sentence(sentence, source_url="https://kenresearch.com/report")

    assert len(candidates) >= 1
    cand_937 = next((c for c in candidates if c.value == 93.7), None)
    assert cand_937 is not None
    assert cand_937.metric_type in (MarketMetricType.AVERAGE_PRICE, MarketMetricType.ANNUAL_SPEND, MarketMetricType.SUBSCRIPTION_PRICE)
    assert cand_937.metric != "market size / revenue"
    assert cand_937.metric_type != MarketMetricType.MARKET_SIZE


def test_comparative_country_values_isolate_geography():
    """TEST B: 'China's USD 43,400 million' extracts geography as 'China', NOT 'India'."""
    extractor = EvidenceExtractionService()
    sentence = "India ranks 2nd among the selected peers at USD 4,300 million in 2025, trailing China's USD 43,400 million but exceeding Indonesia and Thailand at about USD 2,500 million each."
    candidates = extractor.extract_candidates_from_sentence(sentence, source_url="https://kenresearch.com/report")

    cand_china = next((c for c in candidates if c.value == 43400000000.0), None)
    assert cand_china is not None
    assert cand_china.geography == "China"
    assert cand_china.geography != "India"

    cand_india = next((c for c in candidates if c.value == 4300000000.0), None)
    assert cand_india is not None
    assert cand_india.geography == "India"


def test_tam_triangulation_range_excludes_micro_and_foreign_values():
    """TEST C: Macro TAM candidate bounds exclude sub-million micro economics and foreign market values."""
    extractor = EvidenceExtractionService()
    validator = EvidenceValidationService()
    pipeline = MarketAnalysisPipeline()

    s1 = "The India pet care products market size increased from USD 8.6 Billion in 2025 to USD 9.2 Billion in 2026."
    s2 = "Modeled annual expenditure rises from USD 93.7 per companion pet in 2025."
    s3 = "India ranks 2nd at USD 4,300 million in 2025, trailing China's USD 43,400 million."

    cands_1 = extractor.extract_candidates_from_sentence(s1, "https://imarcgroup.com")
    cands_2 = extractor.extract_candidates_from_sentence(s2, "https://kenresearch.com")
    cands_3 = extractor.extract_candidates_from_sentence(s3, "https://kenresearch.com")

    all_cands = cands_1 + cands_2 + cands_3
    tri_res = validator.triangulate_evidence(all_cands)

    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(None, tri_res.validated_items, req)

    # TAM macro input must be valid macro market size
    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.macro_market_size is not None
    macro_input = calc_input.top_down_inputs.macro_market_size
    assert macro_input.value >= 1_000_000_000.0  # $8.6B or $4.3B

    # TAM range bounds must NEVER contain $93.7 or $43.4B (China)
    if macro_input.range_min is not None:
        assert macro_input.range_min >= 1_000_000.0
        assert macro_input.range_min != 93.7
    if macro_input.range_max is not None:
        assert macro_input.range_max <= 15_000_000_000.0  # reasonable India bounds, never China's $43.4B


def test_valid_india_tam_candidate_remains_usable():
    """TEST D: Valid India $8.6B candidate is selected and produces correct calculation."""
    from app.schemas.calculation import TopDownCalculationInputs
    calc_service = CalculationService()

    tam_ev = EvidenceInput(
        name="market size / revenue",
        value=8600000000.0,
        unit="USD",
        currency="USD",
        year=2025,
        geography="India",
        source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
        range_min=4300000000.0,
        range_max=9200000000.0,
    )

    calc_input = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(macro_market_size=tam_ev),
        target_geography="India",
        target_year=2025,
    )

    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam is not None
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 8600000000.0
    assert report.top_down_tam.interval.lower == 4300000000.0
    assert report.top_down_tam.interval.upper == 9200000000.0
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None
