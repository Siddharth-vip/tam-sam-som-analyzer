import pytest
from app.schemas.calculation import (
    AssumptionCategory,
    AssumptionImpact,
    AssumptionItem,
    AssumptionRegistry,
    AssumptionSourceType,
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationStatus,
    DivergenceSeverity,
    EvidenceInput,
    EvidenceQualityRating,
    FreshnessCategory,
    PriceFrequency,
    TopDownCalculationInputs,
)
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.validation import EvidenceConfidence
from app.services.calculation_service import CalculationService

calc_service = CalculationService()


# ---------------------------------------------------------------------------
# 1. Epistemic Classification: Facts vs User Assumptions vs Model Assumptions
# ---------------------------------------------------------------------------

def test_01_verified_fact_classification() -> None:
    """Requirement 1: Tier 1/2 authoritative evidence without assumption flag is classified as VERIFIED_EVIDENCE."""
    inp = EvidenceInput(
        name="India Higher Education Enrollment",
        value=43_000_000.0,
        unit="students",
        geography="India",
        year=2024,
        source_url="https://aishe.gov.in",
        source_name="Ministry of Education (AISHE)",
        source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
        lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
    )
    source_type, reason = calc_service._classify_assumption_source_type(inp)
    assert source_type == AssumptionSourceType.VERIFIED_EVIDENCE
    assert "authoritative" in reason or "Tier 1" in reason or "Direct empirical" in reason


def test_02_validated_fact_classification() -> None:
    """Requirement 2: Tier 3 reputable market research is classified as VALIDATED_EVIDENCE."""
    inp = EvidenceInput(
        name="India EdTech Industry Market Size",
        value=50_000_000_000.0,
        unit="INR",
        source_name="KPMG EdTech Report",
        source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
        lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
    )
    source_type, _ = calc_service._classify_assumption_source_type(inp)
    assert source_type == AssumptionSourceType.VALIDATED_EVIDENCE


def test_03_user_assumption_classification() -> None:
    """Requirement 3: Explicit user-declared price is marked as USER_ASSUMPTION."""
    inp = EvidenceInput(
        name="Annual Course Subscription Fee",
        value=6_000.0,
        unit="INR",
        currency="INR",
        is_assumption=True,
        assumption_justification="Target pricing expected from students",
    )
    source_type, _ = calc_service._classify_assumption_source_type(inp)
    assert source_type == AssumptionSourceType.USER_ASSUMPTION


def test_04_model_assumption_classification() -> None:
    """Requirement 4: General unverified reference is classified as MODEL_ASSUMPTION."""
    inp = EvidenceInput(
        name="Estimated Engineering Students Percentage",
        value=15.0,
        unit="%",
        source_quality_tier=SourceQualityTier.TIER_4_GENERAL_UNVERIFIED,
    )
    source_type, _ = calc_service._classify_assumption_source_type(inp)
    assert source_type == AssumptionSourceType.MODEL_ASSUMPTION


# ---------------------------------------------------------------------------
# 2. Evidence Freshness Evaluation
# ---------------------------------------------------------------------------

def test_05_evidence_freshness_thresholds() -> None:
    """Requirement 5: Evidence age relative to target year evaluates freshness categories correctly."""
    target_year = 2026

    # 0-2 years -> RECENT
    f_recent, age_r = calc_service.evaluate_freshness(2025, target_year)
    assert f_recent == FreshnessCategory.RECENT
    assert age_r == 1

    # 3-5 years -> MODERATELY_OLD
    f_mod, age_m = calc_service.evaluate_freshness(2022, target_year)
    assert f_mod == FreshnessCategory.MODERATELY_OLD
    assert age_m == 4

    # 6-10 years -> OLD
    f_old, age_o = calc_service.evaluate_freshness(2018, target_year)
    assert f_old == FreshnessCategory.OLD
    assert age_o == 8

    # >10 years -> VERY_OLD
    f_vold, age_vo = calc_service.evaluate_freshness(2012, target_year)
    assert f_vold == FreshnessCategory.VERY_OLD
    assert age_vo == 14


def test_06_unknown_publication_date() -> None:
    """Requirement 6: Evidence without publication date returns UNKNOWN freshness, not assumed current."""
    freshness, age = calc_service.evaluate_freshness(None, 2026)
    assert freshness == FreshnessCategory.UNKNOWN
    assert age is None


# ---------------------------------------------------------------------------
# 3. Uncertainty Scenarios: Empirical Bounds Only (No Manufactured Ranges)
# ---------------------------------------------------------------------------

def test_07_unsupported_uncertainty_range_rejected() -> None:
    """Requirement 7: Point-only inputs produce INSUFFICIENT_EVIDENCE uncertainty, NEVER manufactured +-10/20%."""
    request = CalculationInput(
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Students",
                value=40_000_000.0,
                unit="students",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="Annual Fee",
                value=5_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
        )
    )
    report = calc_service.generate_report(request)
    assert report.uncertainty_analysis is not None
    assert report.uncertainty_analysis.status == "INSUFFICIENT_EVIDENCE"
    assert report.uncertainty_analysis.tam_scenario is None
    assert "Point estimates only" in report.uncertainty_analysis.basis


def test_08_evidence_supported_uncertainty_range() -> None:
    """Requirement 8: Range-bounded evidence (4M-5M users and ₹5,000-₹6,000) derives deterministic Low/Base/High."""
    request = CalculationInput(
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Students",
                value=4_500_000.0,
                range_min=4_000_000.0,
                range_max=5_000_000.0,
                unit="students",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="Annual Fee",
                value=5_500.0,
                range_min=5_000.0,
                range_max=6_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
        )
    )
    report = calc_service.generate_report(request)
    assert report.uncertainty_analysis is not None
    assert report.uncertainty_analysis.status == "AVAILABLE"
    assert report.uncertainty_analysis.tam_scenario is not None
    # Low = 4M * ₹5,000 = ₹20B
    assert report.uncertainty_analysis.tam_scenario.low == 20_000_000_000.0
    # Base = 4.5M * ₹5,500 = ₹24.75B
    assert report.uncertainty_analysis.tam_scenario.base == 24_750_000_000.0
    # High = 5M * ₹6,000 = ₹30B
    assert report.uncertainty_analysis.tam_scenario.high == 30_000_000_000.0


# ---------------------------------------------------------------------------
# 4. Deterministic Sensitivity Analysis
# ---------------------------------------------------------------------------

def test_09_deterministic_sensitivity_ranking() -> None:
    """Requirement 9: Sensitivity analysis ranks multiplicative drivers (Price, Customers) as HIGH impact."""
    request = CalculationInput(
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Potential Target Users",
                value=2_000_000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            target_customer_percentage=EvidenceInput(
                name="Qualified Segment Pct",
                value=25.0,
                unit="%",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
            pricing=EvidenceInput(
                name="Monthly Fee",
                value=500.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
            pricing_frequency=PriceFrequency.MONTHLY,
        )
    )
    report = calc_service.generate_report(request)
    assert len(report.sensitivity_analysis) >= 2
    params_dict = {p.parameter: p for p in report.sensitivity_analysis}
    assert "annual_price" in params_dict
    assert params_dict["annual_price"].impact == "HIGH"
    assert params_dict["annual_price"].elasticity == 1.0
    assert "potential_customers" in params_dict
    assert params_dict["potential_customers"].impact == "HIGH"


# ---------------------------------------------------------------------------
# 5. Assumption Risk & Reliability Downgrades
# ---------------------------------------------------------------------------

def test_10_critical_assumption_downgrades_reliability() -> None:
    """Requirement 10: Low divergence with an unverified price assumption does NOT produce HIGH reliability."""
    # Top-down TAM = ₹25B, Bottom-up TAM = ₹25.8B (3.15% divergence = ACCEPTABLE)
    # BUT pricing is a user assumption -> Reliability must be downgraded from HIGH to LOW/MEDIUM
    request = CalculationInput(
        target_geography="India",
        target_year=2024,
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="India EdTech Macro Market",
                value=25_000_000_000.0,
                unit="INR",
                currency="INR",
                source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            )
        ),
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="College Students in India",
                value=43_000_000.0,
                unit="students",
                source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="Hypothetical User Course Price",
                value=600.0,
                unit="INR",
                currency="INR",
                is_assumption=True,
                assumption_justification="User assumption of course price",
            ),
            pricing_frequency=PriceFrequency.ANNUAL,
        ),
    )
    report = calc_service.generate_report(request)
    assert report.method_comparison is not None
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert report.reliability_assessment is not None
    # Rule: Critical price assumption prevents HIGH reliability
    assert report.reliability_assessment.level in ("LOW", "MEDIUM")
    assert report.reliability_assessment.assumption_risk in ("HIGH", "CRITICAL")
    assert "assumption" in report.reliability_assessment.reason.lower()


def test_11_old_evidence_downgrades_reliability() -> None:
    """Requirement 11: Very old evidence (>10 years) downgrades reliability."""
    request = CalculationInput(
        target_year=2026,
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="India Market 2012",
                value=10_000_000_000.0,
                unit="INR",
                currency="INR",
                published_year=2012,  # 14 years old -> VERY_OLD
                source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        ),
    )
    report = calc_service.generate_report(request)
    assert report.reliability_assessment is not None
    assert report.reliability_assessment.freshness == "VERY_OLD"
    assert report.reliability_assessment.level in ("LOW", "MEDIUM")


def test_12_high_reliability_requires_tier1_2_and_freshness() -> None:
    """Requirement 12: High reliability is granted only with Tier 1/2 authoritative evidence, recent data, and no critical assumptions."""
    request = CalculationInput(
        target_geography="India",
        target_year=2025,
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="India AISHE Higher Education Enrollment",
                value=43_000_000.0,
                unit="students",
                published_year=2024,
                source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="National Skill Council Benchmark Fee",
                value=5_000.0,
                unit="INR",
                currency="INR",
                published_year=2024,
                source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        ),
    )
    report = calc_service.generate_report(request)
    assert report.reliability_assessment is not None
    assert report.reliability_assessment.evidence_strength == "HIGH"
    assert report.reliability_assessment.assumption_risk == "LOW"
    assert report.reliability_assessment.freshness == "RECENT"
    assert report.reliability_assessment.level == "HIGH"


# ---------------------------------------------------------------------------
# 6. SOM Safety Rule Preserved
# ---------------------------------------------------------------------------

def test_13_som_safety_rule_no_arbitrary_percentages() -> None:
    """Requirement 13: SOM is NOT calculated unless evidence or explicit user capacity exists."""
    request = CalculationInput(
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Students",
                value=10_000_000.0,
                unit="students",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            target_customer_percentage=EvidenceInput(
                name="Target segment",
                value=20.0,
                unit="%",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
            pricing=EvidenceInput(
                name="Price",
                value=1_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
            # Notice: obtainable_market_share and obtainable_customers are OMITTED
        )
    )
    report = calc_service.generate_report(request)
    assert report.bottom_up_tam is not None
    assert report.bottom_up_tam.status == CalculationStatus.CALCULATED
    assert report.bottom_up_sam is not None
    assert report.bottom_up_sam.status == CalculationStatus.CALCULATED
    assert report.bottom_up_som is not None
    assert report.bottom_up_som.status == CalculationStatus.INSUFFICIENT_EVIDENCE
    assert report.bottom_up_som.estimate is None


# ---------------------------------------------------------------------------
# 7. Five Business Validation Scenarios
# ---------------------------------------------------------------------------

def test_scenario_1_online_programming_platform_india() -> None:
    """Scenario 1: Online programming platform for college students in India."""
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Affordable online programming education for engineering students in India",
            target_geography="India",
            target_year=2025,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India Higher Education & Tech Training TAM",
                    value=200_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                    published_year=2024,
                ),
                segment_percentages=[
                    EvidenceInput(
                        name="Technical & Computer Science Students Share",
                        value=25.0,
                        unit="%",
                        source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                        lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                    )
                ],
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="AISHE Total Higher Education Students in India",
                    value=43_000_000.0,
                    range_min=40_000_000.0,
                    range_max=45_000_000.0,
                    unit="students",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                    published_year=2024,
                ),
                target_customer_percentage=EvidenceInput(
                    name="Engineering & BCA Degree Students",
                    value=20.0,
                    unit="%",
                    source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing=EvidenceInput(
                    name="Annual Platform Subscription Fee",
                    value=5_000.0,
                    range_min=4_000.0,
                    range_max=6_000.0,
                    unit="INR",
                    currency="INR",
                    is_assumption=True,
                    assumption_justification="Target affordable pricing for Indian college students",
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )
    assert report.status == CalculationStatus.CALCULATED
    assert report.assumption_registry is not None
    assert report.assumption_registry.total_count >= 3
    assert report.uncertainty_analysis is not None
    assert report.uncertainty_analysis.status == "AVAILABLE"
    assert report.reliability_assessment is not None
    assert report.reliability_assessment.level in ("LOW", "MEDIUM")


def test_scenario_2_healthy_food_delivery_chennai() -> None:
    """Scenario 2: Healthy food delivery in Chennai for working professionals."""
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Healthy food delivery for working professionals in Chennai",
            target_geography="Chennai",
            target_year=2025,
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Chennai IT Corridor Working Professionals",
                    value=1_800_000.0,
                    unit="professionals",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                    published_year=2025,
                ),
                target_customer_percentage=EvidenceInput(
                    name="Health-conscious daily lunch buyers",
                    value=15.0,
                    unit="%",
                    source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                obtainable_market_share=EvidenceInput(
                    name="Year 1 Central Kitchen Delivery Capacity",
                    value=1.5,
                    unit="%",
                    is_assumption=True,
                    assumption_justification="Realistic production capacity of 4,000 daily meals",
                ),
                pricing=EvidenceInput(
                    name="Monthly Meal Plan",
                    value=3_000.0,
                    unit="INR",
                    currency="INR",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing_frequency=PriceFrequency.MONTHLY,
            ),
        )
    )
    assert report.status == CalculationStatus.CALCULATED
    assert report.bottom_up_tam.estimate == 1_800_000.0 * 36_000.0  # 64.8B
    assert report.bottom_up_som.estimate is not None  # Legitimately calculated via capacity assumption
    assert report.reliability_assessment is not None


def test_scenario_3_saas_accounting_small_businesses_india() -> None:
    """Scenario 3: SaaS accounting platform for small businesses in India."""
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="Cloud accounting software for GST registered MSMEs in India",
            target_geography="India",
            target_year=2024,
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India MSME Accounting Software Spend",
                    value=18_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                    published_year=2023,
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="GST Registered Micro & Small Enterprises",
                    value=3_500_000.0,
                    unit="businesses",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                    published_year=2023,
                ),
                pricing=EvidenceInput(
                    name="Monthly SaaS Subscription",
                    value=400.0,
                    unit="INR",
                    currency="INR",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing_frequency=PriceFrequency.MONTHLY,
            ),
        )
    )
    assert report.status == CalculationStatus.CALCULATED
    # Top-Down = ₹18B, Bottom-Up = 3.5M * ₹4,800 = ₹16.8B (~6.9% divergence -> ACCEPTABLE)
    assert report.method_comparison is not None
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert report.reliability_assessment.level in ("HIGH", "MEDIUM")


def test_scenario_4_fitness_app_professionals_india() -> None:
    """Scenario 4: Fitness subscription app for working professionals in India."""
    report = calc_service.generate_report(
        CalculationInput(
            business_idea="AI-guided workout app for urban professionals in India",
            target_geography="India",
            target_year=2024,
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Urban Working Professionals",
                    value=4_000_000.0,
                    unit="professionals",
                    source_quality_tier=SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                ),
                pricing=EvidenceInput(
                    name="Annual App Subscription",
                    value=2_400.0,
                    unit="INR",
                    currency="INR",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )
    assert report.status == CalculationStatus.CALCULATED
    assert report.bottom_up_tam.estimate == 9_600_000_000.0
    assert report.reliability_assessment is not None


def test_scenario_5_online_tutoring_india() -> None:
    """Scenario 5: 1-on-1 Online tutoring platform for K-12 in India."""
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
                    source_quality_tier=SourceQualityTier.TIER_3_ANALYST_PRESS,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Private School K-12 Students in Tier 1/2 Cities",
                    value=5_000_000.0,
                    unit="students",
                    source_quality_tier=SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                    lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
                ),
                pricing=EvidenceInput(
                    name="Annual Tutoring Package",
                    value=10_000.0,
                    unit="INR",
                    currency="INR",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing_frequency=PriceFrequency.ANNUAL,
            ),
        )
    )
    assert report.status == CalculationStatus.CALCULATED
    assert report.method_comparison is not None
    assert report.method_comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE
    assert report.reliability_assessment is not None


# ---------------------------------------------------------------------------
# 8. Consistency, Currency, Double-Counting & Audit Trail Tests
# ---------------------------------------------------------------------------

def test_14_geography_mismatch_warning() -> None:
    """Requirement 14: Geographic mismatch between top-down (India) and bottom-up (Chennai) is flagged."""
    report = calc_service.generate_report(
        CalculationInput(
            target_geography="Chennai",
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="India National Market Size",
                    value=100_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    geography="India",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Chennai City Buyers",
                    value=500_000.0,
                    unit="buyers",
                    geography="Chennai",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing=EvidenceInput(
                    name="Price",
                    value=2_000.0,
                    unit="INR",
                    currency="INR",
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
            ),
        )
    )
    assert report.method_comparison is not None
    assert any("Geographic Scope Mismatch" in d for d in report.method_comparison.root_cause_diagnostics)


def test_15_temporal_mismatch_warning() -> None:
    """Requirement 15: Benchmark temporal gaps (2020 vs 2024) are diagnosed."""
    report = calc_service.generate_report(
        CalculationInput(
            top_down_inputs=TopDownCalculationInputs(
                macro_market_size=EvidenceInput(
                    name="EdTech 2020 Spend",
                    value=10_000_000_000.0,
                    unit="INR",
                    currency="INR",
                    year=2020,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                )
            ),
            bottom_up_inputs=BottomUpCalculationInputs(
                potential_customers=EvidenceInput(
                    name="Students 2024",
                    value=10_000_000.0,
                    unit="students",
                    year=2024,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
                pricing=EvidenceInput(
                    name="Price",
                    value=1_000.0,
                    unit="INR",
                    currency="INR",
                    year=2024,
                    lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                ),
            ),
        )
    )
    assert report.method_comparison is not None
    assert any("Temporal Gap" in d for d in report.method_comparison.root_cause_diagnostics)


def test_16_currency_mismatch_rejection() -> None:
    """Requirement 16: Top-Down in USD and Bottom-Up in INR without FX evidence refuses silent conversion."""
    td_tam = calc_service.calculate_top_down_tam(
        TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Global Market",
                value=500_000_000.0,
                unit="USD",
                currency="USD",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            )
        )
    )
    bu_tam = calc_service.calculate_bottom_up_tam(
        BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Indian Users",
                value=10_000_000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="Local Pricing",
                value=500.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        )
    )
    comp = calc_service.compare_methods(td_tam, bu_tam)
    assert comp is not None
    assert comp.absolute_difference is None
    assert comp.percentage_difference is None
    assert "Currency mismatch" in comp.explanation


def test_17_double_counting_risk_detection() -> None:
    """Requirement 17: Overlapping unsegmented scope names flag a double-counting risk."""
    request = CalculationInput(
        top_down_inputs=TopDownCalculationInputs(
            macro_market_size=EvidenceInput(
                name="Indian College Students Higher Education",
                value=50_000_000_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            )
        ),
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Indian College Students Higher Education Population",
                value=40_000_000.0,
                unit="students",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
            pricing=EvidenceInput(
                name="Fee",
                value=1_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
            ),
        ),
    )
    is_risk, risks = calc_service.evaluate_double_counting_risk(request)
    assert is_risk is True
    assert any("DOUBLE_COUNTING_RISK" in r for r in risks)


def test_18_user_assumption_audit_trail_in_report() -> None:
    """Requirement 18: User-declared assumptions are tracked with full lineage in AssumptionRegistry."""
    request = CalculationInput(
        assumptions=[
            CalculationAssumption(
                name="Expected Churn Rate",
                value=5.0,
                unit="%",
                justification="Industry SaaS benchmark churn",
                is_user_provided=True,
            )
        ],
        bottom_up_inputs=BottomUpCalculationInputs(
            potential_customers=EvidenceInput(
                name="Audited Population",
                value=1_000_000.0,
                unit="users",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
            pricing=EvidenceInput(
                name="Audited Pricing",
                value=2_000.0,
                unit="INR",
                currency="INR",
                lifecycle_stage=DiscoveryLifecycleStage.VERIFIED,
            ),
        ),
    )
    report = calc_service.generate_report(request)
    assert report.assumption_registry is not None
    assert any(a.name == "Expected Churn Rate" for a in report.assumption_registry.items)
    churn_item = next(a for a in report.assumption_registry.items if a.name == "Expected Churn Rate")
    assert churn_item.is_user_provided is True
    assert churn_item.source_type == AssumptionSourceType.USER_ASSUMPTION

