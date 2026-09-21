import pytest
from typing import Any, Dict, List

from app.orchestration.models import PipelineRequest, PipelineResult
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationStatus,
    DataType,
    EvidenceInput,
    PriceFrequency,
)
from app.schemas.classification import ClassificationStatus
from app.services.calculation_service import CalculationService
from app.services.classification_service import B2BSaaSClassificationService
from app.taxonomy.b2b_saas import (
    B2B_SAAS_TAXONOMY,
    get_all_categories,
    normalize_category_name,
)


@pytest.fixture
def classifier():
    return B2BSaaSClassificationService()


@pytest.fixture
def calc_service():
    return CalculationService()


@pytest.fixture
def pipeline():
    return MarketAnalysisPipeline()


class TestB2BSaaSCategoryCoverage:
    """Validate that the B2B SaaS taxonomy encompasses all required categories."""

    def test_taxonomy_contains_all_25_categories(self):
        categories = get_all_categories()
        cat_ids = {c.category_id for c in categories}

        required_categories = [
            "crm_sales",
            "hr_workforce",
            "accounting_finance",
            "erp_operations",
            "project_task_management",
            "marketing_automation",
            "customer_support_helpdesk",
            "cybersecurity",
            "legal_compliance",
            "healthcare_business_software",
            "education_learning_management",
            "logistics_transportation",
            "ecommerce_retail_operations",
            "fintech_saas",
            "procurement_supply_chain",
            "collaboration_communication",
            "data_analytics_bi",
            "it_management_itsm",
            "developer_tools",
            "real_estate_property_management",
            "construction_field_service",
            "manufacturing_operations",
            "hospitality_restaurant",
            "vertical_saas",
            "other_b2b_saas",
        ]

        for req in required_categories:
            assert req in cat_ids, f"Category '{req}' missing from B2B SaaS taxonomy"

    @pytest.mark.parametrize(
        "query,expected_cat_id",
        [
            ("Sales CRM platform", "crm_sales"),
            ("AI HRMS and payroll", "hr_workforce"),
            ("GST invoicing and accounting", "accounting_finance"),
            ("Cloud ERP for operations", "erp_operations"),
            ("Agile sprint and task tracker", "project_task_management"),
            ("Email marketing automation", "marketing_automation"),
            ("Customer helpdesk and ticketing", "customer_support_helpdesk"),
            ("SOC 2 compliance and endpoint security", "cybersecurity"),
            ("Contract lifecycle management CLM", "legal_compliance"),
            ("Dental clinic practice management", "healthcare_business_software"),
            ("School LMS and student portal", "education_learning_management"),
            ("Fleet telematics and TMS logistics", "logistics_transportation"),
            ("Retail POS and multichannel inventory", "ecommerce_retail_operations"),
            ("B2B payment gateway and invoice financing", "fintech_saas"),
            ("Vendor sourcing and procurement", "procurement_supply_chain"),
            ("Team chat and asynchronous video wiki", "collaboration_communication"),
            ("Data pipeline ETL and BI dashboards", "data_analytics_bi"),
            ("IT service desk ITSM and asset management", "it_management_itsm"),
            ("CI/CD pipeline and code observability", "developer_tools"),
            ("Tenant lease and property management", "real_estate_property_management"),
            ("Construction jobsite and field service dispatch", "construction_field_service"),
            ("MES plant floor and equipment maintenance", "manufacturing_operations"),
            ("Restaurant POS and hotel PMS", "hospitality_restaurant"),
        ],
    )
    def test_category_normalization_accuracy(self, query: str, expected_cat_id: str):
        matched = normalize_category_name(query)
        assert matched is not None, f"Failed to normalize '{query}'"
        assert matched.category_id == expected_cat_id, f"Expected '{expected_cat_id}', got '{matched.category_id}' for '{query}'"


class TestMultiCategoryClassification:
    """Test classification across 12 diverse B2B SaaS categories."""

    B2B_BENCHMARKS = [
        ("Cloud CRM platform for small and medium-sized businesses in India.", "CRM & Sales", "crm_sales"),
        ("AI-powered employee attendance, payroll and leave management SaaS for Indian SMEs.", "HR & Workforce Management", "hr_workforce"),
        ("Cloud accounting and GST invoicing software for small businesses.", "Accounting & Finance", "accounting_finance"),
        ("Collaborative project management SaaS for software development teams.", "Project & Task Management", "project_task_management"),
        ("Cloud-based endpoint security monitoring platform for SMBs.", "Cybersecurity", "cybersecurity"),
        ("Clinic appointment, billing and patient management SaaS.", "Healthcare Business Software", "healthcare_business_software"),
        ("Fleet tracking and logistics management SaaS for transport companies.", "Logistics & Transportation Management", "logistics_transportation"),
        ("School administration and student management SaaS.", "Education & Learning Management", "education_learning_management"),
        ("Cloud-based inventory and POS management platform for retail stores.", "E-commerce & Retail Operations", "ecommerce_retail_operations"),
        ("B2B procurement and vendor management SaaS for manufacturing companies.", "Procurement & Supply Chain", "procurement_supply_chain"),
        ("API monitoring and automated load testing SaaS for engineering teams.", "Developer Tools", "developer_tools"),
        ("Automated invoice financing and B2B receivables collection SaaS.", "FinTech & Payment SaaS", "fintech_saas"),
    ]

    @pytest.mark.parametrize("idea,expected_name,expected_id", B2B_BENCHMARKS)
    def test_rule_classification_across_categories(self, classifier, idea: str, expected_name: str, expected_id: str):
        res = classifier.classify_by_rules(idea)
        assert res.classification_status == ClassificationStatus.IN_SCOPE
        assert res.category_id == expected_id
        assert res.sector == "B2B SaaS"
        assert res.category_confidence >= 0.80
        assert res.provenance.confidence >= 0.80


class TestPricingNormalizationAndCalculations:
    """Verify deterministic TAM/SAM/SOM calculation across pricing models."""

    def test_annual_pricing_tam_sam_som(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Target Enterprises", value=10000, unit="enterprises"),
            pricing=EvidenceInput(name="Annual License", value=50000, unit="INR/enterprise/year", currency="INR"),
            pricing_basis="annual_subscription",
            pricing_frequency=PriceFrequency.ANNUAL,
            serviceable_customers=EvidenceInput(name="Serviceable Tier", value=3000, unit="enterprises"),
            realistically_obtainable_customers=EvidenceInput(name="Year 1 Obtainable", value=300, unit="enterprises"),
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        assert tam.status == CalculationStatus.CALCULATED
        assert tam.estimate == 10000 * 50000  # 50 Crore

        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        assert sam.status == CalculationStatus.CALCULATED
        assert sam.estimate == 3000 * 50000  # 15 Crore

        som = calc_service.calculate_bottom_up_som(sam, inputs)
        assert som.status == CalculationStatus.CALCULATED
        assert som.estimate == 300 * 50000  # 1.5 Crore

        # Check invariants
        assert tam.estimate >= sam.estimate >= som.estimate >= 0

    def test_monthly_pricing_normalization(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Target SMBs", value=5000, unit="smbs"),
            pricing=EvidenceInput(name="Monthly Plan", value=2000, unit="INR/month", currency="INR"),
            pricing_basis="monthly_subscription",
            pricing_frequency=PriceFrequency.MONTHLY,
            serviceable_customers=EvidenceInput(name="Serviceable Tier", value=1000, unit="smbs"),
            realistically_obtainable_customers=EvidenceInput(name="Obtainable Tier", value=100, unit="smbs"),
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        assert tam.status == CalculationStatus.CALCULATED
        # Monthly 2,000 * 12 = 24,000 annual ARPU * 5,000 = 120,000,000 (12 Crore)
        assert tam.estimate == 5000 * (2000 * 12)

        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        assert sam.estimate == 1000 * (2000 * 12)

        som = calc_service.calculate_bottom_up_som(sam, inputs)
        assert som.estimate == 100 * (2000 * 12)

    def test_per_seat_pricing_normalization(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Target Companies", value=2000, unit="companies"),
            pricing=EvidenceInput(name="Per User Monthly", value=500, unit="INR/user/month", currency="INR"),
            pricing_basis="per_seat",
            pricing_frequency=PriceFrequency.MONTHLY,
            users_per_organization=EvidenceInput(name="Avg Seats", value=20, unit="seats"),
            target_customer_percentage=EvidenceInput(name="Target Segment", value=40, unit="%"),
            obtainable_market_share=EvidenceInput(name="Target Share", value=5, unit="%"),
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        # Annual ARPU = 500 * 12 * 20 seats = 120,000 / org / year
        # TAM = 2000 orgs * 120,000 = 240,000,000
        assert tam.estimate == 2000 * (500 * 12 * 20)

        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        # SAM = 2000 * 0.40 * 120,000 = 96,000,000
        assert sam.estimate == (2000 * 0.4) * (500 * 12 * 20)

        som = calc_service.calculate_bottom_up_som(sam, inputs)
        # SOM = SAM * 0.05 = 4,800,000
        assert som.estimate == sam.estimate * 0.05


class TestFunnelInvariantsAndSafetyRules:
    """Verify invariant enforcement and zero-fabrication safety rules."""

    def test_serviceable_exceeding_potential_rejected(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Total Orgs", value=1000, unit="orgs"),
            pricing=EvidenceInput(name="Annual Price", value=10000, unit="INR"),
            serviceable_customers=EvidenceInput(name="Invalid Serviceable", value=1500, unit="orgs"),
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        assert sam.status == CalculationStatus.NOT_CALCULABLE
        assert "cannot exceed total addressable customer population" in sam.message

    def test_obtainable_exceeding_serviceable_rejected(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Total Orgs", value=1000, unit="orgs"),
            pricing=EvidenceInput(name="Annual Price", value=10000, unit="INR"),
            serviceable_customers=EvidenceInput(name="Serviceable", value=500, unit="orgs"),
            realistically_obtainable_customers=EvidenceInput(name="Invalid Obtainable", value=700, unit="orgs"),
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        som = calc_service.calculate_bottom_up_som(sam, inputs)
        assert som.status == CalculationStatus.NOT_CALCULABLE
        assert "cannot exceed serviceable customer population" in som.message

    def test_som_safety_rule_withholds_when_capacity_missing(self, calc_service):
        inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Total Orgs", value=1000, unit="orgs"),
            pricing=EvidenceInput(name="Annual Price", value=10000, unit="INR"),
            serviceable_customers=EvidenceInput(name="Serviceable", value=500, unit="orgs"),
            # Neither realistically_obtainable_customers nor obtainable_market_share provided
        )
        tam = calc_service.calculate_bottom_up_tam(inputs)
        sam = calc_service.calculate_bottom_up_sam(tam, inputs)
        som = calc_service.calculate_bottom_up_som(sam, inputs)
        assert som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
        assert som.estimate is None
        assert "SOM Safety Rule" in som.evidence_quality_reasons[0]


class TestNegativeScenarios:
    """Verify robust rejection of invalid inputs, consumer ideas, and negative values."""

    def test_consumer_app_classified_out_of_scope(self, classifier):
        consumer_ideas = [
            "Mobile fitness app for individual consumers to track daily workouts.",
            "Movie and video streaming subscription platform for individual users.",
            "Personal budget and expense wallet tracker app for individuals.",
            "Dating app for singles to meet new friends.",
        ]
        for idea in consumer_ideas:
            res = classifier.classify_by_rules(idea)
            assert res.classification_status == ClassificationStatus.OUT_OF_SCOPE
            assert res.sector == "NON_B2B_SAAS"

    def test_ambiguous_ideas_detected(self, classifier):
        res = classifier.classify_by_rules("An AI platform.")
        assert res.classification_status == ClassificationStatus.AMBIGUOUS
        assert res.sector_confidence < 0.60

    def test_negative_pricing_rejected(self):
        with pytest.raises(Exception):
            EvidenceInput(name="Negative Price", value=-500.0, unit="INR")

    def test_negative_customer_count_rejected(self):
        with pytest.raises(Exception):
            EvidenceInput(name="Negative Orgs", value=-100.0, unit="orgs")


class TestCrossBusinessIsolation:
    """Ensure consecutive pipeline executions do not leak state between distinct businesses."""

    def test_cross_business_calculation_isolation(self, calc_service):
        inputs1 = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="CRM SMBs", value=10000, unit="smbs"),
            pricing=EvidenceInput(name="CRM Annual Price", value=40000, unit="INR", currency="INR"),
            serviceable_customers=EvidenceInput(name="CRM Serviceable", value=3000, unit="smbs"),
            realistically_obtainable_customers=EvidenceInput(name="CRM Obtainable", value=300, unit="smbs"),
        )

        inputs2 = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Transport Fleets", value=5000, unit="fleets"),
            pricing=EvidenceInput(name="Fleet Annual Price", value=75000, unit="INR", currency="INR"),
            serviceable_customers=EvidenceInput(name="Fleet Serviceable", value=1000, unit="fleets"),
            realistically_obtainable_customers=EvidenceInput(name="Fleet Obtainable", value=100, unit="fleets"),
        )

        tam1 = calc_service.calculate_bottom_up_tam(inputs1)
        sam1 = calc_service.calculate_bottom_up_sam(tam1, inputs1)
        som1 = calc_service.calculate_bottom_up_som(sam1, inputs1)

        tam2 = calc_service.calculate_bottom_up_tam(inputs2)
        sam2 = calc_service.calculate_bottom_up_sam(tam2, inputs2)
        som2 = calc_service.calculate_bottom_up_som(sam2, inputs2)

        assert tam1.estimate == 400000000.0
        assert sam1.estimate == 120000000.0
        assert som1.estimate == 12000000.0

        assert tam2.estimate == 375000000.0
        assert sam2.estimate == 75000000.0
        assert som2.estimate == 7500000.0

        assert tam1.estimate != tam2.estimate
        assert sam1.estimate != sam2.estimate
        assert som1.estimate != som2.estimate
