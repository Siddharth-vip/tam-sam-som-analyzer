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
import re

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

item = [v for v in val_items if v.value == 28.0][0]

unit_norm = (item.unit or "").strip().lower()
metric_name_lower = (item.metric or "").lower()
raw_expr_lower = (getattr(item, "raw_value_expression", "") or "").lower()
context_lower = (getattr(item, "source_context", "") or "").lower()
full_context_text = f"{metric_name_lower} {raw_expr_lower} {context_lower} {(item.source_name or '').lower()} {(item.source_url or '').lower()}"

print("unit_norm:", unit_norm)
print("metric_name_lower:", metric_name_lower)
print("context_lower:", context_lower)

target_cust_str = (analysis.target_customer or "").lower().strip() if analysis else ""
target_cust_words = [w for w in re.findall(r"\w+", target_cust_str) if len(w) > 3]
print("target_cust_words:", target_cust_words)

for w in target_cust_words:
    print(f"w='{w}' in context_lower: {w in context_lower}")
    for v in ("represent", "account", "share", "portion", "orders", "demand", "volume", "users", "customers", "market"):
        if v in context_lower:
            print(f"  v='{v}' in context_lower: True")

SPECIES_OR_DEMOGRAPHIC_TERMS = (
    "dogs dominate", "cats dominate", "dogs make up", "cats make up", "followed by cats",
    "dog population", "cat population", "male", "female", "gender ratio"
)
print("is_species_split:", any(k in context_lower for k in SPECIES_OR_DEMOGRAPHIC_TERMS))

GROWTH_OR_TREND_TERMS = (
    "cagr", "growth", "growing", "grown", "grew", "grow", "yoy", "year-on-year",
    "year on year", "compound annual", "compounded annual", "expanding", "expansion",
    "forecast period", "forecast to", "projected to grow", "annual increase", "rate of growth",
    "growth rate", "increased by", "decreased by", "grew by", "dropped by", "fell by",
    "delayed", "(+", "(-", "+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9",
    "-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"
)
print("is_growth_or_cagr:", any(k in metric_name_lower or k in raw_expr_lower or k in context_lower for k in GROWTH_OR_TREND_TERMS))

OPERATIONAL_TERMS = (
    "no-show", "no-shows", "no show", "no shows", "scheduling efficiency", "efficiency",
    "productivity", "streamline", "optimization", "optimize", "cost reduction",
    "reduce cost", "reduction", "savings", "save up to", "cut cost", "latency",
    "uptime", "accuracy", "error rate", "retention rate", "retention", "churn",
    "satisfaction", "nps", "csat", "margin", "profit margin", "operating margin",
    "gross margin", "ebitda", "discount", "tax rate", "roi", "interest rate",
    "inflation", "conversion rate", "click-through", "ctr", "bounce rate", "open rate",
    "save ", "save 20%", "save 25%", "save 30%", "save 35%", "save 40%", "save 50%",
    "reports • save", "free customization", "promo", "coupon", "voucher",
    "urbanization rate", "urbanisation rate", "literacy rate", "internet penetration",
    "smartphone penetration", "more efficient"
)
print("is_operational_metric:", any(k in metric_name_lower or k in raw_expr_lower or k in context_lower for k in OPERATIONAL_TERMS))
