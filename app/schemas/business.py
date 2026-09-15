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
    sector: Optional[str] = Field(
        default=None,
        description="The broad macro sector (e.g. 'Food / Retail', 'Energy / CleanTech', 'Healthcare', 'Software / Technology', 'Financial Services', 'Manufacturing', 'Education'). Null if unknown.",
    )
    revenue_model: Optional[str] = Field(
        default=None,
        description="The monetization mechanism (e.g. 'Recurring Subscription', 'Usage-based / Metered', 'Transaction Fee / Take Rate', 'One-time License', 'Unit Sales'). Null if unspecified.",
    )
    customer_type: Optional[str] = Field(
        default=None,
        description="Customer tier/type classification (e.g. 'B2B', 'B2C', 'B2B2C', 'Enterprise', 'SMB', 'Consumers', 'Students'). Null if unspecified.",
    )
    target_customer_segment: Optional[str] = Field(
        default=None,
        description="Detailed target customer segment or persona (e.g. 'Working professionals in Tier-2 Indian cities'). Null if unspecified.",
    )
    target_year: Optional[int] = Field(
        default=None,
        description="Target analysis year if mentioned in business idea or context.",
    )
    distribution_model: Optional[str] = Field(
        default=None,
        description="Channel / delivery method (e.g. 'Direct-to-consumer / Mobile App', 'B2B Direct Sales', 'Online Marketplace', 'Partner Channel'). Null if unspecified.",
    )
    market_category: Optional[str] = Field(
        default=None,
        description="Standardized market category (e.g. 'Quick Commerce / Online Grocery', 'Residential Rooftop Solar', 'Enterprise Accounting Software'). Null if unspecified.",
    )
    market_definition: Optional[str] = Field(
        default=None,
        description="Precise, dynamic definition of the market this business participates in (e.g. 'Online grocery and quick-commerce market relevant to urban consumers in India'). Null if unspecified.",
    )
    customer_problem: Optional[str] = Field(
        default=None,
        description="The core customer pain point or problem addressed ONLY when stated or strongly implied by wording. Null if unspecified.",
    )
    value_proposition: Optional[str] = Field(
        default=None,
        description="The key benefit, solution, or unique value offered ONLY when stated or clearly supported by the idea wording. Null if unspecified.",
    )


class MarketStrategy(BaseModel):
    """Dynamic, domain-agnostic market sizing and evidence evaluation strategy."""

    model_config = ConfigDict(extra="ignore")

    business_sector: Optional[str] = Field(default=None, description="Broad economic sector.")
    industry: Optional[str] = Field(default=None, description="Industry sector.")
    product_or_service: Optional[str] = Field(default=None, description="Core product or service.")
    business_model: Optional[str] = Field(default=None, description="Business model (B2B, B2C, Marketplace, SaaS, etc.).")
    customer_type: Optional[str] = Field(default=None, description="Customer classification.")
    target_segment: Optional[str] = Field(default=None, description="Specific target customer segment.")
    market_definition: Optional[str] = Field(default=None, description="Concise definition of the market being sized.")
    market_category: Optional[str] = Field(default=None, description="Market category taxonomy.")
    tam_method: str = Field(default="direct_market_size", description="Recommended TAM method (direct_market_size, customer_spend, transaction_volume, unit_revenue, installed_base).")
    sam_method: str = Field(default="segment_narrowing", description="Recommended SAM method (direct_segment, tam_times_segment_pct, serviceable_customers_spend, serviceable_transactions).")
    som_method: str = Field(default="capacity_or_obtainable", description="Recommended SOM method (obtainable_share, sales_capacity, customer_acquisition, operational_capacity).")
    tam_evidence_requirements: list[str] = Field(default_factory=list, description="Descriptions of valid TAM evidence metrics.")
    sam_evidence_requirements: list[str] = Field(default_factory=list, description="Descriptions of valid SAM evidence metrics.")
    som_evidence_requirements: list[str] = Field(default_factory=list, description="Descriptions of valid SOM evidence metrics.")
    relevant_market_terms: list[str] = Field(default_factory=list, description="Key concepts and synonyms characterizing the target market.")
    unrelated_market_terms: list[str] = Field(default_factory=list, description="Concepts and adjacent sectors that are distinct/unrelated to this market.")
    segment_narrowing_dimensions: list[str] = Field(default_factory=list, description="Valid narrowing dimensions (geography, customer segment, service tier, channel, etc.).")


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
