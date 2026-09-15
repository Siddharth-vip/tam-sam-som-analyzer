from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator



class FetchStatus(str, Enum):
    """Controlled lifecycle status for content retrieval attempts."""

    SUCCESS = "success"
    FETCH_FAILED = "fetch_failed"
    UNSUPPORTED_CONTENT = "unsupported_content"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    INVALID_SOURCE = "invalid_source"
    OVERSIZED = "oversized"
    SNIPPET_FALLBACK = "snippet_fallback"


class FetchRequest(BaseModel):
    """Request schema for retrieving content from a discovered source URL."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(
        ...,
        description="The target HTTP/HTTPS URL to fetch.",
        examples=["https://example.gov.in/higher-education-report.html"],
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional title of the discovered document.",
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Optional source organization or publisher name.",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is non-empty and well-formed."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("URL must be a non-empty string.")
        cleaned = v.strip()
        parsed = urlparse(cleaned)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL format: '{cleaned}'. Must be an absolute http or https URL.")
        return cleaned


class FetchedSource(BaseModel):
    """Schema representing retrieved and sanitized document content."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    original_url: str = Field(
        ...,
        description="The original requested URL.",
    )
    final_url: Optional[str] = Field(
        default=None,
        description="The final URL after resolving any HTTP redirects.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Extracted or declared document title.",
    )
    content: Optional[str] = Field(
        default=None,
        description="Clean, sanitized textual content extracted from the document body.",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="MIME content type returned in HTTP headers (e.g. text/html, text/plain).",
    )
    http_status: Optional[int] = Field(
        default=None,
        description="HTTP response status code.",
    )
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of content retrieval.",
    )
    content_length_bytes: int = Field(
        default=0,
        ge=0,
        description="Size of retrieved content in bytes.",
    )
    fetch_status: FetchStatus = Field(
        ...,
        description="Outcome of the fetch attempt.",
    )
    lifecycle_stage: str = Field(
        default="fetched",
        description="Lifecycle stage. Strictly set to FETCHED.",
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Identifiable source publisher or institution name.",
    )
    domain: Optional[str] = Field(
        default=None,
        description="Normalized domain hostname.",
    )
    is_redirected: bool = Field(
        default=False,
        description="True if the request followed HTTP redirects to a new location.",
    )
    is_cross_domain_redirect: bool = Field(
        default=False,
        description="True if the request was redirected across different domain hostnames.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Diagnostic error message if retrieval failed.",
    )

    @model_validator(mode="after")
    def populate_domain_and_enforce_lifecycle(self) -> "FetchedSource":
        """Auto-populate domain, detect redirects, and enforce FETCHED stage boundary."""
        if self.final_url and self.original_url:
            orig_netloc = urlparse(self.original_url).netloc.lower()
            final_netloc = urlparse(self.final_url).netloc.lower()
            if orig_netloc and final_netloc and orig_netloc != final_netloc:
                self.is_cross_domain_redirect = True
                self.is_redirected = True
                self.domain = final_netloc
            elif self.final_url != self.original_url:
                self.is_redirected = True
                self.domain = final_netloc or orig_netloc
            else:
                self.domain = orig_netloc
        elif not self.domain and self.original_url:
            parsed = urlparse(self.original_url)
            self.domain = parsed.netloc.lower()

        # Epistemic guard: FetchedSource cannot be marked verified
        if str(self.lifecycle_stage).lower() == "verified":
            raise ValueError(
                "A fetched source cannot have lifecycle_stage='verified'. "
                "Fetched content must undergo metric extraction and domain validation before verification."
            )

        return self
