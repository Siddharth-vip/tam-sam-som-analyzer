import pytest
from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    EvidenceConfidence,
    EvidenceValidationResult,
    EvidenceValidationStatus,
    MarketScopeType,
)
from app.schemas.calculation import (
    ACCEPTABLE_DIVERGENCE_THRESHOLD,
    WARNING_DIVERGENCE_THRESHOLD,
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationStatus,
    DivergenceSeverity,
    EvidenceInput,
    EvidenceQualityRating,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.services.calculation_service import CalculationService
from app.services.validation_service import EvidenceValidationService

calc_service = CalculationService()
validation_service = EvidenceValidationService()


# ---------------------------------------------------------------------------
# 1. Triangulation & Divergence Threshold Tests
# ---------------------------------------------------------------------------

def test_matching_top_down_and_bottom_up_estimates() -> None:
    """Perfect agreement between Top-Down ($5B) and Bottom-Up ($5B) yields 0% divergence and ACCEPTABLE status."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Online Education TAM",
                value=5_000_000_000.0,
                unit="USD",
                currency="USD",
                year=2024,
                geography="India",
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Target Students",
                value=1_000_000.0,
                unit="students",
                year=2024,
                geography="India",
            ),
            pricing=EvidenceInput(
                name="Annual Price",
                value=5_000.0,
                unit="USD",
                currency="USD",
                year=2024,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )

    comparison = calc_service.compare_methods(td_tam, bu_tam)

    assert comparison is not None
    assert comparison.top_down_estimate == 5_000_000_000.0
    assert comparison.bottom_up_estimate == 5_000_000_000.0
    assert comparison.absolute_difference == 0.0
    assert comparison.percentage_difference == 0.0
    assert comparison.relative_ratio == 1.0
    assert comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert comparison.triangulation_confidence == EvidenceConfidence.HIGH


def test_acceptable_divergence_threshold() -> None:
    """Top-Down = 20B, Bottom-Up = 18B -> divergence is 10.53% (<= 20% threshold), classified as ACCEPTABLE."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Macro Sizing",
                value=20_000_000_000.0,
                unit="INR",
                currency="INR",
                year=2024,
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Customer Base",
                value=3_000_000.0,
                unit="customers",
                year=2024,
            ),
            pricing=EvidenceInput(
                name="Annual ARPU",
                value=6_000.0,
                unit="INR",
                currency="INR",
                year=2024,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )

    comparison = calc_service.compare_methods(td_tam, bu_tam)

    assert comparison is not None
    assert comparison.absolute_difference == 2_000_000_000.0
    # Midpoint percentage difference: 2 / 19 * 100 ≈ 10.53%
    assert comparison.percentage_difference == pytest.approx(10.53, rel=1e-2)
    assert comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert comparison.triangulation_confidence == EvidenceConfidence.HIGH
    assert "acceptable" in comparison.divergence_explanation.lower()


def test_warning_divergence_threshold() -> None:
    """Top-Down = 20B, Bottom-Up = 14.8B -> divergence is ~29.89% (> 20% and <= 50%), classified as WARNING."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Macro Sizing",
                value=20_000_000_000.0,
                unit="INR",
                currency="INR",
                year=2024,
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Customer Base",
                value=2_466_667.0,
                unit="customers",
                year=2024,
            ),
            pricing=EvidenceInput(
                name="Annual ARPU",
                value=6_000.0,
                unit="INR",
                currency="INR",
                year=2024,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )

    comparison = calc_service.compare_methods(td_tam, bu_tam)

    assert comparison is not None
    assert comparison.percentage_difference > ACCEPTABLE_DIVERGENCE_THRESHOLD
    assert comparison.percentage_difference <= WARNING_DIVERGENCE_THRESHOLD
    assert comparison.divergence_severity == DivergenceSeverity.WARNING
    assert comparison.triangulation_confidence == EvidenceConfidence.MEDIUM


def test_severe_divergence_and_confidence_downgrade() -> None:
    """Top-Down = 100B, Bottom-Up = 20B -> divergence is 133.33% (> 50%), classified as SEVERE_DIVERGENCE with confidence LOW."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Broad Industry Sector Size",
                value=100_000_000_000.0,
                unit="INR",
                currency="INR",
                year=2024,
                geography="India",
                market_scope=MarketScopeType.PARENT_MARKET.value,
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Students Population",
                value=3_333_333.33,
                unit="students",
                year=2024,
                geography="India",
                market_scope=MarketScopeType.ADDRESSABLE_MARKET.value,
            ),
            pricing=EvidenceInput(
                name="Annual ARPU",
                value=6_000.0,
                unit="INR",
                currency="INR",
                year=2024,
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )

    comparison = calc_service.compare_methods(td_tam, bu_tam)

    assert comparison is not None
    assert comparison.percentage_difference > WARNING_DIVERGENCE_THRESHOLD
    assert comparison.divergence_severity == DivergenceSeverity.SEVERE_DIVERGENCE
    assert comparison.triangulation_confidence == EvidenceConfidence.LOW
    assert len(comparison.root_cause_diagnostics) > 0
    assert any("Market Scope" in d or "Market Definition" in d for d in comparison.root_cause_diagnostics)

    # Master report overall confidence must be downgraded to LOW
    report = calc_service.generate_report(
        CalculationInput(
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="Broad Industry Sector Size",
                    value=100_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    year=2024,
                    market_scope=MarketScopeType.PARENT_MARKET.value,
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Students Population",
                    value=3_333_333.33,
                    unit="students",
                    year=2024,
                ),
                pricing=EvidenceInput(
                    name="Annual ARPU",
                    value=6_000.0,
                    unit="INR",
                    currency="INR",
                    year=2024,
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )
    assert report.confidence == EvidenceConfidence.LOW


# ---------------------------------------------------------------------------
# 2. Evidence Mismatch & Guard Tests
# ---------------------------------------------------------------------------

def test_currency_mismatch_without_fx_invention() -> None:
    """When Top-Down is in USD and Bottom-Up is in INR, calculation engine does not invent FX rates."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="US Market TAM",
                value=2_000_000_000.0,
                unit="USD",
                currency="USD",
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Indian Users",
                value=1_000_000.0,
                unit="users",
            ),
            pricing=EvidenceInput(
                name="Indian Pricing",
                value=5_000.0,
                unit="INR",
                currency="INR",
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )

    comparison = calc_service.compare_methods(td_tam, bu_tam)

    assert comparison is not None
    assert comparison.currency == "MISMATCH"
    assert comparison.absolute_difference is None
    assert comparison.percentage_difference is None
    assert any("Currency mismatch" in d for d in comparison.root_cause_diagnostics)


def test_missing_bottom_up_evidence_refusal() -> None:
    """Missing potential customer base halts bottom-up TAM with INSUFFICIENT_EVIDENCE."""
    bu_res = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=None,
            pricing=EvidenceInput(name="Pricing", value=100.0, unit="USD"),
        )
    )
    assert bu_res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert bu_res.estimate is None


def test_missing_pricing_refusal() -> None:
    """Missing pricing/ARPU halts bottom-up TAM with INSUFFICIENT_EVIDENCE."""
    bu_res = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(name="Customers", value=100_000.0, unit="users"),
            pricing=None,
        )
    )
    assert bu_res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert bu_res.estimate is None


def test_som_safety_rule_no_arbitrary_percentage() -> None:
    """SOM calculation strictly refuses to invent an arbitrary market share percentage."""
    sam_res = calc_service.calculate_top_down_sam(
        tam_result=calc_service.calculate_top_down_tam(
            TopDownCalculationInputs(
                macro_market_size=EvidenceInput(name="TAM", value=1_000_000_000.0, unit="USD", currency="USD")
            )
        ),
        inputs=TopDownCalculationInputs(
            macro_market_size=EvidenceInput(name="TAM", value=1_000_000_000.0, unit="USD", currency="USD"),
            target_segment_percentage=EvidenceInput(name="Target Segment", value=25.0, unit="%"),
        ),
    )
    assert sam_res.status == CalculationStatus.CALCULATED
    assert sam_res.estimate == 250_000_000.0
    # No obtainable market share supplied
    som_res = calc_service.calculate_top_down_som(sam_res, TopDownCalculationInputs())
    assert som_res.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert som_res.estimate is None
    assert any("som safety rule" in r.lower() for r in som_res.evidence_quality_reasons) or "som safety rule" in (som_res.message or "").lower()


def test_tier_5_source_exclusion_from_calculation() -> None:
    """Tier 5 unusable evidence cannot enter calculation."""
    candidate = ExtractedEvidenceCandidate(
        candidate_id="cand_unusable_1",
        metric="India Edtech TAM Claim",
        value=50_000_000_000.0,
        unit="USD",
        year=2024,
        geography="India",
        source_context="Random comment claiming edtech is $50B in India.",
        source_url="https://reddit.com/r/edtech/comments/12345/market_size",
        source_name="Reddit Discussion",
        metric_type="market_size",
    )
    val_res = validation_service.validate_candidate(candidate)
    assert not val_res.is_valid
    assert val_res.validation_status == EvidenceValidationStatus.REJECTED


def test_explicit_user_assumption_audit_tracking() -> None:
    """Explicit user assumptions are accepted, tracked, and labeled in audit trail."""
    pricing_assumption = EvidenceInput(
        name="target_annual_subscription",
        value=7_500.0,
        unit="INR",
        currency="INR",
        is_assumption=True,
        assumption_justification="User business plan assumption for pro tier tiering",
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Active Developers",
                value=500_000.0,
                unit="developers",
                year=2024,
            ),
            pricing=pricing_assumption,
            pricing_frequency=PriceFrequency.ANNUAL,
        )
    )
    assert bu_tam.status == CalculationStatus.CALCULATED
    assert bu_tam.estimate == 500_000.0 * 7_500.0
    assert any(a.name == "target_annual_subscription" for a in bu_tam.assumptions_used)
    assert any("target_annual_subscription" in step.assumptions for step in bu_tam.steps)


def test_sam_and_som_cross_methodology_comparison() -> None:
    """SAM and SOM are compared when both Top-Down and Bottom-Up calculations are available."""
    # Top-Down Inputs
    td_macro = EvidenceInput(name="TAM Base", value=10_000_000_000.0, unit="USD", currency="USD")
    td_sam_pct = EvidenceInput(name="Serviceable Segment", value=25.0, unit="%")
    td_som_share = EvidenceInput(name="SOM Share", value=4.0, unit="%")
    td_inputs = TopDownCalculationInputs(
        macro_market_size=td_macro,
        target_segment_percentage=td_sam_pct,
        obtainable_market_share=td_som_share,
    )

    td_tam = calc_service.calculate_top_down_tam(td_inputs)
    td_sam = calc_service.calculate_top_down_sam(td_tam, td_inputs)
    td_som = calc_service.calculate_top_down_som(td_sam, td_inputs)

    # Bottom-Up Inputs
    bu_cust = EvidenceInput(name="Total Cust", value=20_000_000.0, unit="users")
    bu_price = EvidenceInput(name="Price", value=500.0, unit="USD", currency="USD")
    bu_target_pct = EvidenceInput(name="Serviceable Pct", value=25.0, unit="%")
    bu_obt_share = EvidenceInput(name="Obt Share", value=4.0, unit="%")
    bu_inputs = BottomUpCalculationInputs(
        potential_customers=bu_cust,
        pricing=bu_price,
        target_customer_percentage=bu_target_pct,
        obtainable_market_share=bu_obt_share,
    )

    bu_tam = calc_service.calculate_bottom_up_tam(bu_inputs)
    bu_sam = calc_service.calculate_bottom_up_sam(bu_tam, bu_inputs)
    bu_som = calc_service.calculate_bottom_up_som(bu_sam, bu_inputs)

    comparison = calc_service.compare_methods(
        td_tam, bu_tam,
        top_down_sam=td_sam, bottom_up_sam=bu_sam,
        top_down_som=td_som, bottom_up_som=bu_som,
    )

    assert comparison is not None
    assert comparison.sam_comparison is not None
    assert comparison.sam_comparison["top_down_sam"] == 2_500_000_000.0
    assert comparison.sam_comparison["bottom_up_sam"] == 2_500_000_000.0
    assert comparison.sam_comparison["percentage_difference"] == 0.0

    assert comparison.som_comparison is not None
    assert comparison.som_comparison["top_down_som"] == 100_000_000.0
    assert comparison.som_comparison["bottom_up_som"] == 100_000_000.0
    assert comparison.som_comparison["percentage_difference"] == 0.0


# ---------------------------------------------------------------------------
# 3. Five Real-World Target Business Scenario End-to-End Tests
# ---------------------------------------------------------------------------

def test_e2e_scenario_1_online_programming_platform_india() -> None:
    """Scenario 1: Online programming platform for college students in India."""
    # Top-Down: EdTech coding niche TAM = ₹25B
    # Bottom-Up: 4.3M engineering students × ₹6,000 ARPU = ₹25.8B
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Affordable online programming platform for college students in India",
            target_geography="India",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India Coding & Tech Education Market Size",
                    value=25_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    year=2024,
                    geography="India",
                    source_name="NASSCOM Tech Skills Report",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL.value,
                    market_scope=MarketScopeType.ADDRESSABLE_MARKET.value,
                ),
                target_segment_percentage=EvidenceInput(
                    name="College Undergraduate Share",
                    value=40.0,
                    unit="%",
                ),
                obtainable_market_share=EvidenceInput(
                    name="Year 1-2 Obtainable Share",
                    value=5.0,
                    unit="%",
                ),
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Indian Engineering & CS Undergraduates",
                    value=4_300_000.0,
                    unit="students",
                    year=2024,
                    geography="India",
                    source_name="AISHE Census Report",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL.value,
                    market_scope=MarketScopeType.ADDRESSABLE_MARKET.value,
                ),
                pricing=EvidenceInput(
                    name="Annual Platform Subscription",
                    value=6_000.0,
                    unit="INR",
                    currency="INR",
                    year=2024,
                    source_name="Pricing Benchmark Survey",
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
                target_customer_percentage=EvidenceInput(
                    name="Active Self-Learners Segment",
                    value=40.0,
                    unit="%",
                ),
                obtainable_market_share=EvidenceInput(
                    name="Year 1-2 Capture Share",
                    value=5.0,
                    unit="%",
                ),
            ),
        )
    )

    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    # Top-Down TAM = 25B, Bottom-Up TAM = 4.3M * 6,000 = 25.8B -> ~3.15% divergence
    assert report.method_comparison.percentage_difference < ACCEPTABLE_DIVERGENCE_THRESHOLD
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert report.confidence in (EvidenceConfidence.HIGH, EvidenceConfidence.VERY_HIGH)


def test_e2e_scenario_2_healthy_food_delivery_chennai() -> None:
    """Scenario 2: Healthy subscription food delivery in Chennai."""
    # Top-Down: Chennai health food delivery = ₹1.2B
    # Bottom-Up: 100,000 health-conscious professionals × ₹12,000 annual spend = ₹1.2B
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Subscription healthy meal delivery service for working professionals in Chennai",
            target_geography="Chennai",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="Chennai Health Meal Market",
                    value=1_200_000_000.0,
                    unit="INR",
                    currency="INR",
                    geography="Chennai",
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Chennai Target Working Professionals",
                    value=100_000.0,
                    unit="professionals",
                    geography="Chennai",
                ),
                pricing=EvidenceInput(
                    name="Annual Meal Plan Subscription",
                    value=12_000.0,
                    unit="INR",
                    currency="INR",
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )

    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    assert report.method_comparison.percentage_difference == 0.0
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE


def test_e2e_scenario_3_saas_accounting_india() -> None:
    """Scenario 3: Cloud SaaS accounting platform for MSMEs in India."""
    # Top-Down: India MSME accounting software TAM = ₹15B
    # Bottom-Up: 3M GST-registered MSMEs × ₹4,800/yr = ₹14.4B (~4.08% divergence)
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Automated GST and accounting SaaS for small businesses in India",
            target_geography="India",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India MSME Accounting Software TAM",
                    value=15_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    geography="India",
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="GST Registered Small Businesses",
                    value=3_000_000.0,
                    unit="businesses",
                    geography="India",
                ),
                pricing=EvidenceInput(
                    name="Monthly Software Subscription",
                    value=400.0,
                    unit="INR",
                    currency="INR",
                ),
                pricing_frequency=PriceFrequency.MONTHLY,
            ),
        )
    )

    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    # 400 * 12 = 4,800. 3M * 4,800 = 14.4B. Difference |15B - 14.4B| = 600M. Midpoint 14.7B -> 4.08%
    assert report.method_comparison.percentage_difference == pytest.approx(4.08, rel=1e-2)
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE


def test_e2e_scenario_4_fitness_app_professionals_india() -> None:
    """Scenario 4: Digital fitness subscription app for urban professionals in India."""
    # Top-Down: India digital fitness app TAM = ₹8B
    # Bottom-Up: 4M urban professionals × ₹2,400/yr = ₹9.6B (~18.18% divergence -> ACCEPTABLE)
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="AI-guided workout and nutrition app for busy professionals",
            target_geography="India",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India Digital Fitness App TAM",
                    value=8_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    geography="India",
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Urban Working Professionals with Fitness Interest",
                    value=4_000_000.0,
                    unit="users",
                    geography="India",
                ),
                pricing=EvidenceInput(
                    name="Annual App Subscription",
                    value=2_400.0,
                    unit="INR",
                    currency="INR",
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )

    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    # |8B - 9.6B| / 8.8B = 1.6 / 8.8 ≈ 18.18%
    assert report.method_comparison.percentage_difference == pytest.approx(18.18, rel=1e-2)
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE


def test_e2e_scenario_5_online_tutoring_india() -> None:
    """Scenario 5: 1-on-1 Online tutoring platform for K-12 in India."""
    # Top-Down: India K-12 online tutoring market = ₹60B
    # Bottom-Up: 5M students × ₹10,000/yr = ₹50B (~18.18% divergence -> ACCEPTABLE)
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="1-on-1 personalized live online tutoring for K-12 students",
            target_geography="India",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India K-12 Online Tutoring TAM",
                    value=60_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    geography="India",
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Private School K-12 Students in Tier 1/2 Cities",
                    value=5_000_000.0,
                    unit="students",
                    geography="India",
                ),
                pricing=EvidenceInput(
                    name="Annual Tutoring Package",
                    value=10_000.0,
                    unit="INR",
                    currency="INR",
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )

    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    # |60B - 50B| / 55B = 10 / 55 ≈ 18.18%
    assert report.method_comparison.percentage_difference == pytest.approx(18.18, rel=1e-2)
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
