from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.fetching.models import FetchedSource
from app.schemas.business import (
    BusinessAnalysis,
    BusinessModelAnalysis,
    CompetitorInfo,
    CustomerSegmentItem,
    HealthcareCustomerType,
    HealthcarePricingBasis,
    HealthcareSaaSCategory,
    IncompleteInputResponse,
    MarketAttractivenessAssessment,
    MarketGrowthItem,
    MarketTrendItem,
    ValuePropositionAnalysis,
)
from app.schemas.calculation import (
    CalculationAssumption,
    CalculationReport,
    CalculationTrace,
    SAMResult,
    SOMResult,
    TAMResult,
)
from app.schemas.discovery import DiscoveredSource, ResearchQuery
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    ConflictGroup,
    EvidenceConfidence,
    EvidenceValidationResult,
    SourceProvenance,
    TriangulationResult,
)


class PipelineStage(str, Enum):
    """Explicit pipeline execution stages."""

    RECEIVED = "received"
    INPUT_VALIDATION = "input_validation"
    BUSINESS_ANALYSIS = "business_analysis"
    QUERY_GENERATION = "query_generation"
    DISCOVERY = "discovery"
    FETCHING = "fetching"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    TRIANGULATION = "triangulation"
    CALCULATION = "calculation"
    REPORT_GENERATION = "report_generation"
    COMPLETED = "completed"
    FAILED = "failed"


# Explicit state alias for state machine
PipelineState = PipelineStage


class PipelineStatus(str, Enum):
    """Overall and stage status flags."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    CONFLICT = "conflict"


class PipelineRequest(BaseModel):
    """Healthcare SaaS Input Request Schema."""

    model_config = ConfigDict(extra="ignore")

    # A. Business Information
    business_name: Optional[str] = Field(
        default=None,
        description="Name of the Healthcare SaaS product or startup.",
        examples=["MedFlow AI"],
    )
    business_idea: str = Field(
        ...,
        description="The Healthcare SaaS business concept or description.",
        examples=["AI-powered clinic management and EHR SaaS for dental clinics in India"],
    )
    healthcare_saas_category: Optional[Union[HealthcareSaaSCategory, str]] = Field(
        default=None,
        description="Healthcare SaaS category (e.g. Clinic Management SaaS, Hospital Management SaaS, EHR/EMR SaaS).",
    )
    product_description: Optional[str] = Field(
        default=None,
        description="Detailed product features and capabilities.",
    )
    primary_problem: Optional[str] = Field(
        default=None,
        description="Core healthcare/clinical or operational problem being solved.",
    )
    primary_use_case: Optional[str] = Field(
        default=None,
        description="Primary workflow or clinical use case.",
    )
    key_features: List[str] = Field(
        default_factory=list,
        description="List of key software features.",
    )
    unique_value_proposition: Optional[str] = Field(
        default=None,
        description="Unique differentiator or value proposition.",
    )

    # B. Target Market
    target_country: Optional[str] = Field(
        default=None,
        description="Target country (e.g. India, United States, United Kingdom).",
    )
    target_state_or_region: Optional[str] = Field(
        default=None,
        description="Target state, province, or region if applicable.",
    )
    target_region: Optional[str] = Field(
        default=None,
        description="Alias for target_state_or_region.",
    )
    target_city: Optional[str] = Field(
        default=None,
        description="Target city if localized.",
    )
    target_healthcare_market: Optional[str] = Field(
        default=None,
        description="Sub-market within healthcare (e.g. Tier 2/3 Private Hospitals, Dental Clinics).",
    )

    # C. Customer Information (Paying Entity)
    customer_type: Optional[Union[HealthcareCustomerType, str]] = Field(
        default=None,
        description="The paying entity type (e.g. Hospitals, Clinics, Diagnostic Laboratories, Pharmacies, Medical Practices).",
    )
    organization_size: Optional[str] = Field(
        default=None,
        description="Customer organization size (e.g. Small Practice, 50-200 Beds, Large Enterprise Network).",
    )
    number_of_employees: Optional[int] = Field(
        default=None,
        description="Expected users/seats per organization.",
    )
    number_of_facilities: Optional[int] = Field(
        default=None,
        description="Expected facilities/branches per organization.",
    )
    number_of_organizations: Optional[int] = Field(
        default=None,
        description="Explicit user-provided target organization count if known.",
    )
    target_customer_segment: Optional[str] = Field(
        default=None,
        description="Specific target persona or buyer profile (e.g. Independent Dental Practitioners).",
    )

    # D. Product / SaaS Model & Pricing
    business_model: Optional[str] = Field(
        default="B2B SaaS",
        description="Business model (e.g. B2B, B2C, B2B2C).",
    )
    pricing_basis: Optional[Union[HealthcarePricingBasis, str]] = Field(
        default=None,
        description="Pricing basis: 'per_user', 'per_provider', 'per_facility', 'per_bed', 'monthly_subscription', 'annual_subscription', 'usage_based', 'tiered_subscription', 'custom'.",
    )
    pricing_model: Optional[Union[HealthcarePricingBasis, str]] = Field(
        default=None,
        description="Monetization model: 'monthly_subscription', 'annual_subscription', 'per_provider', 'per_facility', 'per_user', 'custom'.",
    )
    monthly_price: Optional[float] = Field(
        default=None,
        description="Monthly subscription price in local currency.",
    )
    annual_price: Optional[float] = Field(
        default=None,
        description="Annual subscription price in local currency.",
    )
    per_user_price: Optional[float] = Field(
        default=None,
        description="Per-user/seat price.",
    )
    per_provider_price: Optional[float] = Field(
        default=None,
        description="Per-doctor/physician/clinician price.",
    )
    per_facility_price: Optional[float] = Field(
        default=None,
        description="Per-hospital/clinic/facility price.",
    )
    currency: Optional[str] = Field(
        default="INR",
        description="Pricing currency (INR, USD, EUR, GBP, etc.).",
    )
    allow_estimated_pricing: bool = Field(
        default=False,
        description="If True, allow the system to use researched industry pricing benchmarks if specific pricing is unprovided.",
    )

    # E. Healthcare-Specific Information
    healthcare_domain: Optional[str] = Field(
        default=None,
        description="Specialty or domain (e.g. Dental, Radiology, Primary Care, Oncology, Cardiology).",
    )
    clinical_use: Optional[bool] = Field(
        default=None,
        description="True if product is directly involved in clinical care/diagnostics; False for administrative/operational.",
    )
    provider_type: Optional[str] = Field(
        default=None,
        description="Provider designation (e.g. Radiologists, General Practitioners, Dentists, Lab Technicians).",
    )
    patient_involvement: Optional[bool] = Field(
        default=None,
        description="True if patients directly log in or interact with the software.",
    )
    healthcare_workflow: Optional[str] = Field(
        default=None,
        description="Target clinical or operational workflow.",
    )
    emr_ehr_integration_required: Optional[bool] = Field(
        default=None,
        description="Whether integration with hospital/clinic EMR/EHR systems is necessary.",
    )
    interoperability_standards: Optional[str] = Field(
        default=None,
        description="Interoperability standards (e.g. HL7 FHIR, ABDM M1/M2/M3, DICOM, SMART-on-FHIR).",
    )
    regulatory_market: Optional[str] = Field(
        default=None,
        description="Applicable healthcare regulatory frameworks (e.g. NABH/ABDM/DISHA for India, HIPAA/FDA for US, CE/MDR for EU).",
    )
    regulatory_constraints: Optional[str] = Field(
        default=None,
        description="Identified compliance constraints or certifications required.",
    )

    # F. SOM Acquisition & Sales Capacity Factors
    sales_team_size: Optional[int] = Field(
        default=None,
        description="Number of direct sales representatives or account executives dedicated to customer acquisition.",
    )
    sales_cycle_months: Optional[float] = Field(
        default=None,
        description="Expected institutional sales and procurement cycle in months (e.g. 1-2 months for single clinics, 6-12 months for enterprise hospitals).",
    )
    expected_customer_acquisition_annual: Optional[float] = Field(
        default=None,
        description="Expected or planned customer acquisition count in Year 1-3.",
    )
    geographic_reach_percentage: Optional[float] = Field(
        default=None,
        description="Initial addressable geographic reach percentage within the country (e.g. 100% for national, 25% for regional launch).",
    )
    serviceable_percentage: Optional[float] = Field(
        default=None,
        description="Explicit user-provided serviceable customer percentage (0-100%).",
    )
    serviceable_organizations: Optional[int] = Field(
        default=None,
        description="Explicit user-provided serviceable organization count.",
    )
    serviceability_criteria: Optional[List[str]] = Field(
        default_factory=list,
        description="Explicit user-specified serviceability constraints (e.g., 'NABH Accredited', 'Tier 1/2 Cities', 'EMR Adoption').",
    )

    # Pipeline controls & backwards compatibility
    max_sources: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum external sources to discover and fetch.",
    )
    enable_calculation: bool = Field(
        default=True,
        description="Whether to perform deterministic TAM/SAM/SOM calculations.",
    )
    explicit_assumptions: List[CalculationAssumption] = Field(
        default_factory=list,
        description="Optional explicit assumptions.",
    )
    assumptions: Optional[List[CalculationAssumption]] = Field(
        default_factory=list,
        description="Alias for explicit_assumptions.",
    )
    preferred_geography: Optional[str] = Field(
        default=None,
        description="Target geography alias.",
    )
    preferred_year: Optional[int] = Field(
        default=None,
        description="Target analysis year alias.",
    )

    @field_validator("business_idea")
    @classmethod
    def validate_business_idea(cls, v: str) -> str:
        """Validate non-empty business idea."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("business_idea must be a non-empty string.")
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("business_idea must be at least 3 characters.")
        return cleaned

    @field_validator("target_country", "preferred_geography", mode="before")
    @classmethod
    def sanitize_geography(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize empty or Swagger placeholder strings."""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned or cleaned.lower() in ("string", "none", "null", "undefined"):
                return None
            return cleaned
        return v

    @field_validator("preferred_year", mode="before")
    @classmethod
    def sanitize_preferred_year(cls, v: Optional[int]) -> Optional[int]:
        """Sanitize year."""
        if v is None:
            return None
        try:
            val = int(v)
            if val < 1900 or val > 2100:
                return None
            return val
        except (ValueError, TypeError):
            return None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        """Normalize aliases and populate missing links."""
        if isinstance(data, dict):
            # Geography synchronization
            if not data.get("target_country") and data.get("preferred_geography"):
                data["target_country"] = data["preferred_geography"]
            elif data.get("target_country") and not data.get("preferred_geography"):
                data["preferred_geography"] = data["target_country"]
            
            # Region synchronization
            if not data.get("target_region") and data.get("target_state_or_region"):
                data["target_region"] = data["target_state_or_region"]
            elif data.get("target_region") and not data.get("target_state_or_region"):
                data["target_state_or_region"] = data["target_region"]

            # Pricing basis / model synchronization
            if data.get("pricing_basis") and not data.get("pricing_model"):
                val = data["pricing_basis"]
                data["pricing_model"] = val.value if hasattr(val, "value") else str(val)
            elif data.get("pricing_model") and not data.get("pricing_basis"):
                val = data["pricing_model"]
                data["pricing_basis"] = val.value if hasattr(val, "value") else str(val)

            # EMR / EHR integration field alias
            if "emr_integration_required" in data and "emr_ehr_integration_required" not in data:
                data["emr_ehr_integration_required"] = data["emr_integration_required"]
            elif "emr_ehr_integration_required" in data and "emr_integration_required" not in data:
                data["emr_integration_required"] = data["emr_ehr_integration_required"]

            # Clinical or non-clinical string alias
            if "clinical_or_non_clinical" in data and data.get("clinical_use") is None:
                val = str(data["clinical_or_non_clinical"]).strip().lower()
                data["clinical_use"] = val == "clinical"

            if "assumptions" in data and not data.get("explicit_assumptions"):
                data["explicit_assumptions"] = data["assumptions"]
        return data


class PipelineProgressEvent(BaseModel):
    """Event emitted during async pipeline streaming."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    pipeline_id: str = Field(..., description="Unique pipeline execution ID.")
    stage: PipelineStage = Field(..., description="Current pipeline stage.")
    status: PipelineStatus = Field(..., description="Stage status.")
    message: str = Field(..., description="Human-readable progress message.")
    progress_percent: int = Field(..., ge=0, le=100, description="Estimated completion percentage 0-100.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of the event.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional stage-specific contextual metadata.",
    )


class StateTransitionRecord(BaseModel):
    """Audit log record for an individual pipeline state transition."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    transition_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique transition record ID.")
    from_state: Optional[str] = Field(default=None, description="Previous pipeline stage/state.")
    to_state: str = Field(..., description="Target pipeline stage/state.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of transition.",
    )
    message: Optional[str] = Field(default=None, description="Diagnostic progress or status note.")
    duration_ms: Optional[float] = Field(default=None, description="Execution duration of previous phase in milliseconds.")
    error: Optional[str] = Field(default=None, description="Error detail if phase encountered an exception.")


class HealthcareMarketAttractiveness(BaseModel):
    """Final assessment of Healthcare SaaS market opportunity."""

    rating: str = Field(..., description="Overall score: HIGH, MEDIUM, LOW.")
    score: float = Field(default=0.0, ge=0.0, le=10.0, description="Quantitative attractiveness score 0-10.")
    market_size_appeal: str = Field(default="MEDIUM", description="Attractiveness of addressable TAM/SAM.")
    growth_outlook: str = Field(default="STRONG", description="Healthcare sector CAGR and adoption trajectory.")
    competitive_intensity: str = Field(default="MODERATE", description="Competitive density and incumbent barriers.")
    procurement_friction: str = Field(default="MODERATE", description="Healthcare sales cycle and decision-maker complexity.")
    regulatory_readiness: str = Field(default="MANAGEABLE", description="Compliance/certification overhead.")
    rationale: str = Field(..., description="Detailed reasoned justification for the rating.")


class PipelineResult(BaseModel):
    """Final comprehensive auditable report for Healthcare SaaS Market Analysis."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    pipeline_id: str = Field(
        default_factory=lambda: f"pipe_{uuid.uuid4().hex[:12]}",
        description="Unique pipeline execution ID.",
    )
    status: PipelineStatus = Field(
        default=PipelineStatus.COMPLETED,
        description="Overall pipeline execution status.",
    )
    business_idea: str = Field(
        ...,
        description="Original raw business idea submitted.",
    )
    business_analysis: Optional[BusinessAnalysis] = Field(
        default=None,
        description="Structured Healthcare SaaS concept extraction and classification.",
    )
    research_queries: List[ResearchQuery] = Field(
        default_factory=list,
        description="Generated healthcare research requirement queries.",
    )
    discovered_sources: List[DiscoveredSource] = Field(
        default_factory=list,
        description="Candidate external sources discovered.",
    )
    fetched_sources: List[FetchedSource] = Field(
        default_factory=list,
        description="Fetched source documents.",
    )
    extracted_candidates: List[ExtractedEvidenceCandidate] = Field(
        default_factory=list,
        description="Candidate numerical evidence extracted.",
    )
    validation_results: List[EvidenceValidationResult] = Field(
        default_factory=list,
        description="Validated evidence items.",
    )
    triangulation_result: Optional[TriangulationResult] = Field(
        default=None,
        description="Multi-source triangulation and corroboration result.",
    )
    calculation_report: Optional[CalculationReport] = Field(
        default=None,
        description="Deterministic TAM/SAM/SOM market sizing calculation report.",
    )
    tam: Optional[TAMResult] = Field(
        default=None,
        description="Total Addressable Market result summary.",
    )
    sam: Optional[SAMResult] = Field(
        default=None,
        description="Serviceable Addressable Market result summary.",
    )
    som: Optional[SOMResult] = Field(
        default=None,
        description="Serviceable Obtainable Market result summary.",
    )
    som_scenarios: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conservative, Base, and Optimistic SOM estimates.",
    )
    calculation_trace: Optional[CalculationTrace] = Field(
        default=None,
        description="Structured deterministic calculation trace for auditing.",
    )
    market_attractiveness: Optional[Union[MarketAttractivenessAssessment, HealthcareMarketAttractiveness, Dict[str, Any]]] = Field(
        default=None,
        description="Overall Market Attractiveness assessment.",
    )
    confidence: str = Field(
        default=EvidenceConfidence.LOW,
        description="Overall pipeline confidence level.",
    )
    evidence_quality_rating: Optional[str] = Field(
        default=None,
        description="Overall deterministic evidence quality rating (HIGH, MEDIUM, LOW, INSUFFICIENT).",
    )
    research_provider: Optional[str] = Field(
        default="mock",
        description="Active discovery search provider mode ('mock', 'live', 'tavily', 'searxng').",
    )
    rejected_sources: List[DiscoveredSource] = Field(
        default_factory=list,
        description="Discovered sources filtered out as irrelevant during pre-fetch relevance evaluation.",
    )
    rejected_candidates: List[ExtractedEvidenceCandidate] = Field(
        default_factory=list,
        description="Extracted candidates rejected as non-market noise during validation.",
    )
    competitors: List[CompetitorInfo] = Field(
        default_factory=list,
        description="Competitor intelligence identified with source provenance.",
    )
    competitor_comparison: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured competitor comparison matrix.",
    )
    market_trends: List[MarketTrendItem] = Field(
        default_factory=list,
        description="Dynamic market trends with supporting evidence.",
    )
    market_growth: Optional[MarketGrowthItem] = Field(
        default=None,
        description="Deterministic or source-reported market CAGR and growth metrics.",
    )
    customer_segmentation: List[CustomerSegmentItem] = Field(
        default_factory=list,
        description="Customer tier segmentation breakdown.",
    )
    value_proposition_analysis: Optional[ValuePropositionAnalysis] = Field(
        default=None,
        description="Structured value proposition and differentiator analysis.",
    )
    business_model_analysis: Optional[BusinessModelAnalysis] = Field(
        default=None,
        description="B2B SaaS monetization and business model breakdown.",
    )
    conflicts: List[ConflictGroup] = Field(
        default_factory=list,
        description="Conflicting evidence groups detected.",
    )
    final_report_sections: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured dictionary containing all 22 required B2B SaaS report sections.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered during pipeline execution.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of pipeline warnings and gaps.",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of missing fields if status is INCOMPLETE_INPUT.",
    )
    audit_trail: List[StateTransitionRecord] = Field(
        default_factory=list,
        description="Chronological state transition audit trail.",
    )
    provenance: List[SourceProvenance] = Field(
        default_factory=list,
        description="Verified source provenance records.",
    )
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Pipeline start timestamp in UTC ISO format.",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Pipeline completion timestamp in UTC ISO format.",
    )


# PipelineReport is an alias for backwards compatibility
PipelineReport = PipelineResult
