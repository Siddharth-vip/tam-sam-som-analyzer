from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.fetching.models import FetchedSource
from app.schemas.business import BusinessAnalysis, CompetitorInfo
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
    BUSINESS_ANALYSIS = "business_analysis"
    QUERY_GENERATION = "query_generation"
    DISCOVERY = "discovery"
    FETCHING = "fetching"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    TRIANGULATION = "triangulation"
    CALCULATION = "calculation"
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
    CONFLICT = "conflict"


class PipelineRequest(BaseModel):
    """Input request model for end-to-end TAM/SAM/SOM market analysis pipeline."""

    model_config = ConfigDict(extra="ignore")

    business_idea: str = Field(
        ...,
        description="The business concept or product idea to analyze.",
        examples=["An affordable online programming platform for college students in India"],
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum external sources to discover and fetch (bounded between 1 and 50).",
    )
    enable_calculation: bool = Field(
        default=True,
        description="Whether to perform deterministic TAM/SAM/SOM calculations after triangulation.",
    )
    explicit_assumptions: List[CalculationAssumption] = Field(
        default_factory=list,
        description="Optional user-provided assumptions (e.g. pricing, target market share).",
    )
    preferred_geography: Optional[str] = Field(
        default=None,
        description="Optional explicit target geography override.",
    )
    preferred_year: Optional[int] = Field(
        default=None,
        description="Optional reference calendar year override.",
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

    @field_validator("preferred_geography", mode="before")
    @classmethod
    def sanitize_preferred_geography(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize Swagger placeholder strings or empty values to None."""
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
        """Sanitize 0 or invalid year placeholders to None."""
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
    def coerce_assumptions_alias(cls, data: Any) -> Any:
        """Coerce assumptions key into explicit_assumptions if provided."""
        if isinstance(data, dict):
            if "assumptions" in data and not data.get("explicit_assumptions"):
                data["explicit_assumptions"] = data["assumptions"]
        return data

    @field_validator("explicit_assumptions", mode="before")
    @classmethod
    def sanitize_explicit_assumptions(cls, v: Any) -> List[Any]:
        """Filter out Swagger dummy placeholders from explicit assumptions."""
        if not v or not isinstance(v, list):
            return []
        sanitized: List[Any] = []
        for item in v:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip().lower()
                unit = str(item.get("unit", "")).strip().lower()
                if name in ("string", "", "none", "null", "undefined") or unit in ("string", ""):
                    continue
                sanitized.append(item)
            elif isinstance(item, CalculationAssumption):
                name = item.name.strip().lower()
                unit = item.unit.strip().lower()
                if name in ("string", "", "none", "null", "undefined") or unit in ("string", ""):
                    continue
                sanitized.append(item)
            else:
                sanitized.append(item)
        return sanitized


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


class PipelineResult(BaseModel):
    """Final comprehensive auditable report returned by the Market Analysis Pipeline."""

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
        description="Structured business concept extraction.",
    )
    research_queries: List[ResearchQuery] = Field(
        default_factory=list,
        description="Generated research requirement queries.",
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
    calculation_trace: Optional[CalculationTrace] = Field(
        default=None,
        description="Structured deterministic calculation trace for auditing.",
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
    conflicts: List[ConflictGroup] = Field(
        default_factory=list,
        description="Conflicting evidence groups detected.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered during pipeline execution.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of pipeline warnings and gaps.",
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
