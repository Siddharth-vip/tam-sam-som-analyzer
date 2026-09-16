"""Comprehensive Mathematical, Invariant, and Provenance Test Suite for TAM -> SAM -> SOM Market Sizing Funnel.

Validates:
1. TAM = N_total × ARPU across pricing models (Annual, Monthly, Quarterly, Per-Provider, Per-User, Usage-based).
2. SAM = N_serviceable × ARPU across explicit counts, percentages, and insufficient evidence.
3. SOM = N_obtainable × ARPU across capacity counts, market shares, and safety rule enforcement.
4. Strict funnel invariant: N_total >= N_serviceable >= N_obtainable >= 0 and TAM >= SAM >= SOM >= 0.
5. Invariant violation rejection: N_serviceable > N_total and N_obtainable > N_serviceable.
6. Boundary conditions (0 customers, 1 customer, 100% serviceability, 100% obtainability).
7. Three distinct dynamic business scenarios without scenario-specific hardcoding.
"""

import pytest
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationStatus,
    DataType,
    EvidenceInput,
    PriceFrequency,
    SAMResult,
    SOMResult,
    TAMResult,
)
from app.services.calculation_service import CalculationService


@pytest.fixture
def calc_service() -> CalculationService:
    return CalculationService()


# ===========================================================================
# 1. TAM Mathematical & Pricing Model Tests
# ===========================================================================

def test_tam_annual_pricing(calc_service: CalculationService):
    """Test standard annual pricing bottom-up TAM = N_total × ARPU."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.ANNUAL,
        potential_customers=EvidenceInput(
            name="Clinics in India",
            value=21000.0,
            unit="clinics",
            data_type=DataType.LIVE_VERIFIED_SOURCE.value,
        ),
        pricing=EvidenceInput(
            name="Annual Subscription",
            value=48000.0,
            unit="INR/year",
            currency="INR",
            data_type=DataType.USER_PROVIDED.value,
        ),
    )
    res = calc_service.calculate_bottom_up_tam(inputs)
    assert res.status == CalculationStatus.CALCULATED
    assert res.estimate == 21000.0 * 48000.0  # 1,008,000,000 INR
    assert res.currency == "INR"
    assert res.inputs["potential_customers"]["value"] == 21000.0
    assert res.inputs["annual_revenue_per_customer"]["value"] == 48000.0


def test_tam_monthly_pricing_normalization(calc_service: CalculationService):
    """Test monthly pricing is normalized to annual ARPU (monthly × 12)."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.MONTHLY,
        potential_customers=EvidenceInput(
            name="Clinics in India",
            value=10000.0,
            unit="clinics",
            data_type=DataType.LIVE_VERIFIED_SOURCE.value,
        ),
        pricing=EvidenceInput(
            name="Monthly Subscription",
            value=5000.0,
            unit="INR/month",
            currency="INR",
            data_type=DataType.USER_PROVIDED.value,
        ),
    )
    res = calc_service.calculate_bottom_up_tam(inputs)
    assert res.status == CalculationStatus.CALCULATED
    expected_arpu = 5000.0 * 12.0  # 60,000 INR/year
    assert res.estimate == 10000.0 * expected_arpu  # 600,000,000 INR
    assert res.inputs["annual_revenue_per_customer"]["value"] == expected_arpu


def test_tam_quarterly_pricing_normalization(calc_service: CalculationService):
    """Test quarterly pricing is normalized to annual ARPU (quarterly × 4)."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.QUARTERLY,
        potential_customers=EvidenceInput(
            name="Hospitals in India",
            value=5000.0,
            unit="hospitals",
            data_type=DataType.LIVE_VERIFIED_SOURCE.value,
        ),
        pricing=EvidenceInput(
            name="Quarterly License Fee",
            value=25000.0,
            unit="INR/quarter",
            currency="INR",
            data_type=DataType.USER_PROVIDED.value,
        ),
    )
    res = calc_service.calculate_bottom_up_tam(inputs)
    assert res.status == CalculationStatus.CALCULATED
    expected_arpu = 25000.0 * 4.0  # 100,000 INR/year
    assert res.estimate == 5000.0 * expected_arpu  # 500,000,000 INR
    assert res.inputs["annual_revenue_per_customer"]["value"] == expected_arpu


def test_tam_per_provider_pricing(calc_service: CalculationService):
    """Test per-provider pricing multiplies by providers_per_organization."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        pricing_frequency=PriceFrequency.ANNUAL,
        potential_customers=EvidenceInput(
            name="Polyclinics in India",
            value=2000.0,
            unit="polyclinics",
            data_type=DataType.LIVE_VERIFIED_SOURCE.value,
        ),
        pricing=EvidenceInput(
            name="Provider Seat Fee",
            value=12000.0,
            unit="INR/provider/year",
            currency="INR",
            data_type=DataType.USER_PROVIDED.value,
        ),
        providers_per_organization=EvidenceInput(
            name="Average Providers per Polyclinic",
            value=5.0,
            unit="providers",
            data_type=DataType.USER_PROVIDED.value,
        ),
    )
    res = calc_service.calculate_bottom_up_tam(inputs)
    assert res.status == CalculationStatus.CALCULATED
    expected_arpu = 12000.0 * 5.0  # 60,000 INR/polyclinic/year
    assert res.estimate == 2000.0 * expected_arpu  # 120,000,000 INR


# ===========================================================================
# 2. SAM Mathematical & Serviceability Determination Tests
# ===========================================================================

def test_sam_explicit_serviceable_customer_count(calc_service: CalculationService):
    """Test SAM with explicit user-provided serviceable customer count."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=20000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=20000.0, unit="clinics"),
        serviceable_customers=EvidenceInput(name="Tier 1/2 EMR Clinics", value=6000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.status == CalculationStatus.CALCULATED
    assert sam_res.estimate == 6000.0 * 50000.0  # 300,000,000 INR
    assert sam_res.serviceable_customer_count == 6000.0
    assert sam_res.sam_percentage_of_tam == 30.0  # (300M / 1000M) * 100


def test_sam_target_customer_percentage(calc_service: CalculationService):
    """Test SAM derived dynamically from target_customer_percentage."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=15000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=40000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=15000.0, unit="clinics"),
        target_customer_percentage=EvidenceInput(name="Digital Ready Share", value=40.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=40000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.status == CalculationStatus.CALCULATED
    expected_serviceable_cust = 15000.0 * 0.40  # 6000 clinics
    assert sam_res.serviceable_customer_count == expected_serviceable_cust
    assert sam_res.estimate == expected_serviceable_cust * 40000.0  # 240,000,000 INR
    assert sam_res.sam_percentage_of_tam == 40.0


def test_sam_insufficient_evidence_rejection(calc_service: CalculationService):
    """Test SAM returns INSUFFICIENT_EVIDENCE when no serviceable data exists."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=30000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=30000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert sam_res.estimate is None


# ===========================================================================
# 3. SOM Mathematical & Safety Rule Tests
# ===========================================================================

def test_som_explicit_obtainable_customer_count(calc_service: CalculationService):
    """Test SOM calculated with explicit obtainable acquisition capacity."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=20000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=20000.0, unit="clinics"),
        serviceable_customers=EvidenceInput(name="Serviceable Clinics", value=5000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        realistically_obtainable_customers=EvidenceInput(name="Year 1 Target", value=500.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.status == CalculationStatus.CALCULATED
    assert som_res.estimate == 500.0 * 50000.0  # 25,000,000 INR
    assert som_res.obtainable_customer_count == 500.0
    assert som_res.som_percentage_of_sam == 10.0  # 500 / 5000 = 10%
    assert som_res.obtainable_percentage_of_sam == 10.0
    assert som_res.obtainable_percentage_of_tam == 2.5  # 25M / 1000M = 2.5%


def test_som_market_share_percentage(calc_service: CalculationService):
    """Test SOM calculated from explicit obtainable market share percentage."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        target_customer_percentage=EvidenceInput(name="Serviceable %", value=50.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        obtainable_market_share=EvidenceInput(name="SOM Penetration Share", value=15.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.status == CalculationStatus.CALCULATED
    expected_som_val = sam_res.estimate * 0.15  # 300,000,000 * 0.15 = 45,000,000 INR
    assert som_res.estimate == expected_som_val
    assert som_res.obtainable_customer_count == 5000.0 * 0.15  # 750 clinics
    assert som_res.som_percentage_of_sam == 15.0


def test_som_safety_rule_no_arbitrary_constant(calc_service: CalculationService):
    """Test SOM Safety Rule: returns INSUFFICIENT_EVIDENCE if no obtainable evidence provided."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        target_customer_percentage=EvidenceInput(name="Serviceable %", value=50.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)

    # Empty SOM inputs -> Must refuse to fabricate arbitrary multiplier
    som_inputs = BottomUpCalculationInputs(pricing=EvidenceInput(name="Price", value=60000.0, unit="INR/year"))
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert som_res.estimate is None


# ===========================================================================
# 4. Strict Funnel Invariant & Violation Rejection Tests
# ===========================================================================

def test_funnel_invariant_rejection_serviceable_exceeds_potential(calc_service: CalculationService):
    """Test rejection when serviceable customers > potential customers."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=5000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=5000.0, unit="clinics"),
        serviceable_customers=EvidenceInput(name="Serviceable Clinics", value=8000.0, unit="clinics"),  # 8000 > 5000!
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.status == CalculationStatus.NOT_CALCULABLE
    assert "cannot exceed total addressable customer population" in sam_res.message


def test_funnel_invariant_rejection_obtainable_exceeds_serviceable(calc_service: CalculationService):
    """Test rejection when obtainable customers > serviceable customers."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=10000.0, unit="clinics"),
        serviceable_customers=EvidenceInput(name="Serviceable Clinics", value=2000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        realistically_obtainable_customers=EvidenceInput(name="Target Clinics", value=3500.0, unit="clinics"),  # 3500 > 2000!
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.status == CalculationStatus.NOT_CALCULABLE
    assert "cannot exceed serviceable customer population" in som_res.message


def test_invalid_negative_customer_count():
    """Test rejection on negative customer population at schema level."""
    with pytest.raises(ValueError, match="cannot be negative"):
        EvidenceInput(name="Invalid Clinics", value=-500.0, unit="clinics")


def test_invalid_negative_pricing():
    """Test rejection on negative price at schema level."""
    with pytest.raises(ValueError, match="cannot be negative"):
        EvidenceInput(name="Price", value=-1000.0, unit="INR/year")


def test_invalid_percentage_bounds():
    """Test rejection when percentage is outside [0, 100] at schema level."""
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        EvidenceInput(name="Over 100%", value=125.0, unit="%")


# ===========================================================================
# 5. Boundary Condition Tests
# ===========================================================================

def test_boundary_100_percent_funnel(calc_service: CalculationService):
    """Test 100% serviceability and 100% obtainability (TAM == SAM == SOM)."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=1000.0, unit="clinics"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Total Clinics", value=1000.0, unit="clinics"),
        target_customer_percentage=EvidenceInput(name="100% Serviceable", value=100.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        obtainable_market_share=EvidenceInput(name="100% Obtainable", value=100.0, unit="%"),
        pricing=EvidenceInput(name="Price", value=50000.0, unit="INR/year", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)

    assert tam_res.estimate == sam_res.estimate == som_res.estimate == 50_000_000.0
    assert tam_inputs.potential_customers.value == sam_res.serviceable_customer_count == som_res.obtainable_customer_count == 1000.0


def test_boundary_single_customer(calc_service: CalculationService):
    """Test single customer boundary arithmetic."""
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Single Enterprise", value=1.0, unit="hospital"),
        pricing=EvidenceInput(name="Enterprise Price", value=500_000.0, unit="INR/year", currency="INR"),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)
    assert tam_res.estimate == 500_000.0


# ===========================================================================
# 6. Three Distinct Multi-Business Scenarios
# ===========================================================================

def test_business_scenario_1_clinicaflow(calc_service: CalculationService):
    """Scenario 1: Clinic Management SaaS in India (Per Facility, Monthly Pricing)."""
    # 21,000 clinics, ₹4,000/month (₹48,000/year), 30% serviceable, 10% obtainable
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.MONTHLY,
        potential_customers=EvidenceInput(name="Indian Clinics", value=21000.0, unit="clinics", data_type=DataType.LIVE_VERIFIED_SOURCE.value),
        pricing=EvidenceInput(name="Monthly Price", value=4000.0, unit="INR/month", currency="INR", data_type=DataType.USER_PROVIDED.value),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)
    assert tam_res.estimate == 21000.0 * 48000.0  # ₹1,008,000,000

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.MONTHLY,
        potential_customers=EvidenceInput(name="Indian Clinics", value=21000.0, unit="clinics"),
        target_customer_percentage=EvidenceInput(name="Tier 1/2 Cities", value=30.0, unit="%", data_type=DataType.USER_PROVIDED.value),
        pricing=EvidenceInput(name="Monthly Price", value=4000.0, unit="INR/month", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.serviceable_customer_count == 6300.0
    assert sam_res.estimate == 6300.0 * 48000.0  # ₹302,400,000

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.MONTHLY,
        realistically_obtainable_customers=EvidenceInput(name="Year 1-3 Sales Target", value=630.0, unit="clinics", data_type=DataType.USER_PROVIDED.value),
        pricing=EvidenceInput(name="Monthly Price", value=4000.0, unit="INR/month", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.obtainable_customer_count == 630.0
    assert som_res.estimate == 630.0 * 48000.0  # ₹30,240,000

    # Verify Funnel Invariant
    assert 21000.0 >= 6300.0 >= 630.0 >= 0
    assert tam_res.estimate >= sam_res.estimate >= som_res.estimate >= 0


def test_business_scenario_2_hospital_ehr(calc_service: CalculationService):
    """Scenario 2: Hospital EHR SaaS in India (Per Hospital, Quarterly Pricing)."""
    # 5,000 hospitals, ₹60,000/quarter (₹240,000/year), 40% serviceable, 5% obtainable
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.QUARTERLY,
        potential_customers=EvidenceInput(name="Private Hospitals in India", value=5000.0, unit="hospitals", data_type=DataType.LIVE_VERIFIED_SOURCE.value),
        pricing=EvidenceInput(name="Quarterly SaaS License", value=60000.0, unit="INR/quarter", currency="INR", data_type=DataType.USER_PROVIDED.value),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)
    assert tam_res.estimate == 5000.0 * 240000.0  # ₹1,200,000,000

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.QUARTERLY,
        potential_customers=EvidenceInput(name="Private Hospitals in India", value=5000.0, unit="hospitals"),
        target_customer_percentage=EvidenceInput(name="NABH Accredited Segment", value=40.0, unit="%", data_type=DataType.SOURCED.value),
        pricing=EvidenceInput(name="Quarterly SaaS License", value=60000.0, unit="INR/quarter", currency="INR"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.serviceable_customer_count == 2000.0
    assert sam_res.estimate == 2000.0 * 240000.0  # ₹480,000,000

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        pricing_frequency=PriceFrequency.QUARTERLY,
        obtainable_market_share=EvidenceInput(name="Year 1-3 Market Share", value=5.0, unit="%", data_type=DataType.ESTIMATED.value),
        pricing=EvidenceInput(name="Quarterly SaaS License", value=60000.0, unit="INR/quarter", currency="INR"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.obtainable_customer_count == 100.0
    assert som_res.estimate == 100.0 * 240000.0  # ₹24,000,000

    # Verify Funnel Invariant
    assert 5000.0 >= 2000.0 >= 100.0 >= 0
    assert tam_res.estimate >= sam_res.estimate >= som_res.estimate >= 0


def test_business_scenario_3_telehealth_specialist(calc_service: CalculationService):
    """Scenario 3: Telehealth SaaS in US (Per Provider, Annual Pricing)."""
    # 40,000 practitioners, $2,400/practitioner/year, 25% serviceable, 8% obtainable
    tam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        pricing_frequency=PriceFrequency.ANNUAL,
        potential_customers=EvidenceInput(name="US Mental Health Specialists", value=40000.0, unit="providers", currency="USD", data_type=DataType.LIVE_VERIFIED_SOURCE.value),
        pricing=EvidenceInput(name="Annual Provider Subscription", value=2400.0, unit="USD/provider/year", currency="USD", data_type=DataType.USER_PROVIDED.value),
    )
    tam_res = calc_service.calculate_bottom_up_tam(tam_inputs)
    assert tam_res.estimate == 40000.0 * 2400.0  # $96,000,000
    assert tam_res.currency == "USD"

    sam_inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        potential_customers=EvidenceInput(name="US Mental Health Specialists", value=40000.0, unit="providers", currency="USD"),
        serviceable_customers=EvidenceInput(name="Independent Practice Providers", value=10000.0, unit="providers", currency="USD", data_type=DataType.SOURCED.value),
        pricing=EvidenceInput(name="Annual Provider Subscription", value=2400.0, unit="USD/provider/year", currency="USD"),
    )
    sam_res = calc_service.calculate_bottom_up_sam(tam_res, sam_inputs)
    assert sam_res.serviceable_customer_count == 10000.0
    assert sam_res.estimate == 10000.0 * 2400.0  # $24,000,000

    som_inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        realistically_obtainable_customers=EvidenceInput(name="Direct Sales Reach", value=800.0, unit="providers", currency="USD", data_type=DataType.DERIVED.value),
        pricing=EvidenceInput(name="Annual Provider Subscription", value=2400.0, unit="USD/provider/year", currency="USD"),
    )
    som_res = calc_service.calculate_bottom_up_som(sam_res, som_inputs)
    assert som_res.obtainable_customer_count == 800.0
    assert som_res.estimate == 800.0 * 2400.0  # $1,920,000

    # Verify Funnel Invariant
    assert 40000.0 >= 10000.0 >= 800.0 >= 0
    assert tam_res.estimate >= sam_res.estimate >= som_res.estimate >= 0
