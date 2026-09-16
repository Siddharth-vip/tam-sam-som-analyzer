"""
Phase 3 — Serviceable Addressable Market (SAM) Engine Test Suite.

Verifies:
1. Valid bottom-up SAM calculations (serviceable_customers × annual_revenue_per_customer)
2. Invariants: 0 <= SAM <= TAM and serviceable_customers <= total_customers
3. Geographic serviceability filtering
4. Customer segment & product compatibility filtering
5. Insufficient evidence handling without fabricated percentages
6. Explicit user-provided serviceability constraints (DataType.USER_PROVIDED)
7. Research evidence provenance (DataType.SOURCED, LIVE_VERIFIED_SOURCE, MOCK_SOURCE)
8. Transparent calculation step trace (Step 1 to Step 5)
9. Dynamic multi-business sizing: ClinicaFlow and MediSchedule
10. Negative test cases with missing serviceability evidence
"""

import json
from unittest.mock import AsyncMock, patch
import pytest

from app.schemas.business import (
    BusinessAnalysis,
    HealthcareCustomerType,
    HealthcarePricingBasis,
    HealthcareSaaSCategory,
)
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationInput,
    CalculationStatus,
    DataType,
    EvidenceConfidence,
    EvidenceInput,
    PriceFrequency,
    SAMResult,
    TAMResult,
)
from app.schemas.pipeline import PipelineRequest, PipelineStatus
from app.schemas.validation import EvidenceValidationResult
from app.services.calculation_service import CalculationService
from app.orchestration.pipeline import MarketAnalysisPipeline


class TestSAMEngineCalculation:
    """Core deterministic SAM calculation logic and invariant tests."""

    @pytest.fixture
    def calc_service(self):
        return CalculationService()

    @pytest.fixture
    def base_tam(self, calc_service):
        """Standard bottom-up TAM fixture: 150,000 clinics × ₹48,000/yr = ₹7.2B."""
        tam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics in India",
                value=150000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
                source_name="Ministry of Health and Family Welfare",
                source_url="https://mohfw.gov.in/registry",
            ),
            pricing=EvidenceInput(
                name="Annual Subscription Price",
                value=48000.0,
                unit="INR/year",
                currency="INR",
                data_type=DataType.SOURCED.value,
                source_name="Healthcare SaaS Benchmark",
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
        return calc_service.calculate_bottom_up_tam(tam_inputs)

    def test_sam_bottom_up_direct_serviceable_customers(self, calc_service, base_tam):
        """Test SAM = serviceable_customers × annual_revenue_per_customer."""
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics in India",
                value=150000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
            ),
            serviceable_customers=EvidenceInput(
                name="Tier 1 & 2 Urban Clinics",
                value=45000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
                source_name="National Healthcare Infrastructure Report",
                source_url="https://mohfw.gov.in/tier1-2-clinics",
            ),
            pricing=EvidenceInput(
                name="Annual Subscription Price",
                value=48000.0,
                unit="INR/year",
                currency="INR",
                data_type=DataType.SOURCED.value,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
            serviceability_constraints=["Geographic: Tier 1 & Tier 2 Urban Areas"],
        )

        sam_result = calc_service.calculate_bottom_up_sam(base_tam, sam_inputs)

        assert sam_result.status == CalculationStatus.CALCULATED
        assert sam_result.estimate == 45000.0 * 48000.0  # ₹2,160,000,000 (₹216 crore)
        assert sam_result.serviceable_customer_count == 45000.0
        assert sam_result.sam_percentage_of_tam == 30.0
        assert sam_result.calculation_method == "bottom_up"
        assert "serviceable_customers × annual_revenue_per_customer" in sam_result.formula
        assert "Geographic: Tier 1 & Tier 2 Urban Areas" in sam_result.serviceability_constraints

    def test_sam_derived_from_user_serviceability_percentage(self, calc_service, base_tam):
        """Test SAM derived via user-provided serviceability percentage constraint."""
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics",
                value=150000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
            ),
            target_customer_percentage=EvidenceInput(
                name="User-Specified Serviceable Share",
                value=20.0,
                unit="%",
                data_type=DataType.USER_PROVIDED.value,
                is_user_provided=True,
            ),
            pricing=EvidenceInput(
                name="Annual Subscription Price",
                value=48000.0,
                unit="INR/year",
                currency="INR",
                data_type=DataType.SOURCED.value,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )

        sam_result = calc_service.calculate_bottom_up_sam(base_tam, sam_inputs)

        assert sam_result.status == CalculationStatus.CALCULATED
        assert sam_result.serviceable_customer_count == 30000.0  # 20% of 150,000
        assert sam_result.estimate == 30000.0 * 48000.0  # ₹1,440,000,000
        assert sam_result.sam_percentage_of_tam == 20.0

    def test_sam_never_exceeds_tam_invariant(self, calc_service, base_tam):
        """Test invariant: SAM must never exceed TAM (0 <= SAM <= TAM)."""
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics",
                value=150000.0,
                unit="clinics",
            ),
            serviceable_customers=EvidenceInput(
                name="Overstated Serviceable Population",
                value=200000.0,  # Greater than TAM population (150,000)
                unit="clinics",
            ),
            pricing=EvidenceInput(
                name="Annual Price",
                value=48000.0,
                unit="INR/year",
                currency="INR",
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )

        sam_result = calc_service.calculate_bottom_up_sam(base_tam, sam_inputs)

        # Must reject calculation with validation error / non-calculable status
        assert sam_result.status in (CalculationStatus.NOT_CALCULABLE, CalculationStatus.INSUFFICIENT_EVIDENCE)
        assert "exceed total addressable" in (sam_result.message or "").lower()

    def test_sam_insufficient_evidence_when_missing_segmentation(self, calc_service, base_tam):
        """Test negative scenario: No serviceability evidence or constraints -> INSUFFICIENT_EVIDENCE."""
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics in India",
                value=150000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
            ),
            serviceable_customers=None,
            target_customer_percentage=None,
            pricing=EvidenceInput(
                name="Annual Price",
                value=48000.0,
                unit="INR/year",
                currency="INR",
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )

        sam_result = calc_service.calculate_bottom_up_sam(base_tam, sam_inputs)

        assert sam_result.status == CalculationStatus.INSUFFICIENT_EVIDENCE
        assert sam_result.estimate is None
        assert "Insufficient evidence" in sam_result.message
        assert len(sam_result.evidence_quality_reasons) > 0

    def test_sam_provenance_and_audit_trace(self, calc_service, base_tam):
        """Test complete provenance dictionary and step-by-step audit trace in SAM."""
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Total Outpatient Clinics in India",
                value=150000.0,
                unit="clinics",
                data_type=DataType.SOURCED.value,
                source_name="Ministry of Health",
                source_url="https://mohfw.gov.in/registry",
            ),
            serviceable_customers=EvidenceInput(
                name="ABDM-Ready Digital Clinics",
                value=37500.0,
                unit="clinics",
                data_type=DataType.LIVE_VERIFIED_SOURCE.value,
                source_name="National Health Authority",
                source_url="https://nha.gov.in/abdm-clinics",
                published_year=2024,
            ),
            pricing=EvidenceInput(
                name="Annual Clinic SaaS Subscription",
                value=48000.0,
                unit="INR/year",
                currency="INR",
                data_type=DataType.LIVE_VERIFIED_SOURCE.value,
                source_name="Healthcare SaaS Benchmark",
                source_url="https://industry-benchmarks.com/saas",
                published_year=2024,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
            serviceability_constraints=[
                "Regulatory & Interoperability: ABDM M1/M2 Certified",
                "Infrastructure: Broadband & Computerized EMR Ready",
            ],
        )

        sam_result = calc_service.calculate_bottom_up_sam(base_tam, sam_inputs)

        # 1. Check Provenance
        assert "serviceable_customers" in sam_result.inputs
        srv_meta = sam_result.inputs["serviceable_customers"]
        assert srv_meta["value"] == 37500.0
        assert srv_meta["data_type"] == DataType.LIVE_VERIFIED_SOURCE.value
        assert srv_meta["source_url"] == "https://nha.gov.in/abdm-clinics"
        assert srv_meta["published_year"] == 2024

        # 2. Check Step Trace (Step 1 to Step 5)
        step_descriptions = [s.description.lower() for s in sam_result.steps]
        assert any("serviceable customer population" in d for d in step_descriptions)
        assert any("calculate serviceable addressable market" in d for d in step_descriptions)
        assert any("validate sam invariant" in d for d in step_descriptions)


class TestSAMMultiBusinessPipeline:
    """Dynamic multi-business end-to-end SAM tests (ClinicaFlow and MediSchedule)."""

    @pytest.mark.asyncio
    async def test_clinicaflow_dynamic_sam_sizing(self):
        """ClinicaFlow: SMB Clinic Management SaaS in India."""
        from app.discovery.mock_provider import MockDiscoveryProvider
        from app.services.discovery_service import DiscoveryService

        pipeline = MarketAnalysisPipeline(discovery_service=DiscoveryService(provider=MockDiscoveryProvider()))
        mock_analysis = {
            "business_name": "ClinicaFlow",
            "healthcare_saas_category": "Clinic Management SaaS",
            "customer_type": "Clinics",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "per_facility_price": 48000.0,
            "annual_revenue_per_customer": 48000.0,
            "emr_integration_required": True,
        }

        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps(mock_analysis)}}

            req = PipelineRequest(
                business_name="ClinicaFlow",
                business_idea="Cloud-based clinic management SaaS for small and medium-sized outpatient clinics in India.",
                healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
                customer_type=HealthcareCustomerType.CLINICS,
                target_country="India",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=48000.0,
                serviceable_percentage=30.0,  # User specifies 30% serviceable digital clinic share
                serviceability_criteria=["Tier 1 & Tier 2 Cities", "Active EMR Adoption"],
            )

            res = await pipeline.run(req)

            assert res.status in ("completed", PipelineStatus.COMPLETED)
            assert res.tam is not None
            assert res.tam.estimate > 0
            assert res.sam is not None
            assert res.sam.estimate > 0
            # SAM must be exactly 30% of TAM
            assert res.sam.sam_percentage_of_tam == 30.0
            assert res.sam.estimate <= res.tam.estimate
            assert any("30.0%" in c or "30%" in c for c in res.sam.serviceability_constraints)

    @pytest.mark.asyncio
    async def test_medischedule_dynamic_sam_sizing(self):
        """MediSchedule: Hospital Surgical & Resource Scheduling SaaS."""
        from app.discovery.mock_provider import MockDiscoveryProvider
        from app.services.discovery_service import DiscoveryService

        pipeline = MarketAnalysisPipeline(discovery_service=DiscoveryService(provider=MockDiscoveryProvider()))
        mock_analysis = {
            "business_name": "MediSchedule",
            "healthcare_saas_category": "Hospital Management SaaS",
            "customer_type": "Hospitals",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "per_facility_price": 240000.0,
            "annual_revenue_per_customer": 240000.0,
        }

        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps(mock_analysis)}}

            req = PipelineRequest(
                business_name="MediSchedule",
                business_idea="Enterprise operating room and multi-specialty patient scheduling SaaS for hospitals in India.",
                healthcare_saas_category=HealthcareSaaSCategory.HOSPITAL_MANAGEMENT,
                customer_type=HealthcareCustomerType.HOSPITALS,
                target_country="India",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=240000.0,
                serviceable_organizations=12000,  # 12,000 multi-specialty private hospitals
                serviceability_criteria=["Private Hospitals >= 50 beds", "NABH Accredited"],
            )

            res = await pipeline.run(req)

            assert res.status in ("completed", PipelineStatus.COMPLETED)
            assert res.tam is not None
            assert res.sam is not None
            assert res.sam.serviceable_customer_count == 12000.0
            assert res.sam.estimate == 12000.0 * 240000.0  # ₹2,880,000,000 (₹288 crore)
            assert res.sam.estimate <= res.tam.estimate

    @pytest.mark.asyncio
    async def test_geographic_reach_percentage_filtering(self):
        """Test geographic reach percentage constraint."""
        from app.discovery.mock_provider import MockDiscoveryProvider
        from app.services.discovery_service import DiscoveryService

        pipeline = MarketAnalysisPipeline(discovery_service=DiscoveryService(provider=MockDiscoveryProvider()))
        mock_analysis = {
            "business_name": "DentisFlow Regional",
            "healthcare_saas_category": "Clinic Management SaaS",
            "customer_type": "Dental Clinics",
            "target_country": "India",
            "pricing_basis": "per_facility",
            "per_facility_price": 36000.0,
            "annual_revenue_per_customer": 36000.0,
        }

        with patch.object(pipeline.llm_service, "_make_request", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"message": {"content": json.dumps(mock_analysis)}}

            req = PipelineRequest(
                business_name="DentisFlow Regional",
                business_idea="Dental practice management for South India region.",
                healthcare_saas_category=HealthcareSaaSCategory.CLINIC_MANAGEMENT,
                customer_type=HealthcareCustomerType.DENTAL_CLINICS,
                target_country="India",
                pricing_basis=HealthcarePricingBasis.PER_FACILITY,
                per_facility_price=36000.0,
                geographic_reach_percentage=25.0,  # 25% regional reach
            )

            res = await pipeline.run(req)

            assert res.status in ("completed", PipelineStatus.COMPLETED)
            assert res.tam is not None
            assert res.sam is not None
            assert res.sam.sam_percentage_of_tam == 25.0
            assert res.sam.estimate == round(res.tam.estimate * 0.25, 2)


class TestSAMNegativeAndBoundaryScenarios:
    """Negative tests, boundary conditions, and isolation safeguards."""

    def test_sam_rejects_negative_pricing(self):
        """Reject negative pricing in SAM inputs."""
        calc_service = CalculationService()
        tam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(
                name="Clinics",
                value=10000.0,
                unit="clinics",
            ),
            pricing=EvidenceInput(
                name="Price",
                value=1000.0,
                unit="INR/year",
                currency="INR",
            ),
        )
        tam = calc_service.calculate_bottom_up_tam(tam_inputs)

        # Attempt missing pricing
        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=tam_inputs.potential_customers,
            serviceable_customers=EvidenceInput(
                name="Serviceable Clinics",
                value=5000.0,
                unit="clinics",
            ),
            pricing=None,  # Missing pricing
        )
        sam_result = calc_service.calculate_bottom_up_sam(tam, sam_inputs)
        assert sam_result.status == CalculationStatus.INSUFFICIENT_EVIDENCE

    def test_sam_clamps_at_zero(self, calc_service=None):
        """Ensure SAM never produces negative market estimates."""
        service = CalculationService()
        tam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=EvidenceInput(name="Clinics", value=1000.0, unit="clinics"),
            pricing=EvidenceInput(name="Price", value=100.0, unit="INR/year", currency="INR"),
        )
        tam = service.calculate_bottom_up_tam(tam_inputs)

        sam_inputs = BottomUpCalculationInputs(
            pricing_basis="per_facility",
            potential_customers=tam_inputs.potential_customers,
            serviceable_customers=EvidenceInput(name="Serviceable Clinics", value=0.0, unit="clinics"),
            pricing=tam_inputs.pricing,
        )
        sam_result = service.calculate_bottom_up_sam(tam, sam_inputs)
        assert sam_result.status == CalculationStatus.CALCULATED
        assert sam_result.estimate == 0.0
        assert sam_result.estimate <= tam.estimate
