import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.classification import (
    B2BSaaSClassification,
    ClassificationStatus,
)
from app.services.classification_service import (
    B2BSaaSClassificationService,
    get_classification_service,
)
from app.taxonomy.b2b_saas import (
    B2B_SAAS_TAXONOMY,
    get_all_categories,
    get_category_by_id,
    normalize_category_name,
)


class TestB2BSaaSTaxonomy:
    """Test Centralized B2B SaaS Taxonomy and Normalization."""

    def test_canonical_taxonomy_has_all_required_categories(self):
        """Ensure all canonical categories exist in taxonomy."""
        categories = get_all_categories()
        assert len(categories) >= 20
        
        required_ids = [
            "crm_sales",
            "hr_workforce",
            "accounting_finance",
            "project_task_management",
            "marketing_automation",
            "customer_support_helpdesk",
            "erp_operations",
            "procurement_supply_chain",
            "cybersecurity",
            "it_management_itsm",
            "collaboration_communication",
            "legal_compliance",
            "data_analytics_bi",
            "developer_tools",
            "productivity_workflow_automation",
            "ecommerce_retail_operations",
            "education_learning_management",
            "healthcare_business_software",
            "real_estate_property_management",
            "construction_field_service",
            "logistics_transportation",
            "vertical_saas",
            "other_b2b_saas",
        ]
        for cat_id in required_ids:
            cat = get_category_by_id(cat_id)
            assert cat is not None, f"Missing category: {cat_id}"
            assert len(cat.typical_use_cases) > 0
            assert len(cat.typical_buyers) > 0

    def test_category_normalization_synonyms(self):
        """Verify various synonyms normalize to canonical taxonomy categories."""
        # CRM synonyms
        assert normalize_category_name("CRM").category_id == "crm_sales"
        assert normalize_category_name("Customer Relationship Management").category_id == "crm_sales"
        assert normalize_category_name("Sales CRM").category_id == "crm_sales"
        assert normalize_category_name("Sales Automation").category_id == "crm_sales"
        assert normalize_category_name("RevOps").category_id == "crm_sales"

        # HR synonyms
        assert normalize_category_name("HRMS").category_id == "hr_workforce"
        assert normalize_category_name("HRIS").category_id == "hr_workforce"
        assert normalize_category_name("Human Resources").category_id == "hr_workforce"
        assert normalize_category_name("Payroll Software").category_id == "hr_workforce"
        assert normalize_category_name("Applicant Tracking System").category_id == "hr_workforce"

        # Finance synonyms
        assert normalize_category_name("Invoicing").category_id == "accounting_finance"
        assert normalize_category_name("Expense Management").category_id == "accounting_finance"
        assert normalize_category_name("Accounting & Finance").category_id == "accounting_finance"

        # Project Management
        assert normalize_category_name("Project Management").category_id == "project_task_management"
        assert normalize_category_name("Task Management").category_id == "project_task_management"

        # Developer Tools
        assert normalize_category_name("DevOps").category_id == "developer_tools"
        assert normalize_category_name("CI/CD").category_id == "developer_tools"
        assert normalize_category_name("Developer Tools").category_id == "developer_tools"

        # Cybersecurity
        assert normalize_category_name("SOC 2 Compliance").category_id == "cybersecurity"
        assert normalize_category_name("InfoSec").category_id == "cybersecurity"


class TestB2BSaaSClassificationScenarios:
    """Test B2B SaaS Semantic and Rule-Based Classification across Diverse Business Scenarios."""

    @pytest.fixture
    def classifier(self):
        return B2BSaaSClassificationService()

    @pytest.mark.asyncio
    async def test_scenario_a_crm_saas(self, classifier):
        """Scenario A: CRM SaaS -> B2B SaaS, CRM & Sales."""
        idea = "Cloud CRM for small businesses to manage sales pipeline and leads."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "CRM & Sales"
        assert result.category_id == "crm_sales"
        assert result.customer_type == "B2B"
        assert result.provenance.data_type == "AI_CLASSIFIED"

    @pytest.mark.asyncio
    async def test_scenario_b_hr_payroll_saas(self, classifier):
        """Scenario B: HR & Payroll SaaS -> B2B SaaS, HR & Workforce Management."""
        idea = "Employee payroll and attendance platform for companies with 20-500 employees."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "HR & Workforce Management"
        assert result.category_id == "hr_workforce"
        assert result.customer_type == "B2B"

    @pytest.mark.asyncio
    async def test_scenario_c_accounting_finance_saas(self, classifier):
        """Scenario C: Accounting SaaS -> B2B SaaS, Accounting & Finance."""
        idea = "Cloud accounting and GST invoicing SaaS for small businesses."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "Accounting & Finance"
        assert result.category_id == "accounting_finance"

    @pytest.mark.asyncio
    async def test_scenario_d_project_management_saas(self, classifier):
        """Scenario D: Project Management -> B2B SaaS, Project & Task Management."""
        idea = "Project management software with agile sprint tracking for software development teams."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "Project & Task Management"
        assert result.category_id == "project_task_management"

    @pytest.mark.asyncio
    async def test_scenario_e_cybersecurity_saas(self, classifier):
        """Scenario E: Cybersecurity -> B2B SaaS, Cybersecurity."""
        idea = "Cloud security compliance platform automating SOC 2 and ISO 27001 for enterprises."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "Cybersecurity"
        assert result.category_id == "cybersecurity"

    @pytest.mark.asyncio
    async def test_scenario_f_healthcare_vertical_saas(self, classifier):
        """Scenario F: Healthcare Vertical SaaS -> B2B SaaS, Healthcare Business Software."""
        idea = "Practice management software and appointment scheduling for private dental clinics."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "B2B SaaS"
        assert result.classification_status == ClassificationStatus.IN_SCOPE
        assert result.category == "Healthcare Business Software"
        assert result.category_id == "healthcare_business_software"

    @pytest.mark.asyncio
    async def test_scenario_g_consumer_fitness_app_out_of_scope(self, classifier):
        """Scenario G: Consumer Fitness App -> OUT_OF_SCOPE / NON_B2B_SAAS."""
        idea = "Mobile fitness application for individual users to track home workouts and diet."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "NON_B2B_SAAS"
        assert result.classification_status == ClassificationStatus.OUT_OF_SCOPE
        assert result.customer_type == "B2C"
        assert "consumer" in result.reasoning.lower() or "individual" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_scenario_h_consumer_streaming_out_of_scope(self, classifier):
        """Scenario H: Consumer Streaming Platform -> OUT_OF_SCOPE / NON_B2B_SAAS."""
        idea = "Movie streaming platform for individual subscribers with on-demand video."
        result = await classifier.classify_business_idea(idea)
        
        assert result.sector == "NON_B2B_SAAS"
        assert result.classification_status == ClassificationStatus.OUT_OF_SCOPE
        assert result.customer_type == "B2C"

    @pytest.mark.asyncio
    async def test_scenario_i_ambiguous_concept(self, classifier):
        """Scenario I: Vague/ambiguous idea -> AMBIGUOUS status."""
        idea = "An AI platform."
        result = await classifier.classify_business_idea(idea)
        
        assert result.classification_status == ClassificationStatus.AMBIGUOUS
        assert result.sector_confidence < 0.60
        assert result.missing_information is not None
        assert len(result.missing_information) > 0

    @pytest.mark.asyncio
    async def test_provenance_and_data_type(self, classifier):
        """Classification must have epistemic provenance with data_type='AI_CLASSIFIED' and NOT 'LIVE_VERIFIED_SOURCE'."""
        idea = "Developer tools platform for automated API testing and CI/CD pipelines."
        result = await classifier.classify_business_idea(idea)
        
        assert result.provenance.data_type == "AI_CLASSIFIED"
        assert result.provenance.data_type != "LIVE_VERIFIED_SOURCE"
        assert result.provenance.confidence > 0.70

    @pytest.mark.asyncio
    async def test_multi_business_classification_is_dynamic(self, classifier):
        """Verify dynamic classification across 5 completely different B2B SaaS ideas."""
        businesses = [
            ("Customer support ticketing and chatbot platform for e-commerce stores", "Customer Support & Helpdesk"),
            ("Automated vendor procurement and purchase order approval software for enterprises", "Procurement & Supply Chain"),
            ("Construction jobsite management and subcontractor scheduling SaaS", "Construction & Field Service Management"),
            ("Fleet tracking and freight transportation management system (TMS) for trucking companies", "Logistics & Transportation Management"),
            ("Corporate learning management system (LMS) for employee training and compliance", "Education & Learning Management"),
        ]

        for idea, expected_cat in businesses:
            res = await classifier.classify_business_idea(idea)
            assert res.sector == "B2B SaaS"
            assert res.classification_status == ClassificationStatus.IN_SCOPE
            assert res.category == expected_cat, f"Expected {expected_cat}, got {res.category} for idea: {idea}"
