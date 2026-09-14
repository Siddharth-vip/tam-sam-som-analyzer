import pytest
from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationResult,
    EvidenceValidationStatus,
)
from app.services.validation_service import EvidenceValidationService
from app.services.calculation_service import CalculationService
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.orchestration.models import PipelineRequest

validation_service = EvidenceValidationService()

SAMPLE_ANALYSIS = BusinessAnalysis(
    business_idea="Affordable online programming platform for college students in India",
    industry="Education / EdTech / Online Learning",
    product="Online Programming Platform / Coding Education",
    target_customer="College Students / Undergraduates in India",
    geography="India",
    business_model="B2C / Subscription",
    pricing_model="Affordable Monthly/Annual Subscription",
)


def test_tier_1_government_source_scoring() -> None:
    """Tier 1: Government and national statistics sources receive top-tier authority scoring (>= 0.90)."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://education.gov.in/aishe-report-2024",
        source_name="Ministry of Education AISHE",
        year=2024,
        context="According to official AISHE 2024 census data, there are 43 million students enrolled.",
        raw_val="43 million",
    )

    assert tier == SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
    assert score >= 0.95
    assert any("Tier 1" in r for r in reasons)
    assert any("Official government" in r for r in reasons)


def test_tier_1_company_filing_and_annual_report_scoring() -> None:
    """Tier 1: Corporate regulatory filings (SEC 10-K, MCA, BSE annual reports) receive Tier 1 status."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://www.sec.gov/edgar/data/12345/annual-report-10k.html",
        source_name="Company SEC Form 10-K Annual Filing",
        year=2024,
        context="Audited annual filing reports annual subscription revenue of $45 million with 120,000 active customers.",
        raw_val="$45 million",
    )

    assert tier == SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
    assert score >= 0.92
    assert any("Tier 1" in r for r in reasons)
    assert any("annual report" in r.lower() or "regulatory filing" in r.lower() or "sec" in r.lower() for r in reasons)


def test_tier_1_industry_trade_association_scoring() -> None:
    """Tier 1: Official industry trade associations (e.g. NASSCOM, GSMA, CII) receive Tier 1 status."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://nasscom.in/research/edtech-skills-report-2025",
        source_name="NASSCOM Trade Association",
        year=2025,
        context="NASSCOM research survey of 500 tech institutions reports market size of $2.5 billion.",
        raw_val="$2.5 billion",
    )

    assert tier == SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
    assert score >= 0.88
    assert any("Tier 1" in r for r in reasons)


def test_tier_2_market_research_firm_scoring() -> None:
    """Tier 2: Established research firms (Gartner, IDC, Statista, Forrester) receive Tier 2 (0.75 - 0.89)."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://statista.com/outlook/edtech/india",
        source_name="Statista Market Insights",
        year=2024,
        context="Statista industry report estimates online coding education market in India is $1.8 billion.",
        raw_val="$1.8 billion",
    )

    assert tier == SourceQualityTier.TIER_2_ACADEMIC_TRADE
    assert 0.78 <= score <= 0.90
    assert any("Tier 2" in r for r in reasons)


def test_tier_2_consulting_and_financial_institution_scoring() -> None:
    """Tier 2: Recognized consulting firms (McKinsey, Bain, BCG) and major banks receive Tier 2 status."""
    score1, _, tier1 = validation_service.score_source_quality(
        url="https://mckinsey.com/industries/education/our-insights/future-of-higher-education",
        source_name="McKinsey & Company",
        year=2024,
        context="McKinsey survey of higher education trends indicates 35% adoption.",
        raw_val="35%",
    )
    score2, _, tier2 = validation_service.score_source_quality(
        url="https://goldmansachs.com/insights/pages/edtech-global-market-outlook.html",
        source_name="Goldman Sachs Equity Research",
        year=2024,
        context="Goldman Sachs investment research estimates market revenue of $12 billion.",
        raw_val="$12 billion",
    )

    assert tier1 == SourceQualityTier.TIER_2_ACADEMIC_TRADE
    assert tier2 == SourceQualityTier.TIER_2_ACADEMIC_TRADE
    assert score1 >= 0.80
    assert score2 >= 0.78


def test_tier_2_academic_peer_reviewed_research_scoring() -> None:
    """Tier 2: Academic repositories (.edu, .ac.in, arXiv, Springer) receive Tier 2 status."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://iitm.ac.in/research/edtech-survey-2024.pdf",
        source_name="IIT Madras Research Department",
        year=2024,
        context="Peer-reviewed survey with sample size n=1200 students reveals 48% study programming online.",
        raw_val="48%",
    )

    assert tier == SourceQualityTier.TIER_2_ACADEMIC_TRADE
    assert score >= 0.85
    assert any("Tier 2" in r for r in reasons)
    assert any("Academic" in r or "peer-reviewed" in r for r in reasons)


def test_tier_3_reputable_news_article_scoring() -> None:
    """Tier 3: Reputable mainstream financial and business press receives Tier 3 (0.55 - 0.74)."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://livemint.com/industry/edtech-growth-in-india-2024",
        source_name="Livemint Financial Daily",
        year=2024,
        context="According to industry estimates reported by Livemint, Indian coding bootcamps reached $1.2B.",
        raw_val="$1.2B",
    )

    assert tier == SourceQualityTier.TIER_3_ANALYST_PRESS
    assert 0.55 <= score <= 0.74
    assert any("Tier 3" in r for r in reasons)


def test_tier_4_generic_blog_scoring() -> None:
    """Tier 4: Generic blogs and self-published articles receive Tier 4 (0.30 - 0.54)."""
    score, reasons, tier = validation_service.score_source_quality(
        url="https://medium.com/@randomauthor/top-10-reasons-edtech-is-growing-in-2024",
        source_name="Medium Blog Post",
        year=2024,
        context="In my opinion as a blogger, the market size is around $500 million.",
        raw_val="$500 million",
    )

    assert tier == SourceQualityTier.TIER_4_GENERAL_UNVERIFIED
    assert 0.30 <= score <= 0.54
    assert any("Tier 4" in r for r in reasons)


def test_tier_5_unusable_social_media_rejected() -> None:
    """Tier 5: Social media posts and discussion forums are classified as Tier 5 and strictly rejected."""
    # Reddit discussion
    cand_reddit = ExtractedEvidenceCandidate(
        metric="student population in India",
        value=50000000.0,
        raw_value_expression="50 million",
        unit="students",
        geography="India",
        year=2024,
        source_name="Reddit Discussion Thread",
        source_url="https://reddit.com/r/india/comments/abc123/student_count",
        source_context="Someone on reddit said there are probably 50 million students in college.",
    )

    # Twitter / X post
    cand_twitter = ExtractedEvidenceCandidate(
        metric="coding market size",
        value=10000000000.0,
        raw_value_expression="$10 billion",
        unit="USD",
        geography="India",
        year=2024,
        source_name="Twitter User Post",
        source_url="https://twitter.com/randomuser/status/987654321",
        source_context="I think the Indian EdTech market is easily $10 billion right now!",
    )

    # Quora answer
    cand_quora = ExtractedEvidenceCandidate(
        metric="annual course fee",
        value=5000.0,
        raw_value_expression="INR 5,000",
        unit="INR",
        geography="India",
        year=2024,
        source_name="Quora Answer",
        source_url="https://quora.com/how-much-do-students-pay",
        source_context="As a random user on Quora, I pay INR 5,000 per year.",
    )

    res_reddit = validation_service.validate_candidate(cand_reddit, business_analysis=SAMPLE_ANALYSIS)
    res_twitter = validation_service.validate_candidate(cand_twitter, business_analysis=SAMPLE_ANALYSIS)
    res_quora = validation_service.validate_candidate(cand_quora, business_analysis=SAMPLE_ANALYSIS)

    for res in (res_reddit, res_twitter, res_quora):
        assert res.is_valid is False
        assert res.validation_status == EvidenceValidationStatus.REJECTED
        assert res.rejection_category == "UNUSABLE_SOURCE"
        assert res.source_quality_tier == SourceQualityTier.TIER_5_UNUSABLE
        assert res.source_quality_score <= 0.25


def test_methodology_transparency_bonus_and_rumor_penalty() -> None:
    """Scoring correctly applies +0.05 bonus for transparent methodology and -0.15 penalty for speculative rumors."""
    # Source with transparent methodology
    score_methodology, reasons_m, _ = validation_service.score_source_quality(
        url="https://research-institute.org/survey-2024",
        source_name="Institute Survey",
        year=2024,
        context="Based on a rigorous methodology with a sample size of n=2500 respondents and margin of error +/-2%.",
        raw_val="2500",
    )
    assert any("Methodology transparency bonus" in r for r in reasons_m)

    # Source with unsubstantiated rumors
    score_rumor, reasons_r, _ = validation_service.score_source_quality(
        url="https://technewsblog.com/edtech-rumors",
        source_name="Tech Blog",
        year=2024,
        context="Rumor has it and unconfirmed reports claim that the market has grown to $50 billion without evidence.",
        raw_val="$50 billion",
    )
    assert any("Unsubstantiated claim penalty" in r for r in reasons_r)
    assert score_rumor < score_methodology


def test_duplicate_sources_handling_across_tiers() -> None:
    """Deduplication groups identical claims and identifies independent domains across tiers."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students in India",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2024,
        source_name="AISHE Portal",
        source_url="https://education.gov.in/aishe",
        source_context="Official AISHE report: 43 million students in India in 2024.",
    )
    cand2 = ExtractedEvidenceCandidate(
        metric="college students in India",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2024,
        source_name="Economic Times Coverage",
        source_url="https://economictimes.indiatimes.com/education/aishe-coverage",
        source_context="Citing AISHE data, 43 million students enrolled in higher education in India in 2024.",
    )

    tri = validation_service.triangulate_evidence([cand1, cand2], business_analysis=SAMPLE_ANALYSIS)

    assert tri.total_candidates_processed == 2
    assert len(tri.duplicate_groups) == 1
    assert tri.duplicate_groups[0].distinct_source_count == 2
    # Because one of the sources is Tier 1 (education.gov.in), corroboration elevates to VERIFIED
    assert len(tri.verified_items) == 1
    assert tri.verified_items[0].confidence == EvidenceConfidence.VERY_HIGH


def test_conflicting_sources_recorded_and_tier_weighted() -> None:
    """Conflicting sources reporting different numbers are detected, recorded in conflict group, and retain tier scores."""
    cand_gov = ExtractedEvidenceCandidate(
        metric="college students in India",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2024,
        source_name="AISHE Government",
        source_url="https://education.gov.in/aishe",
        source_context="Official census reports 43 million students in 2024.",
    )
    cand_blog = ExtractedEvidenceCandidate(
        metric="college students in India",
        value=85000000.0,
        raw_value_expression="85 million",
        unit="students",
        geography="India",
        year=2024,
        source_name="Random SEO Blog",
        source_url="https://medium.com/@blogger/india-students",
        source_context="In my blog, I claim there are 85 million students in India in 2024.",
    )

    tri = validation_service.triangulate_evidence([cand_gov, cand_blog], business_analysis=SAMPLE_ANALYSIS)

    assert len(tri.conflict_groups) == 1
    conflict = tri.conflict_groups[0]
    assert 43000000.0 in conflict.conflicting_values
    assert 85000000.0 in conflict.conflicting_values
    # Check that validated items reflect conflict status
    conflict_items = [i for i in tri.validated_items if i.validation_status == EvidenceValidationStatus.CONFLICT]
    assert len(conflict_items) >= 1


def test_weak_source_does_not_dominate_calculation_gate() -> None:
    """Authoritative Tier 1/Tier 2 evidence is chosen by calculation gate over Tier 4 weak blogs with inflated numbers."""
    pipeline = MarketAnalysisPipeline()

    # Tier 4 weak blog with inflated $500B claim
    blog_candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_blog_1",
        metric="India online education market size",
        value=500000000000.0,
        raw_value_expression="$500 billion",
        unit="USD",
        geography="India",
        year=2025,
        source_name="Generic Marketing Blog",
        source_url="https://medium.com/@marketing/edtech-huge-market",
        source_context="The online education market will reach $500 billion according to my blog post.",
    )
    # Tier 1 trade association with realistic $2.5B market size
    nasscom_candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_nasscom_1",
        metric="online coding education market size in India",
        value=2500000000.0,
        raw_value_expression="$2.5 billion",
        unit="USD",
        geography="India",
        year=2025,
        source_name="NASSCOM Industry Report",
        source_url="https://nasscom.in/research/edtech-market-2025",
        source_context="NASSCOM reports the online coding and programming education market in India reached $2.5 billion in 2025.",
    )

    val_blog = validation_service.validate_candidate(blog_candidate, business_analysis=SAMPLE_ANALYSIS)
    val_nasscom = validation_service.validate_candidate(nasscom_candidate, business_analysis=SAMPLE_ANALYSIS)

    req = PipelineRequest(business_idea="Affordable online programming platform for college students in India")

    # In construction of calculation inputs, NASSCOM (Tier 1) MUST be chosen over Blog (Tier 4)
    calc_input = pipeline._build_calculation_inputs(
        analysis=SAMPLE_ANALYSIS,
        validated_items=[val_blog, val_nasscom],
        request=req,
    )

    assert calc_input.top_down_inputs is not None
    assert calc_input.top_down_inputs.macro_market_size is not None
    # Must be NASSCOM's $2.5B, NOT Blog's $500B
    assert calc_input.top_down_inputs.macro_market_size.value == 2500000000.0
    assert calc_input.top_down_inputs.macro_market_size.source_name == "NASSCOM Industry Report"
