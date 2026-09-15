import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.schemas.calculation import (
    ACCEPTABLE_DIVERGENCE_THRESHOLD,
    WARNING_DIVERGENCE_THRESHOLD,
    AssumptionCategory,
    AssumptionImpact,
    AssumptionItem,
    AssumptionRegistry,
    AssumptionSourceType,
    BottomUpCalculationInputs,
    CalculationAssumption,
    CalculationInput,
    CalculationMethod,
    CalculationReport,
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DivergenceSeverity,
    EvidenceInput,
    EvidenceQualityRating,
    FreshnessCategory,
    MethodComparison,
    MetricCalculationResult,
    PriceFrequency,
    ReliabilityAssessment,
    SAMResult,
    SAMTrace,
    SOMResult,
    SOMTrace,
    ScenarioEstimate,
    SensitivityParameter,
    TAMResult,
    TAMTrace,
    TopDownCalculationInputs,
    UncertaintyAnalysis,
    UncertaintyInterval,
)
from app.schemas.discovery import SourceQualityTier
from app.schemas.validation import EvidenceConfidence


class CalculationServiceException(Exception):
    """Base exception for market sizing calculation errors."""
    pass


class CalculationService:
    """Deterministic, auditable calculation engine for TAM, SAM, and SOM.

    Operates strictly on validated evidence and explicit assumptions with zero numerical hallucination.
    """

    # -----------------------------------------------------------------------
    # Evidence Quality & Consistency Evaluation
    # -----------------------------------------------------------------------

    def _evaluate_result_evidence_quality(
        self,
        inputs: List[EvidenceInput],
        has_warnings: bool,
        status: CalculationStatus,
    ) -> Tuple[EvidenceQualityRating, List[str]]:
        """Evaluate transparent Evidence Quality Rating (HIGH, MEDIUM, LOW, INSUFFICIENT) for a metric."""
        if status != CalculationStatus.CALCULATED:
            return EvidenceQualityRating.INSUFFICIENT, ["Metric could not be calculated due to missing or conflicting evidence."]

        reasons: List[str] = []
        valid_inputs = [i for i in inputs if i is not None]
        tier1_count = sum(1 for i in valid_inputs if i.source_quality_tier == SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL)
        tier2_count = sum(1 for i in valid_inputs if i.source_quality_tier == SourceQualityTier.TIER_2_ACADEMIC_TRADE)
        tier3_count = sum(1 for i in valid_inputs if i.source_quality_tier == SourceQualityTier.TIER_3_ANALYST_PRESS)
        tier4_count = sum(1 for i in valid_inputs if i.source_quality_tier == SourceQualityTier.TIER_4_GENERAL_UNVERIFIED)
        assumption_count = sum(1 for i in valid_inputs if i.is_assumption)
        prior_year_count = sum(1 for i in valid_inputs if i.is_prior_year_benchmark)

        if tier1_count > 0:
            reasons.append(f"Supported by {tier1_count} Tier 1 authoritative/government official source(s).")
        if tier2_count > 0:
            reasons.append(f"Supported by {tier2_count} Tier 2 academic or industry trade association source(s).")
        if tier3_count > 0:
            reasons.append(f"Supported by {tier3_count} Tier 3 market research/press source(s).")
        if tier4_count > 0:
            reasons.append(f"Contains {tier4_count} Tier 4 general web source(s) with lower evidentiary weight.")
        if prior_year_count > 0:
            reasons.append(f"Utilizes {prior_year_count} prior-year benchmark(s) as latest available authoritative baseline.")
        if assumption_count > 0:
            reasons.append(f"Relies on {assumption_count} explicit user-declared assumption(s).")

        # Rating determination
        if assumption_count >= 2 or tier4_count >= 2:
            return EvidenceQualityRating.LOW, reasons or ["Multiple unverified assumptions or low-tier sources used."]
        elif (tier1_count >= 1 or tier2_count >= 1) and assumption_count == 0 and not has_warnings:
            return EvidenceQualityRating.HIGH, reasons or ["High-confidence calculation backed by Tier 1/2 authoritative evidence."]
        elif (tier1_count >= 1 or tier2_count >= 1 or tier3_count >= 1):
            return EvidenceQualityRating.MEDIUM, reasons or ["Medium-confidence calculation backed by reputable evidence."]
        else:
            return EvidenceQualityRating.LOW, reasons or ["Calculation relies primarily on assumptions or lower-tier sources."]

    def _check_bottom_up_unit_compatibility(
        self,
        customers: Optional[EvidenceInput],
        pricing: Optional[EvidenceInput],
    ) -> List[str]:
        """Check compatibility between customer population entity concept and pricing unit."""
        warnings: List[str] = []
        if not customers or not pricing:
            return warnings

        # Entity concept checking
        c_entity = (customers.entity_concept or customers.unit or "").lower()
        p_entity = (pricing.entity_concept or pricing.name or "").lower()

        # Check for incompatible entities (e.g. multiplying household count by per-student pricing)
        if "household" in c_entity and any(k in p_entity for k in ("student", "developer", "per person", "individual")):
            warnings.append(
                f"Entity unit mismatch warning: Customer population is in '{c_entity}' but pricing is '{p_entity}'. "
                f"A household may contain multiple individuals or vice versa."
            )
        elif "enterprise" in c_entity and any(k in p_entity for k in ("per user", "per student", "consumer", "individual")):
            warnings.append(
                f"Entity unit mismatch warning: Customer population is enterprise/B2B ('{c_entity}') while pricing appears per-individual ('{p_entity}')."
            )

        # Currency mismatch check if both have explicit currencies
        if customers.currency and pricing.currency and customers.currency.upper() != pricing.currency.upper():
            warnings.append(
                f"Currency divergence warning: Customer metric has currency '{customers.currency}' while pricing has '{pricing.currency}'."
            )

        return warnings

    # -----------------------------------------------------------------------
    # 1. Top-Down Calculation Pipeline
    # -----------------------------------------------------------------------

    def calculate_top_down_tam(self, inputs: TopDownCalculationInputs) -> TAMResult:
        """Calculate Top-Down TAM from starting macro market size and initial segment percentages."""
        if not inputs or not inputs.macro_market_size:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: Missing required starting macro_market_size for top-down TAM.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing required starting macro market size evidence."],
            )

        macro = inputs.macro_market_size
        if macro.value is None:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: macro_market_size does not contain a numerical value.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["macro_market_size contains no numerical value."],
            )

        if macro.is_conflict:
            return TAMResult(
                status=CalculationStatus.CONFLICT,
                message=(
                    f"Top-down TAM halted due to unresolved conflicting evidence for '{macro.name}'. "
                    f"Conflicting values: {macro.conflicting_values}."
                ),
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Unresolved conflicting evidence for macro market size."],
            )

        steps: List[CalculationStep] = []
        assumptions: List[CalculationAssumption] = []
        warnings: List[str] = []

        current_val = macro.value
        current_low = macro.range_min if macro.range_min is not None else macro.value
        current_high = macro.range_max if macro.range_max is not None else macro.value

        if macro.is_assumption:
            assumptions.append(
                CalculationAssumption(
                    name=macro.name,
                    value=macro.value,
                    unit=macro.unit,
                    justification=macro.assumption_justification or "User-provided assumption",
                )
            )

        # Base Macro Sizing Step
        steps.append(
            CalculationStep(
                step_number=1,
                description=f"Starting macro market size: {macro.name}",
                formula="Base Macro Market Size",
                operands={macro.name: macro.value},
                result=current_val,
                result_interval=UncertaintyInterval(lower=current_low, point=current_val, upper=current_high),
                unit=macro.unit,
                evidence_references=[macro.source_url or macro.evidence_id or "Direct Input"],
                assumptions=[macro.name] if macro.is_assumption else [],
            )
        )

        step_idx = 2
        for seg_pct in inputs.segment_percentages:
            if seg_pct.value is None:
                continue
            if seg_pct.is_conflict:
                return TAMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Top-down TAM halted: segment percentage '{seg_pct.name}' contains conflicting evidence.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=[f"Segment percentage '{seg_pct.name}' contains conflicting evidence."],
                )

            factor = seg_pct.value / 100.0
            factor_low = (seg_pct.range_min / 100.0) if seg_pct.range_min is not None else factor
            factor_high = (seg_pct.range_max / 100.0) if seg_pct.range_max is not None else factor

            current_val = current_val * factor
            current_low = current_low * factor_low
            current_high = current_high * factor_high

            if seg_pct.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=seg_pct.name,
                        value=seg_pct.value,
                        unit=seg_pct.unit,
                        justification=seg_pct.assumption_justification or "Segment assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=step_idx,
                    description=f"Apply segment filter: {seg_pct.name} ({seg_pct.value}%)",
                    formula=f"Previous TAM × ({seg_pct.name} / 100)",
                    operands={"previous": steps[-1].result, seg_pct.name: seg_pct.value},
                    result=current_val,
                    result_interval=UncertaintyInterval(lower=current_low, point=current_val, upper=current_high),
                    unit=macro.unit,
                    evidence_references=[seg_pct.source_url or seg_pct.evidence_id or "Segment Filter"],
                    assumptions=[seg_pct.name] if seg_pct.is_assumption else [],
                )
            )
            step_idx += 1

        # Check for unsegmented parent market warning
        if (macro.market_scope in ("Parent market", "PARENT_MARKET") or "parent market" in (macro.entity_concept or "").lower()) and not inputs.segment_percentages:
            warnings.append(
                f"Parent-market warning: '{macro.name}' represents an aggregate parent market. "
                "Without evidence-backed segmentation percentages, using broad parent industry revenue risks parent-market inflation."
            )

        interval = UncertaintyInterval(lower=current_low, point=current_val, upper=current_high)
        confidence = self._evaluate_confidence([macro] + inputs.segment_percentages)
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            [macro] + inputs.segment_percentages,
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return TAMResult(
            status=CalculationStatus.CALCULATED,
            estimate=current_val,
            interval=interval,
            unit=macro.unit,
            currency=macro.currency,
            year=macro.year,
            geography=macro.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Addressable market",
            market_scope_explanation="Total Addressable Market (TAM): Maximum realistic total market demand for the specific product/service offering within the target geography.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Top-down TAM successfully calculated from evidence.",
        )

    def calculate_top_down_sam(
        self, tam_result: TAMResult, inputs: TopDownCalculationInputs
    ) -> SAMResult:
        """Calculate Top-Down SAM by applying serviceable geography, target segment, and channel filters to TAM."""
        if not tam_result or tam_result.status != CalculationStatus.CALCULATED or tam_result.estimate is None:
            return SAMResult(
                status=tam_result.status if tam_result else CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Cannot calculate SAM: Top-down TAM is not successfully calculated.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Cannot calculate SAM because Top-Down TAM is not available."],
            )

        steps: List[CalculationStep] = list(tam_result.steps)
        assumptions: List[CalculationAssumption] = list(tam_result.assumptions_used)
        warnings: List[str] = list(tam_result.warnings)

        current_val = tam_result.estimate
        current_low = tam_result.interval.lower if tam_result.interval and tam_result.interval.lower is not None else current_val
        current_high = tam_result.interval.upper if tam_result.interval and tam_result.interval.upper is not None else current_val

        narrowing_factors: List[EvidenceInput] = []

        # 1. Geography filter if provided
        if inputs.serviceable_geography_percentage and inputs.serviceable_geography_percentage.value is not None:
            geo_pct = inputs.serviceable_geography_percentage
            if geo_pct.is_conflict:
                return SAMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Top-down SAM halted due to conflicting serviceable geography evidence: {geo_pct.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting serviceable geography percentage."],
                )
            narrowing_factors.append(geo_pct)
            geo_factor = geo_pct.value / 100.0
            geo_low = (geo_pct.range_min / 100.0) if geo_pct.range_min is not None else geo_factor
            geo_high = (geo_pct.range_max / 100.0) if geo_pct.range_max is not None else geo_factor

            current_val = current_val * geo_factor
            current_low = current_low * geo_low
            current_high = current_high * geo_high

            if geo_pct.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=geo_pct.name,
                        value=geo_pct.value,
                        unit=geo_pct.unit,
                        justification=geo_pct.assumption_justification or "Serviceable geography assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Filter serviceable geography: {geo_pct.name} ({geo_pct.value}%)",
                    formula=f"Previous × ({geo_pct.name} / 100)",
                    operands={"previous": steps[-1].result, geo_pct.name: geo_pct.value},
                    result=current_val,
                    result_interval=UncertaintyInterval(lower=current_low, point=current_val, upper=current_high),
                    unit=tam_result.unit or "Currency",
                    evidence_references=[geo_pct.source_url or geo_pct.evidence_id or "Geo Filter"],
                    assumptions=[geo_pct.name] if geo_pct.is_assumption else [],
                )
            )

        # 2. Target customer segment filter if provided
        if inputs.target_segment_percentage and inputs.target_segment_percentage.value is not None:
            seg_pct = inputs.target_segment_percentage
            if seg_pct.is_conflict:
                return SAMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Top-down SAM halted due to conflicting target segment percentage evidence: {seg_pct.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting target segment percentage."],
                )
            narrowing_factors.append(seg_pct)
            seg_factor = seg_pct.value / 100.0
            seg_low = (seg_pct.range_min / 100.0) if seg_pct.range_min is not None else seg_factor
            seg_high = (seg_pct.range_max / 100.0) if seg_pct.range_max is not None else seg_factor

            current_val = current_val * seg_factor
            current_low = current_low * seg_low
            current_high = current_high * seg_high

            if seg_pct.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=seg_pct.name,
                        value=seg_pct.value,
                        unit=seg_pct.unit,
                        justification=seg_pct.assumption_justification or "Target segment assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Filter target customer segment: {seg_pct.name} ({seg_pct.value}%)",
                    formula=f"Previous × ({seg_pct.name} / 100)",
                    operands={"previous": steps[-1].result, seg_pct.name: seg_pct.value},
                    result=current_val,
                    result_interval=UncertaintyInterval(lower=current_low, point=current_val, upper=current_high),
                    unit=tam_result.unit or "Currency",
                    evidence_references=[seg_pct.source_url or seg_pct.evidence_id or "Segment Filter"],
                    assumptions=[seg_pct.name] if seg_pct.is_assumption else [],
                )
            )

        # 3. Other explicit filters if provided
        for flt in getattr(inputs, "other_filters", []):
            if flt and flt.value is not None:
                if flt.is_conflict:
                    return SAMResult(
                        status=CalculationStatus.CONFLICT,
                        message=f"Top-down SAM halted due to conflicting filter evidence: {flt.conflicting_values}.",
                        evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                        evidence_quality_reasons=["Conflicting filter evidence."],
                    )
                narrowing_factors.append(flt)
                flt_factor = flt.value / 100.0
                flt_low = (flt.range_min / 100.0) if flt.range_min is not None else flt_factor
                flt_high = (flt.range_max / 100.0) if flt.range_max is not None else flt_factor

                current_val = current_val * flt_factor
                current_low = current_low * flt_low
                current_high = current_high * flt_high

                if flt.is_assumption:
                    assumptions.append(
                        CalculationAssumption(
                            name=flt.name,
                            value=flt.value,
                            unit=flt.unit,
                            justification=flt.assumption_justification or "Filter assumption",
                        )
                    )

                steps.append(
                    CalculationStep(
                        step_number=len(steps) + 1,
                        description=f"Filter {flt.name}: ({flt.value}%)",
                        formula=f"Previous × ({flt.name} / 100)",
                        operands={"previous": steps[-1].result, flt.name: flt.value},
                        result=current_val,
                        result_interval=UncertaintyInterval(lower=current_low, point=current_val, upper=current_high),
                        unit=tam_result.unit or "Currency",
                        evidence_references=[flt.source_url or flt.evidence_id or "Filter"],
                        assumptions=[flt.name] if flt.is_assumption else [],
                    )
                )

        if not narrowing_factors:
            return SAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                estimate=None,
                interval=None,
                unit=tam_result.unit,
                currency=tam_result.currency,
                year=tam_result.year,
                geography=tam_result.geography,
                confidence=EvidenceConfidence.LOW,
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing quantitative serviceable market evidence (geography or customer segment percentage)."],
                market_scope="Serviceable market",
                market_scope_explanation="Serviceable Addressable Market (SAM): Specific portion of TAM reachable based on customer persona, geography, and distribution channels.",
                steps=steps,
                assumptions_used=assumptions,
                warnings=warnings + ["SAM could not be calculated: No serviceable market narrowing evidence (geography/customer segment filters) was available."],
                message="Insufficient evidence: No serviceable market narrowing factors (e.g. serviceable geography or target segment percentages) were provided to derive SAM from TAM.",
            )

        # Invariant enforcement: 0 <= SAM <= TAM
        if tam_result.estimate is not None and current_val > tam_result.estimate:
            current_val = tam_result.estimate
            warnings.append(f"SAM was clamped to not exceed TAM ({tam_result.estimate:,.0f}).")
        if current_val < 0.0:
            current_val = 0.0

        interval = UncertaintyInterval(lower=current_low, point=current_val, upper=current_high)
        confidence = self._evaluate_confidence(narrowing_factors, base_confidence=tam_result.confidence)
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            narrowing_factors,
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return SAMResult(
            status=CalculationStatus.CALCULATED,
            estimate=current_val,
            interval=interval,
            unit=tam_result.unit,
            currency=tam_result.currency,
            year=tam_result.year,
            geography=tam_result.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Serviceable market",
            market_scope_explanation="Serviceable Addressable Market (SAM): Specific portion of TAM reachable based on customer persona, geography, and distribution channels.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Top-down SAM successfully calculated from evidence.",
        )

    def calculate_top_down_som(
        self, sam_result: SAMResult, inputs: TopDownCalculationInputs
    ) -> SOMResult:
        """Calculate Top-Down SOM by applying evidence-supported or explicit obtainable market share to SAM."""
        if not sam_result or sam_result.status != CalculationStatus.CALCULATED or sam_result.estimate is None:
            return SOMResult(
                status=sam_result.status if sam_result else CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Cannot calculate SOM: Top-down SAM is not successfully calculated.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Cannot calculate SOM because Top-Down SAM is not available."],
            )

        # SOM SAFETY RULE: Must NOT invent arbitrary market share percentage
        share_input = inputs.obtainable_market_share
        if not share_input or share_input.value is None:
            return SOMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message=(
                    "Insufficient evidence: SOM safety rule strictly forbids arbitrary market share percentages. "
                    "Obtainable market share evidence or an explicit user assumption is required to calculate SOM."
                ),
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=[
                    "SOM Safety Rule: Withheld because obtainable market share evidence was not provided."
                ],
            )

        if share_input.is_conflict:
            return SOMResult(
                status=CalculationStatus.CONFLICT,
                message=(
                    f"Top-down SOM halted due to conflicting market share evidence: {share_input.conflicting_values}."
                ),
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Conflicting market share evidence."],
            )

        steps: List[CalculationStep] = list(sam_result.steps)
        assumptions: List[CalculationAssumption] = list(sam_result.assumptions_used)
        warnings: List[str] = list(sam_result.warnings)

        share_ratio = share_input.value / 100.0
        share_low = (share_input.range_min / 100.0) if share_input.range_min is not None else share_ratio
        share_high = (share_input.range_max / 100.0) if share_input.range_max is not None else share_ratio

        sam_val = sam_result.estimate
        sam_low = sam_result.interval.lower if sam_result.interval and sam_result.interval.lower is not None else sam_val
        sam_high = sam_result.interval.upper if sam_result.interval and sam_result.interval.upper is not None else sam_val

        som_val = sam_val * share_ratio
        som_low = sam_low * share_low
        som_high = sam_high * share_high

        # Invariant enforcement: 0 <= SOM <= SAM
        if sam_result.estimate is not None and som_val > sam_result.estimate:
            som_val = sam_result.estimate
            warnings.append(f"SOM was clamped to not exceed SAM ({sam_result.estimate:,.0f}).")
        if som_val < 0.0:
            som_val = 0.0

        if share_input.is_assumption:
            assumptions.append(
                CalculationAssumption(
                    name=share_input.name,
                    value=share_input.value,
                    unit=share_input.unit,
                    justification=share_input.assumption_justification or "Target SOM capture assumption",
                )
            )

        steps.append(
            CalculationStep(
                step_number=len(steps) + 1,
                description=f"Apply obtainable market share: {share_input.name} ({share_input.value}%)",
                formula=f"SAM × ({share_input.name} / 100)",
                operands={"SAM": sam_val, share_input.name: share_input.value},
                result=som_val,
                result_interval=UncertaintyInterval(lower=som_low, point=som_val, upper=som_high),
                unit=sam_result.unit or "Currency",
                evidence_references=[share_input.source_url or share_input.evidence_id or "SOM Share"],
                assumptions=[share_input.name] if share_input.is_assumption else [],
            )
        )

        interval = UncertaintyInterval(lower=som_low, point=som_val, upper=som_high)
        confidence = self._evaluate_confidence([share_input], base_confidence=sam_result.confidence)
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            [share_input],
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return SOMResult(
            status=CalculationStatus.CALCULATED,
            estimate=som_val,
            interval=interval,
            unit=sam_result.unit,
            currency=sam_result.currency,
            year=sam_result.year,
            geography=sam_result.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Obtainable market",
            market_scope_explanation="Serviceable Obtainable Market (SOM): Realistic near-term obtainable market share given operational capacity and competitive dynamics.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Top-down SOM successfully calculated from evidence and market share.",
        )

    # -----------------------------------------------------------------------
    # 2. Bottom-Up Calculation Pipeline
    # -----------------------------------------------------------------------

    def calculate_bottom_up_tam(self, inputs: BottomUpCalculationInputs) -> TAMResult:
        """Calculate Bottom-Up TAM = Potential Customers × Annual Revenue Per Customer."""
        if not inputs or not inputs.potential_customers:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: Missing required potential_customers population for bottom-up TAM.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing required customer population evidence."],
            )

        if not inputs.pricing:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: Missing required pricing/ARPU evidence for bottom-up TAM.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing required pricing/ARPU evidence."],
            )

        customers = inputs.potential_customers
        pricing = inputs.pricing

        if customers.value is None:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: potential_customers does not contain a numerical count.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["potential_customers contains no numerical count."],
            )

        if pricing.value is None:
            return TAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: pricing does not contain a numerical value.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["pricing contains no numerical value."],
            )

        if customers.is_conflict:
            return TAMResult(
                status=CalculationStatus.CONFLICT,
                message=f"Bottom-up TAM halted due to conflicting customer population evidence: {customers.conflicting_values}.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Conflicting customer population evidence."],
            )

        if pricing.is_conflict:
            return TAMResult(
                status=CalculationStatus.CONFLICT,
                message=f"Bottom-up TAM halted due to conflicting pricing evidence: {pricing.conflicting_values}.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Conflicting pricing evidence."],
            )

        steps: List[CalculationStep] = []
        assumptions: List[CalculationAssumption] = []
        warnings: List[str] = []

        # Check year alignment
        if customers.year and pricing.year and customers.year != pricing.year:
            warnings.append(
                f"Year mismatch: Customer population is from year {customers.year}, while pricing benchmark is from year {pricing.year}."
            )

        # Unit & entity compatibility checking
        unit_compat_warns = self._check_bottom_up_unit_compatibility(customers, pricing)
        warnings.extend(unit_compat_warns)

        # Prior-year benchmark notes
        if customers.is_prior_year_benchmark:
            warnings.append(
                f"Prior-year benchmark note: Customer population ({customers.name}) is from {customers.year}, "
                "used as the latest authoritative available baseline."
            )
        if pricing.is_prior_year_benchmark:
            warnings.append(
                f"Prior-year benchmark note: Pricing ({pricing.name}) is from {pricing.year}, "
                "used as the latest authoritative available baseline."
            )

        # Handle Monthly vs Annual Pricing Conversion
        annual_price = pricing.value
        annual_price_low = pricing.range_min if pricing.range_min is not None else annual_price
        annual_price_high = pricing.range_max if pricing.range_max is not None else annual_price

        if inputs.pricing_frequency == PriceFrequency.MONTHLY:
            annual_price = pricing.value * 12.0
            annual_price_low = annual_price_low * 12.0
            annual_price_high = annual_price_high * 12.0
            steps.append(
                CalculationStep(
                    step_number=1,
                    description=f"Convert monthly price to annual revenue per user: {pricing.value} × 12",
                    formula="Monthly Price × 12",
                    operands={"monthly_price": pricing.value, "months": 12},
                    result=annual_price,
                    result_interval=UncertaintyInterval(lower=annual_price_low, point=annual_price, upper=annual_price_high),
                    unit=f"{pricing.currency or pricing.unit}/user/year",
                    evidence_references=[pricing.source_url or pricing.evidence_id or "Pricing"],
                    assumptions=[pricing.name] if pricing.is_assumption else [],
                )
            )

        cust_val = customers.value
        cust_low = customers.range_min if customers.range_min is not None else cust_val
        cust_high = customers.range_max if customers.range_max is not None else cust_val

        tam_val = cust_val * annual_price
        tam_low = cust_low * annual_price_low
        tam_high = cust_high * annual_price_high

        if customers.is_assumption:
            assumptions.append(
                CalculationAssumption(
                    name=customers.name,
                    value=customers.value,
                    unit=customers.unit,
                    justification=customers.assumption_justification or "Customer population assumption",
                )
            )
        if pricing.is_assumption:
            assumptions.append(
                CalculationAssumption(
                    name=pricing.name,
                    value=pricing.value,
                    unit=pricing.unit,
                    justification=pricing.assumption_justification or "Pricing assumption",
                )
            )

        output_unit = f"{pricing.currency or 'USD'}/year"
        steps.append(
            CalculationStep(
                step_number=len(steps) + 1,
                description="Bottom-up TAM = Potential Customers × Annual Price",
                formula="Potential Customers × Annual ARPU",
                operands={"potential_customers": cust_val, "annual_arpu": annual_price},
                result=tam_val,
                result_interval=UncertaintyInterval(lower=tam_low, point=tam_val, upper=tam_high),
                unit=output_unit,
                evidence_references=[
                    customers.source_url or customers.evidence_id or "Population",
                    pricing.source_url or pricing.evidence_id or "Pricing",
                ],
                assumptions=[a.name for a in assumptions],
                warnings=warnings,
            )
        )

        interval = UncertaintyInterval(lower=tam_low, point=tam_val, upper=tam_high)
        confidence = self._evaluate_confidence([customers, pricing])
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            [customers, pricing],
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return TAMResult(
            status=CalculationStatus.CALCULATED,
            estimate=tam_val,
            interval=interval,
            unit=output_unit,
            currency=pricing.currency,
            year=customers.year or pricing.year,
            geography=customers.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Addressable market",
            market_scope_explanation="Total Addressable Market (TAM): Maximum realistic total market demand calculated from potential customer population and annual pricing.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Bottom-up TAM successfully calculated from unit economics.",
        )

    def calculate_bottom_up_sam(
        self, tam_result: TAMResult, inputs: BottomUpCalculationInputs
    ) -> SAMResult:
        """Calculate Bottom-Up SAM = Serviceable Customers × Annual Revenue Per Customer."""
        if not tam_result or tam_result.status != CalculationStatus.CALCULATED or tam_result.estimate is None:
            return SAMResult(
                status=tam_result.status if tam_result else CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Cannot calculate SAM: Bottom-up TAM is not successfully calculated.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Cannot calculate SAM because Bottom-Up TAM is not available."],
            )

        if not inputs.pricing or inputs.pricing.value is None:
            return SAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: Missing pricing information for bottom-up SAM.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing pricing evidence for bottom-up SAM."],
            )

        # Determine Serviceable Customers: either directly supplied or derived from target_customer_percentage
        serviceable_count: Optional[float] = None
        serviceable_low: Optional[float] = None
        serviceable_high: Optional[float] = None
        eval_inputs: List[EvidenceInput] = [inputs.pricing]

        steps: List[CalculationStep] = list(tam_result.steps)
        assumptions: List[CalculationAssumption] = list(tam_result.assumptions_used)
        warnings: List[str] = list(tam_result.warnings)

        annual_price = inputs.pricing.value * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)
        annual_price_low = (inputs.pricing.range_min or inputs.pricing.value) * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)
        annual_price_high = (inputs.pricing.range_max or inputs.pricing.value) * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)

        if inputs.serviceable_customers and inputs.serviceable_customers.value is not None:
            srv = inputs.serviceable_customers
            if srv.is_conflict:
                return SAMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Bottom-up SAM halted due to conflicting serviceable customers evidence: {srv.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting serviceable customer evidence."],
                )
            serviceable_count = srv.value
            serviceable_low = srv.range_min if srv.range_min is not None else serviceable_count
            serviceable_high = srv.range_max if srv.range_max is not None else serviceable_count
            eval_inputs.append(srv)

            if srv.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=srv.name,
                        value=srv.value,
                        unit=srv.unit,
                        justification=srv.assumption_justification or "Serviceable customer count assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Directly supplied serviceable customer count: {srv.name}",
                    formula="Direct Serviceable Customer Input",
                    operands={srv.name: srv.value},
                    result=serviceable_count,
                    result_interval=UncertaintyInterval(lower=serviceable_low, point=serviceable_count, upper=serviceable_high),
                    unit=srv.unit,
                    evidence_references=[srv.source_url or srv.evidence_id or "Serviceable Customers"],
                    assumptions=[srv.name] if srv.is_assumption else [],
                )
            )

        elif inputs.target_customer_percentage and inputs.target_customer_percentage.value is not None:
            pct = inputs.target_customer_percentage
            if pct.is_conflict:
                return SAMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Bottom-up SAM halted due to conflicting target customer percentage evidence: {pct.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting target customer percentage evidence."],
                )
            if not inputs.potential_customers or inputs.potential_customers.value is None:
                return SAMResult(
                    status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                    message="Insufficient evidence: potential_customers count missing to apply target_customer_percentage.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Missing potential customers count to apply target %."],
                )

            p_val = inputs.potential_customers.value
            p_low = inputs.potential_customers.range_min if inputs.potential_customers.range_min is not None else p_val
            p_high = inputs.potential_customers.range_max if inputs.potential_customers.range_max is not None else p_val

            ratio = pct.value / 100.0
            ratio_low = (pct.range_min / 100.0) if pct.range_min is not None else ratio
            ratio_high = (pct.range_max / 100.0) if pct.range_max is not None else ratio

            serviceable_count = p_val * ratio
            serviceable_low = p_low * ratio_low
            serviceable_high = p_high * ratio_high
            eval_inputs.extend([inputs.potential_customers, pct])

            if pct.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=pct.name,
                        value=pct.value,
                        unit=pct.unit,
                        justification=pct.assumption_justification or "Target customer % assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Derive serviceable customers: Potential Customers × {pct.name} ({pct.value}%)",
                    formula="Potential Customers × (Target % / 100)",
                    operands={"potential_customers": p_val, pct.name: pct.value},
                    result=serviceable_count,
                    result_interval=UncertaintyInterval(lower=serviceable_low, point=serviceable_count, upper=serviceable_high),
                    unit=inputs.potential_customers.unit,
                    evidence_references=[pct.source_url or pct.evidence_id or "Target Customer %"],
                    assumptions=[pct.name] if pct.is_assumption else [],
                )
            )
        else:
            return SAMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                estimate=None,
                interval=None,
                unit=f"{inputs.pricing.currency or 'USD'}/year",
                currency=inputs.pricing.currency,
                year=inputs.pricing.year,
                geography=inputs.pricing.geography,
                confidence=EvidenceConfidence.LOW,
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing serviceable customer segmentation evidence."],
                market_scope="Serviceable market",
                market_scope_explanation="Serviceable Addressable Market (SAM): Portion of potential customer population that is serviceable.",
                steps=steps,
                assumptions_used=assumptions,
                warnings=warnings + ["SAM could not be calculated: Missing serviceable customer count or target customer qualification percentage."],
                message=(
                    "Insufficient evidence: Missing serviceable customer segmentation evidence "
                    "(e.g. serviceable customer count or target customer qualification percentage) to derive SAM from TAM."
                ),
            )

        sam_val = serviceable_count * annual_price
        sam_low = serviceable_low * annual_price_low
        sam_high = serviceable_high * annual_price_high

        # Funnel Invariant: SAM <= TAM
        if tam_result.estimate is not None and sam_val > tam_result.estimate:
            sam_val = tam_result.estimate
            warnings.append(f"SAM was clamped to not exceed TAM ({tam_result.estimate:,.0f}).")

        steps.append(
            CalculationStep(
                step_number=len(steps) + 1,
                description="Bottom-up SAM = Serviceable Customers × Annual Price",
                formula="Serviceable Customers × Annual ARPU",
                operands={"serviceable_customers": serviceable_count, "annual_arpu": annual_price},
                result=sam_val,
                result_interval=UncertaintyInterval(lower=sam_low, point=sam_val, upper=sam_high),
                unit=tam_result.unit or "USD/year",
                evidence_references=[inputs.pricing.source_url or inputs.pricing.evidence_id or "Pricing"],
                assumptions=[a.name for a in assumptions],
            )
        )

        interval = UncertaintyInterval(lower=sam_low, point=sam_val, upper=sam_high)
        confidence = self._evaluate_confidence(eval_inputs, base_confidence=tam_result.confidence)
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            eval_inputs,
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return SAMResult(
            status=CalculationStatus.CALCULATED,
            estimate=sam_val,
            interval=interval,
            unit=tam_result.unit,
            currency=tam_result.currency,
            year=tam_result.year,
            geography=tam_result.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Serviceable market",
            market_scope_explanation="Serviceable Addressable Market (SAM): Specific portion of TAM reachable by filtering for the serviceable target customer segment.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Bottom-up SAM successfully calculated.",
        )

    def calculate_bottom_up_som(
        self, sam_result: SAMResult, inputs: BottomUpCalculationInputs
    ) -> SOMResult:
        """Calculate Bottom-Up SOM = Obtainable Customers × Annual Revenue Per Customer."""
        if not sam_result or sam_result.status != CalculationStatus.CALCULATED or sam_result.estimate is None:
            return SOMResult(
                status=sam_result.status if sam_result else CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Cannot calculate SOM: Bottom-up SAM is not successfully calculated.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Cannot calculate SOM because Bottom-Up SAM is not available."],
            )

        if not inputs.pricing or inputs.pricing.value is None:
            return SOMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message="Insufficient evidence: Missing pricing information for bottom-up SOM.",
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=["Missing pricing evidence for bottom-up SOM."],
            )

        # SOM SAFETY RULE: Must not invent obtainable customers or market share
        has_obtainable_cust = inputs.realistically_obtainable_customers and inputs.realistically_obtainable_customers.value is not None
        has_obtainable_share = inputs.obtainable_market_share and inputs.obtainable_market_share.value is not None

        if not has_obtainable_cust and not has_obtainable_share:
            return SOMResult(
                status=CalculationStatus.INSUFFICIENT_EVIDENCE,
                message=(
                    "Insufficient evidence: SOM safety rule strictly forbids arbitrary market share percentages. "
                    "Neither realistically_obtainable_customers nor obtainable_market_share was provided."
                ),
                evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                evidence_quality_reasons=[
                    "SOM Safety Rule: Withheld because obtainable customer evidence or market share was not provided."
                ],
            )

        steps: List[CalculationStep] = list(sam_result.steps)
        assumptions: List[CalculationAssumption] = list(sam_result.assumptions_used)
        warnings: List[str] = list(sam_result.warnings)

        annual_price = inputs.pricing.value * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)
        annual_price_low = (inputs.pricing.range_min or inputs.pricing.value) * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)
        annual_price_high = (inputs.pricing.range_max or inputs.pricing.value) * (12.0 if inputs.pricing_frequency == PriceFrequency.MONTHLY else 1.0)

        som_val: float
        som_low: float
        som_high: float
        eval_inputs: List[EvidenceInput] = [inputs.pricing]

        if has_obtainable_cust:
            obt = inputs.realistically_obtainable_customers
            if obt.is_conflict:
                return SOMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Bottom-up SOM halted due to conflicting obtainable customer evidence: {obt.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting obtainable customer evidence."],
                )
            obt_val = obt.value
            obt_low = obt.range_min if obt.range_min is not None else obt_val
            obt_high = obt.range_max if obt.range_max is not None else obt_val
            eval_inputs.append(obt)

            som_val = obt_val * annual_price
            som_low = obt_low * annual_price_low
            som_high = obt_high * annual_price_high

            if obt.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=obt.name,
                        value=obt.value,
                        unit=obt.unit,
                        justification=obt.assumption_justification or "Target obtainable customer assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Apply realistically obtainable customers: {obt.name} ({obt.value:,.0f} {obt.unit})",
                    formula="Obtainable Customers × Annual ARPU",
                    operands={"obtainable_customers": obt_val, "annual_arpu": annual_price},
                    result=som_val,
                    result_interval=UncertaintyInterval(lower=som_low, point=som_val, upper=som_high),
                    unit=sam_result.unit or "USD/year",
                    evidence_references=[obt.source_url or obt.evidence_id or "Obtainable Customers"],
                    assumptions=[obt.name] if obt.is_assumption else [],
                )
            )
        else:
            obt_share = inputs.obtainable_market_share
            if obt_share.is_conflict:
                return SOMResult(
                    status=CalculationStatus.CONFLICT,
                    message=f"Bottom-up SOM halted due to conflicting obtainable market share evidence: {obt_share.conflicting_values}.",
                    evidence_quality=EvidenceQualityRating.INSUFFICIENT,
                    evidence_quality_reasons=["Conflicting obtainable market share evidence."],
                )
            share_ratio = obt_share.value / 100.0
            share_low = (obt_share.range_min / 100.0) if obt_share.range_min is not None else share_ratio
            share_high = (obt_share.range_max / 100.0) if obt_share.range_max is not None else share_ratio
            eval_inputs.append(obt_share)

            sam_val = sam_result.estimate
            sam_low = sam_result.interval.lower if sam_result.interval and sam_result.interval.lower is not None else sam_val
            sam_high = sam_result.interval.upper if sam_result.interval and sam_result.interval.upper is not None else sam_val

            som_val = sam_val * share_ratio
            som_low = sam_low * share_low
            som_high = sam_high * share_high

            if obt_share.is_assumption:
                assumptions.append(
                    CalculationAssumption(
                        name=obt_share.name,
                        value=obt_share.value,
                        unit=obt_share.unit,
                        justification=obt_share.assumption_justification or "Target SOM market share assumption",
                    )
                )

            steps.append(
                CalculationStep(
                    step_number=len(steps) + 1,
                    description=f"Apply obtainable market share: {obt_share.name} ({obt_share.value}%)",
                    formula=f"SAM × ({obt_share.name} / 100)",
                    operands={"SAM": sam_val, obt_share.name: obt_share.value},
                    result=som_val,
                    result_interval=UncertaintyInterval(lower=som_low, point=som_val, upper=som_high),
                    unit=sam_result.unit or "USD/year",
                    evidence_references=[obt_share.source_url or obt_share.evidence_id or "SOM Share"],
                    assumptions=[obt_share.name] if obt_share.is_assumption else [],
                )
            )

        # Funnel Invariant: SOM <= SAM
        if sam_result.estimate is not None and som_val > sam_result.estimate:
            som_val = sam_result.estimate
            warnings.append(f"SOM was clamped to not exceed SAM ({sam_result.estimate:,.0f}).")

        interval = UncertaintyInterval(lower=som_low, point=som_val, upper=som_high)
        confidence = self._evaluate_confidence(eval_inputs, base_confidence=sam_result.confidence)
        eq_rating, eq_reasons = self._evaluate_result_evidence_quality(
            eval_inputs,
            bool(warnings),
            CalculationStatus.CALCULATED,
        )

        return SOMResult(
            status=CalculationStatus.CALCULATED,
            estimate=som_val,
            interval=interval,
            unit=sam_result.unit,
            currency=sam_result.currency,
            year=sam_result.year,
            geography=sam_result.geography,
            confidence=confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            market_scope="Obtainable market",
            market_scope_explanation="Serviceable Obtainable Market (SOM): Realistic near-term obtainable market share given operational capacity and competitive dynamics.",
            steps=steps,
            assumptions_used=assumptions,
            warnings=warnings,
            message="Bottom-up SOM successfully calculated.",
        )

    # -----------------------------------------------------------------------
    # 3. Cross-Methodology Comparison & Divergence Analysis
    # -----------------------------------------------------------------------

    def compare_methods(
        self,
        top_down_tam: Optional[TAMResult],
        bottom_up_tam: Optional[TAMResult],
        top_down_sam: Optional[SAMResult] = None,
        bottom_up_sam: Optional[SAMResult] = None,
        top_down_som: Optional[SOMResult] = None,
        bottom_up_som: Optional[SOMResult] = None,
    ) -> Optional[MethodComparison]:
        """Transparently compare Top-Down and Bottom-Up market sizing results and compute divergence."""
        if not top_down_tam or not bottom_up_tam:
            return None
        if top_down_tam.status != CalculationStatus.CALCULATED or bottom_up_tam.status != CalculationStatus.CALCULATED:
            return None
        if top_down_tam.estimate is None or bottom_up_tam.estimate is None:
            return None

        td = top_down_tam.estimate
        bu = bottom_up_tam.estimate
        curr = top_down_tam.currency or bottom_up_tam.currency or "USD"

        # Currency mismatch check
        if top_down_tam.currency and bottom_up_tam.currency and top_down_tam.currency.upper() != bottom_up_tam.currency.upper():
            return MethodComparison(
                top_down_tam=td,
                bottom_up_tam=bu,
                top_down_estimate=td,
                bottom_up_estimate=bu,
                currency="MISMATCH",
                absolute_difference=None,
                percentage_difference=None,
                relative_ratio=None,
                divergence_severity=DivergenceSeverity.WARNING,
                triangulation_confidence=EvidenceConfidence.LOW,
                divergence_explanation=(
                    f"Currency mismatch between Top-Down ({top_down_tam.currency}) and "
                    f"Bottom-Up ({bottom_up_tam.currency}). Cannot compute numerical divergence ratio without verified FX rate evidence."
                ),
                root_cause_diagnostics=[
                    f"Currency mismatch: Top-Down is calculated in {top_down_tam.currency}, while Bottom-Up is in {bottom_up_tam.currency}."
                ],
                explanation=(
                    f"Currency mismatch between Top-Down ({top_down_tam.currency}) and "
                    f"Bottom-Up ({bottom_up_tam.currency}). Cannot directly compute numerical divergence ratio."
                ),
            )

        abs_diff = round(abs(td - bu), 2)
        min_val = min(td, bu)
        max_val = max(td, bu)
        midpoint = (td + bu) / 2.0

        pct_diff = round((abs_diff / midpoint) * 100.0, 2) if midpoint > 0 else 0.0
        ratio = round(max_val / min_val, 2) if min_val > 0 else 1.0

        diagnostics: List[str] = []

        if pct_diff <= ACCEPTABLE_DIVERGENCE_THRESHOLD:
            severity = DivergenceSeverity.ACCEPTABLE
            triang_conf = EvidenceConfidence.HIGH
            div_expl = (
                f"Independent top-down ({td:,.0f} {curr}) and bottom-up ({bu:,.0f} {curr}) estimates "
                f"are within the acceptable divergence threshold ({pct_diff:.1f}% <= {ACCEPTABLE_DIVERGENCE_THRESHOLD:.0f}%, {ratio:.2f}x ratio)."
            )
            explanation = (
                f"Top-Down ({td:,.0f}) and Bottom-Up ({bu:,.0f}) methods show strong convergence "
                f"with a divergence of {pct_diff:.1f}% ({ratio:.2f}x)."
            )
        elif pct_diff <= WARNING_DIVERGENCE_THRESHOLD:
            severity = DivergenceSeverity.WARNING
            triang_conf = EvidenceConfidence.MEDIUM
            div_expl = (
                f"Top-down ({td:,.0f} {curr}) and bottom-up ({bu:,.0f} {curr}) estimates exhibit moderate divergence "
                f"of {pct_diff:.1f}% ({ratio:.2f}x ratio), exceeding the {ACCEPTABLE_DIVERGENCE_THRESHOLD:.0f}% acceptable threshold but within {WARNING_DIVERGENCE_THRESHOLD:.0f}% warning bounds."
            )
            explanation = (
                f"Top-Down ({td:,.0f}) and Bottom-Up ({bu:,.0f}) exhibit moderate divergence "
                f"of {pct_diff:.1f}% ({ratio:.2f}x). Review whether top-down macro scope includes broader adjacencies."
            )
        else:
            severity = DivergenceSeverity.SEVERE_DIVERGENCE
            triang_conf = EvidenceConfidence.LOW
            div_expl = (
                f"SEVERE DIVERGENCE: Top-down ({td:,.0f} {curr}) and bottom-up ({bu:,.0f} {curr}) estimates differ substantially "
                f"by {pct_diff:.1f}% ({ratio:.2f}x ratio), exceeding the {WARNING_DIVERGENCE_THRESHOLD:.0f}% severe threshold. Both methodologies are preserved side-by-side and must NOT be averaged."
            )
            explanation = (
                f"SEVERE DIVERGENCE: Top-Down ({td:,.0f}) and Bottom-Up ({bu:,.0f}) differ by "
                f"{pct_diff:.1f}% ({ratio:.2f}x). Both methodologies are preserved side-by-side and must NOT be averaged."
            )

        # Root-Cause Diagnostics
        # 1. Market Scope Diagnostics
        td_scope = top_down_tam.market_scope or ""
        if "parent" in td_scope.lower() or any("parent" in w.lower() for w in top_down_tam.warnings):
            diagnostics.append("Market Scope Mismatch: Top-down estimate starts from aggregate parent market demand, which may overestimate narrow product TAM without further segmentation.")
        elif td > bu * 3.0:
            diagnostics.append("Market Definition Divergence: Top-down sizing captures broad industry spending, whereas bottom-up sizing strictly measures unit economics of direct buyers.")

        # 2. Geography Alignment Diagnostics
        if top_down_tam.geography and bottom_up_tam.geography and top_down_tam.geography.lower() != bottom_up_tam.geography.lower():
            diagnostics.append(f"Geographic Scope Mismatch: Top-down targets '{top_down_tam.geography}', while bottom-up targets '{bottom_up_tam.geography}'.")

        # 3. Temporal / Year Alignment Diagnostics
        if top_down_tam.year and bottom_up_tam.year and abs(top_down_tam.year - bottom_up_tam.year) >= 2:
            diagnostics.append(f"Temporal Gap: Top-down benchmark is from {top_down_tam.year}, while bottom-up benchmark is from {bottom_up_tam.year}.")

        # 4. Source Quality Diagnostics
        if top_down_tam.evidence_quality and bottom_up_tam.evidence_quality and top_down_tam.evidence_quality != bottom_up_tam.evidence_quality:
            diagnostics.append(f"Evidence Quality Difference: Top-down rating is {top_down_tam.evidence_quality}, bottom-up rating is {bottom_up_tam.evidence_quality}.")

        # 5. Assumption Reliance Diagnostics
        td_assump_count = len(top_down_tam.assumptions_used)
        bu_assump_count = len(bottom_up_tam.assumptions_used)
        if td_assump_count > 0 or bu_assump_count > 0:
            diagnostics.append(f"Modeling Assumptions: Top-down applied {td_assump_count} assumption(s), bottom-up applied {bu_assump_count} assumption(s).")

        # SAM & SOM Cross-Method Comparisons
        sam_comp = None
        if (
            top_down_sam
            and bottom_up_sam
            and top_down_sam.status == CalculationStatus.CALCULATED
            and bottom_up_sam.status == CalculationStatus.CALCULATED
            and top_down_sam.estimate is not None
            and bottom_up_sam.estimate is not None
        ):
            sam_td = top_down_sam.estimate
            sam_bu = bottom_up_sam.estimate
            sam_diff = round(abs(sam_td - sam_bu), 2)
            sam_mid = (sam_td + sam_bu) / 2.0
            sam_pct = round((sam_diff / sam_mid) * 100.0, 2) if sam_mid > 0 else 0.0
            sam_ratio = round(max(sam_td, sam_bu) / min(sam_td, sam_bu), 2) if min(sam_td, sam_bu) > 0 else 1.0
            sam_comp = {
                "top_down_sam": sam_td,
                "bottom_up_sam": sam_bu,
                "absolute_difference": sam_diff,
                "percentage_difference": sam_pct,
                "relative_ratio": sam_ratio,
            }

        som_comp = None
        if (
            top_down_som
            and bottom_up_som
            and top_down_som.status == CalculationStatus.CALCULATED
            and bottom_up_som.status == CalculationStatus.CALCULATED
            and top_down_som.estimate is not None
            and bottom_up_som.estimate is not None
        ):
            som_td = top_down_som.estimate
            som_bu = bottom_up_som.estimate
            som_diff = round(abs(som_td - som_bu), 2)
            som_mid = (som_td + som_bu) / 2.0
            som_pct = round((som_diff / som_mid) * 100.0, 2) if som_mid > 0 else 0.0
            som_ratio = round(max(som_td, som_bu) / min(som_td, som_bu), 2) if min(som_td, som_bu) > 0 else 1.0
            som_comp = {
                "top_down_som": som_td,
                "bottom_up_som": som_bu,
                "absolute_difference": som_diff,
                "percentage_difference": som_pct,
                "relative_ratio": som_ratio,
            }

        return MethodComparison(
            top_down_tam=td,
            bottom_up_tam=bu,
            top_down_estimate=td,
            bottom_up_estimate=bu,
            currency=top_down_tam.currency or bottom_up_tam.currency,
            absolute_difference=abs_diff,
            percentage_difference=pct_diff,
            relative_ratio=ratio,
            divergence_severity=severity,
            divergence_explanation=div_expl,
            triangulation_confidence=triang_conf,
            root_cause_diagnostics=diagnostics,
            sam_comparison=sam_comp,
            som_comparison=som_comp,
            explanation=explanation,
        )

    # -----------------------------------------------------------------------
    # Phase 5: Assumption, Freshness, Uncertainty & Reliability Engine
    # -----------------------------------------------------------------------

    def evaluate_freshness(
        self, published_year: Optional[int], target_year: Optional[int] = None
    ) -> Tuple[FreshnessCategory, Optional[int]]:
        """Evaluate evidence freshness relative to target analysis year.

        Thresholds:
        - 0-2 years: RECENT
        - 3-5 years: MODERATELY_OLD
        - 6-10 years: OLD
        - >10 years: VERY_OLD
        - Unknown: UNKNOWN
        """
        if published_year is None:
            return FreshnessCategory.UNKNOWN, None

        base_year = target_year if target_year is not None else 2026
        age = base_year - published_year
        if age <= 2:
            return FreshnessCategory.RECENT, max(0, age)
        elif 3 <= age <= 5:
            return FreshnessCategory.MODERATELY_OLD, age
        elif 6 <= age <= 10:
            return FreshnessCategory.OLD, age
        else:
            return FreshnessCategory.VERY_OLD, age

    def _classify_assumption_source_type(self, inp: EvidenceInput) -> Tuple[AssumptionSourceType, str]:
        """Classify epistemic origin of an input operand."""
        if inp.is_assumption or inp.is_user_provided:
            return AssumptionSourceType.USER_ASSUMPTION, "User-declared input parameter or pricing/volume assumption."
        if inp.lifecycle_stage in ("verified", "VERIFIED") or inp.source_quality_tier in (
            SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
            SourceQualityTier.TIER_2_ACADEMIC_TRADE,
        ):
            return AssumptionSourceType.VERIFIED_EVIDENCE, f"Direct empirical evidence verified from {inp.source_quality_tier or 'authoritative source'}."
        if inp.lifecycle_stage in ("validated", "VALIDATED") or inp.source_quality_tier == SourceQualityTier.TIER_3_ANALYST_PRESS:
            return AssumptionSourceType.VALIDATED_EVIDENCE, "Empirical market research validated from reputable industry benchmark."
        if inp.source_quality_tier == SourceQualityTier.TIER_4_GENERAL_UNVERIFIED:
            return AssumptionSourceType.MODEL_ASSUMPTION, "General web reference treated as modeling assumption due to unverified provenance."
        if inp.value is not None:
            return AssumptionSourceType.MODEL_ASSUMPTION, "Model heuristic / benchmark assumption."
        return AssumptionSourceType.UNKNOWN, "Source origin unverified."

    def _classify_assumption_impact(self, category: AssumptionCategory, is_assumption: bool) -> AssumptionImpact:
        """Rate impact level of parameter on final TAM/SAM/SOM results."""
        if category in (AssumptionCategory.PRICE, AssumptionCategory.ARPU, AssumptionCategory.MARKET_SIZE, AssumptionCategory.CUSTOMER_COUNT, AssumptionCategory.TARGET_POPULATION):
            return AssumptionImpact.CRITICAL if is_assumption else AssumptionImpact.HIGH_IMPACT
        if category in (AssumptionCategory.SEGMENT_PERCENTAGE, AssumptionCategory.PENETRATION, AssumptionCategory.MARKET_SHARE, AssumptionCategory.CONVERSION_RATE):
            return AssumptionImpact.HIGH_IMPACT if is_assumption else AssumptionImpact.MEDIUM_IMPACT
        if category in (AssumptionCategory.GROWTH_RATE, AssumptionCategory.CAPACITY, AssumptionCategory.FX_RATE, AssumptionCategory.TIME_PERIOD, AssumptionCategory.GEOGRAPHY):
            return AssumptionImpact.MEDIUM_IMPACT if is_assumption else AssumptionImpact.LOW_IMPACT
        return AssumptionImpact.LOW_IMPACT

    def build_assumption_registry(
        self,
        request: CalculationInput,
        td_tam: Optional[TAMResult] = None,
        bu_tam: Optional[TAMResult] = None,
        td_sam: Optional[SAMResult] = None,
        bu_sam: Optional[SAMResult] = None,
        td_som: Optional[SOMResult] = None,
        bu_som: Optional[SOMResult] = None,
    ) -> AssumptionRegistry:
        """Build formal Assumption Registry categorizing every input, fact, and assumption."""
        items: List[AssumptionItem] = []
        seen_names = set()

        def _register_input(inp: Optional[EvidenceInput], category: AssumptionCategory, affects: List[str]):
            if not inp or inp.name in seen_names or inp.value is None:
                return
            seen_names.add(inp.name)
            source_type, auto_justification = self._classify_assumption_source_type(inp)
            is_user = inp.is_user_provided or inp.is_assumption or (source_type == AssumptionSourceType.USER_ASSUMPTION)
            is_ev = source_type in (AssumptionSourceType.VERIFIED_EVIDENCE, AssumptionSourceType.VALIDATED_EVIDENCE)
            is_model = source_type == AssumptionSourceType.MODEL_ASSUMPTION
            impact = self._classify_assumption_impact(category, is_user or is_model)

            unc_status = "EVIDENCE_BOUNDED" if (inp.range_min is not None and inp.range_max is not None) else "POINT_ONLY"

            items.append(
                AssumptionItem(
                    name=inp.name,
                    value=inp.value,
                    unit=inp.unit or "units",
                    category=category,
                    source_type=source_type,
                    source_reference=getattr(inp, "source_url", None) or getattr(inp, "source_name", None) or getattr(inp, "source_title", None),
                    confidence=getattr(inp, "confidence", None) or EvidenceConfidence.MEDIUM,
                    justification=getattr(inp, "assumption_justification", None) or getattr(inp, "source_title", None) or getattr(inp, "source_name", None) or auto_justification,
                    is_user_provided=is_user,
                    is_evidence_based=is_ev,
                    is_model_derived=is_model,
                    impact=impact,
                    affects=affects,
                    min_value=inp.range_min,
                    max_value=inp.range_max,
                    uncertainty_status=unc_status,
                )
            )

        if request.top_down_inputs:
            td = request.top_down_inputs
            _register_input(td.macro_market_size, AssumptionCategory.MARKET_SIZE, ["TAM", "SAM"])
            for seg in td.segment_percentages:
                _register_input(seg, AssumptionCategory.SEGMENT_PERCENTAGE, ["SAM"])
            _register_input(td.serviceable_geography_percentage, AssumptionCategory.GEOGRAPHY, ["SAM"])
            _register_input(td.target_segment_percentage, AssumptionCategory.SEGMENT_PERCENTAGE, ["SAM"])
            for flt in td.other_filters:
                _register_input(flt, AssumptionCategory.SEGMENT_PERCENTAGE, ["SAM"])
            _register_input(td.obtainable_market_share, AssumptionCategory.MARKET_SHARE, ["SOM"])

        if request.bottom_up_inputs:
            bu = request.bottom_up_inputs
            _register_input(bu.potential_customers, AssumptionCategory.CUSTOMER_COUNT, ["TAM"])
            _register_input(bu.serviceable_customers, AssumptionCategory.TARGET_POPULATION, ["SAM"])
            _register_input(bu.target_customer_percentage, AssumptionCategory.PENETRATION, ["SAM"])
            _register_input(bu.realistically_obtainable_customers, AssumptionCategory.CUSTOMER_COUNT, ["SOM"])
            _register_input(bu.obtainable_market_share, AssumptionCategory.MARKET_SHARE, ["SOM"])
            _register_input(bu.pricing, AssumptionCategory.PRICE, ["TAM", "SAM", "SOM"])

        for asmp in request.assumptions:
            if asmp.name not in seen_names:
                seen_names.add(asmp.name)
                name_lower = asmp.name.lower()
                cat = AssumptionCategory.OTHER
                if "price" in name_lower or "arpu" in name_lower or "fee" in name_lower:
                    cat = AssumptionCategory.PRICE
                elif "customer" in name_lower or "user" in name_lower or "student" in name_lower or "population" in name_lower:
                    cat = AssumptionCategory.CUSTOMER_COUNT
                elif "share" in name_lower:
                    cat = AssumptionCategory.MARKET_SHARE
                elif "cagr" in name_lower or "growth" in name_lower:
                    cat = AssumptionCategory.GROWTH_RATE
                elif "penetration" in name_lower or "percent" in name_lower:
                    cat = AssumptionCategory.PENETRATION
                elif "market" in name_lower or "size" in name_lower:
                    cat = AssumptionCategory.MARKET_SIZE

                impact = self._classify_assumption_impact(cat, is_assumption=True)
                items.append(
                    AssumptionItem(
                        name=asmp.name,
                        value=asmp.value,
                        unit=asmp.unit,
                        category=cat,
                        source_type=AssumptionSourceType.USER_ASSUMPTION if asmp.is_user_provided else AssumptionSourceType.MODEL_ASSUMPTION,
                        confidence=EvidenceConfidence.MEDIUM if asmp.is_user_provided else EvidenceConfidence.LOW,
                        justification=asmp.justification or "User-provided calculation assumption.",
                        is_user_provided=asmp.is_user_provided,
                        is_evidence_based=False,
                        is_model_derived=not asmp.is_user_provided,
                        impact=impact,
                        affects=["TAM", "SAM"] if cat in (AssumptionCategory.PRICE, AssumptionCategory.CUSTOMER_COUNT, AssumptionCategory.MARKET_SIZE) else ["SAM", "SOM"],
                        uncertainty_status="POINT_ONLY",
                    )
                )

        user_cnt = sum(1 for i in items if i.is_user_provided or i.source_type == AssumptionSourceType.USER_ASSUMPTION)
        model_cnt = sum(1 for i in items if i.is_model_derived or i.source_type in (AssumptionSourceType.MODEL_ASSUMPTION, AssumptionSourceType.DERIVED_VALUE))
        crit_cnt = sum(1 for i in items if i.impact == AssumptionImpact.CRITICAL)
        high_cnt = sum(1 for i in items if i.impact in (AssumptionImpact.CRITICAL, AssumptionImpact.HIGH_IMPACT))

        return AssumptionRegistry(
            items=items,
            total_count=len(items),
            user_provided_count=user_cnt,
            model_derived_count=model_cnt,
            critical_assumptions_count=crit_cnt,
            high_impact_count=high_cnt,
        )

    def calculate_uncertainty_scenarios(
        self,
        request: CalculationInput,
        td_tam: Optional[TAMResult] = None,
        bu_tam: Optional[TAMResult] = None,
        td_sam: Optional[SAMResult] = None,
        bu_sam: Optional[SAMResult] = None,
        td_som: Optional[SOMResult] = None,
        bu_som: Optional[SOMResult] = None,
    ) -> UncertaintyAnalysis:
        """Calculate deterministic Low/Base/High scenarios when empirical range bounds exist."""
        tam_scen: Optional[ScenarioEstimate] = None
        sam_scen: Optional[ScenarioEstimate] = None
        som_scen: Optional[ScenarioEstimate] = None
        has_ranges = False
        range_bases: List[str] = []

        if request.bottom_up_inputs:
            bu = request.bottom_up_inputs
            c = bu.potential_customers
            p = bu.pricing
            if c and p and bu_tam and bu_tam.status == CalculationStatus.CALCULATED and bu_tam.estimate is not None:
                freq_mult = 12.0 if bu.pricing_frequency == PriceFrequency.MONTHLY else 1.0
                c_min = c.range_min if c.range_min is not None else c.value
                c_max = c.range_max if c.range_max is not None else c.value
                p_min = (p.range_min * freq_mult) if p.range_min is not None else (p.value * freq_mult if p.value else None)
                p_max = (p.range_max * freq_mult) if p.range_max is not None else (p.value * freq_mult if p.value else None)

                if (c.range_min is not None or c.range_max is not None or p.range_min is not None or p.range_max is not None) and c_min and c_max and p_min and p_max:
                    has_ranges = True
                    range_bases.append("Bottom-Up customer population / pricing empirical range bounds")
                    tam_scen = ScenarioEstimate(
                        low=round(c_min * p_min, 2),
                        base=round(bu_tam.estimate, 2),
                        high=round(c_max * p_max, 2),
                        unit=bu_tam.unit,
                        currency=bu_tam.currency,
                    )

        if not tam_scen and request.top_down_inputs:
            td = request.top_down_inputs
            m = td.macro_market_size
            if m and td_tam and td_tam.status == CalculationStatus.CALCULATED and td_tam.estimate is not None:
                if m.range_min is not None and m.range_max is not None:
                    has_ranges = True
                    range_bases.append("Top-Down macro market empirical range bounds")
                    tam_scen = ScenarioEstimate(
                        low=round(m.range_min, 2),
                        base=round(td_tam.estimate, 2),
                        high=round(m.range_max, 2),
                        unit=td_tam.unit,
                        currency=td_tam.currency,
                    )

        if bu_sam and bu_sam.status == CalculationStatus.CALCULATED and bu_sam.estimate is not None and tam_scen and tam_scen.low and tam_scen.high:
            bu = request.bottom_up_inputs
            if bu and bu.target_customer_percentage and bu.target_customer_percentage.value:
                pct = bu.target_customer_percentage.value / 100.0
                pct_min = (bu.target_customer_percentage.range_min / 100.0) if bu.target_customer_percentage.range_min is not None else pct
                pct_max = (bu.target_customer_percentage.range_max / 100.0) if bu.target_customer_percentage.range_max is not None else pct
                sam_scen = ScenarioEstimate(
                    low=round(tam_scen.low * pct_min, 2),
                    base=round(bu_sam.estimate, 2),
                    high=round(tam_scen.high * pct_max, 2),
                    unit=bu_sam.unit,
                    currency=bu_sam.currency,
                )

        if bu_som and bu_som.status == CalculationStatus.CALCULATED and bu_som.estimate is not None and sam_scen and sam_scen.low and sam_scen.high:
            bu = request.bottom_up_inputs
            if bu and bu.obtainable_market_share and bu.obtainable_market_share.value:
                share = bu.obtainable_market_share.value / 100.0
                share_min = (bu.obtainable_market_share.range_min / 100.0) if bu.obtainable_market_share.range_min is not None else share
                share_max = (bu.obtainable_market_share.range_max / 100.0) if bu.obtainable_market_share.range_max is not None else share
                som_scen = ScenarioEstimate(
                    low=round(sam_scen.low * share_min, 2),
                    base=round(bu_som.estimate, 2),
                    high=round(sam_scen.high * share_max, 2),
                    unit=bu_som.unit,
                    currency=bu_som.currency,
                )

        if has_ranges:
            return UncertaintyAnalysis(
                status="AVAILABLE",
                tam_scenario=tam_scen,
                sam_scenario=sam_scen,
                som_scenario=som_scen,
                basis="; ".join(range_bases) if range_bases else "Empirical range bounds from validated source evidence.",
                explanation="Low, Base, and High scenario estimates are deterministically derived from empirical range intervals in source evidence.",
            )
        else:
            return UncertaintyAnalysis(
                status="INSUFFICIENT_EVIDENCE",
                tam_scenario=None,
                sam_scenario=None,
                som_scenario=None,
                basis="Point estimates only; range evidence not provided in sources.",
                explanation="Uncertainty scenarios require empirical min/max bounds or user-supplied intervals. The engine does not fabricate arbitrary percentage ranges.",
            )

    def perform_sensitivity_analysis(
        self,
        request: CalculationInput,
        base_tam: Optional[float] = None,
    ) -> List[SensitivityParameter]:
        """Perform deterministic sensitivity analysis ranking key driver parameters."""
        params: List[SensitivityParameter] = []

        if request.bottom_up_inputs:
            bu = request.bottom_up_inputs
            if bu.pricing and bu.pricing.value is not None:
                freq_mult = 12.0 if bu.pricing_frequency == PriceFrequency.MONTHLY else 1.0
                annual_p = bu.pricing.value * freq_mult
                params.append(
                    SensitivityParameter(
                        parameter="annual_price",
                        base_value=annual_p,
                        unit=bu.pricing.currency or "currency/year",
                        impact="HIGH",
                        elasticity=1.0,
                        explanation="TAM scales linearly 1:1 with annual customer price/ARPU.",
                    )
                )
            if bu.potential_customers and bu.potential_customers.value is not None:
                params.append(
                    SensitivityParameter(
                        parameter="potential_customers",
                        base_value=bu.potential_customers.value,
                        unit=bu.potential_customers.unit or "customers",
                        impact="HIGH",
                        elasticity=1.0,
                        explanation="TAM scales linearly 1:1 with target customer population count.",
                    )
                )
            if bu.target_customer_percentage and bu.target_customer_percentage.value is not None:
                params.append(
                    SensitivityParameter(
                        parameter="target_customer_percentage",
                        base_value=bu.target_customer_percentage.value,
                        unit="%",
                        impact="MEDIUM",
                        elasticity=1.0,
                        explanation="Serviceable Addressable Market (SAM) scales directly with target customer qualification rate.",
                    )
                )
            if bu.obtainable_market_share and bu.obtainable_market_share.value is not None:
                params.append(
                    SensitivityParameter(
                        parameter="obtainable_market_share",
                        base_value=bu.obtainable_market_share.value,
                        unit="%",
                        impact="HIGH",
                        elasticity=1.0,
                        explanation="Serviceable Obtainable Market (SOM) scales linearly with captured market share percentage.",
                    )
                )

        if request.top_down_inputs:
            td = request.top_down_inputs
            if td.macro_market_size and td.macro_market_size.value is not None:
                params.append(
                    SensitivityParameter(
                        parameter="macro_market_size",
                        base_value=td.macro_market_size.value,
                        unit=td.macro_market_size.currency or "currency/year",
                        impact="HIGH",
                        elasticity=1.0,
                        explanation="Top-Down TAM scales linearly with starting macro industry spend.",
                    )
                )
            for seg in td.segment_percentages:
                if seg.value is not None:
                    params.append(
                        SensitivityParameter(
                            parameter=seg.name,
                            base_value=seg.value,
                            unit="%",
                            impact="MEDIUM",
                            elasticity=1.0,
                            explanation=f"Market sizing scales proportionally with {seg.name} segment filter.",
                        )
                    )

        impact_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        params.sort(key=lambda p: impact_order.get(p.impact, 3))
        return params

    def evaluate_double_counting_risk(
        self,
        request: CalculationInput,
        td_tam: Optional[TAMResult] = None,
        bu_tam: Optional[TAMResult] = None,
    ) -> Tuple[bool, List[str]]:
        """Detect potential double-counting or unsegmented overlapping scope risks."""
        risks: List[str] = []
        if (
            request.top_down_inputs
            and request.top_down_inputs.macro_market_size
            and request.bottom_up_inputs
            and request.bottom_up_inputs.potential_customers
        ):
            td_name = (request.top_down_inputs.macro_market_size.name or "").lower()
            bu_name = (request.bottom_up_inputs.potential_customers.name or "").lower()
            if td_name and bu_name and (td_name in bu_name or bu_name in td_name):
                risks.append("DOUBLE_COUNTING_RISK: Top-Down and Bottom-Up inputs reference overlapping market definitions without independent verification.")

        return (len(risks) > 0, risks)

    def evaluate_reliability_assessment(
        self,
        overall_status: CalculationStatus,
        registry: AssumptionRegistry,
        comparison: Optional[MethodComparison],
        all_metric_results: List[MetricCalculationResult],
        all_inputs: List[EvidenceInput],
        target_year: Optional[int],
        double_counting_risk: bool,
    ) -> ReliabilityAssessment:
        """Synthesize multi-dimensional Evidence-Based Reliability rating."""
        if overall_status != CalculationStatus.CALCULATED:
            return ReliabilityAssessment(
                level="INSUFFICIENT",
                reason="Calculation could not be completed reliably due to missing or conflicting evidence.",
                evidence_strength="INSUFFICIENT",
                assumption_risk="HIGH",
                freshness="UNKNOWN",
                methodology_agreement="SINGLE_METHOD",
                double_counting_risk=double_counting_risk,
                geography_consistency="CONSISTENT",
                temporal_consistency="CONSISTENT",
                currency_consistency="CONSISTENT",
            )

        tier1_2_cnt = sum(
            1
            for inp in all_inputs
            if inp.source_quality_tier in (SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL, SourceQualityTier.TIER_2_ACADEMIC_TRADE)
            and not inp.is_assumption
        )
        tier3_cnt = sum(
            1
            for inp in all_inputs
            if inp.source_quality_tier == SourceQualityTier.TIER_3_ANALYST_PRESS and not inp.is_assumption
        )
        tier4_or_assump = sum(
            1
            for inp in all_inputs
            if inp.source_quality_tier == SourceQualityTier.TIER_4_GENERAL_UNVERIFIED or inp.is_assumption
        )

        if tier1_2_cnt >= 2 and tier4_or_assump == 0:
            ev_strength = "HIGH"
        elif tier1_2_cnt >= 1 or tier3_cnt >= 1:
            ev_strength = "MEDIUM"
        else:
            ev_strength = "LOW"

        high_impact_asmp_cnt = sum(
            1
            for i in registry.items
            if (i.impact in (AssumptionImpact.CRITICAL, AssumptionImpact.HIGH_IMPACT) or str(i.impact) in ("CRITICAL", "HIGH_IMPACT"))
            and (i.is_user_provided or i.is_model_derived or not i.is_evidence_based)
        )

        if registry.critical_assumptions_count >= 1:
            asmp_risk = "CRITICAL"
        elif high_impact_asmp_cnt >= 2 or registry.user_provided_count >= 2:
            asmp_risk = "HIGH"
        elif registry.user_provided_count >= 1 or registry.model_derived_count >= 1 or high_impact_asmp_cnt >= 1:
            asmp_risk = "MEDIUM"
        else:
            asmp_risk = "LOW"

        years = [inp.published_year for inp in all_inputs if inp.published_year is not None]
        if not years:
            overall_freshness = "UNKNOWN"
        else:
            freshness_list = [self.evaluate_freshness(y, target_year)[0] for y in years]
            if FreshnessCategory.VERY_OLD in freshness_list:
                overall_freshness = "VERY_OLD"
            elif FreshnessCategory.OLD in freshness_list:
                overall_freshness = "OLD"
            elif FreshnessCategory.MODERATELY_OLD in freshness_list:
                overall_freshness = "MODERATELY_OLD"
            elif FreshnessCategory.UNKNOWN in freshness_list:
                overall_freshness = "UNKNOWN"
            else:
                overall_freshness = "RECENT"

        meth_agreement = "SINGLE_METHOD"
        if comparison:
            if comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE:
                meth_agreement = "ACCEPTABLE"
            elif comparison.divergence_severity == DivergenceSeverity.WARNING:
                meth_agreement = "WARNING"
            elif comparison.divergence_severity == DivergenceSeverity.SEVERE_DIVERGENCE:
                meth_agreement = "SEVERE_DIVERGENCE"

        reasons: List[str] = []
        if asmp_risk == "CRITICAL":
            level = "LOW"
            reasons.append(f"Result is highly sensitive to {registry.critical_assumptions_count} critical unverified assumption(s).")
        elif ev_strength == "LOW":
            level = "LOW"
            reasons.append("Underlying evidence lacks Tier 1/2 authoritative backing.")
        elif meth_agreement == "SEVERE_DIVERGENCE":
            level = "LOW"
            reasons.append("Top-Down and Bottom-Up estimates diverge significantly (>50%).")
        elif overall_freshness in ("OLD", "VERY_OLD"):
            level = "LOW" if overall_freshness == "VERY_OLD" else "MEDIUM"
            reasons.append(f"Input evidence is {overall_freshness.lower().replace('_', ' ')} relative to analysis target year.")
        elif ev_strength == "HIGH" and asmp_risk in ("LOW", "MEDIUM") and meth_agreement in ("ACCEPTABLE", "SINGLE_METHOD") and overall_freshness == "RECENT":
            level = "HIGH"
            reasons.append("Backed by authoritative Tier 1/2 empirical sources, fresh baseline data, and aligned methodology.")
        elif ev_strength in ("HIGH", "MEDIUM") and asmp_risk in ("LOW", "MEDIUM"):
            level = "MEDIUM"
            reasons.append("Supported by validated evidence, but contains modeling assumptions or single-source derivation.")
        else:
            level = "LOW"
            reasons.append("Calculations rely primarily on assumptions or lower-tier sources.")

        if double_counting_risk:
            reasons.append("Warning: Potential double-counting risk detected across methodologies.")

        return ReliabilityAssessment(
            level=level,
            reason=" ".join(reasons),
            evidence_strength=ev_strength,
            assumption_risk=asmp_risk,
            freshness=overall_freshness,
            methodology_agreement=meth_agreement,
            double_counting_risk=double_counting_risk,
            geography_consistency="CONSISTENT",
            temporal_consistency="CONSISTENT" if overall_freshness in ("RECENT", "MODERATELY_OLD") else "TEMPORAL_GAP",
            currency_consistency="CONSISTENT",
        )

    # -----------------------------------------------------------------------
    # 4. Master Report Generation
    # -----------------------------------------------------------------------

    def generate_report(self, request: CalculationInput) -> CalculationReport:
        """Generate comprehensive market sizing report executing all available methodologies."""
        calc_id = f"calc_{uuid.uuid4().hex[:12]}"
        all_steps: List[CalculationStep] = []
        all_assumptions: List[CalculationAssumption] = list(request.assumptions)
        all_conflicts: List[Dict[str, Any]] = []
        all_warnings: List[str] = []
        unit_compat_warnings: List[str] = []

        td_tam: Optional[TAMResult] = None
        td_sam: Optional[SAMResult] = None
        td_som: Optional[SOMResult] = None

        bu_tam: Optional[TAMResult] = None
        bu_sam: Optional[SAMResult] = None
        bu_som: Optional[SOMResult] = None

        # Execute Top-Down if inputs present
        if request.top_down_inputs:
            td_tam = self.calculate_top_down_tam(request.top_down_inputs)
            if td_tam.status == CalculationStatus.CALCULATED:
                td_sam = self.calculate_top_down_sam(td_tam, request.top_down_inputs)
                if td_sam.status == CalculationStatus.CALCULATED:
                    td_som = self.calculate_top_down_som(td_sam, request.top_down_inputs)

            for res in (td_tam, td_sam, td_som):
                if res:
                    all_steps.extend(res.steps)
                    all_assumptions.extend(res.assumptions_used)
                    all_warnings.extend(res.warnings)
                    if res.status == CalculationStatus.CONFLICT:
                        all_conflicts.append({"method": "top_down", "message": res.message})

        # Execute Bottom-Up if inputs present
        if request.bottom_up_inputs:
            bu_tam = self.calculate_bottom_up_tam(request.bottom_up_inputs)
            if bu_tam.status == CalculationStatus.CALCULATED:
                bu_sam = self.calculate_bottom_up_sam(bu_tam, request.bottom_up_inputs)
                if bu_sam.status == CalculationStatus.CALCULATED:
                    bu_som = self.calculate_bottom_up_som(bu_sam, request.bottom_up_inputs)

            for res in (bu_tam, bu_sam, bu_som):
                if res:
                    all_steps.extend(res.steps)
                    all_assumptions.extend(res.assumptions_used)
                    all_warnings.extend(res.warnings)
                    if res.status == CalculationStatus.CONFLICT:
                        all_conflicts.append({"method": "bottom_up", "message": res.message})

        # Deduplicate assumptions by name
        unique_assumptions: Dict[str, CalculationAssumption] = {}
        for a in all_assumptions:
            unique_assumptions[a.name] = a

        # Cross-method comparison
        comparison = self.compare_methods(
            td_tam,
            bu_tam,
            top_down_sam=td_sam,
            bottom_up_sam=bu_sam,
            top_down_som=td_som,
            bottom_up_som=bu_som,
        )

        # Overall status determination
        overall_status = CalculationStatus.CALCULATED
        if all_conflicts:
            overall_status = CalculationStatus.CONFLICT
        elif not td_tam and not bu_tam:
            overall_status = CalculationStatus.INSUFFICIENT_EVIDENCE
        elif (not td_tam or td_tam.status != CalculationStatus.CALCULATED) and (not bu_tam or bu_tam.status != CalculationStatus.CALCULATED):
            overall_status = CalculationStatus.INSUFFICIENT_EVIDENCE

        # Collect all raw input objects for audit
        all_raw_inputs: List[EvidenceInput] = []
        if request.top_down_inputs:
            td_inp = request.top_down_inputs
            if td_inp.macro_market_size:
                all_raw_inputs.append(td_inp.macro_market_size)
            all_raw_inputs.extend([s for s in td_inp.segment_percentages if s])
            if td_inp.serviceable_geography_percentage:
                all_raw_inputs.append(td_inp.serviceable_geography_percentage)
            if td_inp.target_segment_percentage:
                all_raw_inputs.append(td_inp.target_segment_percentage)
            all_raw_inputs.extend([f for f in td_inp.other_filters if f])
            if td_inp.obtainable_market_share:
                all_raw_inputs.append(td_inp.obtainable_market_share)

        if request.bottom_up_inputs:
            bu_inp = request.bottom_up_inputs
            if bu_inp.potential_customers:
                all_raw_inputs.append(bu_inp.potential_customers)
            if bu_inp.serviceable_customers:
                all_raw_inputs.append(bu_inp.serviceable_customers)
            if bu_inp.target_customer_percentage:
                all_raw_inputs.append(bu_inp.target_customer_percentage)
            if bu_inp.realistically_obtainable_customers:
                all_raw_inputs.append(bu_inp.realistically_obtainable_customers)
            if bu_inp.obtainable_market_share:
                all_raw_inputs.append(bu_inp.obtainable_market_share)
            if bu_inp.pricing:
                all_raw_inputs.append(bu_inp.pricing)

        # Build Assumption Registry
        assumption_registry = self.build_assumption_registry(
            request, td_tam, bu_tam, td_sam, bu_sam, td_som, bu_som
        )

        # Build Uncertainty Analysis
        uncertainty_analysis = self.calculate_uncertainty_scenarios(
            request, td_tam, bu_tam, td_sam, bu_sam, td_som, bu_som
        )

        # Build Deterministic Sensitivity Analysis
        base_val = (bu_tam.estimate if bu_tam and bu_tam.estimate else (td_tam.estimate if td_tam and td_tam.estimate else None))
        sensitivity_analysis = self.perform_sensitivity_analysis(request, base_val)

        # Check Double Counting
        is_dc_risk, dc_risks = self.evaluate_double_counting_risk(request, td_tam, bu_tam)
        if is_dc_risk:
            all_warnings.extend(dc_risks)

        # All valid metric results
        all_metric_results = [r for r in (td_tam, td_sam, td_som, bu_tam, bu_sam, bu_som) if r and r.status == CalculationStatus.CALCULATED]

        # Reliability Assessment
        reliability_assessment = self.evaluate_reliability_assessment(
            overall_status=overall_status,
            registry=assumption_registry,
            comparison=comparison,
            all_metric_results=all_metric_results,
            all_inputs=all_raw_inputs,
            target_year=request.target_year,
            double_counting_risk=is_dc_risk,
        )

        overall_confidence = self._compute_overall_report_confidence(
            td_tam, bu_tam, comparison, all_conflicts, assumption_registry.user_provided_count + assumption_registry.model_derived_count
        )

        # Overall Evidence Quality Rating
        eq_rating = EvidenceQualityRating.INSUFFICIENT
        eq_reasons: List[str] = []

        if overall_status == CalculationStatus.CALCULATED and all_metric_results:
            ratings = [r.evidence_quality for r in all_metric_results if r.evidence_quality]
            if any(r == EvidenceQualityRating.HIGH for r in ratings) and not any(r == EvidenceQualityRating.LOW for r in ratings):
                eq_rating = EvidenceQualityRating.HIGH
                eq_reasons.append("Calculations are supported by high-quality verified authoritative sources.")
            elif any(r in (EvidenceQualityRating.HIGH, EvidenceQualityRating.MEDIUM) for r in ratings):
                eq_rating = EvidenceQualityRating.MEDIUM
                eq_reasons.append("Calculations are supported by reputable market research and validated benchmarks.")
            else:
                eq_rating = EvidenceQualityRating.LOW
                eq_reasons.append("Calculations rely heavily on assumptions or lower-tier sources.")
        elif overall_status == CalculationStatus.CONFLICT:
            eq_rating = EvidenceQualityRating.INSUFFICIENT
            eq_reasons.append("Conflicting evidence prevented reliable final market sizing calculation.")
        else:
            eq_rating = EvidenceQualityRating.INSUFFICIENT
            eq_reasons.append("Insufficient evidence to reliably calculate market sizing.")

        # Unit compatibility warnings collection
        for w in all_warnings:
            if "unit mismatch" in w.lower() or "currency divergence" in w.lower() or "entity unit" in w.lower():
                unit_compat_warnings.append(w)

        # Build deterministic calculation trace for auditing & debugging
        tam_trace = None
        sam_trace = None
        som_trace = None

        if td_tam and td_tam.status == CalculationStatus.CALCULATED and td_tam.estimate is not None:
            macro_input = request.top_down_inputs.macro_market_size if request.top_down_inputs else None
            tam_trace = TAMTrace(
                candidate_id=macro_input.evidence_id if macro_input else None,
                value=td_tam.estimate,
                geography=td_tam.geography,
                year=td_tam.year,
                source=macro_input.source_url if (macro_input and macro_input.source_url) else (td_tam.steps[0].evidence_references[0] if td_tam.steps and td_tam.steps[0].evidence_references else None),
            )
        elif bu_tam and bu_tam.status == CalculationStatus.CALCULATED and bu_tam.estimate is not None:
            pop_input = request.bottom_up_inputs.potential_customers if request.bottom_up_inputs else None
            tam_trace = TAMTrace(
                candidate_id=pop_input.evidence_id if pop_input else None,
                value=bu_tam.estimate,
                geography=bu_tam.geography,
                year=bu_tam.year,
                source=pop_input.source_url if (pop_input and pop_input.source_url) else None,
            )

        if td_sam and td_sam.status == CalculationStatus.CALCULATED and td_sam.estimate is not None:
            td_inp = request.top_down_inputs
            factor_item = (
                td_inp.serviceable_geography_percentage
                or td_inp.target_segment_percentage
                or (td_inp.other_filters[0] if getattr(td_inp, "other_filters", None) else None)
            )
            factor_type = "geography" if td_inp.serviceable_geography_percentage else ("segment" if td_inp.target_segment_percentage else "filter")
            formula_str = td_sam.steps[-1].formula if td_sam.steps else None
            sam_trace = SAMTrace(
                candidate_id=factor_item.evidence_id if factor_item else None,
                factor=factor_item.value if factor_item else None,
                factor_type=factor_type if factor_item else None,
                reason="Direct narrowing factor from evidence",
                formula=formula_str,
                value=td_sam.estimate,
            )
        elif td_sam:
            sam_trace = SAMTrace(
                candidate_id=None,
                factor=None,
                factor_type=None,
                reason=td_sam.message,
                formula=None,
                value=None,
            )

        if td_som and td_som.status == CalculationStatus.CALCULATED and td_som.estimate is not None:
            som_input = request.top_down_inputs.obtainable_market_share if request.top_down_inputs else None
            som_trace = SOMTrace(
                candidate_id=som_input.evidence_id if som_input else None,
                factor=som_input.value if som_input else None,
                reason="Obtainable market share from evidence",
                value=td_som.estimate,
            )
        elif td_som:
            som_trace = SOMTrace(
                candidate_id=None,
                factor=None,
                reason=td_som.message,
                value=None,
            )
        else:
            som_trace = SOMTrace(
                candidate_id=None,
                factor=None,
                reason="Insufficient evidence: SOM safety rule strictly forbids arbitrary market share percentages. Obtainable market share evidence or an explicit user assumption is required to calculate SOM.",
                value=None,
            )

        currency = (
            (td_tam.currency if td_tam and td_tam.currency else None)
            or (bu_tam.currency if bu_tam and bu_tam.currency else None)
        )

        calc_trace = CalculationTrace(
            tam=tam_trace,
            sam=sam_trace,
            som=som_trace,
        )

        # Determine methodologies dynamically if not explicitly specified
        tam_meth = request.tam_methodology
        if not tam_meth:
            if td_tam and td_tam.status == CalculationStatus.CALCULATED and bu_tam and bu_tam.status == CalculationStatus.CALCULATED:
                tam_meth = "Triangulated (Top-Down Direct Market Size & Bottom-Up Customer Unit Economics)"
            elif td_tam and td_tam.status == CalculationStatus.CALCULATED:
                tam_meth = "Top-Down (Direct Reported Relevant Market Size)"
            elif bu_tam and bu_tam.status == CalculationStatus.CALCULATED:
                tam_meth = "Bottom-Up (Relevant Customer Population × Annual Spend/ARPU)"
            else:
                tam_meth = "Direct Market Sizing or Customer Unit Economics"

        sam_meth = request.sam_methodology
        if not sam_meth:
            if td_sam and td_sam.status == CalculationStatus.CALCULATED:
                sam_meth = "Serviceable Segment Narrowing (TAM × Serviceable Geography/Customer Segment %)"
            elif bu_sam and bu_sam.status == CalculationStatus.CALCULATED:
                sam_meth = "Serviceable Customer Economics (Serviceable Population × Annual Spend)"
            else:
                sam_meth = "Serviceable Segment Narrowing or Serviceable Population Spend"

        som_meth = request.som_methodology
        if not som_meth:
            if (td_som and td_som.status == CalculationStatus.CALCULATED) or (bu_som and bu_som.status == CalculationStatus.CALCULATED):
                som_meth = "Capacity-Based & Obtainable Market Share"
            else:
                som_meth = "Operational/Sales Capacity or Realistic Near-Term Obtainable Share"

        return CalculationReport(
            calculation_id=calc_id,
            status=overall_status,
            target_geography=request.target_geography,
            target_year=request.target_year,
            market_definition=request.market_definition,
            tam_methodology=tam_meth,
            sam_methodology=sam_meth,
            som_methodology=som_meth,
            currency=currency,
            top_down_tam=td_tam,
            top_down_sam=td_sam,
            top_down_som=td_som,
            bottom_up_tam=bu_tam,
            bottom_up_sam=bu_sam,
            bottom_up_som=bu_som,
            method_comparison=comparison,
            confidence=overall_confidence,
            evidence_quality=eq_rating,
            evidence_quality_reasons=eq_reasons,
            assumption_registry=assumption_registry,
            uncertainty_analysis=uncertainty_analysis,
            sensitivity_analysis=sensitivity_analysis,
            reliability_assessment=reliability_assessment,
            all_steps=all_steps,
            all_assumptions=list(unique_assumptions.values()),
            conflicts=all_conflicts,
            warnings=list(dict.fromkeys(all_warnings)),
            unit_compatibility_warnings=list(dict.fromkeys(unit_compat_warnings)),
            message=self._build_report_message(overall_status, td_tam, bu_tam, comparison),
            calculation_trace=calc_trace,
        )

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _evaluate_confidence(
        self, inputs: List[EvidenceInput], base_confidence: Optional[str] = None
    ) -> str:
        """Evaluate deterministic confidence for a computation step based on input provenance."""
        if any(inp.is_conflict for inp in inputs):
            return EvidenceConfidence.LOW

        assumption_count = sum(1 for inp in inputs if inp.is_assumption)
        verified_count = sum(1 for inp in inputs if inp.lifecycle_stage in ("verified", "VERIFIED"))
        validated_count = sum(1 for inp in inputs if inp.lifecycle_stage in ("validated", "VALIDATED"))

        if assumption_count > 1:
            return EvidenceConfidence.MEDIUM if verified_count > 0 else EvidenceConfidence.LOW

        if verified_count >= 2 and assumption_count == 0:
            return EvidenceConfidence.VERY_HIGH

        if verified_count >= 1 or validated_count >= 1:
            return EvidenceConfidence.HIGH if assumption_count == 0 else EvidenceConfidence.MEDIUM

        return EvidenceConfidence.MEDIUM

    def _compute_overall_report_confidence(
        self,
        td_tam: Optional[TAMResult],
        bu_tam: Optional[TAMResult],
        comparison: Optional[MethodComparison],
        conflicts: List[Dict[str, Any]],
        total_assumptions: int,
    ) -> str:
        """Compute final deterministic confidence score for the entire report."""
        if conflicts:
            return EvidenceConfidence.LOW

        if comparison and comparison.divergence_severity == DivergenceSeverity.SEVERE_DIVERGENCE:
            return EvidenceConfidence.LOW

        if comparison and comparison.divergence_severity == DivergenceSeverity.ACCEPTABLE:
            if total_assumptions <= 1:
                return EvidenceConfidence.VERY_HIGH
            return EvidenceConfidence.HIGH

        if (td_tam and td_tam.confidence == EvidenceConfidence.HIGH) or (bu_tam and bu_tam.confidence == EvidenceConfidence.HIGH):
            return EvidenceConfidence.HIGH if total_assumptions <= 1 else EvidenceConfidence.MEDIUM

        return EvidenceConfidence.MEDIUM if (td_tam or bu_tam) else EvidenceConfidence.LOW

    def _build_report_message(
        self,
        status: CalculationStatus,
        td_tam: Optional[TAMResult],
        bu_tam: Optional[TAMResult],
        comparison: Optional[MethodComparison],
    ) -> str:
        """Build transparent summary description for the report."""
        if status == CalculationStatus.CONFLICT:
            return "Calculation completed with active evidence conflicts flagged."
        if status == CalculationStatus.INSUFFICIENT_EVIDENCE:
            return "Insufficient evidence to calculate a reliable TAM/SAM/SOM."
        if comparison:
            severity_str = comparison.divergence_severity.value if hasattr(comparison.divergence_severity, "value") else str(comparison.divergence_severity)
            return f"Market sizing completed using Top-Down and Bottom-Up methodologies ({severity_str})."
        if td_tam and td_tam.status == CalculationStatus.CALCULATED:
            return "Market sizing completed using Top-Down methodology."
        if bu_tam and bu_tam.status == CalculationStatus.CALCULATED:
            return "Market sizing completed using Bottom-Up methodology."
        return "Market sizing calculation completed."


_calculation_service_instance: Optional[CalculationService] = None


def get_calculation_service() -> CalculationService:
    """Dependency provider returning singleton CalculationService."""
    global _calculation_service_instance
    if _calculation_service_instance is None:
        _calculation_service_instance = CalculationService()
    return _calculation_service_instance

