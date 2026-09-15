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

raw_text_1 = (
    "The overall pet care market in India reached $800 million in 2024. "
    "Pet owners in India spend an average of $29.5 per customer annually on grooming items. "
    "The global pet care market was valued at $14.8 billion in 2024, with US market size at $8.2 billion. "
    "Pet care market in India is expanding at a CAGR of 19.2% per year. "
    "Furthermore, 65% of households in urban India own dogs rather than cats. "
    "Pet food products represent 70% of total pet care sales, while pet grooming and veterinary services account for 18% of the total pet care market in India."
)

doc = FetchedSource(
    original_url="https://marketresearch.in/pet-care-india-2024",
    final_url="https://marketresearch.in/pet-care-india-2024",
    title="India Pet Care Market Size & Services Overview",
    raw_content=raw_text_1,
    extracted_text=raw_text_1,
    content=raw_text_1,
    fetch_status=FetchStatus.SUCCESS,
    status_code=200,
    content_length=len(raw_text_1),
    category=SourceCategory.INDUSTRY_ANALYST,
    source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
    lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
)

ext_svc = EvidenceExtractionService()
val_svc = EvidenceValidationService()

analysis = BusinessAnalysis(
    business_idea="Online pet care and grooming service platform connecting pet owners with certified groomers across India",
    product="Pet care and grooming service platform",
    industry="Pet Care / Pet Services",
    target_customer="Urban pet owners",
    geography="India",
    pricing_model="Transaction fee / subscription",
    business_model="B2C Marketplace / Services",
)

candidates = ext_svc.extract_evidence_from_source(ExtractionRequest(source=doc)).candidates
tri_res = val_svc.triangulate_evidence(candidates, business_analysis=analysis)

for v in tri_res.validated_items:
    if v.value == 18.0:
        print("Candidate 18% metric:", v.metric)
        print("Candidate 18% context:", v.source_context)
        print("Candidate 18% raw_value_expression:", getattr(v, "raw_value_expression", ""))
