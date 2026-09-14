import pytest
from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate, ExtractionMethod
from app.schemas.evidence import ConfidenceLevel
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceRelevanceScore,
    EvidenceValidationResult,
    EvidenceValidationStatus,
)
from app.services.validation_service import EvidenceValidationService

validation_service = EvidenceValidationService()

# Reference business idea analysis for test cases
SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS = BusinessAnalysis(
    business_idea="Affordable online programming platform for college students in India",
    industry="Education / EdTech / Online Learning",
    product="Online Programming Platform / Coding Education",
    target_customer="College Students / Undergraduates in India",
    geography="India",
    business_model="B2C / Subscription",
    pricing_model="Affordable Monthly/Annual Subscription",
)


def test_phone_numbers_rejected_with_audit_reason() -> None:
    """Rejection Rule 1: Phone numbers and toll-free helplines must be rejected with explicit category."""
    candidate = ExtractedEvidenceCandidate(
        metric="helpline contact number",
        value=1800123456.0,
        raw_value_expression="1800-123-456",
        unit="units",
        geography="India",
        year=2025,
        source_name="Sample Directory",
        source_url="https://example.com/contact",
        source_context="For inquiries or admissions, call our toll free helpline at 1800-123-456.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "NOISE_CONTACT_INFO"
    assert "phone number" in result.rejection_reason.lower() or "contact" in result.rejection_reason.lower()


def test_contact_info_and_postal_codes_rejected() -> None:
    """Rejection Rule 2: Email addresses, pin codes, and office addresses must be rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="pin code",
        value=600001.0,
        raw_value_expression="600001",
        unit="units",
        geography="India",
        year=2025,
        source_name="Corporate Registry",
        source_url="https://example.com/about",
        source_context="Registered office address: Chennai, Pin code: 600001. Email us at support@example.com.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "NOISE_CONTACT_INFO"


def test_navigation_and_menu_text_rejected() -> None:
    """Rejection Rule 3: Web boilerplate, cookie policies, and menu navigation text must be rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="terms and conditions",
        value=1.0,
        raw_value_expression="1",
        unit="units",
        geography="India",
        year=2025,
        source_name="Site Footer",
        source_url="https://example.com/policy",
        source_context="Home > Privacy Policy > Terms and Conditions. All rights reserved. Copyright 2025.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "NAVIGATION_TEXT"


def test_unrelated_retail_prices_rejected() -> None:
    """Rejection Rule 4: Isolated retail product prices (e.g. coffee, t-shirts, textbooks) must be rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="hoodie price",
        value=25.0,
        raw_value_expression="$25",
        unit="USD",
        geography="India",
        year=2025,
        source_name="Merchandise Store",
        source_url="https://example.com/store",
        source_context="Official university merchandise: campus hoodie price is $25 per hoodie.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "UNRELATED_PRICE"


def test_unrelated_industry_evidence_rejected() -> None:
    """Rejection Rule 5: Completely unrelated industry statistics (e.g. steel, automotive) must be rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="crude steel production",
        value=125.0,
        raw_value_expression="125 million tonnes",
        unit="million",
        geography="India",
        year=2025,
        source_name="Ministry of Steel",
        source_url="https://statistics.gov.in/steel-report",
        source_context="India crude steel production reached 125 million tonnes from blast furnace smelting plants in 2025.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "UNRELATED_INDUSTRY"
    assert result.relevance_breakdown.industry_match_score == 0.0


def test_geographic_mismatch_rejected() -> None:
    """Rejection Rule 6: Foreign country statistics when target is explicitly India must be rejected."""
    candidate = ExtractedEvidenceCandidate(
        metric="college students enrollment",
        value=20000000.0,
        raw_value_expression="20 million",
        unit="students",
        geography="United States",
        year=2025,
        source_name="National Center for Education Statistics",
        source_url="https://nces.ed.gov/fastfacts",
        source_context="Total college students enrolled in United States higher education institutions is 20 million in 2025.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.is_valid is False
    assert result.validation_status == EvidenceValidationStatus.REJECTED
    assert result.rejection_category == "GEOGRAPHY_MISMATCH"


def test_broad_parent_market_not_confused_with_direct_tam() -> None:
    """Validation Rule 7: Broad parent market (e.g. $313B India Education Market) is scored with low product match.

    It must have a high source quality & geography match, but low product match, preventing automated misclassification as narrow TAM.
    """
    candidate = ExtractedEvidenceCandidate(
        metric="India education market size",
        value=313000000000.0,
        raw_value_expression="$313 billion",
        unit="USD",
        geography="India",
        year=2025,
        source_name="IBEF Education Sector Report",
        source_url="https://ibef.org/industry/education-sector-india",
        source_context="India education market is expected to reach $313 billion by 2025 driven by primary, secondary, and higher education.",
    )

    result = validation_service.validate_candidate(candidate, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert result.relevance_breakdown is not None
    score = result.relevance_breakdown

    # Dimensional assertions
    assert score.source_quality_score >= 80.0
    assert score.geography_match_score == 100.0
    assert score.industry_match_score >= 70.0
    # Customer match is broad demographic, product match is low (broad parent market vs coding platform)
    assert score.product_match_score <= 45.0
    assert score.customer_match_score <= 50.0
    assert "Broad macro parent market" in score.dimensional_breakdown.get("product", "")


def test_directly_matching_evidence_accepted_with_high_relevance() -> None:
    """Validation Rule 8: Relevant, grounded evidence matching target geography, customer, and product is accepted."""
    cand1 = ExtractedEvidenceCandidate(
        metric="college students enrolled in India",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_name="Ministry of Education AISHE",
        source_url="https://education.gov.in/aishe-report-2025",
        source_context="According to AISHE 2025, there are 43 million college students enrolled in higher education in India.",
    )

    cand2 = ExtractedEvidenceCandidate(
        metric="online coding and programming education market size in India",
        value=2500000000.0,
        raw_value_expression="$2.5 billion",
        unit="USD",
        geography="India",
        year=2025,
        source_name="NASSCOM EdTech Research",
        source_url="https://nasscom.in/research/edtech-coding-market-2025",
        source_context="The online coding education and programming platform market in India reached $2.5 billion in 2025.",
    )

    res1 = validation_service.validate_candidate(cand1, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)
    res2 = validation_service.validate_candidate(cand2, business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS)

    assert res1.is_valid is True
    assert res1.validation_status == EvidenceValidationStatus.VALID
    assert res1.relevance_score is not None and res1.relevance_score >= 70.0
    assert res1.relevance_breakdown.customer_match_score >= 90.0

    assert res2.is_valid is True
    assert res2.validation_status == EvidenceValidationStatus.VALID
    assert res2.relevance_score is not None and res2.relevance_score >= 75.0
    assert res2.relevance_breakdown.product_match_score >= 80.0


def test_triangulation_segregates_rejected_items_with_audit_trail() -> None:
    """Triangulation auditability: Rejected items are preserved in TriangulationResult.rejected_items without data loss."""
    valid_cand = ExtractedEvidenceCandidate(
        metric="college students in India",
        value=43000000.0,
        raw_value_expression="43 million",
        unit="students",
        geography="India",
        year=2025,
        source_name="AISHE",
        source_url="https://statistics.gov.in/aishe",
        source_context="43 million college students enrolled in India.",
    )

    rejected_phone = ExtractedEvidenceCandidate(
        metric="helpline contact",
        value=1800999999.0,
        raw_value_expression="1800-999-999",
        unit="units",
        geography="India",
        year=2025,
        source_name="Directory",
        source_url="https://example.com/helpline",
        source_context="Helpline phone: 1800-999-999 for inquiries.",
    )

    rejected_industry = ExtractedEvidenceCandidate(
        metric="coal mining extraction",
        value=800.0,
        raw_value_expression="800 million tonnes",
        unit="million",
        geography="India",
        year=2025,
        source_name="Mining Ministry",
        source_url="https://gov.in/coal-mining",
        source_context="India coal mining mineral extraction reached 800 million tonnes in 2025.",
    )

    tri_res = validation_service.triangulate_evidence(
        [valid_cand, rejected_phone, rejected_industry],
        business_analysis=SAMPLE_PROGRAMMING_PLATFORM_ANALYSIS,
    )

    assert tri_res.total_candidates_processed == 3
    # 1 valid item in verified / validated groups
    assert len(tri_res.duplicate_groups) == 1
    # 2 rejected items preserved in rejected_items
    assert len(tri_res.rejected_items) == 2
    rej_cats = [r.rejection_category for r in tri_res.rejected_items]
    assert "NOISE_CONTACT_INFO" in rej_cats
    assert "UNRELATED_INDUSTRY" in rej_cats
    # Check that rejection reasons are preserved
    for rej in tri_res.rejected_items:
        assert rej.rejection_reason is not None
        assert rej.relevance_score is not None
        assert rej.is_valid is False
