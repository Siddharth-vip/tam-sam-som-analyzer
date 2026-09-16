import pytest
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationInput,
    CalculationStatus,
    DataType,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import SourceQualityTier
from app.schemas.validation import EvidenceConfidence
from app.services.calculation_service import CalculationService


@pytest.fixture
def calc_service() -> CalculationService:
    return CalculationService()


# =========================================================================
# 1. Per-Organization Pricing
# =========================================================================
def test_per_organization_pricing(calc_service: CalculationService):
    """TAM = Number of organizations × Annual price per organization."""
    cust = EvidenceInput(
        name="Registered Private Hospitals in India",
        value=40_000.0,
        unit="hospitals",
        currency=None,
        year=2024,
        geography="India",
        source_name="Ministry of Health and Family Welfare",
        source_url="https://mohfw.gov.in/stats",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Annual Hospital EHR SaaS License",
        value=300_000.0,
        unit="INR/hospital/year",
        currency="INR",
        year=2025,
        geography="India",
        source_name="Healthcare SaaS Benchmark",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_organization",
        potential_customers=cust,
        pricing=pricing,
        pricing_frequency=PriceFrequency.ANNUAL,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert res.estimate == 40_000.0 * 300_000.0  # 12,000,000,000 (1,200 crore)
    assert res.currency == "INR"
    assert "₹1,200.00 crore" in (res.display_value or "")
    assert res.method == "bottom_up"
    assert "potential_customers" in res.inputs
    assert "annual_revenue_per_customer" in res.inputs
    assert res.inputs["potential_customers"]["data_type"] == "sourced"
    assert len(res.steps) >= 1


# =========================================================================
# 2. Monthly Subscription -> Annual Conversion
# =========================================================================
def test_monthly_subscription_to_annual_conversion(calc_service: CalculationService):
    """Annual revenue = Monthly price × 12. TAM = Potential Customers × (Monthly Price × 12)."""
    cust = EvidenceInput(
        name="Small Dental Clinics",
        value=15_000.0,
        unit="clinics",
        year=2024,
        geography="India",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Monthly Clinic SaaS Subscription",
        value=2_500.0,
        unit="INR/month",
        currency="INR",
        year=2025,
        geography="India",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="monthly_subscription",
        potential_customers=cust,
        pricing=pricing,
        pricing_frequency=PriceFrequency.MONTHLY,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    expected_arpu = 2_500.0 * 12.0  # 30,000
    expected_tam = 15_000.0 * 30_000.0  # 450,000,000 (45 crore)
    assert res.estimate == expected_tam
    assert res.inputs["annual_revenue_per_customer"]["value"] == expected_arpu
    # Verify monthly conversion step exists in calculation trace
    monthly_step = any("12" in s.formula or "monthly_price" in s.formula for s in res.steps)
    assert monthly_step is True


# =========================================================================
# 3. Per-Provider Pricing
# =========================================================================
def test_per_provider_pricing_with_providers_per_org(calc_service: CalculationService):
    """TAM = Orgs × Providers/Org × Annual Price/Provider."""
    orgs = EvidenceInput(
        name="Multi-Specialty Polyclinics",
        value=8_000.0,
        unit="polyclinics",
        year=2024,
        data_type=DataType.SOURCED.value,
    )
    ppo = EvidenceInput(
        name="Average Doctors Per Polyclinic",
        value=6.0,
        unit="doctors",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Annual Doctor E-Prescription License",
        value=12_000.0,
        unit="INR/doctor/year",
        currency="INR",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        potential_customers=orgs,
        providers_per_organization=ppo,
        pricing=pricing,
        pricing_frequency=PriceFrequency.ANNUAL,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    # 8,000 orgs * 6 doctors * 12,000 INR = 576,000,000 (57.6 crore)
    assert res.estimate == 8_000.0 * 6.0 * 12_000.0
    assert "providers_per_organization" in res.inputs
    assert res.inputs["providers_per_organization"]["value"] == 6.0


def test_per_provider_pricing_direct_population(calc_service: CalculationService):
    """TAM = Direct Providers Population × Annual Price/Provider."""
    providers = EvidenceInput(
        name="Active Radiologists in India",
        value=12_000.0,
        unit="radiologists",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Annual AI Radiology Copilot",
        value=50_000.0,
        unit="INR/radiologist/year",
        currency="INR",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_provider",
        potential_customers=providers,
        pricing=pricing,
        pricing_frequency=PriceFrequency.ANNUAL,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert res.estimate == 12_000.0 * 50_000.0  # 600,000,000


# =========================================================================
# 4. Per-Seat Pricing
# =========================================================================
def test_per_seat_pricing_with_users_per_org(calc_service: CalculationService):
    """TAM = Orgs × Seats/Org × Annual Price/Seat."""
    orgs = EvidenceInput(
        name="Diagnostic Center Labs",
        value=10_000.0,
        unit="laboratories",
        data_type=DataType.SOURCED.value,
    )
    seats = EvidenceInput(
        name="Average Staff Seats Per Lab",
        value=4.0,
        unit="seats",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Monthly Seat Price",
        value=1_000.0,
        unit="INR/seat/month",
        currency="INR",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_seat",
        potential_customers=orgs,
        users_per_organization=seats,
        pricing=pricing,
        pricing_frequency=PriceFrequency.MONTHLY,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    # 10,000 orgs * 4 seats * (1,000 * 12) = 480,000,000 (48 crore)
    assert res.estimate == 10_000.0 * 4.0 * 12_000.0
    assert "users_per_organization" in res.inputs


# =========================================================================
# 5. Derived Customer Count
# =========================================================================
def test_derived_customer_count(calc_service: CalculationService):
    """Derive potential customers: 100,000 base orgs × 30% target segment = 30,000."""
    base_orgs = EvidenceInput(
        name="Total Primary Clinics in India",
        value=100_000.0,
        unit="clinics",
        source_name="National Health Authority Registry",
        source_url="https://abdm.gov.in/registry",
        data_type=DataType.SOURCED.value,
    )
    seg_pct = EvidenceInput(
        name="Urban Private Clinic Segment",
        value=30.0,
        unit="%",
        source_name="Healthcare Survey Report",
        source_url="https://research.example.com/clinics",
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Annual Practice Management SaaS",
        value=40_000.0,
        unit="INR/clinic/year",
        currency="INR",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        base_organizations=base_orgs,
        segment_percentage=seg_pct,
        pricing=pricing,
        pricing_frequency=PriceFrequency.ANNUAL,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    # 100,000 * 30% = 30,000 clinics
    # 30,000 * 40,000 = 1,200,000,000 (120 crore)
    assert res.estimate == 30_000.0 * 40_000.0
    assert res.inputs["potential_customers"]["value"] == 30_000.0
    assert res.inputs["potential_customers"]["data_type"] == DataType.DERIVED.value
    # Calculation steps must record the derivation
    assert any("100,000" in s.description and "30" in s.description for s in res.steps)


# =========================================================================
# 6. Sourced Customer Count
# =========================================================================
def test_sourced_customer_count_provenance(calc_service: CalculationService):
    """Directly sourced customer count must preserve full evidence metadata."""
    cust = EvidenceInput(
        name="Licensed Pharmacies in India",
        value=850_000.0,
        unit="pharmacies",
        source_name="All India Chemists & Druggists Association (AIOCD)",
        source_url="https://aiocd.net/data",
        published_year=2024,
        data_type=DataType.SOURCED.value,
        source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE.value,
    )
    pricing = EvidenceInput(
        name="Pharmacy Inventory SaaS",
        value=15_000.0,
        unit="INR/pharmacy/year",
        currency="INR",
        source_name="SaaS Market Benchmark",
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=cust,
        pricing=pricing,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert res.inputs["potential_customers"]["source"] == "All India Chemists & Druggists Association (AIOCD)"
    assert res.inputs["potential_customers"]["source_url"] == "https://aiocd.net/data"
    assert res.inputs["potential_customers"]["data_type"] == "sourced"
    assert res.inputs["potential_customers"]["published_year"] == 2024


# =========================================================================
# 7. Estimated Input & Confidence Rating
# =========================================================================
def test_estimated_input_marked_and_lowers_confidence(calc_service: CalculationService):
    """Estimated inputs must be marked data_type='estimated' and reflect in confidence."""
    cust = EvidenceInput(
        name="Estimated AYUSH Clinics",
        value=50_000.0,
        unit="clinics",
        data_type=DataType.ESTIMATED.value,
        is_assumption=True,
        assumption_justification="Extrapolated from regional directory sample.",
    )
    pricing = EvidenceInput(
        name="AYUSH EHR SaaS",
        value=20_000.0,
        unit="INR/clinic/year",
        currency="INR",
        data_type=DataType.ESTIMATED.value,
        is_assumption=True,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=cust,
        pricing=pricing,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert res.inputs["potential_customers"]["data_type"] == "estimated"
    # When relying on estimates and assumptions, confidence is LOW
    assert res.confidence == EvidenceConfidence.LOW


# =========================================================================
# 8. Missing Critical TAM Data
# =========================================================================
def test_missing_critical_tam_data(calc_service: CalculationService):
    """Missing potential_customers or pricing must return INSUFFICIENT_EVIDENCE."""
    # Missing customers
    res_no_cust = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=None,
            pricing=EvidenceInput(name="Price", value=50_000.0, unit="INR"),
        )
    )
    assert res_no_cust.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert res_no_cust.estimate is None

    # Missing pricing
    res_no_price = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Cust", value=10_000.0, unit="clinics"),
            pricing=None,
        )
    )
    assert res_no_price.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert res_no_price.estimate is None


# =========================================================================
# 9. Invalid Price (<= 0)
# =========================================================================
def test_invalid_price_rejected(calc_service: CalculationService):
    """Price <= 0 must return INVALID_INPUT."""
    cust = EvidenceInput(name="Clinics", value=5_000.0, unit="clinics")
    pricing_zero = EvidenceInput(name="Free Tier", value=0.0, unit="INR/year", currency="INR")
    inputs = BottomUpCalculationInputs(potential_customers=cust, pricing=pricing_zero)

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.INVALID_INPUT
    assert "Invalid price" in (res.message or "")


# =========================================================================
# 10. Invalid Customer Count (<= 0)
# =========================================================================
def test_invalid_customer_count_rejected(calc_service: CalculationService):
    """Customer count <= 0 must return INVALID_INPUT."""
    cust_zero = EvidenceInput(name="Clinics", value=0.0, unit="clinics")
    pricing = EvidenceInput(name="Price", value=50_000.0, unit="INR/year", currency="INR")
    inputs = BottomUpCalculationInputs(potential_customers=cust_zero, pricing=pricing)

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.INVALID_INPUT
    assert "Invalid customer count" in (res.message or "")


# =========================================================================
# 11. Source Tracking & Provenance Structure
# =========================================================================
def test_source_tracking_provenance_schema(calc_service: CalculationService):
    """TAM result inputs dictionary must strictly follow provenance schema."""
    cust = EvidenceInput(
        name="Registered Dialysis Centers",
        value=3_500.0,
        unit="centers",
        source_name="National Dialysis Programme",
        source_url="https://pmndp.mohfw.gov.in",
        published_year=2024,
        data_type=DataType.SOURCED.value,
    )
    pricing = EvidenceInput(
        name="Dialysis Management SaaS License",
        value=180_000.0,
        unit="INR/center/year",
        currency="INR",
        source_name="Industry Pricing Survey",
        source_url="https://healthtechinsights.org/pricing",
        published_year=2025,
        data_type=DataType.SOURCED.value,
    )
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=cust,
        pricing=pricing,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    for key in ("potential_customers", "annual_revenue_per_customer"):
        assert key in res.inputs
        item = res.inputs[key]
        assert "value" in item
        assert "unit" in item
        assert "data_type" in item
        assert "source" in item
        assert "confidence" in item
        assert item["data_type"] in ("sourced", "derived", "estimated", "AI_assumption")


# =========================================================================
# 12. Calculation Trace (Arithmetic Steps)
# =========================================================================
def test_calculation_trace_arithmetic_equations(calc_service: CalculationService):
    """Calculation trace must include explicit arithmetic steps and operand values."""
    cust = EvidenceInput(name="Hospitals", value=1_200.0, unit="hospitals")
    pricing = EvidenceInput(name="Monthly Price", value=10_000.0, unit="INR/month", currency="INR")
    inputs = BottomUpCalculationInputs(
        pricing_basis="monthly_subscription",
        potential_customers=cust,
        pricing=pricing,
        pricing_frequency=PriceFrequency.MONTHLY,
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert len(res.steps) >= 2
    step1 = res.steps[0]
    assert step1.result == 120_000.0
    step2 = res.steps[1]
    assert step2.result == 1_200.0 * 120_000.0


# =========================================================================
# 13. Top-Down TAM Unavailable
# =========================================================================
def test_top_down_tam_unavailable_when_no_macro_data(calc_service: CalculationService):
    """When macro market size evidence is not found, top-down TAM must report unavailable."""
    empty_inputs = TopDownCalculationInputs(macro_market_size=None)

    res = calc_service.calculate_top_down_tam(empty_inputs)

    assert res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert res.estimate is None


# =========================================================================
# 14. Top-Down + Bottom-Up Comparison & Divergence
# =========================================================================
def test_top_down_and_bottom_up_comparison(calc_service: CalculationService):
    """Compare top-down and bottom-up TAM side-by-side without forcing them to match."""
    # Bottom-up: 50,000 clinics × ₹40,000 = ₹200 crore
    bu_res = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Clinics", value=50_000.0, unit="clinics", data_type=DataType.SOURCED.value),
            pricing=EvidenceInput(name="Clinic SaaS", value=40_000.0, unit="INR/year", currency="INR", data_type=DataType.SOURCED.value),
        )
    )
    # Top-down: India Healthcare SaaS market ₹800 crore × 30% clinic segment = ₹240 crore
    td_res = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="India Healthcare IT Software Market",
                value=8_000_000_000.0,
                unit="INR/year",
                currency="INR",
                data_type=DataType.SOURCED.value,
            ),
            segment_percentages=[
                EvidenceInput(name="Clinic Management Segment", value=30.0, unit="%", data_type=DataType.SOURCED.value)
            ],
        )
    )

    comparison = calc_service.compare_methods(top_down_tam=td_res, bottom_up_tam=bu_res)

    assert comparison is not None
    assert comparison.top_down_estimate == 2_400_000_000.0
    assert comparison.bottom_up_estimate == 2_000_000_000.0
    assert comparison.absolute_difference == 400_000_000.0
    assert comparison.divergence_severity is not None
    assert comparison.explanation is not None


# =========================================================================
# 15. Different Healthcare SaaS Categories
# =========================================================================
@pytest.mark.parametrize(
    "category,customer_unit,count,price,expected_tam",
    [
        ("Hospital SaaS", "hospitals", 30_000, 500_000, 15_000_000_000),
        ("Clinic SaaS", "clinics", 120_000, 36_000, 4_320_000_000),
        ("Diagnostic Lab SaaS", "laboratories", 80_000, 60_000, 4_800_000_000),
        ("Pharmacy SaaS", "pharmacies", 600_000, 18_000, 10_800_000_000),
    ],
)
def test_different_healthcare_saas_categories(
    calc_service: CalculationService, category, customer_unit, count, price, expected_tam
):
    """Verify TAM calculations for different Healthcare SaaS categories."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_organization",
        potential_customers=EvidenceInput(name=f"Total {category} Customers", value=float(count), unit=customer_unit),
        pricing=EvidenceInput(name=f"{category} Price", value=float(price), unit="INR/year", currency="INR"),
    )

    res = calc_service.calculate_bottom_up_tam(inputs)

    assert res.status == CalculationStatus.CALCULATED
    assert res.estimate == float(expected_tam)
    assert res.method == "bottom_up"


# =========================================================================
# 16. Deterministic Multiple Independent Analyses
# =========================================================================
def test_deterministic_independent_analyses(calc_service: CalculationService):
    """Running identical inputs multiple times must yield identical deterministic results."""
    inputs = BottomUpCalculationInputs(
        pricing_basis="per_facility",
        potential_customers=EvidenceInput(name="Specialty Centers", value=5_000.0, unit="centers"),
        pricing=EvidenceInput(name="SaaS License", value=100_000.0, unit="INR/year", currency="INR"),
    )

    res1 = calc_service.calculate_bottom_up_tam(inputs)
    res2 = calc_service.calculate_bottom_up_tam(inputs)

    assert res1.estimate == res2.estimate == 500_000_000.0
    assert res1.display_value == res2.display_value
    assert len(res1.steps) == len(res2.steps)
