import pytest
from app.fetching.models import FetchedSource
from app.schemas.extraction import ExtractionRequest, MarketMetricType
from app.services.extraction_service import EvidenceExtractionService
from app.services.validation_service import EvidenceValidationService


@pytest.fixture
def extraction_service() -> EvidenceExtractionService:
    return EvidenceExtractionService()


@pytest.fixture
def validation_service() -> EvidenceValidationService:
    return EvidenceValidationService()


# =========================================================================
# 1. ADVERSARIAL LISTICLE & HEADLINE PROTECTION TESTS
# =========================================================================

class TestAdversarialListicleRejection:
    """Verify that listicle counts, article headings, rankings, and non-market numbers

    are never falsely extracted as market population, customer counts, or market operands.
    """

    @pytest.mark.parametrize(
        "headline",
        [
            "6 Factors Propelling Small Medium Businesses in India",
            "10 Best CRM Platforms for High-Growth Startups in 2025",
            "Top 20 ERP Vendors for Manufacturing Enterprises",
            "7 Reasons Why Companies Are Adopting Cloud HR Software",
            "5 Trends Shaping Cybersecurity in 2025 and Beyond",
            "8 Challenges Facing Modern Logistics and Fleet Operators",
            "3 Key Pillars of Modern LegalTech and Contract Management",
            "12 Essential Tips for Optimizing DevOps Workflows",
            "4 Common Myths About Marketing Automation for SMBs",
            "5 Predictions for Generative AI in Healthcare SaaS",
            "Top 15 Tools Every Data Engineer Needs in 2025",
            "9 Key Strategies to Improve Customer Support Retention",
            "10 Simple Steps to Scale Your FinTech SaaS Platform",
            "14 Outstanding Frameworks for Real Estate Asset Management",
        ],
    )
    def test_listicle_headings_rejected(self, extraction_service: EvidenceExtractionService, headline: str):
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=headline,
            source_url="https://example.com/blog/trends",
            source_name="Industry Blog",
        )
        # Verify that no single-digit or listicle integer is extracted as a customer count or population
        for cand in candidates:
            assert cand.metric_type not in (
                MarketMetricType.CUSTOMER_COUNT,
                MarketMetricType.POPULATION,
                MarketMetricType.USERS,
                MarketMetricType.MARKET_SIZE,
            ), f"Listicle number unexpectedly extracted from headline '{headline}': {cand}"


# =========================================================================
# 2. MULTI-CATEGORY B2B SAAS EVIDENCE EXTRACTION TESTS (15+ CATEGORIES)
# =========================================================================

class TestUniversalCategoryExtraction:
    """Verify robust evidence extraction across 15+ canonical B2B SaaS categories."""

    def test_hr_workforce_management(self, extraction_service: EvidenceExtractionService):
        text = "India has 5.2 million registered MSMEs employing over 120 million workers across industrial hubs."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://msme.gov.in/annual-report",
            source_name="Ministry of MSME",
        )
        assert len(candidates) >= 1
        msme_cand = next((c for c in candidates if "msme" in (c.unit or "").lower() or "msme" in (c.metric or "").lower()), None)
        assert msme_cand is not None
        assert msme_cand.value == 5_200_000.0 or (msme_cand.is_range_or_approximate and msme_cand.range_min <= 5_200_000.0 <= msme_cand.range_max)
        assert msme_cand.geography == "India"

    def test_crm_and_sales(self, extraction_service: EvidenceExtractionService):
        text = "The US CRM market size reached USD 28.5 billion in 2024, with over 650,000 mid-market enterprises deploying sales automation."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://gartner.com/crm-market-2024",
            source_name="Gartner Research",
        )
        assert len(candidates) >= 1
        mkt_cand = next((c for c in candidates if c.metric_type == MarketMetricType.MARKET_SIZE), None)
        assert mkt_cand is not None
        assert mkt_cand.value == 28_500_000_000.0
        assert mkt_cand.unit == "USD"
        assert mkt_cand.geography == "United States"

    def test_cybersecurity_saas(self, extraction_service: EvidenceExtractionService):
        text = "Enterprise cybersecurity spending in India is projected to reach USD 3.8 billion by 2026."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://idc.com/india-cybersecurity-forecast",
            source_name="IDC",
        )
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.value == 3_800_000_000.0
        assert cand.metric_type == MarketMetricType.MARKET_SIZE
        assert cand.geography == "India"
        assert cand.year == 2026

    def test_erp_and_business_management(self, extraction_service: EvidenceExtractionService):
        text = "Over 180,000 manufacturing companies in Germany utilize cloud ERP software."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://statista.com/german-erp-market",
            source_name="Statista",
        )
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.value == 180_000.0 or (cand.is_range_or_approximate and cand.range_min <= 180_000.0 <= cand.range_max)
        assert cand.geography == "Germany"

    def test_fintech_and_accounting_saas(self, extraction_service: EvidenceExtractionService):
        text = "The global accounting software market was valued at USD 14.2 billion and is expanding at a CAGR of 11.4%."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://grandviewresearch.com/accounting-software",
            source_name="Grand View Research",
        )
        assert len(candidates) >= 2
        mkt_cand = next(c for c in candidates if c.metric_type == MarketMetricType.MARKET_SIZE)
        assert mkt_cand.value == 14_200_000_000.0
        cagr_cand = next(c for c in candidates if c.metric_type == MarketMetricType.GROWTH_RATE)
        assert cagr_cand.value == 11.4
        assert cagr_cand.unit == "%"

    def test_devops_and_developer_tools(self, extraction_service: EvidenceExtractionService):
        text = "There are 28 million active software developers globally utilizing CI/CD automation pipelines."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://slashdata.co/state-of-developers",
            source_name="SlashData",
        )
        assert len(candidates) >= 1
        dev_cand = candidates[0]
        assert dev_cand.value == 28_000_000.0 or (dev_cand.is_range_or_approximate and dev_cand.range_min <= 28_000_000.0 <= dev_cand.range_max)

    def test_edtech_saas(self, extraction_service: EvidenceExtractionService):
        text = "India has over 43 million college students enrolled across 52,000 higher education institutions."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://aishe.gov.in/report-2023",
            source_name="AISHE Ministry of Education",
        )
        assert len(candidates) >= 2
        stud_cand = next(c for c in candidates if "student" in (c.unit or "").lower() or "student" in (c.metric or "").lower())
        assert stud_cand.value == 43_000_000.0 or (stud_cand.is_range_or_approximate and stud_cand.range_min <= 43_000_000.0 <= stud_cand.range_max)

        inst_cand = next(c for c in candidates if "institution" in (c.unit or "").lower() or "institution" in (c.metric or "").lower())
        assert inst_cand.value == 52_000.0 or (inst_cand.is_range_or_approximate and inst_cand.range_min <= 52_000.0 <= inst_cand.range_max)

    def test_healthcare_saas(self, extraction_service: EvidenceExtractionService):
        text = "India operates 69,000 hospitals and 150,000 clinics adopting digital health infrastructure."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://mohfw.gov.in/infrastructure-census",
            source_name="Ministry of Health and Family Welfare",
        )
        assert len(candidates) >= 2
        hosp_cand = next(c for c in candidates if "hospital" in (c.unit or "").lower() or "hospital" in (c.metric or "").lower())
        assert hosp_cand.value == 69_000.0 or (hosp_cand.is_range_or_approximate and hosp_cand.range_min <= 69_000.0 <= hosp_cand.range_max)

        clinic_cand = next(c for c in candidates if "clinic" in (c.unit or "").lower() or "clinic" in (c.metric or "").lower())
        assert clinic_cand.value == 150_000.0 or (clinic_cand.is_range_or_approximate and clinic_cand.range_min <= 150_000.0 <= clinic_cand.range_max)

    def test_logistics_and_supply_chain(self, extraction_service: EvidenceExtractionService):
        text = "The commercial transport market spans 450,000 vehicles operating across the United Kingdom."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://gov.uk/vehicle-licensing-statistics",
            source_name="UK Department for Transport",
        )
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.value == 450_000.0 or (cand.is_range_or_approximate and cand.range_min <= 450_000.0 <= cand.range_max)
        assert cand.geography == "United Kingdom"

    def test_legaltech_saas(self, extraction_service: EvidenceExtractionService):
        text = "US law practices spent USD 1.6 billion on legal workflow software across 120,000 law firms."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://americanbar.org/legaltech-survey",
            source_name="American Bar Association",
        )
        assert len(candidates) >= 1
        mkt_cand = next((c for c in candidates if c.metric_type == MarketMetricType.MARKET_SIZE), None)
        assert mkt_cand is not None
        assert mkt_cand.value == 1_600_000_000.0
        assert mkt_cand.geography == "United States"

    def test_marketing_automation(self, extraction_service: EvidenceExtractionService):
        text = "Over 320,000 businesses in France deploy automated email and marketing platforms."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://insee.fr/enterprises-data",
            source_name="INSEE",
        )
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.value == 320_000.0 or (cand.is_range_or_approximate and cand.range_min <= 320_000.0 <= cand.range_max)
        assert cand.geography == "France"

    def test_customer_support_saas(self, extraction_service: EvidenceExtractionService):
        text = "The global customer service software market reached USD 11.8 billion with 18.2% annual growth."
        candidates = extraction_service.extract_candidates_from_sentence(
            sentence=text,
            source_url="https://forrester.com/customer-service-trends",
            source_name="Forrester",
        )
        assert len(candidates) >= 2
        mkt_cand = next(c for c in candidates if c.metric_type == MarketMetricType.MARKET_SIZE)
        assert mkt_cand.value == 11_800_000_000.0


# =========================================================================
# 3. METRIC DISAMBIGUATION & PRICING NORMALIZATION TESTS
# =========================================================================

class TestMetricDisambiguation:
    """Verify that macro market size ($2B), ARPU ($200/yr), population, and CAGR are cleanly distinguished."""

    def test_macro_market_size_vs_arpu(self, extraction_service: EvidenceExtractionService):
        # Macro market size: large value + macro multiplier + market context
        mkt_sentence = "The CRM software market reached USD 2.4 billion in 2024."
        cands_mkt = extraction_service.extract_candidates_from_sentence(
            sentence=mkt_sentence,
            source_url="https://example.com",
        )
        assert len(cands_mkt) == 1
        assert cands_mkt[0].metric_type == MarketMetricType.MARKET_SIZE
        assert cands_mkt[0].value == 2_400_000_000.0

        # Unit pricing / ARPU: smaller value + per user/unit context
        pricing_sentence = "Average pricing for SMB payroll software is USD 180 per year per employee."
        cands_price = extraction_service.extract_candidates_from_sentence(
            sentence=pricing_sentence,
            source_url="https://example.com",
        )
        assert len(cands_price) >= 1
        assert cands_price[0].metric_type in (
            MarketMetricType.AVERAGE_PRICE,
            MarketMetricType.ANNUAL_SPEND,
            MarketMetricType.SUBSCRIPTION_PRICE,
        )
        assert cands_price[0].value == 180.0
