import pytest
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService
from app.services.calculation_service import CalculationService
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.orchestration.models import PipelineRequest, PipelineStatus
from app.schemas.extraction import ExtractedEvidenceCandidate, MarketMetricType
from app.schemas.calculation import CalculationStatus

def test_pet_care_india_semantic_gating_and_no_double_narrowing():
    """
    Regression Test Case for:
    "Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India"
    
    Covers:
    A. India-specific TAM ($14.8B) must not receive India's global-share percentage (5.41%) again.
    B. Geographic share (5.41% of global market) converts Global TAM to India, but is NOT applied to an already India TAM.
    C. "North India accounted for 35% of the pet food market" must NOT be accepted as SAM narrowing evidence.
    D. If no valid SAM narrowing factor remains, SAM must be INSUFFICIENT_EVIDENCE.
    E. SOM must remain INSUFFICIENT_EVIDENCE without obtainable market-share evidence.
    F. Preserve protections: growth %, forecast years, and commodity tariffs must not corrupt customer counts or pricing.
    """
    extractor = EvidenceExtractionService()
    orchestrator = MarketAnalysisPipeline()
    val_service = EvidenceValidationService()
    calc_service = CalculationService()

    # 1. Extraction: 5.41% global share extracted as percentage
    snippet_1 = "India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market."
    cands_1 = extractor.extract_candidates_from_sentence(snippet_1, source_url="https://fortunebusinessinsights.com/pet-care", source_name="Fortune Business Insights")
    
    pct_cands = [c for c in cands_1 if c.unit == "%" and c.value == 5.41]
    assert len(pct_cands) >= 1, "5.41% candidate must be extracted"
    
    # 2. Extraction: 35% pet food market share
    snippet_2 = "North India accounted for a whopping 35% of the pet food market share in 2024."
    cands_2 = extractor.extract_candidates_from_sentence(snippet_2, source_url="https://unleashedbypurina.com/pet-food", source_name="Unleashed By Purina")
    food_cand = [c for c in cands_2 if c.value == 35.0]
    assert len(food_cand) >= 1

    # 3. Create realistic validated candidates
    india_tam_cand = ExtractedEvidenceCandidate(
        metric="India pet care market revenue",
        metric_type=MarketMetricType.MARKET_SIZE,
        value=14_800_000_000.0,
        unit="USD",
        geography="India",
        year=2025,
        source_name="Fortune Business Insights",
        source_url="https://fortunebusinessinsights.com/pet-care",
        source_context="India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market.",
    )
    
    global_share_cand = ExtractedEvidenceCandidate(
        metric="India share of the global market",
        metric_type=MarketMetricType.MARKET_SHARE,
        value=5.41,
        unit="%",
        geography="India",
        year=2025,
        source_name="Fortune Business Insights",
        source_url="https://fortunebusinessinsights.com/pet-care",
        source_context="India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market.",
    )

    pet_food_share_cand = ExtractedEvidenceCandidate(
        metric="North India pet food market share",
        metric_type=MarketMetricType.MARKET_SHARE,
        value=35.0,
        unit="%",
        geography="North India",
        year=2024,
        source_name="Unleashed By Purina",
        source_url="https://unleashedbypurina.com/pet-food",
        source_context="North India accounted for a whopping 35% of the pet food market share in 2024.",
    )

    tri_res = val_service.triangulate_evidence([india_tam_cand, global_share_cand, pet_food_share_cand])
    validated_items = tri_res.validated_items

    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    # 4. Build calculation inputs
    calc_input = orchestrator._build_calculation_inputs(
        analysis=None,
        validated_items=validated_items,
        request=req,
    )

    # Invariant A & B: India-specific TAM ($14.8B) must NOT receive 5.41% global share
    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.macro_market_size is not None
    assert calc_input.top_down_inputs.macro_market_size.value == 14_800_000_000.0
    assert calc_input.top_down_inputs.macro_market_size.geography == "India"
    assert calc_input.top_down_inputs.serviceable_geography_percentage is None, "Global-to-India 5.41% must not be applied to already-India TAM"

    # Invariant C: 35% North India pet food share must NOT be accepted as target_segment_percentage
    assert calc_input.top_down_inputs.target_segment_percentage is None, "Pet food share in North India must be rejected as SAM segment narrowing"

    # 5. Execute report calculation
    report = calc_service.generate_report(calc_input)

    # Invariant D: TAM is calculated ($14.8B), SAM is INSUFFICIENT_EVIDENCE
    assert report.top_down_tam is not None
    assert report.top_down_tam.status == CalculationStatus.CALCULATED
    assert report.top_down_tam.estimate == 14_800_000_000.0

    assert report.top_down_sam is not None
    assert report.top_down_sam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.top_down_sam.estimate is None

    # Invariant E: Top-down SOM is not calculated (or insufficient evidence) if SAM is insufficient evidence
    if report.top_down_som is not None:
        assert report.top_down_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
        assert report.top_down_som.estimate is None

    # 6. Final result construction
    final_res = orchestrator._build_final_result(
        pipeline_id="pipe_test_india_tam",
        request=req,
        status=PipelineStatus.COMPLETED,
        analysis=None,
        research_queries=[],
        discovered_sources=[],
        fetched_sources=[],
        extracted_candidates=[india_tam_cand, global_share_cand, pet_food_share_cand],
        validation_results=validated_items,
        tri_result=tri_res,
        calc_report=report,
        errors=[],
        warnings=[],
        audit_trail=[],
        started_at="2026-09-15T00:00:00Z",
    )

    assert final_res.tam.status == "calculated"
    assert final_res.tam.estimate == 14_800_000_000.0
    assert final_res.sam.status == "insufficient_evidence"
    assert final_res.sam.estimate is None
    assert final_res.som.status == "insufficient_evidence"
    assert final_res.som.estimate is None


def test_global_tam_with_geographic_conversion():
    """
    Test B (Global-to-India conversion):
    When TAM is explicitly Global ($29.5B USD), 5.41% converts Global TAM to India SAM:
    SAM = $29.5B * 5.41% = $1.59595B.
    """
    orchestrator = MarketAnalysisPipeline()
    val_service = EvidenceValidationService()
    calc_service = CalculationService()

    global_tam_cand = ExtractedEvidenceCandidate(
        metric="global pet care services market",
        metric_type=MarketMetricType.MARKET_SIZE,
        value=29_500_000_000.0,
        unit="USD",
        geography="Global",
        year=2025,
        source_name="Wise Guy Reports",
        source_url="https://wiseguyreports.com/pet-care",
        source_context="The Global Pet Care Services Market was valued at USD 29.5 Billion in 2025.",
    )

    global_share_cand = ExtractedEvidenceCandidate(
        metric="India share of global market",
        metric_type=MarketMetricType.MARKET_SHARE,
        value=5.41,
        unit="%",
        geography="India",
        year=2025,
        source_name="Fortune Business Insights",
        source_url="https://fortunebusinessinsights.com/pet-care",
        source_context="India’s market is projected to be one of the largest worldwide, with revenues accounting for USD 14.80 billion in 2025, representing roughly 5.41% of the global market.",
    )

    tri_res = val_service.triangulate_evidence([global_tam_cand, global_share_cand])
    req = PipelineRequest(
        business_idea="Online platform connecting pet owners with verified veterinarians, groomers, and pet-care providers in India",
        preferred_geography="India",
        preferred_year=2025,
    )

    calc_input = orchestrator._build_calculation_inputs(
        analysis=None,
        validated_items=tri_res.validated_items,
        request=req,
    )

    assert calc_input.top_down_inputs.macro_market_size.value == 29_500_000_000.0
    assert calc_input.top_down_inputs.macro_market_size.geography == "Global"
    assert calc_input.top_down_inputs.serviceable_geography_percentage.value == 5.41

    report = calc_service.generate_report(calc_input)
    assert report.top_down_tam.estimate == 29_500_000_000.0
    assert report.top_down_sam.status == CalculationStatus.CALCULATED
    expected_sam = 29_500_000_000.0 * 0.0541  # $1,595,950,000.0 (~$1.60B)
    assert pytest.approx(report.top_down_sam.estimate, rel=1e-3) == expected_sam
    assert report.top_down_sam.estimate < report.top_down_tam.estimate
