from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceType(str, Enum):
    """Controlled vocabulary for research evidence source types."""

    GOVERNMENT = "government"
    OFFICIAL_STATISTICS = "official_statistics"
    REGULATORY = "regulatory"
    INDUSTRY_REPORT = "industry_report"
    COMPANY_REPORT = "company_report"
    ACADEMIC = "academic"
    REPUTABLE_RESEARCH = "reputable_research"
    NEWS = "news"
    SECONDARY_SOURCE = "secondary_source"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Categorical confidence level for evidence items."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    """Epistemic status of a market evidence item."""

    VERIFIED = "verified"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    """Pydantic model representing a single verifiable market research evidence record."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    metric: str = Field(
        ...,
        description="The specific market metric name (e.g. 'Number of college students in India').",
        examples=["Number of college students in India"],
    )
    value: Optional[float] = Field(
        default=None,
        description="Numerical value of the metric. Null if unknown.",
        examples=[43000000.0],
    )
    unit: Optional[str] = Field(
        default=None,
        description="The unit of measurement (e.g. 'students', 'USD', 'INR', '%'). Required if value is numerical.",
        examples=["students"],
    )
    geography: Optional[str] = Field(
        default=None,
        description="Target geographical scope (e.g. 'India', 'Chennai', 'Global').",
        examples=["India"],
    )
    year: Optional[int] = Field(
        default=None,
        description="Reference calendar year for the data point.",
        examples=[2025],
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Identifiable name of the authoring organization or publication.",
        examples=["Ministry of Education / AISHE"],
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Direct URL to verifiable source documentation.",
        examples=["https://example.gov.in/aishe-report"],
    )
    source_type: SourceType = Field(
        default=SourceType.UNKNOWN,
        description="Controlled classification of the source type.",
    )
    source_date: Optional[str] = Field(
        default=None,
        description="Publication date or retrieval date (e.g. '2025-01-15' or '2025').",
    )
    methodology: Optional[str] = Field(
        default=None,
        description="Data collection or estimation methodology.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.UNKNOWN,
        description="Categorical confidence assessment.",
    )
    evidence_status: EvidenceStatus = Field(
        default=EvidenceStatus.UNKNOWN,
        description="Core epistemic status (verified, inferred, assumed, unknown).",
    )
    used_for: Optional[str] = Field(
        default=None,
        description="Downstream market modeling purpose (e.g. 'TAM base population', 'SAM filtering').",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Contextual notes, caveats, definitions, or currency details.",
    )

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        """Validate metric title is non-empty."""
        if not isinstance(v, str):
            raise ValueError("Metric name must be a string.")
        cleaned = v.strip()
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Metric name must not be empty and must be at least 2 characters.")
        return cleaned

    @field_validator(
        "unit",
        "geography",
        "source_name",
        "source_url",
        "source_date",
        "methodology",
        "used_for",
        "notes",
        mode="before",
    )
    @classmethod
    def sanitize_string_fields(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and convert empty strings to None."""
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate reasonable 4-digit calendar year."""
        if v is not None and (v < 1900 or v > 2100):
            raise ValueError("Year must be a valid 4-digit year between 1900 and 2100.")
        return v

    @model_validator(mode="after")
    def validate_epistemic_integrity(self) -> "EvidenceItem":
        """Enforce strict domain rules for evidence validity and traceability."""
        # 1. Numerical value requires an explicit unit
        if self.value is not None and not self.unit:
            raise ValueError("A unit of measurement is required when a numerical value is provided.")

        # 2. Verified evidence must have an identifiable source and cannot have source_type 'assumption'
        if self.evidence_status == EvidenceStatus.VERIFIED or self.evidence_status == "verified":
            if not self.source_name:
                raise ValueError("Verified evidence must have an identifiable source_name.")
            if self.source_type == SourceType.ASSUMPTION or self.source_type == "assumption":
                raise ValueError("Evidence with status 'verified' cannot have source_type 'assumption'.")

        # 3. Unknown evidence must not contain a fabricated numerical value
        if self.evidence_status == EvidenceStatus.UNKNOWN or self.evidence_status == "unknown":
            if self.value is not None:
                raise ValueError("Evidence with status 'unknown' must not contain a numerical value.")

        # 4. Assumed evidence must not claim to be verified official statistics
        if self.evidence_status == EvidenceStatus.ASSUMED or self.evidence_status == "assumed":
            if self.source_type in (SourceType.GOVERNMENT, SourceType.OFFICIAL_STATISTICS, SourceType.REGULATORY):
                raise ValueError("Evidence with status 'assumed' cannot be attributed to official government or regulatory sources.")

        return self
