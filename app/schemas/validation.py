from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate, ExtractionMethod
from app.schemas.evidence import ConfidenceLevel


class EvidenceValidationStatus(str, Enum):
    """Execution status and structural integrity outcome of evidence candidate validation."""

    VALID = "valid"
    REJECTED = "rejected"
    INVALID = "invalid"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    DUPLICATE = "duplicate"
    INSUFFICIENT_CORROBORATION = "insufficient_corroboration"


class EvidenceConfidence(str, Enum):
    """Categorical confidence level after validation and multi-source triangulation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarketScopeType(str, Enum):
    """Categorical classification of market evidence scope and TAM/SAM/SOM boundaries."""

    PARENT_MARKET = "Parent market"
    RELEVANT_MARKET = "Relevant market"
    ADDRESSABLE_MARKET = "Addressable market"
    SERVICEABLE_MARKET = "Serviceable market"
    OBTAINABLE_MARKET = "Obtainable market"
    ADJACENT_MARKET = "Adjacent market"
    UNRELATED_MARKET = "Unrelated market"


class EvidenceRelevanceScore(BaseModel):
    """Multi-dimensional relevance and quality score assessing evidence suitability for TAM/SAM/SOM."""

    model_config = ConfigDict(extra="ignore")

    source_quality_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Source credibility & tier score (0-100).")
    industry_match_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Industry sector alignment score (0-100).")
    geography_match_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Geographical market alignment score (0-100).")
    customer_match_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Target customer segment alignment score (0-100).")
    product_match_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Product / service offering specificity score (0-100).")
    usefulness_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Direct TAM/SAM/SOM market-sizing usefulness score (0-100).")
    recency_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Temporal recency benchmark score (0-100).")
    claim_type_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Actual statistical/market sizing claim authenticity score (0-100).")
    overall_relevance_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Composite weighted relevance score (0-100).")
    market_scope: Optional[MarketScopeType] = Field(default=None, description="Classified market scope category.")
    market_scope_explanation: Optional[str] = Field(default=None, description="Explicit explanation of market scope.")
    is_accepted: bool = Field(default=True, description="Whether the evidence meets acceptance thresholds for market analysis.")
    rejection_reason: Optional[str] = Field(default=None, description="Explicit human-readable explanation if rejected.")
    rejection_category: Optional[str] = Field(default=None, description="Standardized rejection category code.")
    dimensional_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Detailed dimension-level diagnostic notes.")


class SourceProvenance(BaseModel):
    """Structured representation of source metadata and quality assessment."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    source_url: str = Field(..., description="Canonical source URL.")
    source_name: Optional[str] = Field(default=None, description="Publisher or organization name.")
    domain: Optional[str] = Field(default=None, description="Extracted domain hostname.")
    source_context: Optional[str] = Field(default=None, description="Verbatim textual snippet.")
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality score (0.0 - 1.0).")
    source_quality_reasons: List[str] = Field(default_factory=list, description="Audit trail for quality scoring.")
    source_quality_tier: Optional[SourceQualityTier] = Field(default=None, description="Hierarchy tier classification.")
    market_scope: Optional[MarketScopeType] = Field(default=None, description="Classified market scope category.")
    market_scope_explanation: Optional[str] = Field(default=None, description="Explicit explanation of market scope.")


class ConflictSource(BaseModel):
    """Details of an independent candidate that materially contradicts a data point."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    candidate_id: str = Field(..., description="Candidate ID of the conflicting evidence.")
    value: Optional[float] = Field(default=None, description="Reported conflicting numerical value.")
    raw_value_expression: Optional[str] = Field(default=None, description="Original conflicting text expression.")
    unit: Optional[str] = Field(default=None, description="Unit of measurement.")
    source_name: Optional[str] = Field(default=None, description="Conflicting source publisher.")
    source_url: str = Field(..., description="Conflicting source URL.")
    source_context: str = Field(..., description="Sentence context exhibiting the discrepancy.")
    source_quality_score: float = Field(default=0.0, description="Quality score of the conflicting source.")
    source_quality_tier: Optional[SourceQualityTier] = Field(default=None, description="Hierarchy tier classification.")


class EvidenceValidationResult(BaseModel):
    """Complete validation, deduplication, and triangulation outcome for an evidence candidate."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    candidate_id: str = Field(..., description="Identifier of the validated candidate.")
    metric: str = Field(..., description="Validated market metric title.")
    metric_type: Optional[str] = Field(default=None, description="Classified market metric category.")
    value: Optional[float] = Field(default=None, description="Validated numerical value.")
    raw_value_expression: Optional[str] = Field(default=None, description="Verbatim raw text expression.")
    unit: Optional[str] = Field(default=None, description="Validated measurement unit.")
    geography: Optional[str] = Field(default=None, description="Target geography.")
    year: Optional[int] = Field(default=None, description="Validated reference year.")
    is_range_or_approximate: bool = Field(default=False, description="Flag for interval/approximate bounds.")
    range_min: Optional[float] = Field(default=None, description="Lower bound if range.")
    range_max: Optional[float] = Field(default=None, description="Upper bound if range.")
    source_name: Optional[str] = Field(default=None, description="Publisher organization name.")
    source_url: str = Field(..., description="Direct verifiable URL.")
    source_context: str = Field(..., description="Verbatim sentence context supporting the metric.")
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Deterministic source quality score (0.0 - 1.0).")
    source_quality_reasons: List[str] = Field(default_factory=list, description="Transparent quality rationale.")
    source_quality_tier: Optional[SourceQualityTier] = Field(default=None, description="Hierarchy authority tier.")
    extraction_method: Optional[str] = Field(default=None, description="Extraction methodology utilized.")
    extraction_confidence: Optional[str] = Field(default=None, description="Extraction-stage confidence level.")
    validation_status: EvidenceValidationStatus = Field(
        default=EvidenceValidationStatus.VALID,
        description="Validation outcome status (valid, invalid, partial, conflict, duplicate, insufficient_corroboration).",
    )
    confidence: EvidenceConfidence = Field(
        default=EvidenceConfidence.LOW,
        description="Overall confidence level (low, medium, high, very_high).",
    )
    validation_reasons: List[str] = Field(
        default_factory=list,
        description="Audit list of validation checks passed, warnings, or rejection reasons.",
    )
    duplicate_group_id: Optional[str] = Field(
        default=None,
        description="Identifier of duplicate group if merged/corroborated.",
    )
    corroborating_source_count: int = Field(
        default=1,
        ge=0,
        description="Number of distinct independent source domains corroborating this claim.",
    )
    conflicting_source_count: int = Field(
        default=0,
        ge=0,
        description="Number of distinct independent source domains contradicting this claim.",
    )
    corroborating_sources: List[SourceProvenance] = Field(
        default_factory=list,
        description="Full provenance list of independent corroborating sources.",
    )
    conflicting_sources: List[ConflictSource] = Field(
        default_factory=list,
        description="Full provenance list of conflicting sources with contradicting values.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.VALIDATED,
        description="Lifecycle stage (VALIDATED or VERIFIED). Strictly cannot be VERIFIED without independent corroboration.",
    )
    is_valid: bool = Field(
        default=True,
        description="Boolean summary whether the candidate is structurally valid and usable.",
    )
    is_syndicated_copy: bool = Field(
        default=False,
        description="Flag indicating if this item was identified as syndicated/republished copy rather than independent primary research.",
    )
    evidence_quality_rating: Optional[str] = Field(
        default=None,
        description="Evidence quality rating category (HIGH, MEDIUM, LOW, INSUFFICIENT).",
    )
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Multi-dimensional market relevance score (0-100).",
    )
    relevance_breakdown: Optional[EvidenceRelevanceScore] = Field(
        default=None,
        description="Detailed multi-dimensional relevance and suitability assessment.",
    )
    market_scope: Optional[MarketScopeType] = Field(
        default=None,
        description="Classified market scope category (e.g. Parent market, Addressable market, Serviceable market, Obtainable market).",
    )
    market_scope_explanation: Optional[str] = Field(
        default=None,
        description="Detailed explanation of market scope categorization.",
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Audit reason explaining why the evidence was rejected or flagged as unsuitable.",
    )
    rejection_category: Optional[str] = Field(
        default=None,
        description="Machine-readable category code for evidence rejection.",
    )
    year_consistency_note: Optional[str] = Field(
        default=None,
        description="Audit note regarding temporal consistency.",
    )
    geography_consistency_note: Optional[str] = Field(
        default=None,
        description="Audit note regarding geographic alignment.",
    )
    notes: Optional[str] = Field(default=None, description="Contextual notes or caveats.")


    @model_validator(mode="after")
    def enforce_verification_invariants(self) -> "EvidenceValidationResult":
        """Epistemic Guard: Candidate cannot claim VERIFIED lifecycle stage unless corroboration is met."""
        if self.lifecycle_stage in (DiscoveryLifecycleStage.VERIFIED, "verified"):
            if self.corroborating_source_count < 2:
                raise ValueError(
                    "Evidence item cannot have lifecycle_stage='verified' with fewer than 2 independent corroborating sources."
                )
            if self.validation_status in (EvidenceValidationStatus.INVALID, EvidenceValidationStatus.REJECTED) or not self.is_valid:
                raise ValueError("An invalid or rejected evidence candidate cannot have lifecycle_stage='verified'.")
        return self


class DeduplicationGroup(BaseModel):
    """Group of evidence candidates referring to the exact same metric, unit, geography, year, and normalized value."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    group_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique deduplication group ID.")
    canonical_metric: str = Field(..., description="Canonical metric name for the group.")
    canonical_value: Optional[float] = Field(default=None, description="Canonical normalized numerical value.")
    canonical_unit: Optional[str] = Field(default=None, description="Canonical unit.")
    canonical_geography: Optional[str] = Field(default=None, description="Canonical geography.")
    canonical_year: Optional[int] = Field(default=None, description="Canonical reference year.")
    candidates: List[ExtractedEvidenceCandidate] = Field(default_factory=list, description="Candidates belonging to this group.")
    source_urls: List[str] = Field(default_factory=list, description="All source URLs in this group.")
    distinct_domains: List[str] = Field(default_factory=list, description="Unique domain hostnames in this group.")
    distinct_source_count: int = Field(default=0, ge=0, description="Count of unique domain hostnames.")


class ConflictGroup(BaseModel):
    """Group of candidates targeting the same metric, geography, and year, but presenting conflicting numerical values."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique conflict group ID.")
    metric: str = Field(..., description="Target metric subject.")
    geography: Optional[str] = Field(default=None, description="Target geography.")
    year: Optional[int] = Field(default=None, description="Target calendar year.")
    unit: Optional[str] = Field(default=None, description="Target measurement unit.")
    conflicting_values: List[float] = Field(default_factory=list, description="The distinct conflicting values observed.")
    candidates: List[ExtractedEvidenceCandidate] = Field(default_factory=list, description="The conflicting candidate items.")
    reason: str = Field(
        default="Conflicting values reported by independent sources for the same metric, geography, and year.",
        description="Diagnostic explanation of the factual discrepancy.",
    )


class TriangulationRequest(BaseModel):
    """Request payload containing extracted candidates to triangulate."""

    model_config = ConfigDict(extra="ignore")

    candidates: List[ExtractedEvidenceCandidate] = Field(
        default_factory=list,
        description="List of extracted candidate evidence items to validate, deduplicate, and triangulate.",
    )
    candidate: Optional[ExtractedEvidenceCandidate] = Field(
        default=None,
        description="Single candidate item if provided in singular format.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_candidates_payload(cls, data: Any) -> Any:
        """Coerce singular candidate, list payloads, or root dictionaries into candidates array."""
        if isinstance(data, dict):
            if "candidates" in data and isinstance(data["candidates"], list):
                return data
            if "candidate" in data and data["candidate"]:
                c = data["candidate"]
                if isinstance(c, list):
                    return {"candidates": c}
                return {"candidates": [c]}
            if "candidates" not in data and "candidate" not in data:
                if "metric" in data and "source_url" in data:
                    return {"candidates": [data]}
        elif isinstance(data, list):
            return {"candidates": data}
        return data


class TriangulationResult(BaseModel):
    """Comprehensive triangulation response detailing verified, validated, duplicate, and conflicting evidence."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    total_candidates_processed: int = Field(default=0, ge=0, description="Total number of candidates processed.")
    validated_items: List[EvidenceValidationResult] = Field(
        default_factory=list,
        description="All validly processed evidence items (including single-source validated items).",
    )
    verified_items: List[EvidenceValidationResult] = Field(
        default_factory=list,
        description="Multi-source verified evidence items meeting the 2+ independent domain corroboration threshold.",
    )
    duplicate_groups: List[DeduplicationGroup] = Field(
        default_factory=list,
        description="Clusters of deduplicated identical evidence claims.",
    )
    conflict_groups: List[ConflictGroup] = Field(
        default_factory=list,
        description="Detected factual contradictions preserved with full provenance for transparency.",
    )
    rejected_items: List[EvidenceValidationResult] = Field(
        default_factory=list,
        description="Auditable list of evidence candidates rejected during structural or multi-dimensional relevance validation.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.VALIDATED,
        description="Batch outcome lifecycle stage.",
    )
    message: Optional[str] = Field(default=None, description="Summary description of triangulation outcomes.")
