import sys
import os
sys.path.insert(0, os.path.abspath("."))
from app.schemas.business import BusinessAnalysis
from app.schemas.extraction import ExtractedEvidenceCandidate, ExtractionRequest
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.orchestration.models import PipelineRequest
from app.fetching.models import FetchedSource, FetchStatus
from app.schemas.discovery import SourceCategory, SourceQualityTier, DiscoveryLifecycleStage

raw_text_2 = (
    "The total tutoring and supplemental education market in India reached USD 1.8 billion in 2024. "
    "Average student annual subscription price is $45 per student per year. "
    "In comparison, the tutoring market in China reached $12 billion in 2024. "
    "EdTech sector is growing at a compound annual growth rate CAGR of 15.4% through 2028. "
    "Demographic survey shows 52% of high school students are male and 48% are female. "
    "Secondary and high-school tutoring (grades 9-12) accounts for 28% of the tutoring market in India. "
    "Discount promotions of 30% are common during back-to-school season."
)

doc = FetchedSource(
    original_url="https://edtechindia.org/reports/k12-tutoring-2024",
    final_url="https://edtechindia.org/reports/k12-tutoring-2024",
    title="India K-12 Tutoring & EdTech Market Report 2024",
    raw_content=raw_text_2,
    extracted_text=raw_text_2,
    content=raw_text_2,
    fetch_status=FetchStatus.SUCCESS,
    status_code=200,
    content_length=len(raw_text_2),
    category=SourceCategory.INDUSTRY_ANALYST,
    source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
    lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
)

ext_svc = EvidenceExtractionService()
val_svc = EvidenceValidationService()
pipe = MarketAnalysisPipeline()

req = PipelineRequest(
    business_idea="High-school online tutoring and test prep platform for students in India",
    target_geography="India",
    target_year=2024,
)

analysis = BusinessAnalysis(
    business_idea="High-school online tutoring and test prep platform for students in India",
    product="High-school tutoring platform",
    industry="Education / Online Tutoring",
    target_customer="High-school students",
    geography="India",
    pricing_model="Monthly subscription",
    business_model="B2C EdTech",
)

candidates = ext_svc.extract_evidence_from_source(ExtractionRequest(source=doc)).candidates
tri_res = val_svc.triangulate_evidence(candidates, business_analysis=analysis)
val_items = tri_res.validated_items

print("Validated candidates:")
for v in val_items:
    print(f"Candidate: {v.metric} | {v.value} {v.unit} | geo: {v.geography} | context: {v.source_context}")

calc_inputs = pipe._build_calculation_inputs(analysis, val_items, req)
print("\nTopDown inputs:")
print("Macro:", calc_inputs.top_down_inputs.macro_market_size if calc_inputs.top_down_inputs else None)
print("Segment %:", calc_inputs.top_down_inputs.segment_percentages if calc_inputs.top_down_inputs else None)
print("Target %:", calc_inputs.top_down_inputs.target_segment_percentage if calc_inputs.top_down_inputs else None)
print("Geo %:", calc_inputs.top_down_inputs.serviceable_geography_percentage if calc_inputs.top_down_inputs else None)
