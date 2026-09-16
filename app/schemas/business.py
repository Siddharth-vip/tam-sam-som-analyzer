from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthcareCustomerType(str, Enum):
    """Paying customer organization types in the Healthcare SaaS ecosystem."""

    HOSPITALS = "Hospitals"
    CLINICS = "Clinics"
    DIAGNOSTIC_LABORATORIES = "Diagnostic Laboratories"
    PHARMACIES = "Pharmacies"
    DENTAL_CLINICS = "Dental Clinics"
    MEDICAL_PRACTICES = "Medical Practices"
    HEALTHCARE_NETWORKS = "Healthcare Networks / Hospital Chains"
    TELEMEDICINE_PROVIDERS = "Telemedicine Providers"
    NURSING_HOMES = "Nursing Homes & Long-Term Care"
    INDIVIDUAL_PRACTITIONERS = "Individual Healthcare Professionals"
    PATIENTS_CONSUMERS = "Patients / Consumers (B2C)"
    PAYERS_INSURANCE = "Payers & Health Insurance Organizations"
    OTHER_HEALTHCARE_ORG = "Other Healthcare Organizations"


class HealthcareSaaSCategory(str, Enum):
    """Recognized Healthcare SaaS classification taxonomy."""

    HOSPITAL_MANAGEMENT = "Hospital Management SaaS"
    CLINIC_MANAGEMENT = "Clinic Management SaaS"
    EHR_EMR = "EHR/EMR SaaS"
    TELEMEDICINE = "Telemedicine SaaS"
    MEDICAL_BILLING_RCM = "Medical Billing & Revenue Cycle Management (RCM) SaaS"
    HEALTHCARE_CRM = "Healthcare CRM SaaS"
    PATIENT_ENGAGEMENT = "Patient Engagement & Portal SaaS"
    APPOINTMENT_MANAGEMENT = "Appointment & Scheduling SaaS"
    PHARMACY_MANAGEMENT = "Pharmacy Management SaaS"
    LABORATORY_MANAGEMENT = "Laboratory & Diagnostic Management SaaS"
    DIAGNOSTIC_MANAGEMENT = "Diagnostic Imaging & PACS SaaS"
    PRACTICE_MANAGEMENT = "Medical Practice Management SaaS"
    HEALTHCARE_ANALYTICS = "Healthcare Analytics & BI SaaS"
    HEALTHCARE_AI = "Healthcare AI & Clinical Decision Support SaaS"
    REMOTE_PATIENT_MONITORING = "Remote Patient Monitoring (RPM) SaaS"
    HEALTHCARE_WORKFORCE = "Healthcare Workforce & Staffing SaaS"
    HEALTHCARE_REVENUE_CYCLE = "Healthcare Revenue Cycle SaaS"
    OTHER_HEALTHCARE_SAAS = "Other Healthcare SaaS"


class HealthcarePricingBasis(str, Enum):
    """Pricing bases common in Healthcare SaaS."""

    MONTHLY_SUBSCRIPTION = "monthly_subscription"
    ANNUAL_SUBSCRIPTION = "annual_subscription"
    PER_USER = "per_user"
    PER_PROVIDER = "per_provider"
    PER_FACILITY = "per_facility"
    PER_BED = "per_bed"
    PER_TRANSACTION = "per_transaction"
    USAGE_BASED = "usage_based"
    TIERED = "tiered_subscription"
    CUSTOM = "custom"


class IncompleteInputResponse(BaseModel):
    """Structured response returned when required Healthcare SaaS inputs are missing."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(
        default="INCOMPLETE_INPUT",
        description="Status flag indicating missing required information.",
    )
    message: str = Field(
        default="Additional information is required to perform the Healthcare SaaS market analysis.",
        description="Human-readable description of why analysis cannot proceed.",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of required field names that must be provided.",
    )
    suggested_inputs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional suggestions or valid examples for the missing fields.",
    )


class BusinessIdeaRequest(BaseModel):
    """Request schema for business idea analysis."""

    business_idea: str = Field(
        ...,
        description="The raw unstructured Healthcare SaaS business idea description.",
        examples=["An AI-powered clinic management and EHR SaaS for dental clinics in India"],
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
    """Structured Healthcare SaaS business concept analysis schema."""

    model_config = ConfigDict(extra="ignore")

    # Core concept & identity
    business_name: Optional[str] = Field(default=None, description="Name of the Healthcare SaaS product or company.")
    business_idea: str = Field(..., description="The exact user-provided business idea string.")
    product: Optional[str] = Field(default=None, description="Core product or platform offering.")
    product_description: Optional[str] = Field(default=None, description="Detailed description of the SaaS product.")
    
    # Healthcare Classification
    sector: str = Field(default="Healthcare SaaS", description="Overall sector fixed to Healthcare SaaS.")
    healthcare_saas_category: Optional[str] = Field(
        default=None,
        description="Classified Healthcare SaaS category (e.g., 'Clinic Management SaaS', 'EHR/EMR SaaS').",
    )
    industry: Optional[str] = Field(default="Healthcare SaaS", description="Industry classification.")
    market_category: Optional[str] = Field(default=None, description="Specific Healthcare SaaS market sub-segment.")
    market_definition: Optional[str] = Field(default=None, description="Dynamic market scope definition.")

    # Target Market & Customer
    target_country: Optional[str] = Field(default=None, description="Target country (e.g. India, United States).")
    target_region: Optional[str] = Field(default=None, description="Target state, province, or region if applicable.")
    target_city: Optional[str] = Field(default=None, description="Target city if localized.")
    geography: Optional[str] = Field(default=None, description="Target geography string representation.")
    
    customer_type: Optional[str] = Field(
        default=None,
        description="The paying entity type (e.g., 'Clinics', 'Hospitals', 'Diagnostic Laboratories').",
    )
    target_customer: Optional[str] = Field(default=None, description="Primary paying customer organization persona.")
    target_customer_segment: Optional[str] = Field(default=None, description="Granular target customer tier/segment.")
    organization_size: Optional[str] = Field(default=None, description="Target customer organization size (e.g. SMB, 50-200 beds, Enterprise).")
    number_of_facilities: Optional[int] = Field(default=None, description="Expected facilities per customer if multi-location.")
    number_of_employees: Optional[int] = Field(default=None, description="Expected seats/users per facility.")

    # Product & SaaS Model
    business_model: Optional[str] = Field(default="B2B SaaS", description="Business model (B2B, B2C, B2B2C).")
    pricing_basis: Optional[str] = Field(
        default=None,
        description="Healthcare SaaS pricing basis ('per_user', 'per_provider', 'per_facility', 'monthly_subscription', 'annual_subscription', 'tiered_subscription').",
    )
    pricing_model: Optional[str] = Field(
        default=None,
        description="Monetization model (e.g. 'per_provider', 'monthly_subscription', 'per_facility').",
    )
    revenue_model: Optional[str] = Field(default=None, description="Revenue model description.")
    monthly_price: Optional[float] = Field(default=None, description="Monthly subscription price in local currency.")
    annual_price: Optional[float] = Field(default=None, description="Annual subscription price in local currency.")
    per_user_price: Optional[float] = Field(default=None, description="Per-user/seat price.")
    per_provider_price: Optional[float] = Field(default=None, description="Per-doctor/clinician/provider price.")
    per_facility_price: Optional[float] = Field(default=None, description="Per-hospital/clinic/facility price.")
    currency: Optional[str] = Field(default="INR", description="Currency for pricing (e.g. INR, USD, EUR).")
    annual_revenue_per_customer: Optional[float] = Field(
        default=None,
        description="Computed or estimated annual contract value / ARPU per paying customer.",
    )

    # Healthcare-Specific Attributes
    healthcare_domain: Optional[str] = Field(default=None, description="Domain within healthcare (e.g. Radiology, Dental, Oncology).")
    clinical_use: Optional[bool] = Field(default=None, description="Whether software directly impacts clinical workflows vs administrative.")
    provider_type: Optional[str] = Field(default=None, description="Types of providers using the system.")
    patient_involvement: Optional[bool] = Field(default=None, description="Whether patients directly interact with the software.")
    healthcare_workflow: Optional[str] = Field(default=None, description="Specific workflow automated or enhanced.")
    emr_ehr_integration_required: Optional[bool] = Field(default=None, description="Whether integration with existing EMR/EHR is required.")
    interoperability_standards: Optional[str] = Field(default=None, description="Interoperability standards (e.g. HL7 FHIR, ABDM M1/M2/M3, DICOM).")
    regulatory_market: Optional[str] = Field(default=None, description="Applicable regulatory frameworks (e.g. HIPAA, NABH, ABDM, GDPR, FDA 510k).")
    regulatory_constraints: Optional[str] = Field(default=None, description="Identified regulatory or compliance requirements.")

    # Problems & Value Proposition
    primary_problem: Optional[str] = Field(default=None, description="Primary problem solved in healthcare workflow.")
    customer_problem: Optional[str] = Field(default=None, description="Customer pain point.")
    primary_use_case: Optional[str] = Field(default=None, description="Primary clinical or administrative use case.")
    key_features: List[str] = Field(default_factory=list, description="Key functional capabilities of the SaaS.")
    unique_value_proposition: Optional[str] = Field(default=None, description="Unique value proposition.")
    value_proposition: Optional[str] = Field(default=None, description="Value proposition summary.")

    # Meta
    target_year: Optional[int] = Field(default=None, description="Target analysis year.")


class MarketStrategy(BaseModel):
    """Market sizing and evidence evaluation strategy for Healthcare SaaS."""

    model_config = ConfigDict(extra="ignore")

    business_sector: str = Field(default="Healthcare SaaS", description="Healthcare SaaS sector.")
    industry: str = Field(default="Healthcare Information Technology", description="Healthcare IT industry.")
    product_or_service: Optional[str] = Field(default=None, description="Healthcare SaaS product.")
    business_model: Optional[str] = Field(default="B2B SaaS", description="Business model.")
    customer_type: Optional[str] = Field(default=None, description="Healthcare customer category.")
    target_segment: Optional[str] = Field(default=None, description="Specific healthcare customer segment.")
    market_definition: Optional[str] = Field(default=None, description="Precise definition of the Healthcare SaaS market.")
    market_category: Optional[str] = Field(default=None, description="Healthcare SaaS category.")
    tam_method: str = Field(default="bottom_up_customer_arpu", description="Recommended TAM method.")
    sam_method: str = Field(default="serviceable_population_arpu", description="Recommended SAM method.")
    som_method: str = Field(default="customer_acquisition_capacity", description="Recommended SOM method.")
    tam_evidence_requirements: List[str] = Field(default_factory=list, description="Descriptions of valid TAM evidence metrics.")
    sam_evidence_requirements: List[str] = Field(default_factory=list, description="Descriptions of valid SAM evidence metrics.")
    som_evidence_requirements: List[str] = Field(default_factory=list, description="Descriptions of valid SOM evidence metrics.")
    relevant_market_terms: List[str] = Field(default_factory=list, description="Healthcare SaaS keywords and terms.")
    unrelated_market_terms: List[str] = Field(default_factory=list, description="Non-healthcare terms to filter out.")
    segment_narrowing_dimensions: List[str] = Field(default_factory=list, description="Valid narrowing dimensions.")


class CompetitorInfo(BaseModel):
    """Structured competitor insight grounded in verified source evidence."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Name of the competing Healthcare SaaS company or product.")
    product_service: Optional[str] = Field(default=None, description="Product or service offering description.")
    target_market: Optional[str] = Field(default=None, description="Target healthcare customer segment or geography.")
    pricing: Optional[str] = Field(default=None, description="Reported pricing or monetization model if available.")
    differentiators: Optional[str] = Field(default=None, description="Key differentiators or market positioning.")
    source_url: Optional[str] = Field(default=None, description="Provenance URL where competitor evidence was identified.")
    source_name: Optional[str] = Field(default=None, description="Publisher or source name.")
    confidence: Optional[str] = Field(default="medium", description="Confidence level of competitor observation.")
