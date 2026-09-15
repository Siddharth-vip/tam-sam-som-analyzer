import pytest
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.orchestration.models import PipelineRequest
from app.schemas.calculation import CalculationStatus
from app.schemas.extraction import ExtractedEvidenceCandidate, MarketMetricType
from app.services.calculation_service import CalculationService
from app.services.validation_service import EvidenceValidationService


def test_promotional_discount_and_urbanization_rejected_for_sam():
    """
    Regression test:
    1. Promotional store discounts ("save 35%", "save 20%") must NOT be accepted as SAM narrowing factors.
    2. Demographic urbanization rates ("urbanization rate of nearly 48%") must NOT be accepted as target customer segment percentages.
    3. Generic metric name 'market share / segment percentage' must NOT trigger false positive segment intent.
    4. When no valid SAM narrowing evidence exists, SAM must remain INSUFFICIENT_EVIDENCE.
    """
    pipeline = MarketAnalysisPipeline()
    val_service = EvidenceValidationService()
    calc_service = CalculationService()

    # 1. Macro TAM Candidate
    tam_cand = ExtractedEvidenceCandidate(
        metric="India pet care market",
        metric_type=MarketMetricType.MARKET_SIZE,
        value=4_300_000_000.0,
        unit="USD",
        geography="India",
        year=2025,
        source_name="Ken Research",
        source_url="https://example.com/pet-market",
        source_context="The India Pet Market worth USD 4,300 million in 2025.",
    )

    # 2. Promotional store discount candidate
    discount_cand = ExtractedEvidenceCandidate(
        metric="market share / segment percentage",
        metric_type=MarketMetricType.MARKET_SHARE,
        value=35.0,
        unit="%",
        geography=None,
        year=None,
        source_name="Report Store",
        source_url="https://example.com/store",
        source_context="10 reports • save 35% on your next purchase",
    )

    # 3. Demographic urbanization candidate
    urban_cand = ExtractedEvidenceCandidate(
        metric="market share / segment percentage",
        metric_type=MarketMetricType.MARKET_SHARE,
        value=48.0,
        unit="%",
        geography="India",
        year=2025,
        source_name="Demographics Study",
        source_url="https://example.com/urban",
        source_context="Tamil Nadu has an urbanization rate of nearly 48%.",
    )

    tri_res = val_service.triangulate_evidence([tam_cand, discount_cand, urban_cand])
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = pipeline._build_calculation_inputs(
        analysis=None,
        validated_items=tri_res.validated_items,
        request=req,
    )

    # Discounts and urbanization rates must be rejected
    assert calc_input.top_down_inputs.target_segment_percentage is None
    assert calc_input.top_down_inputs.serviceable_geography_percentage is None

    # TAM must calculate, SAM must safely be INSUFFICIENT_EVIDENCE
    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 4_300_000_000.0
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None
