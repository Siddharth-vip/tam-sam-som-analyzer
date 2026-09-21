from enum import Enum
import math
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.validation import EvidenceConfidence, EvidenceValidationStatus


class CalculationMethod(str, Enum):
    """Methodology applied for TAM/SAM/SOM market sizing."""

    TOP_DOWN = "top_down"
    BOTTOM_UP = "bottom_up"


class CalculationStatus(str, Enum):
    """Execution and evidentiary status of a calculation attempt."""

    CALCULATED = "calculated"
    NOT_CALCULABLE = "not_calculable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT = "conflict"
    INVALID_INPUT = "invalid_input"
    EXECUTION_FAILED = "execution_failed"


class EvidenceQualityRating(str, Enum):
    """Overall evidence quality assessment for market sizing."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class DivergenceSeverity(str, Enum):
    """Categorical classification of cross-method divergence between top-down and bottom-up."""

    ACCEPTABLE = "acceptable"
    WARNING = "warning"
    SEVERE_DIVERGENCE = "severe_divergence"


# Deterministic, configurable divergence thresholds (symmetric midpoint percentage difference)
ACCEPTABLE_DIVERGENCE_THRESHOLD: float = 20.0
WARNING_DIVERGENCE_THRESHOLD: float = 50.0


class AssumptionCategory(str, Enum):
    """Categorical scope of a calculation assumption or input parameter."""

    MARKET_SIZE = "MARKET_SIZE"
    TARGET_POPULATION = "TARGET_POPULATION"
    SEGMENT_PERCENTAGE = "SEGMENT_PERCENTAGE"
    PRICE = "PRICE"
    ARPU = "ARPU"
    PENETRATION = "PENETRATION"
    GEOGRAPHY = "GEOGRAPHY"
    GROWTH_RATE = "GROWTH_RATE"
    CUSTOMER_COUNT = "CUSTOMER_COUNT"
    CONVERSION_RATE = "CONVERSION_RATE"
    MARKET_SHARE = "MARKET_SHARE"
    CAPACITY = "CAPACITY"
    TIME_PERIOD = "TIME_PERIOD"
    FX_RATE = "FX_RATE"
    OTHER = "OTHER"


class AssumptionSourceType(str, Enum):
    """Epistemic provenance type distinguishing verified facts from explicit or model assumptions."""

    VERIFIED_EVIDENCE = "VERIFIED_EVIDENCE"
    VALIDATED_EVIDENCE = "VALIDATED_EVIDENCE"
    USER_ASSUMPTION = "USER_ASSUMPTION"
    MODEL_ASSUMPTION = "MODEL_ASSUMPTION"
    DERIVED_VALUE = "DERIVED_VALUE"
    UNKNOWN = "UNKNOWN"


class AssumptionImpact(str, Enum):
    """Assessed criticality and sensitivity impact of an assumption on final market results."""

    LOW_IMPACT = "LOW_IMPACT"
    MEDIUM_IMPACT = "MEDIUM_IMPACT"
    HIGH_IMPACT = "HIGH_IMPACT"
    CRITICAL = "CRITICAL"


class DataType(str, Enum):
    """Classification of empirical origin for market figures."""

    LIVE_VERIFIED_SOURCE = "LIVE_VERIFIED_SOURCE"
    SOURCED = "sourced"
    MOCK_SOURCE = "MOCK_SOURCE"
    USER_PROVIDED = "USER_PROVIDED"
    DERIVED = "derived"
    ESTIMATED = "estimated"
    AI_ASSUMPTION = "AI_assumption"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FreshnessCategory(str, Enum):
    """Temporal freshness classification of evidence relative to analysis target year."""

    RECENT = "RECENT"                   # 0-2 years old
    MODERATELY_OLD = "MODERATELY_OLD"   # 3-5 years old
    OLD = "OLD"                         # 6-10 years old
    VERY_OLD = "VERY_OLD"               # >10 years old
    UNKNOWN = "UNKNOWN"                 # Date unstated


class PriceFrequency(str, Enum):
    """Stated billing frequency for unit pricing inputs."""

    ANNUAL = "annual"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ONE_TIME = "one_time"


class UncertaintyInterval(BaseModel):
    """Structured representation of lower bound, point estimate, and upper bound."""

    model_config = ConfigDict(extra="ignore")

    lower: Optional[float] = Field(default=None, description="Lower bound of estimate.")
    point: Optional[float] = Field(default=None, description="Deterministic point estimate.")
    upper: Optional[float] = Field(default=None, description="Upper bound of estimate.")

    @model_validator(mode="after")
    def validate_bounds(self) -> "UncertaintyInterval":
        """Ensure lower bound does not exceed upper bound when both are present."""
        if self.lower is not None and self.upper is not None:
            if self.lower > self.upper:
                raise ValueError(f"Invalid uncertainty bounds: lower ({self.lower}) cannot exceed upper ({self.upper}).")
        return self


class EvidenceInput(BaseModel):
    """Numerical input for market calculation backed by validated evidence or explicit assumption."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    name: str = Field(..., description="Descriptive identifier for the input operand.")
    value: Optional[float] = Field(default=None, description="Normalized numerical value.")
    unit: str = Field(..., description="Unit of measurement (e.g., 'students', 'USD', 'INR', '%').")
    currency: Optional[str] = Field(default=None, description="Currency ISO code if monetary (e.g., 'USD', 'INR').")
    year: Optional[int] = Field(default=None, description="Reference calendar year.")
    geography: Optional[str] = Field(default=None, description="Geographic scope.")
    source_url: Optional[str] = Field(default=None, description="Verifiable source documentation URL.")
    source_name: Optional[str] = Field(default=None, description="Source authoring institution.")
    source_title: Optional[str] = Field(default=None, description="Source document or article title.")
    published_year: Optional[int] = Field(default=None, description="Publication calendar year.")
    evidence_id: Optional[str] = Field(default=None, description="ID of source candidate or evidence item.")
    validation_status: Optional[str] = Field(default=None, description="Validation status (e.g., valid, verified, assumed).")
    lifecycle_stage: Optional[str] = Field(default=None, description="Lifecycle stage. Must NOT be 'discovered'.")
    confidence: Optional[str] = Field(default=None, description="Confidence assessment of source evidence.")
    data_type: Optional[str] = Field(default="sourced", description="Epistemic data type: 'sourced', 'derived', 'estimated', 'AI_assumption'.")
    is_assumption: bool = Field(default=False, description="True if this input is an explicit assumption.")
    is_user_provided: bool = Field(default=False, description="True if this input was provided by the user.")
    is_model_derived: bool = Field(default=False, description="True if this input was derived by a model heuristic.")
    assumption_justification: Optional[str] = Field(default=None, description="Rationale for assumption.")
    range_min: Optional[float] = Field(default=None, description="Lower bound if input is an interval.")
    range_max: Optional[float] = Field(default=None, description="Upper bound if input is an interval.")
    is_conflict: bool = Field(default=False, description="True if input has unresolved conflicting source values.")
    conflicting_values: List[float] = Field(default_factory=list, description="List of distinct contradictory values.")
    source_quality_tier: Optional[str] = Field(default=None, description="Authority tier (Tier 1 Government to Tier 4 General Web).")
    market_scope: Optional[str] = Field(default=None, description="Classified market scope (e.g. Parent market, Addressable market, Serviceable market, Obtainable market).")
    market_scope_explanation: Optional[str] = Field(default=None, description="Detailed explanation of market scope.")
    is_prior_year_benchmark: bool = Field(default=False, description="True if evidence represents a prior-year baseline (e.g. 2024 data for 2025).")
    entity_concept: Optional[str] = Field(default=None, description="Entity type classification (person_demographic, institutional_business, household, volume_unit, currency).")


    @field_validator("name", "unit")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate string fields are non-empty."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v.strip()

    @field_validator("value")
    @classmethod
    def validate_finite_number(cls, v: Optional[float]) -> Optional[float]:
        """Validate finite numbers."""
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Value must be a finite number.")
        return v

    @model_validator(mode="after")
    def validate_bounds_and_percentages(self) -> "EvidenceInput":
        """Validate percentage ranges and ensure physical bounds."""
        # 0. Epistemic Guard: Discovered-only evidence cannot be used as a numerical calculation input
        if self.lifecycle_stage in (DiscoveryLifecycleStage.DISCOVERED, "discovered"):
            raise ValueError(
                f"Discovered-only evidence '{self.name}' cannot be used as a numerical calculation input. "
                "Evidence must be VALIDATED or VERIFIED before calculation."
            )

        norm_unit = self.unit.lower().strip()

        # 1. Reject invalid noise terms as unit
        if norm_unit in ("tip", "tips", "distributions", "lts", "bird", "birds", "tired"):
            raise ValueError(f"Unit '{self.unit}' is not a recognized market measurement unit.")

        # 2. Percentage bounds checking
        if norm_unit in ("%", "pct", "percent", "percentage", "share"):
            if self.value is not None:
                if self.value < 0.0 or self.value > 100.0:
                    raise ValueError(f"Percentage value ({self.value}) for '{self.name}' must be between 0 and 100.")
            if self.range_min is not None and (self.range_min < 0.0 or self.range_min > 100.0):
                raise ValueError(f"Percentage range_min ({self.range_min}) must be between 0 and 100.")
            if self.range_max is not None and (self.range_max < 0.0 or self.range_max > 100.0):
                raise ValueError(f"Percentage range_max ({self.range_max}) must be between 0 and 100.")

        # 3. Non-negativity for count and monetary metrics
        if norm_unit not in ("%", "pct", "percent", "percentage", "ratio", "cagr", "growth_rate"):
            if self.value is not None and self.value < 0.0:
                raise ValueError(f"Numerical value ({self.value}) for '{self.name}' cannot be negative.")
            if self.range_min is not None and self.range_min < 0.0:
                raise ValueError(f"range_min ({self.range_min}) for '{self.name}' cannot be negative.")

        # 4. Range consistency
        if self.range_min is not None and self.range_max is not None:
            if self.range_min > self.range_max:
                raise ValueError(f"range_min ({self.range_min}) cannot exceed range_max ({self.range_max}).")

        return self


class CalculationAssumption(BaseModel):
    """Explicitly declared modeling assumption with justification."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Assumption name (e.g., 'annual_subscription_price').")
    value: float = Field(..., description="Numerical value of the assumption.")
    unit: str = Field(..., description="Unit of measurement.")
    justification: str = Field(..., description="Explicit rationale or benchmark reference for the assumption.")
    is_user_provided: bool = Field(default=True, description="True if provided by the user.")


class CalculationStep(BaseModel):
    """Auditable mathematical step documenting formulas, operands, units, and references."""

    model_config = ConfigDict(extra="ignore")

    step_number: int = Field(..., ge=1, description="Sequential step index.")
    description: str = Field(..., description="Human-readable description of this computation step.")
    formula: str = Field(..., description="Mathematical formula expression.")
    operands: Dict[str, Any] = Field(default_factory=dict, description="Names and numerical values of operands.")
    result: Optional[float] = Field(default=None, description="Calculated point result.")
    result_interval: Optional[UncertaintyInterval] = Field(default=None, description="Calculated uncertainty interval.")
    unit: str = Field(..., description="Resulting unit of measurement.")
    evidence_references: List[str] = Field(default_factory=list, description="Source URLs or evidence IDs.")
    assumptions: List[str] = Field(default_factory=list, description="Names of assumptions applied in this step.")
    warnings: List[str] = Field(default_factory=list, description="Caveats or warnings for this step.")


def format_market_display_value(value: Optional[float], currency: Optional[str] = None) -> Optional[str]:
    """Format numerical market size into standard human-readable financial notation."""
    if value is None:
        return None
    curr = (currency or "INR").upper()
    if curr in ("INR", "₹"):
        if abs(value) >= 10_000_000:  # 1 Crore = 10 Million
            crores = value / 10_000_000
            return f"₹{crores:,.2f} crore"
        elif abs(value) >= 100_000:  # 1 Lakh = 100 Thousand
            lakhs = value / 100_000
            return f"₹{lakhs:,.2f} lakh"
        else:
            return f"₹{value:,.2f}"
    elif curr in ("USD", "$"):
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.2f}B"
        elif abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        elif abs(value) >= 1_000:
            return f"${value / 1_000:,.2f}K"
        else:
            return f"${value:,.2f}"
    else:
        if abs(value) >= 1_000_000_000:
            return f"{curr} {value / 1_000_000_000:,.2f}B"
        elif abs(value) >= 1_000_000:
            return f"{curr} {value / 1_000_000:,.2f}M"
        else:
            return f"{curr} {value:,.2f}"


class MetricCalculationResult(BaseModel):
    """Result of an individual market sizing computation (TAM, SAM, or SOM)."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    status: CalculationStatus = Field(default=CalculationStatus.NOT_CALCULABLE, description="Calculation outcome status.")
    estimate: Optional[float] = Field(default=None, description="Deterministic point estimate.")
    display_value: Optional[str] = Field(default=None, description="Human-formatted market sizing display value (e.g. '₹180 crore', '$1.4B').")
    method: Optional[str] = Field(default="bottom_up", description="Methodology applied (bottom_up, top_down).")
    formula: Optional[str] = Field(default=None, description="Mathematical formula expression.")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Detailed dictionary of input operands with provenance.")
    interval: Optional[UncertaintyInterval] = Field(default=None, description="Uncertainty range bounds.")
    unit: Optional[str] = Field(default=None, description="Measurement unit (e.g., 'INR/year', 'USD/year').")
    currency: Optional[str] = Field(default=None, description="Currency ISO code.")
    year: Optional[int] = Field(default=None, description="Reference calendar year.")
    geography: Optional[str] = Field(default=None, description="Target geographic scope.")
    confidence: Optional[str] = Field(default=None, description="Confidence level (low, medium, high, very_high).")
    evidence_quality: Optional[str] = Field(default=None, description="Deterministic evidence quality rating (HIGH, MEDIUM, LOW, INSUFFICIENT).")
    evidence_quality_reasons: List[str] = Field(default_factory=list, description="Audit rationale for evidence quality assessment.")
    market_scope: Optional[str] = Field(default=None, description="Explicit market scope category (e.g. Addressable market, Serviceable market, Obtainable market).")
    market_scope_explanation: Optional[str] = Field(default=None, description="Detailed scope definition explaining maximum realistic demand vs serviceable vs obtainable portions.")
    unit_compatibility_warnings: List[str] = Field(default_factory=list, description="Warnings if operand entities require normalization or have potential unit mismatch.")
    year_consistency_note: Optional[str] = Field(default=None, description="Audit note regarding temporal consistency.")
    geography_consistency_note: Optional[str] = Field(default=None, description="Audit note regarding geographic alignment.")
    sam_percentage_of_tam: Optional[float] = Field(default=None, description="Derived percentage of TAM (SAM / TAM * 100).")
    som_percentage_of_sam: Optional[float] = Field(default=None, description="Derived percentage of SAM (SOM / SAM * 100).")
    som_scenarios: Optional[Dict[str, float]] = Field(default=None, description="Conservative, Base, and Optimistic SOM scenario values.")
    steps: List[CalculationStep] = Field(default_factory=list, description="Auditable step-by-step calculation trace.")
    assumptions_used: List[CalculationAssumption] = Field(default_factory=list, description="Assumptions utilized.")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings or caveats.")
    message: Optional[str] = Field(default=None, description="Status summary or refusal reason.")

    @property
    def value(self) -> Optional[float]:
        """Backwards compatible alias for estimate."""
        return self.estimate

    @model_validator(mode="after")
    def validate_estimate_and_status(self) -> "MetricCalculationResult":
        # Automatically generate display value if estimate is present and display_value is unset
        if self.estimate is not None and not self.display_value:
            self.display_value = format_market_display_value(self.estimate, self.currency)

        # A metric with no numerical result must NOT be marked "Calculated"
        if self.estimate is None:
            if self.status == CalculationStatus.CALCULATED or self.status == "calculated":
                self.status = CalculationStatus.NOT_CALCULABLE
        elif self.estimate is not None:
            if self.status in (CalculationStatus.NOT_CALCULABLE, "not_calculable", CalculationStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence", None):
                self.status = CalculationStatus.CALCULATED
        return self


class TAMResult(MetricCalculationResult):
    """Total Addressable Market sizing result."""
    pass


class SAMResult(MetricCalculationResult):
    """Serviceable Addressable Market sizing result."""

    serviceable_customer_count: Optional[float] = Field(
        default=None, description="Deterministic serviceable customer population count."
    )
    serviceability_constraints: List[str] = Field(
        default_factory=list,
        description="Applied serviceability dimensions/constraints (geography, segment, product compatibility, regulatory).",
    )
    serviceability_evidence: List[str] = Field(
        default_factory=list, description="Evidence source references justifying serviceability bounds."
    )
    serviceability_factor: Optional[float] = Field(
        default=None, description="Derived serviceability percentage (0-100%)."
    )
    calculation_method: Optional[str] = Field(
        default="bottom_up", description="Calculation method (bottom_up or top_down)."
    )


class SOMResult(MetricCalculationResult):
    """Serviceable Obtainable Market sizing result."""

    obtainable_customer_count: Optional[float] = Field(
        default=None, description="Deterministic obtainable customer count."
    )
    obtainable_percentage_of_sam: Optional[float] = Field(
        default=None, description="Derived percentage of SAM (0-100%)."
    )
    obtainable_percentage_of_tam: Optional[float] = Field(
        default=None, description="Derived percentage of TAM (0-100%)."
    )
    calculation_method: Optional[str] = Field(
        default="bottom_up", description="Calculation method (bottom_up or top_down)."
    )
    capacity_assumptions: List[str] = Field(
        default_factory=list, description="Sales capacity, geographic coverage, or penetration constraints."
    )


class TopDownCalculationInputs(BaseModel):
    """Inputs required for top-down market sizing."""

    model_config = ConfigDict(extra="ignore")

    macro_market_size: Optional[EvidenceInput] = Field(
        default=None,
        description="Starting aggregate market size in currency (e.g., National or Global industry spend).",
    )
    segment_percentages: List[EvidenceInput] = Field(
        default_factory=list,
        description="List of segment narrowing percentages (0-100%).",
    )
    serviceable_geography_percentage: Optional[EvidenceInput] = Field(
        default=None,
        description="Geographic narrowing percentage (0-100%).",
    )
    target_segment_percentage: Optional[EvidenceInput] = Field(
        default=None,
        description="Target customer segment percentage (0-100%).",
    )
    other_filters: List[EvidenceInput] = Field(
        default_factory=list,
        description="Additional evidence-supported percentage filters.",
    )
    obtainable_market_share: Optional[EvidenceInput] = Field(
        default=None,
        description="Evidence-backed or explicit user assumption for obtainable market share percentage (0-100%).",
    )


class BottomUpCalculationInputs(BaseModel):
    """Inputs required for bottom-up unit-economics market sizing."""

    model_config = ConfigDict(extra="ignore")

    pricing_basis: Optional[str] = Field(
        default="per_facility",
        description="Healthcare SaaS pricing basis ('per_facility', 'per_organization', 'per_provider', 'per_user', 'per_seat', 'per_patient', 'per_transaction', 'monthly_subscription', 'annual_subscription', 'usage_based', 'tiered_subscription', 'custom').",
    )
    potential_customers: Optional[EvidenceInput] = Field(
        default=None,
        description="Total potential customer population count (organizations, facilities, or individual providers).",
    )
    base_organizations: Optional[EvidenceInput] = Field(
        default=None,
        description="Base healthcare organization count before applying segment percentage filter.",
    )
    segment_percentage: Optional[EvidenceInput] = Field(
        default=None,
        description="Percentage of base organizations in target segment (0-100%). Used to derive potential_customers.",
    )
    serviceable_customers: Optional[EvidenceInput] = Field(
        default=None,
        description="Serviceable customer count (if directly known), or computed via target_customer_percentage.",
    )
    target_customer_percentage: Optional[EvidenceInput] = Field(
        default=None,
        description="Percentage of potential customers that meet serviceable criteria (0-100%).",
    )
    serviceability_constraints: List[str] = Field(
        default_factory=list,
        description="List of applied serviceability constraints (e.g., geography, segment, product/integration capability).",
    )
    realistically_obtainable_customers: Optional[EvidenceInput] = Field(
        default=None,
        description="Explicit count of realistically obtainable customers in Years 1-3.",
    )
    obtainable_market_share: Optional[EvidenceInput] = Field(
        default=None,
        description="Obtainable market share percentage of serviceable customers (0-100%).",
    )
    pricing: Optional[EvidenceInput] = Field(
        default=None,
        description="Annual, monthly, per-provider, or per-user revenue price.",
    )
    pricing_frequency: PriceFrequency = Field(
        default=PriceFrequency.ANNUAL,
        description="Pricing billing frequency. If monthly, annual price = monthly * 12.",
    )
    users_per_organization: Optional[EvidenceInput] = Field(
        default=None,
        description="Expected users or seats per organization for per-user / per-seat models.",
    )
    providers_per_organization: Optional[EvidenceInput] = Field(
        default=None,
        description="Expected providers/clinicians per organization for per-provider models.",
    )
    annual_volume_per_customer: Optional[EvidenceInput] = Field(
        default=None,
        description="Expected annual patient interactions or transactions per customer for usage-based models.",
    )


class CalculationInput(BaseModel):
    """Complete request payload for market sizing calculation."""

    model_config = ConfigDict(extra="ignore")

    business_idea: Optional[str] = Field(default=None, description="Brief description of the business idea.")
    target_geography: Optional[str] = Field(default=None, description="Target geographic scope.")
    target_year: Optional[int] = Field(default=None, description="Target calendar year.")
    market_definition: Optional[str] = Field(default=None, description="Dynamic market definition.")
    tam_methodology: Optional[str] = Field(default=None, description="Selected TAM calculation methodology.")
    sam_methodology: Optional[str] = Field(default=None, description="Selected SAM calculation methodology.")
    som_methodology: Optional[str] = Field(default=None, description="Selected SOM calculation methodology.")
    top_down_inputs: Optional[TopDownCalculationInputs] = Field(default=None, description="Top-down sizing inputs.")
    bottom_up_inputs: Optional[BottomUpCalculationInputs] = Field(default=None, description="Bottom-up sizing inputs.")
    assumptions: List[CalculationAssumption] = Field(default_factory=list, description="Explicit assumptions.")


class MethodComparison(BaseModel):
    """Side-by-side comparison and divergence analysis between top-down and bottom-up sizing."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    top_down_tam: Optional[float] = Field(default=None, description="Top-down TAM point estimate.")
    bottom_up_tam: Optional[float] = Field(default=None, description="Bottom-up TAM point estimate.")
    top_down_estimate: Optional[float] = Field(default=None, description="Primary estimate from Top-Down calculation.")
    bottom_up_estimate: Optional[float] = Field(default=None, description="Primary estimate from Bottom-Up calculation.")
    currency: Optional[str] = Field(default=None, description="Common currency unit.")
    absolute_difference: Optional[float] = Field(default=None, description="Absolute difference (|TopDown - BottomUp|).")
    percentage_difference: Optional[float] = Field(default=None, description="Symmetric midpoint percentage difference (|A-B| / ((A+B)/2) * 100).")
    relative_ratio: Optional[float] = Field(default=None, description="Ratio of larger to smaller (max/min).")
    divergence_severity: Optional[DivergenceSeverity] = Field(
        default=None,
        description="Classification: ACCEPTABLE (<=20%), WARNING (20%-50%), SEVERE_DIVERGENCE (>50%).",
    )
    divergence_explanation: Optional[str] = Field(default=None, description="Detailed explanation of the divergence calculation and severity.")
    triangulation_confidence: Optional[str] = Field(default=None, description="Deterministic confidence level assigned to triangulation.")
    root_cause_diagnostics: List[str] = Field(default_factory=list, description="Diagnostic reasons for divergence between methods.")
    sam_comparison: Optional[Dict[str, Any]] = Field(default=None, description="Optional cross-method comparison for SAM.")
    som_comparison: Optional[Dict[str, Any]] = Field(default=None, description="Optional cross-method comparison for SOM.")
    explanation: str = Field(..., description="Transparent narrative explaining the comparative alignment.")


class AssumptionItem(BaseModel):
    """Individual formal assumption with epistemic classification, impact rating, and provenance."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: str = Field(default_factory=lambda: f"asmp_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., description="Parameter or assumption name.")
    value: float = Field(..., description="Numerical value.")
    unit: str = Field(..., description="Unit of measurement.")
    category: AssumptionCategory = Field(default=AssumptionCategory.OTHER, description="Parameter category.")
    source_type: AssumptionSourceType = Field(default=AssumptionSourceType.USER_ASSUMPTION, description="Epistemic source type.")
    source_reference: Optional[str] = Field(default=None, description="URL or citation if evidence-backed.")
    confidence: Optional[str] = Field(default=EvidenceConfidence.MEDIUM, description="Confidence level.")
    justification: str = Field(..., description="Explicit rationale or benchmark reference.")
    is_user_provided: bool = Field(default=True, description="True if provided by user.")
    is_evidence_based: bool = Field(default=False, description="True if supported by empirical source.")
    is_model_derived: bool = Field(default=False, description="True if derived by model heuristic.")
    impact: AssumptionImpact = Field(default=AssumptionImpact.MEDIUM_IMPACT, description="Impact level on TAM/SAM/SOM.")
    affects: List[str] = Field(default_factory=list, description="Target metrics affected, e.g. ['TAM', 'SAM'].")
    min_value: Optional[float] = Field(default=None, description="Lower bound if interval known.")
    max_value: Optional[float] = Field(default=None, description="Upper bound if interval known.")
    uncertainty_status: str = Field(default="POINT_ONLY", description="Interval status, e.g. EVIDENCE_BOUNDED, POINT_ONLY, INSUFFICIENT_EVIDENCE.")


class AssumptionRegistry(BaseModel):
    """Formal registry aggregating all assumptions, empirical facts, and heuristics used in calculations."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    items: List[AssumptionItem] = Field(default_factory=list, description="All registered parameters and assumptions.")
    total_count: int = Field(default=0)
    user_provided_count: int = Field(default=0)
    model_derived_count: int = Field(default=0)
    critical_assumptions_count: int = Field(default=0)
    high_impact_count: int = Field(default=0)


class ScenarioEstimate(BaseModel):
    """Scenario bounds for an individual market metric."""

    model_config = ConfigDict(extra="ignore")

    low: Optional[float] = Field(default=None, description="Conservative / lower-bound estimate.")
    base: Optional[float] = Field(default=None, description="Base point estimate.")
    high: Optional[float] = Field(default=None, description="Optimistic / upper-bound estimate.")
    unit: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default=None)


class UncertaintyAnalysis(BaseModel):
    """Deterministic scenario analysis across Low, Base, and High cases when supported by range evidence."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="INSUFFICIENT_EVIDENCE", description="'AVAILABLE' if backed by range data, else 'INSUFFICIENT_EVIDENCE'.")
    tam_scenario: Optional[ScenarioEstimate] = Field(default=None)
    sam_scenario: Optional[ScenarioEstimate] = Field(default=None)
    som_scenario: Optional[ScenarioEstimate] = Field(default=None)
    basis: str = Field(default="Point estimates only; range evidence not provided in sources.", description="Grounds for uncertainty calculation.")
    explanation: str = Field(default="Uncertainty scenarios require empirical min/max bounds or user-supplied intervals.", description="Detailed uncertainty narrative.")


class SensitivityParameter(BaseModel):
    """Deterministic sensitivity assessment showing how a single input parameter drives market size variance."""

    model_config = ConfigDict(extra="ignore")

    parameter: str = Field(..., description="Parameter identifier.")
    base_value: float = Field(..., description="Baseline value.")
    unit: str = Field(..., description="Measurement unit.")
    impact: str = Field(default="MEDIUM", description="'HIGH', 'MEDIUM', 'LOW'.")
    elasticity: float = Field(default=1.0, description="Percentage change in TAM per 1% change in parameter.")
    explanation: str = Field(..., description="Explanation of sensitivity impact.")


class ReliabilityAssessment(BaseModel):
    """Multi-dimensional Evidence-Based Reliability rating for the final TAM/SAM/SOM market assessment."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    level: str = Field(..., description="Overall reliability level: HIGH, MEDIUM, LOW, INSUFFICIENT.")
    reason: str = Field(..., description="Comprehensive rationale for assigned reliability rating.")
    evidence_strength: str = Field(default="MEDIUM", description="Strength of underlying empirical evidence (HIGH, MEDIUM, LOW, INSUFFICIENT).")
    assumption_risk: str = Field(default="LOW", description="Risk level posed by unverified or critical assumptions (LOW, MEDIUM, HIGH, CRITICAL).")
    freshness: str = Field(default="RECENT", description="Freshness of primary input data (RECENT, MODERATELY_OLD, OLD, VERY_OLD, UNKNOWN).")
    methodology_agreement: str = Field(default="ACCEPTABLE", description="Agreement between top-down and bottom-up (ACCEPTABLE, WARNING, SEVERE_DIVERGENCE, SINGLE_METHOD).")
    double_counting_risk: bool = Field(default=False, description="True if top-down and bottom-up operands risk measuring identical pools without segmentation.")
    geography_consistency: str = Field(default="CONSISTENT", description="Geographic scope alignment status.")
    temporal_consistency: str = Field(default="CONSISTENT", description="Temporal alignment status.")
    currency_consistency: str = Field(default="CONSISTENT", description="Currency alignment status.")


class TAMTrace(BaseModel):
    """Deterministic trace of evidence selected for TAM."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Unique ID of selected TAM evidence candidate.")
    value: Optional[Any] = Field(default=None, description="Selected TAM value or estimate.")
    geography: Optional[str] = Field(default=None, description="Geographic scope of selected evidence.")
    year: Optional[Any] = Field(default=None, description="Reference year of selected evidence.")
    source: Optional[str] = Field(default=None, description="Source URL or publication name.")


class SAMTrace(BaseModel):
    """Deterministic trace of evidence and factors selected for SAM."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Unique ID of selected narrowing candidate.")
    factor: Optional[Any] = Field(default=None, description="Selected narrowing percentage or customer count factor.")
    factor_type: Optional[str] = Field(default=None, description="Type of narrowing factor (geography, segment, channel, etc.).")
    reason: Optional[str] = Field(default=None, description="Justification or semantic rationale for applying this factor.")
    formula: Optional[str] = Field(default=None, description="Exact arithmetic derivation formula.")
    value: Optional[Any] = Field(default=None, description="Calculated SAM value.")


class SOMTrace(BaseModel):
    """Deterministic trace of evidence selected for SOM."""

    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Unique ID of selected SOM candidate.")
    factor: Optional[Any] = Field(default=None, description="Obtainable capture percentage or target customer capacity.")
    reason: Optional[str] = Field(default=None, description="Justification or rationale for SOM status.")
    value: Optional[Any] = Field(default=None, description="Calculated SOM value.")


class CalculationTrace(BaseModel):
    """Structured calculation trace object for deterministic auditing and debugging."""

    model_config = ConfigDict(extra="ignore")

    tam: Optional[TAMTrace] = Field(default=None, description="TAM derivation trace.")
    sam: Optional[SAMTrace] = Field(default=None, description="SAM derivation trace.")
    som: Optional[SOMTrace] = Field(default=None, description="SOM derivation trace.")


class CalculationReport(BaseModel):
    """Comprehensive auditable calculation report containing TAM, SAM, SOM, and method comparison."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    calculation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique calculation run ID.")
    status: CalculationStatus = Field(default=CalculationStatus.CALCULATED, description="Overall calculation outcome.")
    target_geography: Optional[str] = Field(default=None, description="Target geographic scope.")
    target_year: Optional[int] = Field(default=None, description="Target calendar year.")
    currency: Optional[str] = Field(default=None, description="Primary reporting currency.")
    top_down_tam: Optional[TAMResult] = Field(default=None, description="Top-down TAM calculation.")
    top_down_sam: Optional[SAMResult] = Field(default=None, description="Top-down SAM calculation.")
    top_down_som: Optional[SOMResult] = Field(default=None, description="Top-down SOM calculation.")
    bottom_up_tam: Optional[TAMResult] = Field(default=None, description="Bottom-up TAM calculation.")
    bottom_up_sam: Optional[SAMResult] = Field(default=None, description="Bottom-up SAM calculation.")
    bottom_up_som: Optional[SOMResult] = Field(default=None, description="Bottom-up SOM calculation.")
    method_comparison: Optional[MethodComparison] = Field(default=None, description="Cross-methodology validation.")
    confidence: str = Field(default=EvidenceConfidence.LOW, description="Overall report confidence level.")
    evidence_quality: Optional[str] = Field(default=None, description="Deterministic evidence quality rating (HIGH, MEDIUM, LOW, INSUFFICIENT).")
    evidence_quality_reasons: List[str] = Field(default_factory=list, description="Audit rationale for evidence quality assessment.")
    assumption_registry: Optional[AssumptionRegistry] = Field(default=None, description="Formal Assumption Registry tracking epistemic classifications and risk.")
    uncertainty_analysis: Optional[UncertaintyAnalysis] = Field(default=None, description="Deterministic Low/Base/High uncertainty scenario analysis.")
    sensitivity_analysis: List[SensitivityParameter] = Field(default_factory=list, description="Deterministic sensitivity ranking of key driver parameters.")
    reliability_assessment: Optional[ReliabilityAssessment] = Field(default=None, description="Evidence-Based Reliability assessment.")
    unit_compatibility_warnings: List[str] = Field(default_factory=list, description="Warnings regarding unit or entity compatibility across operands.")
    all_steps: List[CalculationStep] = Field(default_factory=list, description="Complete unified audit trail.")
    all_assumptions: List[CalculationAssumption] = Field(default_factory=list, description="All assumptions utilized.")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Contradictory evidence items flagged.")
    market_definition: Optional[str] = Field(default=None, description="Concise definition of the market being analyzed.")
    tam_methodology: Optional[str] = Field(default=None, description="Selected TAM sizing methodology.")
    sam_methodology: Optional[str] = Field(default=None, description="Selected SAM sizing methodology.")
    som_methodology: Optional[str] = Field(default=None, description="Selected SOM sizing methodology.")
    warnings: List[str] = Field(default_factory=list, description="Global calculation warnings and caveats.")
    calculation_trace: Optional[CalculationTrace] = Field(default=None, description="Deterministic evidence calculation trace for debugging.")


