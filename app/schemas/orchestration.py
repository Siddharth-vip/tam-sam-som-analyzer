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
    SAMResult,
    SOMResult,
    TAMResult,
)
from app.schemas.discovery import DiscoveredSource, ResearchQuery
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    ConflictGroup,
    DeduplicationGroup,
    EvidenceConfidence,
    EvidenceValidationResult,
    SourceProvenance,
    TriangulationResult,
)


class OrchestrationStage(str, Enum):
    """Explicit lifecycle stages in the end-to-end market analysis pipeline."""

    ANALYZING_BUSINESS = "analyzing_business"
    DISCOVERING_EVIDENCE = "discovering_evidence"
    FETCHING_SOURCES = "fetching_sources"
    EXTRACTING_EVIDENCE = "extracting_evidence"
    VALIDATING_EVIDENCE = "validating_evidence"
    TRIANGULATING_EVIDENCE = "triangulating_evidence"
    CALCULATING_MARKET = "calculating_market"
    COMPLETED = "completed"
    FAILED = "failed"


# Backward-compatible enum alias
PipelineStage = OrchestrationStage


class OrchestrationStageStatus(str, Enum):
    """Execution status for an individual orchestration stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Backward-compatible enum alias
PipelineStageStatus = OrchestrationStageStatus


class OrchestrationProgress(BaseModel):
    """Real-time diagnostic progress record for an individual orchestration stage."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    stage: OrchestrationStage = Field(..., description="The pipeline stage.")
    status: OrchestrationStageStatus = Field(default=OrchestrationStageStatus.PENDING, description="Current stage status.")
    started_at: Optional[str] = Field(default=None, description="UTC ISO timestamp when stage started.")
    completed_at: Optional[str] = Field(default=None, description="UTC ISO timestamp when stage completed.")
    duration_ms: Optional[float] = Field(default=None, description="Execution duration in milliseconds.")
    message: Optional[str] = Field(default=None, description="Diagnostic stage message.")
    error: Optional[str] = Field(default=None, description="Error message if stage failed.")


# Backward-compatible alias
PipelineProgress = OrchestrationProgress


class OrchestrationError(BaseModel):
    """Structured error record capturing a failure at a specific orchestration stage."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    stage: OrchestrationStage = Field(..., description="Stage where the error occurred.")
    error_message: str = Field(..., description="Detailed description of the error.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp when error was recorded.",
    )
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional diagnostic error metadata.")


# Backward-compatible alias
PipelineError = OrchestrationError


class EvidenceSummary(BaseModel):
    """Summary of evidence counts across discovery, extraction, validation, and triangulation."""

    model_config = ConfigDict(extra="ignore")

    total_discovered: int = Field(default=0, ge=0, description="Total candidate sources discovered.")
    total_fetched: int = Field(default=0, ge=0, description="Total documents successfully fetched.")
    total_extracted_candidates: int = Field(default=0, ge=0, description="Total numerical evidence candidates extracted.")
    total_validated: int = Field(default=0, ge=0, description="Total candidates that passed structural validation.")
    total_verified: int = Field(default=0, ge=0, description="Total multi-source verified evidence items.")
    total_conflicts: int = Field(default=0, ge=0, description="Total conflicting evidence groups detected.")


class OrchestrationRequest(BaseModel):
    """Request payload to trigger end-to-end market analysis orchestration."""

    model_config = ConfigDict(extra="ignore")

    business_idea: str = Field(
        ...,
        description="The raw business idea or product description to analyze.",
        examples=["An affordable online programming platform for college students in India"],
    )
    geography: Optional[str] = Field(
        default=None,
        description="Optional explicit target geography override.",
    )
    year: Optional[int] = Field(
        default=None,
        description="Optional reference calendar year.",
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum sources to discover per research query (1-20).",
    )
    explicit_assumptions: List[CalculationAssumption] = Field(
        default_factory=list,
        description="Optional user-provided assumptions (e.g. pricing, target market share).",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_assumptions_alias(cls, data: Any) -> Any:
        """Coerce assumptions key into explicit_assumptions if provided."""
        if isinstance(data, dict):
            if "assumptions" in data and not data.get("explicit_assumptions"):
                data["explicit_assumptions"] = data["assumptions"]
        return data

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

    @field_validator("geography", mode="before")
    @classmethod
    def sanitize_geography(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize Swagger placeholder strings or empty values to None."""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned or cleaned.lower() in ("string", "none", "null", "undefined"):
                return None
            return cleaned
        return v

    @field_validator("year", mode="before")
    @classmethod
    def sanitize_year(cls, v: Optional[int]) -> Optional[int]:
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


# Backward-compatible alias
MarketAnalysisRequest = OrchestrationRequest


class OrchestrationResult(BaseModel):
    """Comprehensive, auditable market sizing and research report produced by the Orchestrator."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    analysis_id: str = Field(
        default_factory=lambda: f"mkt_{uuid.uuid4().hex[:12]}",
        description="Unique market analysis execution ID.",
    )
    status: str = Field(
        default="completed",
        description="Overall execution status (completed, partial, insufficient_evidence, conflict, failed).",
    )
    current_stage: OrchestrationStage = Field(
        default=OrchestrationStage.COMPLETED,
        description="Final or current stage in the orchestration workflow.",
    )
    business_idea: str = Field(..., description="Original raw business idea submitted.")
    business_analysis: Optional[BusinessAnalysis] = Field(
        default=None,
        description="Structured business concept attributes extracted.",
    )
    research_queries: List[ResearchQuery] = Field(
        default_factory=list,
        description="Structured research requirement queries generated.",
    )
    discovered_sources: List[DiscoveredSource] = Field(
        default_factory=list,
        description="Discovered candidate source records.",
    )
    fetched_sources: List[FetchedSource] = Field(
        default_factory=list,
        description="Fetched document sources.",
    )
    extracted_candidates: List[ExtractedEvidenceCandidate] = Field(
        default_factory=list,
        description="Candidate numerical evidence items parsed.",
    )
    validation_results: List[EvidenceValidationResult] = Field(
        default_factory=list,
        description="Validation outcome records.",
    )
    deduplication_groups: List[DeduplicationGroup] = Field(
        default_factory=list,
        description="Clusters of deduplicated evidence claims.",
    )
    conflict_groups: List[ConflictGroup] = Field(
        default_factory=list,
        description="Detected contradictory evidence preserved for transparency.",
    )
    triangulation_result: Optional[TriangulationResult] = Field(
        default=None,
        description="Multi-source validation, deduplication, and triangulation outcome.",
    )
    calculation_report: Optional[CalculationReport] = Field(
        default=None,
        description="Deterministic TAM/SAM/SOM calculation report.",
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
    confidence: str = Field(
        default=EvidenceConfidence.LOW,
        description="Overall market sizing confidence level.",
    )
    evidence_quality_rating: Optional[str] = Field(
        default=None,
        description="Overall deterministic evidence quality rating (HIGH, MEDIUM, LOW, INSUFFICIENT).",
    )
    research_provider: Optional[str] = Field(
        default="mock",
        description="Provider mode utilized (mock fixture vs live search).",
    )
    competitors: List[CompetitorInfo] = Field(
        default_factory=list,
        description="Extracted competitor intelligence with provenance.",
    )

    stages: List[OrchestrationProgress] = Field(
        default_factory=list,
        description="Ordered progress records across all orchestration stages.",
    )
    stage_progress: List[OrchestrationProgress] = Field(
        default_factory=list,
        description="Alias for stages for backward compatibility.",
    )
    errors: List[OrchestrationError] = Field(
        default_factory=list,
        description="Errors encountered during execution.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Diagnostic warnings, caveats, and data gaps.",
    )
    assumptions: List[CalculationAssumption] = Field(
        default_factory=list,
        description="Explicit user-provided calculation assumptions.",
    )
    evidence_summary: EvidenceSummary = Field(
        default_factory=EvidenceSummary,
        description="Evidence volume breakdown.",
    )
    provenance: List[SourceProvenance] = Field(
        default_factory=list,
        description="Traceable source provenance records.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Execution start timestamp in UTC ISO format.",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Execution completion timestamp in UTC ISO format.",
    )
    total_duration_ms: Optional[float] = Field(
        default=None,
        description="Total end-to-end execution duration in milliseconds.",
    )


# Backward-compatible alias
MarketAnalysisResponse = OrchestrationResult
