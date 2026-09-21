from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClassificationStatus(str, Enum):
    """Scope determination status for business classification."""

    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    AMBIGUOUS = "AMBIGUOUS"


class BusinessModelType(str, Enum):
    """Business model classification."""

    B2B_SAAS = "B2B SaaS"
    B2B_NON_SAAS = "B2B Non-SaaS"
    B2C_SAAS = "B2C SaaS"
    B2C_CONSUMER = "Consumer Application"
    MARKETPLACE = "Marketplace"
    HARDWARE = "Hardware"
    PROFESSIONAL_SERVICES = "Professional Services"
    OTHER = "Other"


class ClassificationProvenance(BaseModel):
    """Epistemic provenance record for AI classification."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    data_type: str = Field(default="AI_CLASSIFIED", description="Epistemic data type (AI_CLASSIFIED).")
    source: str = Field(default="Ollama qwen3:8b", description="Classification source engine.")
    model: str = Field(default="qwen3:8b", description="Underlying model identifier.")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Overall classification confidence score.")


class B2BSaaSClassification(BaseModel):
    """Structured B2B SaaS Business Classification Result."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    sector: str = Field(
        default="B2B SaaS",
        description="Sector designation ('B2B SaaS' or 'NON_B2B_SAAS').",
    )
    classification_status: ClassificationStatus = Field(
        default=ClassificationStatus.IN_SCOPE,
        description="Whether the business idea is within the B2B SaaS scope.",
    )
    sector_confidence: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Confidence that the business is in the B2B SaaS sector (0.0 to 1.0).",
    )
    category: Optional[str] = Field(
        default=None,
        description="Canonical B2B SaaS Category name (e.g. 'CRM & Sales', 'HR & Workforce Management').",
    )
    category_id: Optional[str] = Field(
        default=None,
        description="Canonical category slug ID (e.g. 'crm_sales', 'hr_workforce').",
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="Granular B2B SaaS subcategory (e.g. 'Recruitment / ATS', 'Sales CRM').",
    )
    category_confidence: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Confidence in category classification (0.0 to 1.0).",
    )
    business_model: str = Field(
        default="B2B SaaS",
        description="Business and delivery model (e.g. 'B2B SaaS', 'Consumer Application').",
    )
    customer_type: str = Field(
        default="B2B",
        description="Primary customer orientation ('B2B', 'B2C', 'B2B2C').",
    )
    target_segment: Optional[str] = Field(
        default=None,
        description="Target customer organization tier (e.g. 'SMB', 'Mid-Market', 'Enterprise', 'Startups').",
    )
    target_customer: Optional[str] = Field(
        default=None,
        description="Target customer persona or organization profile.",
    )
    primary_buyer: Optional[str] = Field(
        default=None,
        description="Primary purchasing authority/department (e.g. 'VP of Sales', 'HR Department').",
    )
    use_cases: List[str] = Field(
        default_factory=list,
        description="Key enterprise workflow use cases automated or addressed.",
    )
    reasoning: str = Field(
        default="",
        description="Detailed justification for the sector and category classification.",
    )
    missing_information: Optional[List[str]] = Field(
        default=None,
        description="List of underspecified parameters if classification is AMBIGUOUS or INCOMPLETE.",
    )
    provenance: ClassificationProvenance = Field(
        default_factory=ClassificationProvenance,
        description="Epistemic provenance tracking for the classification.",
    )
