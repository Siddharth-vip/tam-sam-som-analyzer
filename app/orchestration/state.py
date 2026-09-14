from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.fetching.models import FetchedSource
from app.schemas.business import BusinessAnalysis
from app.schemas.calculation import CalculationReport
from app.schemas.discovery import DiscoveredSource
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.pipeline import PipelineState, StateTransitionRecord
from app.schemas.validation import (
    ConflictGroup,
    EvidenceValidationResult,
    TriangulationResult,
)


class PipelineExecutionContext(BaseModel):
    """Execution context state object tracking data and audit trails across pipeline phases."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    pipeline_id: str = Field(default_factory=lambda: f"pipe_{uuid.uuid4().hex[:12]}", description="Unique pipeline execution ID.")
    business_idea: str = Field(..., description="The original raw business idea string.")
    current_state: PipelineState = Field(default=PipelineState.RECEIVED, description="Current pipeline state.")
    previous_state: Optional[PipelineState] = Field(default=None, description="Previous pipeline state.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation timestamp.",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Last update timestamp.",
    )
    progress_message: Optional[str] = Field(default=None, description="Current progress summary.")
    errors: List[str] = Field(default_factory=list, description="List of recorded error messages.")
    audit_trail: List[StateTransitionRecord] = Field(default_factory=list, description="Ordered state transition history.")

    # Pipeline Artifacts
    business_analysis: Optional[BusinessAnalysis] = Field(default=None, description="Structured business concept extraction.")
    discovered_sources: List[DiscoveredSource] = Field(default_factory=list, description="Sources found during discovery.")
    fetched_sources: List[FetchedSource] = Field(default_factory=list, description="Documents fetched and sanitized.")
    extracted_candidates: List[ExtractedEvidenceCandidate] = Field(default_factory=list, description="Candidate evidence parsed.")
    validated_evidence: List[EvidenceValidationResult] = Field(default_factory=list, description="Validated evidence records.")
    conflicts: List[ConflictGroup] = Field(default_factory=list, description="Detected factual conflicts.")
    triangulation_result: Optional[TriangulationResult] = Field(default=None, description="Multi-source triangulation outcome.")
    calculation_report: Optional[CalculationReport] = Field(default=None, description="Deterministic market sizing report.")

    def transition_to(
        self,
        new_state: PipelineState,
        message: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Deterministically transition the pipeline to a new state and record the audit log."""
        record = StateTransitionRecord(
            from_state=self.current_state,
            to_state=new_state,
            message=message,
            error=error,
            duration_ms=duration_ms,
        )
        self.audit_trail.append(record)
        self.previous_state = self.current_state
        self.current_state = new_state
        self.progress_message = message
        self.updated_at = datetime.now(timezone.utc).isoformat()
        if error:
            self.errors.append(error)
