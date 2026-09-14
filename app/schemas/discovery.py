from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.evidence import SourceType


class DiscoveryLifecycleStage(str, Enum):
    """Explicit stages in the evidence discovery and verification pipeline."""

    DISCOVERED = "discovered"  # Metadata found via search/indexing, unverified
    FETCHED = "fetched"        # Raw web document / content retrieved
    EXTRACTED = "extracted"    # Candidate metric data point parsed
    VALIDATED = "validated"    # Structural and domain validation rules passed
    VERIFIED = "verified"      # Provenance and source authentication confirmed


class DiscoveryStatus(str, Enum):
    """Execution status of a discovery operation."""

    PENDING = "pending"
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    FAILED = "failed"


class SourceCategory(str, Enum):
    """Categorized provenance taxonomy for market evidence sources."""

    OFFICIAL_GOVERNMENT = "official_government"
    NATIONAL_STATISTICS = "national_statistics"
    ACADEMIC_INSTITUTION = "academic_institution"
    INDUSTRY_ANALYST = "industry_analyst"
    COMPANY_FILING = "company_filing"
    TRADE_ASSOCIATION = "trade_association"
    FINANCIAL_MARKET_RESEARCH = "financial_market_research"
    REPUTABLE_NEWS = "reputable_news"
    OTHER = "other"


class SourceQualityTier(str, Enum):
    """Hierarchical 5-tier classification of evidence source authority and credibility."""

    TIER_1_GOVERNMENT_OFFICIAL = "Tier 1: Government & Official Statistics"
    TIER_2_ACADEMIC_TRADE = "Tier 2: Academic & Industry Trade Associations"
    TIER_3_ANALYST_PRESS = "Tier 3: Market Analysts & Financial Press"
    TIER_4_GENERAL_UNVERIFIED = "Tier 4: General Web & Secondary Articles"
    TIER_5_UNUSABLE = "Tier 5: Unusable (Social/Forums/Unsourced)"



class ResearchQuery(BaseModel):
    """Structured research query specifying parameters for evidence discovery."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    metric_required: str = Field(
        ...,
        description="The specific market metric or data point to discover.",
        examples=["Number of college students in India"],
    )
    geography: Optional[str] = Field(
        default=None,
        description="Target geographic scope for the evidence search.",
        examples=["India"],
    )
    year: Optional[int] = Field(
        default=None,
        description="Target or reference calendar year.",
        examples=[2025],
    )
    industry_topic: Optional[str] = Field(
        default=None,
        description="Industry sector or domain topic.",
        examples=["Higher Education / EdTech"],
    )
    target_population: Optional[str] = Field(
        default=None,
        description="Specific target audience or demographic segment.",
        examples=["College and university students"],
    )
    preferred_source_types: List[SourceType] = Field(
        default_factory=list,
        description="Preferred source types for prioritization (e.g. government, official_statistics).",
    )
    preferred_categories: List[SourceCategory] = Field(
        default_factory=list,
        description="Preferred institutional categories.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of search results to return (1-20).",
    )

    @field_validator("metric_required")
    @classmethod
    def validate_metric_required(cls, v: str) -> str:
        """Validate metric title is non-empty."""
        if not isinstance(v, str):
            raise ValueError("metric_required must be a string.")
        cleaned = v.strip()
        if not cleaned or len(cleaned) < 2:
            raise ValueError("metric_required must not be empty and must be at least 2 characters.")
        return cleaned

    @field_validator("geography", "industry_topic", "target_population", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Optional[str]) -> Optional[str]:
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


class DiscoveredSource(BaseModel):
    """Schema representing an individual search result discovered from external indexing."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    title: str = Field(
        ...,
        description="The title of the discovered document or web page.",
    )
    url: str = Field(
        ...,
        description="The absolute URL to the discovered source document.",
    )
    snippet: Optional[str] = Field(
        default=None,
        description="Text snippet or abstract returned in the search result.",
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Identifiable publication or publisher name.",
    )
    domain: Optional[str] = Field(
        default=None,
        description="Extracted domain hostname (e.g. 'education.gov.in').",
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Publication or index date string if available.",
    )
    category: SourceCategory = Field(
        default=SourceCategory.OTHER,
        description="Institutional source category.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.DISCOVERED,
        description="Current lifecycle stage of the source item. Starts as DISCOVERED.",
    )
    discovery_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp when the source was discovered.",
    )
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relevance confidence score (0.0 to 1.0).",
    )
    is_mock: Optional[bool] = Field(
        default=False,
        description="Flag indicating if source originated from deterministic mock discovery provider.",
    )
    mock_content: Optional[str] = Field(
        default=None,
        description="Optional fixture text content for deterministic mock discovery testing.",
    )
    relevance_status: Optional[str] = Field(
        default="accepted",
        description="Relevance determination ('accepted' or 'rejected').",
    )
    relevance_reason: Optional[str] = Field(
        default=None,
        description="Audit reason for source relevance filtering decision.",
    )
    query_used: Optional[str] = Field(
        default=None,
        description="The search query string that produced this result.",
    )
    source_quality_tier: Optional[SourceQualityTier] = Field(
        default=None,
        description="Hierarchical authority tier (Tier 1 Government to Tier 4 General Web).",
    )
    year_consistency_note: Optional[str] = Field(
        default=None,
        description="Audit note regarding temporal applicability or baseline year.",
    )
    geography_consistency_note: Optional[str] = Field(
        default=None,
        description="Audit note regarding geographic alignment or conversion.",
    )


    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is non-empty."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Title must be a non-empty string.")
        return v.strip()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is a well-formed HTTP/HTTPS address."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("URL must be a non-empty string.")
        cleaned = v.strip()
        parsed = urlparse(cleaned)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL format: '{cleaned}'. Must be an absolute http or https URL.")
        return cleaned

    @model_validator(mode="after")
    def populate_domain_and_check_stage(self) -> "DiscoveredSource":
        """Auto-populate domain if not supplied and enforce discovery stage rules."""
        if not self.domain and self.url:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc.lower()

        # Epistemic guard: Discovered source cannot be marked VERIFIED during discovery stage
        if self.lifecycle_stage in (DiscoveryLifecycleStage.VERIFIED, "verified"):
            raise ValueError(
                "A newly discovered source cannot have lifecycle_stage='verified'. "
                "Discovered URLs must undergo fetching, extraction, and validation before verification."
            )

        return self


class DiscoveryResponse(BaseModel):
    """Response schema containing discovered search results for a research query."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    query: ResearchQuery = Field(
        ...,
        description="The original structured research query.",
    )
    query_string: str = Field(
        ...,
        description="The canonical search query constructed from parameters.",
    )
    status: DiscoveryStatus = Field(
        default=DiscoveryStatus.SUCCESS,
        description="Overall discovery query execution status.",
    )
    total_results_found: int = Field(
        default=0,
        ge=0,
        description="Number of discovered source results.",
    )
    sources: List[DiscoveredSource] = Field(
        default_factory=list,
        description="List of discovered source records.",
    )
    lifecycle_stage: DiscoveryLifecycleStage = Field(
        default=DiscoveryLifecycleStage.DISCOVERED,
        description="Current lifecycle stage of the response batch.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Informational or diagnostic status message.",
    )
