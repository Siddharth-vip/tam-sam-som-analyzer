from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.fetching.models import FetchedSource
from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.evidence import ConfidenceLevel


class ExtractionStatus(str, Enum):
    """Execution status of the evidence extraction process."""

    SUCCESS = "success"
    NO_METRICS_FOUND = "no_metrics_found"
    PARTIAL = "partial"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    """Methodology utilized to extract candidate evidence from source text."""

    DETERMINISTIC_PATTERN = "deterministic_pattern"
    LLM_GROUNDED = "llm_grounded"
    HYBRID = "hybrid"


class MarketMetricType(str, Enum):
    """Explicit taxonomy of recognized market research and TAM/SAM/SOM metric categories."""

    MARKET_SIZE = "market_size"
    MARKET_REVENUE = "market_revenue"
    CUSTOMER_COUNT = "customer_count"
    POPULATION = "population"
    STUDENT_COUNT = "student_count"
    ENROLLMENT = "enrollment"
    USERS = "users"
    HOUSEHOLDS = "households"
    ANNUAL_SPEND = "annual_spend"
    AVERAGE_PRICE = "average_price"
    SUBSCRIPTION_PRICE = "subscription_price"
    MARKET_SHARE = "market_share"
    GROWTH_RATE = "growth_rate"
    CAGR = "cagr"
    OTHER = "other"


class ExtractedEvidenceCandidate(BaseModel):
    """Intermediate candidate evidence metric extracted from a fetched source document.

    Note: This is an unverified candidate and is strictly separate from a verified EvidenceItem.
    """

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    candidate_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique candidate identifier.",
    )
    metric: str = Field(
        ...,
        description="Extracted market metric title or concept (e.g. 'college students', 'market size').",
    )
    metric_type: Optional[MarketMetricType] = Field(
        default=None,
        description="Classified market metric category from the supported taxonomy.",
    )
    value: Optional[float] = Field(
        default=None,
        description="Normalized scalar numerical value. Null if range/approximate or unquantified.",
    )
    raw_value_expression: Optional[str] = Field(
        default=None,
        description="Verbatim numeric text snippet from the source (e.g. '43 million', 'USD 2.5 billion').",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Extracted unit of measurement (e.g. 'students', 'USD', 'INR', '%').",
    )
    geography: Optional[str] = Field(
        default=None,
        description="Geographic scope explicitly mentioned in surrounding source context.",
    )
    year: Optional[int] = Field(
        default=None,
        description="Reference calendar year explicitly mentioned in surrounding source context.",
    )
    is_range_or_approximate: bool = Field(
        default=False,
        description="True if the number is an interval (e.g. '10-15 million') or approximate (e.g. 'more than 10 million').",
    )
    range_min: Optional[float] = Field(
        default=None,
        description="Lower bound if a range was extracted.",
    )
    range_max: Optional[float] = Field(
        default=None,
        description="Upper bound if a range was extracted.",
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Publication or publisher organization name.",
    )
    source_url: str = Field(
        ...,
        description="URL of the document from which this candidate was extracted.",
    )
    source_context: str = Field(
        ...,
        description="The verbatim sentence or paragraph snippet containing the factual claim.",
    )
    extraction_method: ExtractionMethod = Field(
        default=ExtractionMethod.DETERMINISTIC_PATTERN,
        description="Extraction method utilized.",
    )
    extraction_confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence assessment of extraction fidelity.",
    )
    extraction_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.EXTRACTED,
        description="Lifecycle stage. Strictly set to EXTRACTED.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Extraction qualifiers, caveats, or normalization notes.",
    )

    @field_validator("metric", "source_url", "source_context")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate string is non-empty."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v.strip()

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate reasonable 4-digit calendar year."""
        if v is not None and (v < 1900 or v > 2100):
            raise ValueError("Year must be a valid 4-digit year between 1900 and 2100.")
        return v

    @model_validator(mode="after")
    def enforce_extraction_lifecycle(self) -> "ExtractedEvidenceCandidate":
        """Epistemic Guard: Extracted candidate cannot claim verified stage."""
        if self.lifecycle_stage in (DiscoveryLifecycleStage.VERIFIED, "verified"):
            raise ValueError(
                "An extracted candidate cannot have lifecycle_stage='verified'. "
                "Candidate evidence must pass domain validation and triangulation before verification."
            )
        return self


class ExtractionRequest(BaseModel):
    """Request schema for extracting evidence candidates from fetched source content."""

    model_config = ConfigDict(extra="ignore")

    source: FetchedSource = Field(
        ...,
        description="The fetched document object containing sanitized content.",
    )
    target_metric: Optional[str] = Field(
        default=None,
        description="Optional metric filter to focus extraction on a specific subject.",
    )
    target_geography: Optional[str] = Field(
        default=None,
        description="Optional geography filter for context association.",
    )
    method: ExtractionMethod = Field(
        default=ExtractionMethod.DETERMINISTIC_PATTERN,
        description="Preferred extraction methodology.",
    )


class ExtractionResponse(BaseModel):
    """Response schema containing extracted evidence candidates."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    source_url: str = Field(
        ...,
        description="The URL of the processed source document.",
    )
    status: ExtractionStatus = Field(
        default=ExtractionStatus.SUCCESS,
        description="Overall extraction execution status.",
    )
    candidates: List[ExtractedEvidenceCandidate] = Field(
        default_factory=list,
        description="List of extracted candidate evidence items.",
    )
    total_candidates_found: int = Field(
        default=0,
        ge=0,
        description="Total count of candidate evidence items parsed.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.EXTRACTED,
        description="Lifecycle stage of the extraction output.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Status message or summary notes.",
    )
