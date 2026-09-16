import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json
from pydantic import ValidationError

from app.schemas.business import (
    BusinessAnalysis,
    HealthcareCustomerType,
    HealthcareSaaSCategory,
    HealthcarePricingBasis,
)
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationMethod,
    CalculationStatus,
    DataType,
    EvidenceInput,
    MetricCalculationResult,
    TopDownCalculationInputs,
)
from app.schemas.pipeline import (
    PipelineRequest,
    PipelineResult,
    PipelineStatus,
    HealthcareMarketAttractiveness,
)
from app.services.calculation_service import CalculationService
from app.services.llm_service import OllamaLLMService
from app.orchestration.pipeline import MarketAnalysisPipeline
from app.schemas.validation import EvidenceValidationResult
from app.storage.database import init_db, get_db_connection
from app.storage.repository import AnalysisRepository


class TestHealthcareSaaSValidation:
    """Test Healthcare SaaS Input Validation Gate."""

    def test_valid_healthcare_saas_input(self):
        """A complete valid Healthcare SaaS input passes validation with zero missing fields."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="AI-powered clinic management and EHR SaaS for dental clinics in India",
            target_country="India",
            customer_type=HealthcareCustomerType.DENTAL_CLINICS,
            pricing_basis=HealthcarePricingBasis.PER_FACILITY,
            per_facility_price=36000.0,
            clinical_use=True,
            emr_ehr_integration_required=True,
        )
        missing = pipeline.validate_healthcare_input(req)
        assert len(missing) == 0

    def test_missing_business_idea(self):
        """Empty or whitespace-only business_idea must be rejected."""
        pipeline = MarketAnalysisPipeline()
        # Direct validation function test
        req = PipelineRequest.model_construct(
            business_idea="",
            target_country="India",
            customer_type="Clinics",
            pricing_basis="monthly_subscription",
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "business_idea" in missing

    def test_missing_target_country(self):
        """Missing target country / geography must be flagged."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Specialized radiology viewer for imaging clinics",
            target_country="",
            customer_type="Clinics",
            pricing_basis="annual_subscription",
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "target_country" in missing

    def test_missing_customer_type(self):
        """Missing customer type must be flagged."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Cloud billing software in India",
            target_country="India",
            customer_type="",
            pricing_basis="monthly_subscription",
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "customer_type" in missing

    def test_missing_pricing_basis(self):
        """Missing pricing basis must be flagged when no explicit pricing is given."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Hospital bed management software in India",
            target_country="India",
            customer_type="Hospitals",
            pricing_basis=None,
            pricing_model=None,
            monthly_price=None,
            annual_price=None,
            allow_estimated_pricing=False,
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "pricing_basis" in missing

    def test_non_clinical_healthcare_saas_without_clinical_fields(self):
        """Non-clinical operational SaaS (workforce, billing, inventory) must pass without clinical fields."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Healthcare nurse shift scheduling and workforce SaaS for private hospitals in India.",
            healthcare_saas_category=HealthcareSaaSCategory.HEALTHCARE_WORKFORCE,
            target_country="India",
            customer_type=HealthcareCustomerType.HOSPITALS,
            pricing_basis=HealthcarePricingBasis.PER_FACILITY,
            per_facility_price=50000.0,
            # No clinical_use or emr_ehr_integration_required provided
        )
        missing = pipeline.validate_healthcare_input(req)
        assert len(missing) == 0, f"Expected no missing fields for non-clinical SaaS, got: {missing}"

    def test_clinical_healthcare_saas_with_required_fields(self):
        """Clinical Healthcare SaaS with all required clinical/EMR fields passes validation."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Cloud dental practice management and digital charting SaaS for clinics in India.",
            healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
            target_country="India",
            customer_type=HealthcareCustomerType.DENTAL_CLINICS,
            pricing_basis=HealthcarePricingBasis.PER_FACILITY,
            per_facility_price=36000.0,
            clinical_use=True,
            emr_ehr_integration_required=True,
            regulatory_market="ABDM / NABH",
        )
        missing = pipeline.validate_healthcare_input(req)
        assert len(missing) == 0

    def test_ehr_emr_saas_missing_conditional_fields(self):
        """EHR/EMR SaaS requires clinical_use and emr_ehr_integration_required if not specified."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Electronic medical records SaaS for outpatient clinics in India.",
            healthcare_saas_category=HealthcareSaaSCategory.EHR_EMR,
            target_country="India",
            customer_type=HealthcareCustomerType.CLINICS,
            pricing_basis=HealthcarePricingBasis.MONTHLY_SUBSCRIPTION,
            monthly_price=5000.0,
            clinical_use=None,
            emr_ehr_integration_required=None,
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "clinical_use" in missing or "emr_ehr_integration_required" in missing

    def test_healthcare_ai_saas_missing_clinical_use(self):
        """Healthcare AI SaaS requires clinical_use specification."""
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="AI diagnostic decision support tool for hospitals in India.",
            healthcare_saas_category=HealthcareSaaSCategory.HEALTHCARE_AI,
            target_country="India",
            customer_type=HealthcareCustomerType.HOSPITALS,
            pricing_basis=HealthcarePricingBasis.ANNUAL_SUBSCRIPTION,
            annual_price=300000.0,
            clinical_use=None,
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "clinical_use" in missing

    def test_missing_critical_fields_rejected(self):
        pipeline = MarketAnalysisPipeline()
        # Request with vague non-healthcare text and no details
        req = PipelineRequest(
            business_idea="A generic software tool with no details provided",
            target_country="",
            customer_type="",
            pricing_basis=None,
            pricing_model="",
        )
        missing = pipeline.validate_healthcare_input(req)
        assert "target_country" in missing
        assert "customer_type" in missing
        assert "pricing_basis" in missing or "pricing_model" in missing

    @pytest.mark.asyncio
    async def test_incomplete_input_pipeline_response(self):
        pipeline = MarketAnalysisPipeline()
        req = PipelineRequest(
            business_idea="Just an idea without any specifics",
            target_country="",
            customer_type="",
            pricing_basis=None,
            pricing_model="",
        )
        result = await pipeline.run(req)
        assert result.status in (PipelineStatus.INCOMPLETE_INPUT, "incomplete_input", "INCOMPLETE_INPUT")
        assert len(result.missing_fields) > 0
        assert "target_country" in result.missing_fields


class TestHealthcareSaaSClassification:
    """Test Healthcare SaaS classification and taxonomy."""

    @pytest.mark.asyncio
    async def test_classification_dental_saas(self):
        service = OllamaLLMService()
        mock_response = {
            "industry": "Healthcare Information Technology",
            "healthcare_saas_category": "Clinic Management SaaS",
            "target_customer": "Dental Clinics",
            "customer_type": "Dental Clinics",
            "product": "Cloud Dental Imaging & Practice Management",
            "business_model": "B2B SaaS",
            "pricing_model": "per facility subscription",
            "pricing_basis": "per_facility",
            "per_facility_price": 36000,
            "target_country": "India",
            "clinical_or_non_clinical": "clinical",
            "regulatory_market": "ABDM / NABH",
            "customer_problem": "Fragmented dental imaging and paper charts",
            "value_proposition": "All-in-one cloud dental EMR with ABDM compliance",
        }

        with patch.object(service, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "message": {"content": json.dumps(mock_response)}
            }
            analysis = await service.analyze_business_idea("Cloud dental clinic management software in India")
            assert analysis.healthcare_saas_category == "Clinic Management SaaS"
            assert analysis.customer_type == HealthcareCustomerType.DENTAL_CLINICS
            assert analysis.target_country == "India"
            assert analysis.per_facility_price == 36000


class TestHealthcareSaaSCalculations:
    """Test Bottom-up TAM, SAM, SOM with derived percentages and scenarios."""

    def test_bottom_up_tam_calculation(self):
        calc_service = CalculationService()
        target_cust = EvidenceInput(
            name="Total Dental Clinics",
            metric="Number of dental clinics in India",
            value=50000,
            unit="clinics",
            data_type=DataType.SOURCED,
            source_name="Dental Council of India Survey",
            source_quality_tier="tier_1_official",
        )
        arpu = EvidenceInput(
            name="SaaS ARPU",
            metric="Annual SaaS subscription price per clinic",
            value=36000,
            unit="INR/year",
            data_type=DataType.SOURCED,
            source_name="Healthcare IT Pricing Index",
            source_quality_tier="tier_2_academic_trade",
        )

        inputs = BottomUpCalculationInputs(
            potential_customers=target_cust,
            pricing=arpu,
        )

        result = calc_service.calculate_bottom_up_tam(inputs)

        assert result.estimate == 50000 * 36000
        assert result.estimate == 1800000000  # 180 Crore INR
        assert result.status == CalculationStatus.CALCULATED

    def test_sam_calculation_and_percentage_derivation(self):
        calc_service = CalculationService()
        target_cust = EvidenceInput(
            name="Total Dental Clinics",
            metric="Number of dental clinics in India",
            value=50000,
            unit="clinics",
            data_type=DataType.SOURCED,
        )
        arpu = EvidenceInput(
            name="SaaS ARPU",
            metric="Annual SaaS subscription price per clinic",
            value=36000,
            unit="INR/year",
            data_type=DataType.SOURCED,
        )
        bu_inputs = BottomUpCalculationInputs(
            potential_customers=target_cust,
            pricing=arpu,
            target_customer_percentage=EvidenceInput(
                name="Digital Clinics %",
                metric="Clinics with digital hardware",
                value=25.0,
                unit="percentage",
                data_type=DataType.SOURCED,
            ),
        )

        tam_result = calc_service.calculate_bottom_up_tam(bu_inputs)
        sam_result = calc_service.calculate_bottom_up_sam(tam_result, bu_inputs)

        expected_sam = 1800000000 * 0.25
        assert sam_result.estimate == expected_sam  # 45 Crore INR
        assert sam_result.sam_percentage_of_tam == 25.0

    def test_som_calculation_with_scenarios_and_percentage_derivation(self):
        calc_service = CalculationService()
        target_cust = EvidenceInput(
            name="Total Dental Clinics",
            metric="Number of dental clinics in India",
            value=50000,
            unit="clinics",
        )
        arpu = EvidenceInput(
            name="SaaS ARPU",
            metric="Annual SaaS subscription price per clinic",
            value=36000,
            unit="INR/year",
        )
        bu_inputs = BottomUpCalculationInputs(
            potential_customers=target_cust,
            pricing=arpu,
            target_customer_percentage=EvidenceInput(
                name="Digital Clinics %",
                metric="Clinics with digital hardware",
                value=25.0,
                unit="percentage",
            ),
            obtainable_market_share=EvidenceInput(
                name="Target Share Year 1-3",
                metric="Capacity-based market share",
                value=4.0,
                unit="percentage",
            ),
        )

        tam_result = calc_service.calculate_bottom_up_tam(bu_inputs)
        sam_result = calc_service.calculate_bottom_up_sam(tam_result, bu_inputs)
        som_result = calc_service.calculate_bottom_up_som(sam_result, bu_inputs)

        expected_som = 450000000 * 0.04  # 1.8 Crore INR
        assert som_result.estimate == expected_som
        assert som_result.som_percentage_of_sam == 4.0
        assert som_result.som_scenarios is not None
        assert som_result.som_scenarios["base"] == expected_som
        assert som_result.som_scenarios["conservative"] < som_result.som_scenarios["base"]
        assert som_result.som_scenarios["optimistic"] > som_result.som_scenarios["base"]

    def test_top_down_vs_bottom_up_comparison(self):
        calc_service = CalculationService()
        bu_inputs = BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Clinics", metric="Clinics", value=50000, unit="clinics"),
            pricing=EvidenceInput(name="ARPU", metric="ARPU", value=36000, unit="INR"),
            target_customer_percentage=EvidenceInput(name="Target %", metric="Target %", value=50.0, unit="percentage"),
            obtainable_market_share=EvidenceInput(name="Share %", metric="Share %", value=10.0, unit="percentage"),
        )
        bu_tam = calc_service.calculate_bottom_up_tam(bu_inputs)
        bu_sam = calc_service.calculate_bottom_up_sam(bu_tam, bu_inputs)
        bu_som = calc_service.calculate_bottom_up_som(bu_sam, bu_inputs)

        td_inputs = TopDownCalculationInputs(
            macro_market_size=EvidenceInput(name="Macro Healthcare IT", metric="Market Size", value=2000000000, unit="INR"),
            target_segment_percentage=EvidenceInput(name="Segment %", metric="Segment %", value=50.0, unit="percentage"),
            obtainable_market_share=EvidenceInput(name="Share %", metric="Share %", value=10.0, unit="percentage"),
        )
        td_tam = calc_service.calculate_top_down_tam(td_inputs)
        td_sam = calc_service.calculate_top_down_sam(td_tam, td_inputs)
        td_som = calc_service.calculate_top_down_som(td_sam, td_inputs)

        comparison = calc_service.compare_methods(
            top_down_tam=td_tam,
            bottom_up_tam=bu_tam,
            top_down_sam=td_sam,
            bottom_up_sam=bu_sam,
            top_down_som=td_som,
            bottom_up_som=bu_som,
        )
        assert comparison is not None
        assert comparison.percentage_difference is not None
        assert comparison.divergence_severity is not None

    def test_invalid_pricing_and_customer_counts(self):
        # Strict validation rejects negative values
        with pytest.raises(ValidationError):
            EvidenceInput(name="Clinics", metric="Clinics", value=-10, unit="clinics")

    def test_som_derived_from_capacity_and_user_inputs(self):
        """SOM must dynamically adapt to user-provided acquisition targets or sales capacity."""
        pipeline = MarketAnalysisPipeline()
        analysis = BusinessAnalysis(
            business_idea="Hospital pharmacy inventory SaaS in India",
            healthcare_saas_category=HealthcareSaaSCategory.PHARMACY_MANAGEMENT,
            customer_type=HealthcareCustomerType.HOSPITALS,
            target_country="India",
            pricing_basis=HealthcarePricingBasis.PER_FACILITY,
            per_facility_price=120000.0,
            annual_revenue_per_customer=120000.0,
        )
        # Custom user acquisition capacity: 50 hospitals in Year 1-3
        req_with_user_target = PipelineRequest(
            business_idea="Hospital pharmacy inventory SaaS in India",
            healthcare_saas_category=HealthcareSaaSCategory.PHARMACY_MANAGEMENT,
            customer_type=HealthcareCustomerType.HOSPITALS,
            target_country="India",
            pricing_basis=HealthcarePricingBasis.PER_FACILITY,
            per_facility_price=120000.0,
            expected_customer_acquisition_annual=50.0,
        )

        validated_items = [
            EvidenceValidationResult(
                candidate_id="cand_hosp_1",
                source_url="https://mohfw.gov.in/registry",
                source_context="Official healthcare infrastructure census confirms 69,000 registered hospitals in India.",
                metric="Total Hospitals in India",
                value=69000.0,
                unit="hospitals",
                year=2024,
                geography="India",
                data_type=DataType.SOURCED.value,
            )
        ]

        report = pipeline._calculate_healthcare_market(analysis, validated_items, req_with_user_target)
        som = report.bottom_up_som
        assert som is not None
        assert som.estimate == 50.0 * 120000.0  # ₹60 Lakhs
        assert som.som_scenarios is not None
        assert som.som_scenarios["base"] == 50.0 * 120000.0
        assert som.som_scenarios["conservative"] == 25.0 * 120000.0


class TestHealthcareSaaSPipelineEndToEnd:
    """Test full Healthcare SaaS pipeline execution with SQLite run isolation."""

    @pytest.mark.asyncio
    async def test_full_pipeline_run_mock_provider(self):
        pipeline = MarketAnalysisPipeline()
        mock_analysis = {
            "industry": "Healthcare Information Technology",
            "healthcare_saas_category": "Clinic Management SaaS",
            "target_customer": "Dental Clinics",
            "customer_type": "Dental Clinics",
            "product": "Cloud Dental Imaging & Practice Management",
            "business_model": "B2B SaaS",
            "pricing_model": "per facility subscription",
            "target_country": "India",
        }

        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps(mock_analysis)}}

            req = PipelineRequest(
                business_name="DentisFlow Pro",
                business_idea="Cloud-based dental practice management and digital imaging SaaS for private clinics in India.",
                healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
                customer_type=HealthcareCustomerType.DENTAL_CLINICS,
                target_country="India",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=36000.0,
                clinical_or_non_clinical="clinical",
                regulatory_market="ABDM / NABH Compliant",
                emr_integration_required=True,
                enable_calculation=True,
            )

            result = await pipeline.run(req)

            # Verification of pipeline result structure
            assert result.status in ("completed", PipelineStatus.COMPLETED)
            assert result.pipeline_id is not None
            assert result.business_analysis is not None
            assert result.business_analysis.healthcare_saas_category in [HealthcareSaaSCategory.CLINIC_MANAGEMENT, "Dental Practice Management SaaS", "Clinic Management SaaS"]

            # Verification of TAM / SAM / SOM
            assert result.tam is not None
            assert result.tam.estimate > 0
            assert result.sam is not None
            assert result.sam.estimate > 0
            assert result.sam.sam_percentage_of_tam is not None
            assert result.som is not None
            assert result.som.estimate > 0
            assert result.som.som_percentage_of_sam is not None

            # Verification of SOM Scenarios
            assert result.som_scenarios is not None
            assert result.som_scenarios["base"] == result.som.estimate

            # Verification of Market Attractiveness
            assert result.market_attractiveness is not None
            assert result.market_attractiveness.rating in ["HIGH", "MEDIUM", "LOW"]
            assert result.market_attractiveness.score >= 0

            # Verification of 20 Final Report Sections
            assert result.final_report_sections is not None
            assert len(result.final_report_sections) >= 15
            assert any("executive" in k.lower() for k in result.final_report_sections.keys())

    @pytest.mark.asyncio
    async def test_multiple_independent_pipeline_runs_isolated(self):
        from app.discovery.mock_provider import MockDiscoveryProvider
        from app.services.discovery_service import DiscoveryService
        pipeline = MarketAnalysisPipeline(discovery_service=DiscoveryService(provider=MockDiscoveryProvider()))

        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps({"healthcare_saas_category": "Clinic Management SaaS"})}}

            req1 = PipelineRequest(
                business_name="DentisFlow Pro",
                business_idea="Dental SaaS for clinics in India",
                healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
                customer_type=HealthcareCustomerType.DENTAL_CLINICS,
                target_country="India",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=36000.0,
            )

            req2 = PipelineRequest(
                business_name="PharmLogic USA",
                business_idea="Hospital Pharmacy inventory SaaS in United States",
                healthcare_saas_category=HealthcareSaaSCategory.PHARMACY_MANAGEMENT,
                customer_type=HealthcareCustomerType.HOSPITALS,
                target_country="United States",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=120000.0,
            )

            res1 = await pipeline.run(req1)
            res2 = await pipeline.run(req2)

            assert res1.pipeline_id != res2.pipeline_id
            assert res1.business_analysis.target_country == "India"
            assert res2.business_analysis.target_country == "United States"

            # Check repository retrieval
            rec1 = pipeline.repository.get_by_id(res1.pipeline_id)
            rec2 = pipeline.repository.get_by_id(res2.pipeline_id)
            assert rec1 is not None
            assert rec2 is not None
            id1 = rec1.get("pipeline_id") or rec1.get("analysis_id")
            id2 = rec2.get("pipeline_id") or rec2.get("analysis_id")
            assert id1 is not None
            assert id2 is not None
            assert id1 != id2

    @pytest.mark.parametrize(
        "cat,cust,pricing_basis,price",
        [
            (HealthcareSaaSCategory.HOSPITAL_MANAGEMENT, HealthcareCustomerType.HOSPITALS, HealthcarePricingBasis.PER_FACILITY, 250000.0),
            (HealthcareSaaSCategory.EHR_EMR, HealthcareCustomerType.CLINICS, HealthcarePricingBasis.MONTHLY_SUBSCRIPTION, 3000.0),
            (HealthcareSaaSCategory.TELEMEDICINE, HealthcareCustomerType.TELEMEDICINE_PROVIDERS, HealthcarePricingBasis.PER_PROVIDER, 15000.0),
            (HealthcareSaaSCategory.LABORATORY_MANAGEMENT, HealthcareCustomerType.DIAGNOSTIC_LABORATORIES, HealthcarePricingBasis.ANNUAL_SUBSCRIPTION, 180000.0),
        ],
    )
    @pytest.mark.asyncio
    async def test_different_healthcare_categories_and_pricing_models(self, cat, cust, pricing_basis, price):
        from app.discovery.mock_provider import MockDiscoveryProvider
        from app.services.discovery_service import DiscoveryService
        pipeline = MarketAnalysisPipeline(discovery_service=DiscoveryService(provider=MockDiscoveryProvider()))
        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps({"healthcare_saas_category": cat.value})}}

            req = PipelineRequest(
                business_name=f"Venture {cat.value}",
                business_idea=f"Specialized {cat.value} serving {cust.value} with digital workflows.",
                healthcare_saas_category=cat,
                customer_type=cust,
                target_country="India",
                pricing_basis=pricing_basis,
                monthly_price=price if pricing_basis == HealthcarePricingBasis.MONTHLY_SUBSCRIPTION else None,
                annual_price=price if pricing_basis == HealthcarePricingBasis.ANNUAL_SUBSCRIPTION else None,
                per_facility_price=price if pricing_basis == HealthcarePricingBasis.PER_FACILITY else None,
                per_provider_price=price if pricing_basis == HealthcarePricingBasis.PER_PROVIDER else None,
                clinical_use=True if cat == HealthcareSaaSCategory.EHR_EMR else None,
                emr_ehr_integration_required=True if cat == HealthcareSaaSCategory.EHR_EMR else None,
            )

            res = await pipeline.run(req)
            assert res.status in ("completed", PipelineStatus.COMPLETED)
            assert res.tam is not None
            assert res.tam.estimate > 0
            assert res.sam is not None
            assert res.sam.estimate > 0
            assert res.som is not None
            assert res.som.estimate > 0
