from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessIdeaRequest(BaseModel):
    """Request schema for business idea analysis."""

    business_idea: str = Field(
        ...,
        description="The raw unstructured business idea description.",
        examples=["An affordable online programming platform for college students in India"],
    )

    @field_validator("business_idea")
    @classmethod
    def validate_business_idea(cls, v: str) -> str:
        """Validate and sanitize the business idea input."""
        if not isinstance(v, str):
            raise ValueError("Business idea must be a string.")
        
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Business idea must not be empty or whitespace-only.")
        
        if len(cleaned) < 3:
            raise ValueError("Business idea must be at least 3 characters long.")
            
        return cleaned


class BusinessAnalysis(BaseModel):
    """Structured business idea analysis response schema."""

    model_config = ConfigDict(extra="ignore")

    business_idea: str = Field(
        ...,
        description="The exact user-provided business idea string.",
    )
    industry: Optional[str] = Field(
        default=None,
        description="The primary industry, sector, or market category directly identifiable from the product (e.g. 'Food Delivery / Online Food Ordering', 'Accounting Software / SaaS'). Null if unknown.",
    )
    product: Optional[str] = Field(
        default=None,
        description="The core product, application, platform, or service concept (e.g. 'Food delivery app', 'SaaS accounting platform'). Avoid generic words like 'app' when specifics are present. Null if unspecified.",
    )
    target_customer: Optional[str] = Field(
        default=None,
        description="The primary intended target audience or customer persona explicitly stated or directly implied (e.g. 'Urban families', 'Small businesses'). Null if unspecified.",
    )
    geography: Optional[str] = Field(
        default=None,
        description="Target geographical market (city, country, region) ONLY when explicitly mentioned in the input (e.g. 'Chennai', 'India'). Never guess. Null if unspecified.",
    )
    business_model: Optional[str] = Field(
        default=None,
        description="The business model (e.g. 'B2B', 'B2C', 'SaaS', 'Marketplace') ONLY when explicitly stated or unambiguous. Null if unspecified.",
    )
    pricing_model: Optional[str] = Field(
        default=None,
        description="The pricing or revenue model (e.g. 'Monthly subscription', 'Freemium') ONLY when explicitly stated. Never assume. Null if unspecified.",
    )
    customer_problem: Optional[str] = Field(
        default=None,
        description="The core customer pain point or problem addressed ONLY when stated or strongly implied by wording. Null if unspecified.",
    )
    value_proposition: Optional[str] = Field(
        default=None,
        description="The key benefit, solution, or unique value offered ONLY when stated or clearly supported by the idea wording. Null if unspecified.",
    )


class CompetitorInfo(BaseModel):
    """Structured competitor insight grounded in verified source evidence."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Name of the competing company or product.")
    product_service: Optional[str] = Field(default=None, description="Product or service offering description.")
    target_market: Optional[str] = Field(default=None, description="Target customer segment or geography.")
    pricing: Optional[str] = Field(default=None, description="Reported pricing or monetization model if available.")
    differentiators: Optional[str] = Field(default=None, description="Key differentiators or market positioning.")
    source_url: Optional[str] = Field(default=None, description="Provenance URL where competitor evidence was identified.")
    source_name: Optional[str] = Field(default=None, description="Publisher or source name.")
    confidence: Optional[str] = Field(default="medium", description="Confidence level of competitor observation.")
