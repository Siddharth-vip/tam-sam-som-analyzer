import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.calculation import (
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationStatus,
    DivergenceSeverity,
    EvidenceInput,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.validation import EvidenceConfidence
from app.services.calculation_service import CalculationService

client = TestClient(app)
calculation_service = CalculationService()


# ---------------------------------------------------------------------------
# TEST SUITE: Deterministic Market Sizing Engine (Phase 4.2)
# All inputs are clearly marked FIXED TEST DATA.
# ---------------------------------------------------------------------------

def test_1_valid_top_down_calculation() -> None:
    """TEST 1: Valid top-down calculation computes TAM, SAM, and SOM with full step lineage."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="TEST_DATA_global_edtech_spend",
            value=100000000.0,  # $100M TEST DATA
            unit="USD",
            currency="USD",
            year=2025,
            geography="Global",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_url="https://statistics.example.org/edtech",
        ),
        segment_percentages=[
            EvidenceInput(
                name="TEST_DATA_higher_ed_share",
                value=40.0,  # 40%
                unit="%",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        ],
        serviceable_geography_percentage=EvidenceInput(
            name="TEST_DATA_india_geography_share",
            value=25.0,  # 25%
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        obtainable_market_share=EvidenceInput(
            name="TEST_DATA_year_1_market_share",
            value=10.0,  # 10%
            unit="%",
            is_assumption=True,
            assumption_justification="Target Year 1 sales capacity assumption",
        ),
    )

    tam = calculation_service.calculate_top_down_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 40000000.0  # 100M * 0.40 = 40M

    sam = calculation_service.calculate_top_down_sam(tam, inputs)
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 10000000.0  # 40M * 0.25 = 10M

    som = calculation_service.calculate_top_down_som(sam, inputs)
    assert som.status == CalculationStatus.CALCULATED
    assert som.estimate == 1000000.0  # 10M * 0.10 = 1M


def test_2_valid_bottom_up_calculation() -> None:
    """TEST 2: Valid bottom-up calculation computes TAM, SAM, and SOM from unit economics."""
    inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_total_college_students",
            value=40000000.0,  # 40M students TEST DATA
            unit="students",
            geography="India",
            year=2025,
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_url="https://statistics.gov.in/aishe",
        ),
        target_customer_percentage=EvidenceInput(
            name="TEST_DATA_cs_engineering_share",
            value=20.0,  # 20%
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            source_url="https://aicte.gov.in/stats",
        ),
        obtainable_market_share=EvidenceInput(
            name="TEST_DATA_som_capture_rate",
            value=5.0,  # 5%
            unit="%",
            is_assumption=True,
            assumption_justification="Sales capacity assumption",
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_annual_saas_pricing",
            value=1200.0,  # 1,200 INR TEST DATA
            unit="INR",
            currency="INR",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
        pricing_frequency=PriceFrequency.ANNUAL,
    )

    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 48000000000.0  # 40M * 1,200 = 48B INR

    sam = calculation_service.calculate_bottom_up_sam(tam, inputs)
    assert sam.status == CalculationStatus.CALCULATED
    assert sam.estimate == 9600000000.0  # (40M * 0.20) * 1,200 = 9.6B INR

    som = calculation_service.calculate_bottom_up_som(sam, inputs)
    assert som.status == CalculationStatus.CALCULATED
    assert som.estimate == 480000000.0  # 9.6B * 0.05 = 480M INR


def test_3_missing_evidence_returns_insufficient_evidence() -> None:
    """TEST 3: Missing macro market size returns INSUFFICIENT_EVIDENCE rather than guessing."""
    inputs = TopDownCalculationInputs(
        macro_market_size=None,
    )
    tam = calculation_service.calculate_top_down_tam(inputs)
    assert tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert "Missing required starting macro_market_size" in tam.message


def test_4_missing_pricing_returns_insufficient_evidence() -> None:
    """TEST 4: Missing pricing returns INSUFFICIENT_EVIDENCE for bottom-up TAM."""
    inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_customers",
            value=100000.0,
            unit="users",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing=None,  # Missing pricing
    )
    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert "Missing required pricing" in tam.message


def test_5_missing_customer_population_returns_insufficient_evidence() -> None:
    """TEST 5: Missing customer population returns INSUFFICIENT_EVIDENCE for bottom-up TAM."""
    inputs = BottomUpCalculationInputs(
        potential_customers=None,  # Missing population
        pricing=EvidenceInput(
            name="TEST_DATA_price",
            value=50.0,
            unit="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
    )
    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert tam.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert "Missing required potential_customers" in tam.message


def test_6_invalid_negative_value_rejected() -> None:
    """TEST 6: Negative population or market value raises validation error."""
    with pytest.raises(ValidationError) as exc:
        EvidenceInput(
            name="TEST_DATA_invalid_negative",
            value=-5000.0,  # Negative count
            unit="students",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        )
    assert "cannot be negative" in str(exc.value)


def test_7_invalid_percentage_greater_than_100_rejected() -> None:
    """TEST 7: Percentage greater than 100 raises validation error."""
    with pytest.raises(ValidationError) as exc:
        EvidenceInput(
            name="TEST_DATA_invalid_percentage",
            value=150.0,  # > 100%
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        )
    assert "must be between 0 and 100" in str(exc.value)


def test_8_conflicting_evidence_returns_conflict_status() -> None:
    """TEST 8: Contradictory evidence flags CONFLICT status and halts calculation."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="TEST_DATA_conflicted_macro",
            value=100000000.0,
            unit="USD",
            currency="USD",
            is_conflict=True,  # Active unresolved conflict
            conflicting_values=[100000000.0, 80000000.0],
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        )
    )
    tam = calculation_service.calculate_top_down_tam(inputs)
    assert tam.status == CalculationStatus.CONFLICT
    assert "unresolved conflicting evidence" in tam.message


def test_9_discovered_only_evidence_rejected() -> None:
    """TEST 9: Discovered-only evidence is strictly rejected by schema validators."""
    with pytest.raises(ValidationError) as exc:
        EvidenceInput(
            name="TEST_DATA_unverified_search_result",
            value=5000000.0,
            unit="USD",
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,  # Prohibited stage
        )
    assert "Discovered-only evidence" in str(exc.value)


def test_10_validated_evidence_accepted() -> None:
    """TEST 10: Validated evidence from single source is accepted."""
    inp = EvidenceInput(
        name="TEST_DATA_validated_item",
        value=50000.0,
        unit="users",
        lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
    )
    assert inp.value == 50000.0
    assert inp.lifecycle_stage == "validated"


def test_11_verified_evidence_accepted() -> None:
    """TEST 11: Multi-source verified evidence is accepted."""
    inp = EvidenceInput(
        name="TEST_DATA_verified_item",
        value=100000.0,
        unit="users",
        lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
    )
    assert inp.value == 100000.0
    assert inp.lifecycle_stage == "verified"


def test_12_currency_mismatch_warning() -> None:
    """TEST 12: Differing currencies between Top-Down and Bottom-Up produce a mismatch warning."""
    td_tam = calculation_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="TEST_DATA_macro",
                value=1000000.0,
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        )
    )
    bu_tam = calculation_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="TEST_DATA_users",
                value=1000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="TEST_DATA_price",
                value=50000.0,
                unit="INR",
                currency="INR",  # INR vs USD mismatch
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        )
    )

    comparison = calculation_service.compare_methods(td_tam, bu_tam)
    assert comparison is not None
    assert comparison.currency == "MISMATCH"
    assert "Currency mismatch" in comparison.explanation


def test_13_year_mismatch_produces_warning() -> None:
    """TEST 13: Vintage year discrepancy between customer count and pricing generates a warning."""
    inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_population_2025",
            value=10000.0,
            unit="users",
            year=2025,
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_pricing_2021",
            value=100.0,
            unit="USD",
            currency="USD",
            year=2021,  # 2021 vs 2025 mismatch
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
    )
    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert any("Year mismatch" in w for w in tam.warnings)


def test_14_uncertainty_interval_calculation() -> None:
    """TEST 14: Uncertainty intervals propagate through multiplication bounds."""
    inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_population_interval",
            value=1000.0,
            range_min=800.0,
            range_max=1200.0,
            unit="users",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_pricing_interval",
            value=100.0,
            range_min=90.0,
            range_max=110.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
    )
    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert tam.status == CalculationStatus.CALCULATED
    assert tam.estimate == 100000.0
    assert tam.interval.lower == 72000.0   # 800 * 90
    assert tam.interval.upper == 132000.0  # 1200 * 110


def test_15_som_without_market_share_returns_insufficient_evidence() -> None:
    """TEST 15: SOM Safety Rule refuses calculation when market share is missing."""
    inputs = TopDownCalculationInputs(
        macro_market_size=EvidenceInput(
            name="TEST_DATA_macro",
            value=1000000.0,
            unit="USD",
            currency="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        serviceable_geography_percentage=EvidenceInput(
            name="TEST_DATA_geo",
            value=50.0,
            unit="%",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        obtainable_market_share=None,  # Missing market share!
    )
    tam = calculation_service.calculate_top_down_tam(inputs)
    sam = calculation_service.calculate_top_down_sam(tam, inputs)
    som = calculation_service.calculate_top_down_som(sam, inputs)

    assert som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert "SOM safety rule strictly forbids arbitrary market share" in som.message


def test_16_top_down_vs_bottom_up_comparison() -> None:
    """TEST 16: Cross-method validation correctly classifies convergent methodologies."""
    td_tam = calculation_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="TEST_DATA_macro",
                value=10000000.0,  # 10M
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        )
    )
    bu_tam = calculation_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="TEST_DATA_customers",
                value=100000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="TEST_DATA_price",
                value=90.0,  # 100k * $90 = $9M
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        )
    )

    comparison = calculation_service.compare_methods(td_tam, bu_tam)
    assert comparison is not None
    assert comparison.absolute_difference == 1000000.0
    assert comparison.percentage_difference == 10.53  # |10M - 9M| / ((10M + 9M) / 2) * 100 = 10.53%
    assert comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE


def test_17_severe_divergence_detected() -> None:
    """TEST 17: Severe divergence (>300%) is flagged without silent averaging."""
    td_tam = calculation_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="TEST_DATA_macro",
                value=100000000.0,  # 100M
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        )
    )
    bu_tam = calculation_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="TEST_DATA_customers",
                value=10000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="TEST_DATA_price",
                value=100.0,  # 10k * $100 = $1M (100x discrepancy!)
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        )
    )

    comparison = calculation_service.compare_methods(td_tam, bu_tam)
    assert comparison is not None
    assert comparison.divergence_severity == DivergenceSeverity.SEVERE_DIVERGENCE
    assert "SEVERE DIVERGENCE" in comparison.explanation


def test_18_calculation_audit_trail() -> None:
    """TEST 18: Every step exposes mathematical formula, operands, and evidence provenance."""
    inputs = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_population",
            value=50000.0,
            unit="students",
            source_url="https://source1.example.org",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_monthly_pricing",
            value=10.0,  # $10/mo -> $120/yr
            unit="USD",
            currency="USD",
            source_url="https://source2.example.org",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing_frequency=PriceFrequency.MONTHLY,
    )
    tam = calculation_service.calculate_bottom_up_tam(inputs)
    assert len(tam.steps) == 2
    step1 = tam.steps[0]
    assert step1.formula == "Monthly Price × 12"
    assert step1.result == 120.0
    step2 = tam.steps[1]
    assert "potential_customers" in step2.formula.lower()
    assert step2.result == 6000000.0  # 50,000 * 120
    assert "https://source1.example.org" in step2.evidence_references


def test_19_confidence_calculation() -> None:
    """TEST 19: Provenance quality and assumption counts determine confidence level."""
    # Two verified inputs + 0 assumptions = VERY_HIGH
    inputs_verified = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_verified_pop",
            value=10000.0,
            unit="users",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_verified_pricing",
            value=50.0,
            unit="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
        ),
    )
    tam_verified = calculation_service.calculate_bottom_up_tam(inputs_verified)
    assert tam_verified.confidence == EvidenceConfidence.VERY_HIGH

    # Input with assumption = MEDIUM
    inputs_assumed = BottomUpCalculationInputs(
        potential_customers=EvidenceInput(
            name="TEST_DATA_assumed_pop",
            value=10000.0,
            unit="users",
            is_assumption=True,
            assumption_justification="Estimated user count",
        ),
        pricing=EvidenceInput(
            name="TEST_DATA_price",
            value=50.0,
            unit="USD",
            lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
        ),
    )
    tam_assumed = calculation_service.calculate_bottom_up_tam(inputs_assumed)
    assert tam_assumed.confidence == EvidenceConfidence.MEDIUM


# ---------------------------------------------------------------------------
# API Integration Tests (POST /api/v1/market/calculate)
# ---------------------------------------------------------------------------

def test_20_api_market_calculate_success() -> None:
    """TEST 20: POST /api/v1/market/calculate successfully executes full market sizing report."""
    payload = {
        "business_idea": "TEST_DATA EdTech Platform for Students",
        "target_geography": "India",
        "target_year": 2025,
        "bottom_up_inputs": {
            "potential_customers": {
                "name": "TEST_DATA_college_students_india",
                "value": 43000000.0,
                "unit": "students",
                "year": 2025,
                "geography": "India",
                "source_url": "https://statistics.gov.in/aishe",
                "lifecycle_stage": "verified",
            },
            "target_customer_percentage": {
                "name": "TEST_DATA_cs_students_pct",
                "value": 15.0,
                "unit": "%",
                "lifecycle_stage": "verified",
            },
            "obtainable_market_share": {
                "name": "TEST_DATA_som_capture",
                "value": 5.0,
                "unit": "%",
                "is_assumption": True,
                "assumption_justification": "Initial Year 1 capacity",
            },
            "pricing": {
                "name": "TEST_DATA_arpu",
                "value": 1200.0,
                "unit": "INR",
                "currency": "INR",
                "lifecycle_stage": "validated",
            },
            "pricing_frequency": "annual",
        },
    }

    response = client.post("/api/v1/market/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "calculated"
    assert data["currency"] == "INR"
    assert data["bottom_up_tam"]["estimate"] == 51600000000.0  # 43M * 1,200 = 51.6B INR
    assert data["bottom_up_sam"]["estimate"] == 7740000000.0   # (43M * 0.15) * 1,200 = 7.74B INR
    assert data["bottom_up_som"]["estimate"] == 387000000.0    # 7.74B * 0.05 = 387M INR
    assert len(data["all_steps"]) >= 3


def test_21_api_market_calculate_validation_failure() -> None:
    """TEST 21: POST /api/v1/market/calculate returns 422 on invalid schema inputs."""
    payload = {
        "bottom_up_inputs": {
            "potential_customers": {
                "name": "TEST_DATA_invalid",
                "value": -100.0,  # Negative count invalid
                "unit": "users",
            }
        }
    }
    response = client.post("/api/v1/market/calculate", json=payload)
    assert response.status_code == 422
