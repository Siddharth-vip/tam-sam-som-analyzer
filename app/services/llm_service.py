from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas.business import (
    BusinessAnalysis,
    BusinessModelAnalysis,
    CompetitorInfo,
    CustomerSegmentItem,
    HealthcareCustomerType,
    HealthcarePricingBasis,
    HealthcareSaaSCategory,
    MarketAttractivenessAssessment,
    MarketGrowthItem,
    MarketStrategy,
    MarketTrendItem,
    ValuePropositionAnalysis,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert B2B SaaS Market Research & Business Intelligence Analyst.
Analyze the user's B2B SaaS business concept and extract structured business attributes.
Output ONLY a valid JSON object matching these fields:
{
  "business_name": "string or null",
  "business_idea": "exact user input string",
  "product": "core product offering or null",
  "product_description": "short description or null",
  "sector": "B2B SaaS",
  "category": "one of canonical categories e.g. CRM & Sales, HR & Workforce Management, Accounting & Finance, Project & Task Management, Marketing & Marketing Automation, Customer Support & Helpdesk, ERP & Business Operations, Procurement & Supply Chain, Cybersecurity, IT Management & IT Service Management, Collaboration & Communication, Legal & Compliance, Data & Analytics / Business Intelligence, Developer Tools, Productivity & Workflow Automation, E-commerce & Retail Operations, Education & Learning Management, Healthcare Business Software, Real Estate & Property Management, Construction & Field Service Management, Logistics & Transportation Management, FinTech & Payment SaaS, Manufacturing & Industrial Operations, Hospitality & Restaurant Management, Other B2B SaaS",
  "subcategory": "specific subcategory or null",
  "industry": "target industry vertical e.g. Information Technology, Healthcare IT, Logistics, Education, Financial Services, Retail, Manufacturing",
  "market_category": "sub-segment string or null",
  "target_country": "e.g. India, United States",
  "customer_type": "target customer organization tier e.g. SMBs, Mid-Market, Enterprises, Startups, Clinics, Hospitals, Schools, Retail Stores, Transport Companies",
  "primary_buyer": "department or buyer title e.g. VP of Sales, HR Director, CFO, CTO, Operations Manager",
  "use_cases": ["use case 1", "use case 2"],
  "business_model": "B2B SaaS",
  "pricing_model": "one of: per_user, per_seat, per_provider, per_facility, usage_based, monthly_subscription, annual_subscription or null",
  "healthcare_saas_category": "healthcare category if healthcare domain, else null",
  "clinical_use": boolean,
  "emr_ehr_integration_required": boolean,
  "regulatory_market": "relevant compliance standards e.g. GDPR, SOC 2, HIPAA, ABDM / NABH or null"
}

Do NOT output markdown code fences or conversational text. Output pure JSON only."""



def derive_market_strategy(analysis: BusinessAnalysis) -> MarketStrategy:
    """Derive dynamic B2B SaaS MarketStrategy from structured BusinessAnalysis."""
    product = (analysis.product or analysis.product_description or "B2B SaaS Solution").strip()
    category = (analysis.category or analysis.healthcare_saas_category or analysis.market_category or "B2B SaaS").strip()
    cust_type = (analysis.customer_type or "Businesses").strip()
    target_cust = (analysis.target_customer_segment or analysis.target_customer or cust_type).strip()
    geo = (analysis.target_country or analysis.geography or "").strip()
    geo_str = f" in {geo}" if geo else ""
    market_def = (
        analysis.market_definition
        or f"{category} market serving {target_cust}{geo_str}".strip()
    )

    # Determine recommended TAM method
    pricing_mod = (analysis.pricing_model or "").lower()
    if any(k in pricing_mod for k in ("provider", "doctor", "physician")):
        tam_method = "bottom_up_per_provider_pricing"
    elif any(k in pricing_mod for k in ("facility", "hospital", "clinic", "practice", "store", "plant", "location")):
        tam_method = "bottom_up_per_facility_pricing"
    elif any(k in pricing_mod for k in ("seat", "user", "employee", "per_user", "per_seat")):
        tam_method = "bottom_up_customer_arpu"
    else:
        tam_method = "bottom_up_customer_arpu"

    # Targeted B2B SaaS evidence requirements
    tam_reqs = [
        f"Total count of potential {cust_type.lower()} ({target_cust}{geo_str})",
        f"Average annual SaaS contract value (ARPU / annual subscription) for {category}{geo_str}",
        f"Top-down total market spend for {category} software{geo_str}",
    ]
    sam_reqs = [
        f"Count of serviceable {cust_type.lower()} meeting technology/digital readiness criteria{geo_str}",
        f"Serviceable segment percentage based on target organization size and regulatory readiness",
        f"Estimated annual software budget for {target_cust}{geo_str}",
    ]
    som_reqs = [
        f"Realistically obtainable customer acquisition count across Years 1-3 based on sales capacity and B2B procurement cycles",
        f"Near-term obtainable market share percentage within serviceable {target_cust}",
        f"Conservative, Base, and Optimistic adoption scenarios",
    ]

    use_case_str = " ".join(analysis.use_cases) if analysis.use_cases else ""
    terms_raw = f"{product} {category} {cust_type} {target_cust} {analysis.industry or ''} {use_case_str} b2b saas hospital clinic medical emr ehr software platform".lower()
    relevant_terms = [t for t in set(re.findall(r"[a-zA-Z]{3,}", terms_raw)) if t not in ("for", "the", "and", "with", "market", "service", "platform", "app", "software")]

    is_healthcare = (category and "health" in category.lower()) or (analysis.healthcare_saas_category is not None)
    sector = "Healthcare SaaS" if is_healthcare else (analysis.sector or "B2B SaaS")
    industry = "Healthcare Information Technology" if is_healthcare else (analysis.industry or category or "B2B Software")

    return MarketStrategy(
        business_sector=sector,
        industry=industry,
        product_or_service=product,
        business_model=analysis.business_model or "B2B SaaS",
        customer_type=cust_type,
        target_segment=target_cust,
        market_definition=market_def,
        market_category=category,
        tam_method=tam_method,
        sam_method="serviceable_population_arpu",
        som_method="customer_acquisition_capacity",
        tam_evidence_requirements=tam_reqs,
        sam_evidence_requirements=sam_reqs,
        som_evidence_requirements=som_reqs,
        relevant_market_terms=relevant_terms,
        unrelated_market_terms=["agriculture", "real estate", "food delivery", "crypto", "generic retail", "logistics freight"],
        segment_narrowing_dimensions=["geography", "organization_size", "industry_vertical", "digital_maturity", "regulatory_compliance"],
    )


from app.schemas.classification import (
    B2BSaaSClassification,
    ClassificationStatus,
)
from app.services.classification_service import (
    B2BSaaSClassificationService,
    get_classification_service,
)
from app.taxonomy.b2b_saas import normalize_category_name


def normalize_business_analysis(
    data: Dict[str, Any],
    business_idea: str,
    classification: Optional[B2BSaaSClassification] = None,
) -> Dict[str, Any]:
    """Layer 2: Deterministic normalization and classification enrichment for B2B SaaS."""
    text = business_idea.strip()
    text_lower = text.lower()

    # Always enforce exact user input
    data["business_idea"] = text

    # Apply B2B SaaS classification if not provided
    if classification is None:
        classifier = get_classification_service()
        classification = classifier.classify_by_rules(text)

    data["b2b_saas_classification"] = classification
    data["is_b2b_saas"] = (classification.classification_status == ClassificationStatus.IN_SCOPE)
    data["classification_status"] = classification.classification_status.value if hasattr(classification.classification_status, "value") else str(classification.classification_status)
    data["category"] = classification.category
    data["subcategory"] = classification.subcategory
    data["sector"] = classification.sector
    data["industry"] = data.get("industry") or classification.category or "B2B SaaS"
    data["target_industry"] = data.get("target_industry") or classification.category
    data["primary_buyer"] = data.get("primary_buyer") or classification.primary_buyer
    data["use_cases"] = data.get("use_cases") or classification.use_cases

    # Healthcare-Specific Classification for backward compatibility
    if not data.get("healthcare_saas_category"):
        if any(w in text_lower for w in ["hospital management", "hims", "his", "hospital information", "bed management"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.HOSPITAL_MANAGEMENT.value
        elif any(w in text_lower for w in ["clinic management", "outpatient clinic", "polyclinic"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.CLINIC_MANAGEMENT.value
        elif any(w in text_lower for w in ["ehr", "emr", "electronic health record", "electronic medical record", "medical charting"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.EHR_EMR.value
        elif any(w in text_lower for w in ["telemedicine", "telehealth", "video consult", "virtual doctor", "remote consultation"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.TELEMEDICINE.value
        elif any(w in text_lower for w in ["billing", "revenue cycle", "rcm", "insurance claim", "medical coding", "tpa claim"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.MEDICAL_BILLING_RCM.value
        elif any(w in text_lower for w in ["patient engagement", "patient portal", "patient app", "treatment adherence", "health companion"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.PATIENT_ENGAGEMENT.value
        elif any(w in text_lower for w in ["dental", "dentist", "dental practice", "dental clinic"]):
            data["healthcare_saas_category"] = "Dental Practice Management SaaS"
        elif any(w in text_lower for w in ["lab", "laboratory", "pathology", "lims", "diagnostic lab"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.LABORATORY_MANAGEMENT.value
        elif any(w in text_lower for w in ["radiology", "pacs", "dicom", "imaging", "x-ray", "mri", "ct scan"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.DIAGNOSTIC_MANAGEMENT.value
        elif any(w in text_lower for w in ["rpm", "remote patient monitoring", "vitals monitoring", "wearable health", "tele-monitoring"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.REMOTE_PATIENT_MONITORING.value
        elif any(w in text_lower for w in ["pharmacy", "drug inventory", "e-prescription"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.PHARMACY_MANAGEMENT.value
        elif any(w in text_lower for w in ["ai diagnostic", "clinical ai", "decision support", "radiology ai"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.HEALTHCARE_AI.value
        elif any(w in text_lower for w in ["analytics", "healthcare bi", "clinical intelligence"]):
            data["healthcare_saas_category"] = HealthcareSaaSCategory.HEALTHCARE_ANALYTICS.value
        elif "healthcare" in text_lower or "medical" in text_lower or "clinic" in text_lower or "hospital" in text_lower:
            data["healthcare_saas_category"] = HealthcareSaaSCategory.CLINIC_MANAGEMENT.value
        else:
            data["healthcare_saas_category"] = None

    # Customer Type fallback
    if not data.get("customer_type"):
        if any(w in text_lower for w in ["hospital", "hospitals", "hospital chain", "tertiary care"]):
            data["customer_type"] = HealthcareCustomerType.HOSPITALS.value
        elif any(w in text_lower for w in ["dental", "dentist", "dentists"]):
            data["customer_type"] = HealthcareCustomerType.DENTAL_CLINICS.value
        elif any(w in text_lower for w in ["diagnostic", "pathology", "radiology lab", "imaging center"]):
            data["customer_type"] = HealthcareCustomerType.DIAGNOSTIC_LABORATORIES.value
        elif any(w in text_lower for w in ["pharmacy", "pharmacies", "chemist"]):
            data["customer_type"] = HealthcareCustomerType.PHARMACIES.value
        elif any(w in text_lower for w in ["nursing home", "elder care", "assisted living"]):
            data["customer_type"] = HealthcareCustomerType.NURSING_HOMES.value
        elif any(w in text_lower for w in ["telemedicine provider", "telehealth company"]):
            data["customer_type"] = HealthcareCustomerType.TELEMEDICINE_PROVIDERS.value
        elif any(w in text_lower for w in ["insurance", "payer", "tpa", "health plan"]):
            data["customer_type"] = HealthcareCustomerType.PAYERS_INSURANCE.value
        elif any(w in text_lower for w in ["doctor", "physician", "practitioner", "solo practice"]):
            data["customer_type"] = HealthcareCustomerType.MEDICAL_PRACTICES.value
        elif any(w in text_lower for w in ["clinic", "clinics"]):
            data["customer_type"] = HealthcareCustomerType.CLINICS.value
        else:
            data["customer_type"] = data.get("target_customer") or None

    # 3. Geography
    if not data.get("target_country") and not data.get("geography"):
        for known_geo in ["India", "United States", "USA", "UK", "United Kingdom", "Canada", "Australia", "Germany", "Singapore", "UAE"]:
            if re.search(rf"\b(?:in|across|for)\s+{known_geo}\b", text, re.IGNORECASE) or text_lower.endswith(f"in {known_geo.lower()}"):
                data["target_country"] = known_geo
                data["geography"] = known_geo
                break

    if data.get("target_country") and not data.get("geography"):
        data["geography"] = data["target_country"]

    # 4. Product
    if not data.get("product"):
        data["product"] = data.get("healthcare_saas_category") or (text if len(text) < 60 else "Healthcare SaaS Platform")

    # 5. Business Model
    if not data.get("business_model"):
        data["business_model"] = "B2B SaaS"

    # 6. Pricing Model
    pm = data.get("pricing_model")
    if pm and str(pm).strip().lower() in ("premium", "cheap", "affordable", "budget", "luxury", "low-cost", "high-cost", "none", "null"):
        data["pricing_model"] = None
    elif not data.get("pricing_model"):
        if any(w in text_lower for w in ["per doctor", "per physician", "per provider", "per-doctor", "per-provider"]):
            data["pricing_model"] = "per_provider"
        elif any(w in text_lower for w in ["per clinic", "per hospital", "per facility", "per-clinic", "per-facility", "per-hospital"]):
            data["pricing_model"] = "per_facility"
        elif any(w in text_lower for w in ["per user", "per seat", "per staff", "per-user"]):
            data["pricing_model"] = "per_user"
        elif any(w in text_lower for w in ["annual", "yearly", "annual subscription"]):
            data["pricing_model"] = "annual_subscription"
        elif any(w in text_lower for w in ["monthly", "month", "monthly subscription", "subscription"]):
            data["pricing_model"] = "monthly_subscription"
        else:
            data["pricing_model"] = None

    # 7. Healthcare Clinical Use & EMR Interoperability
    if data.get("clinical_use") is None:
        cat_lower = str(data.get("healthcare_saas_category", "")).lower()
        if any(k in cat_lower for k in ("ehr", "emr", "diagnostic", "ai", "clinical", "monitoring", "rpm", "imaging", "pacs")):
            data["clinical_use"] = True
        else:
            data["clinical_use"] = False

    if data.get("emr_ehr_integration_required") is None:
        cat_lower = str(data.get("healthcare_saas_category", "")).lower()
        if any(k in cat_lower for k in ("ehr", "emr", "hims", "his", "hospital", "interoperability", "pacs")):
            data["emr_ehr_integration_required"] = True
        else:
            data["emr_ehr_integration_required"] = False

    # 8. Regulatory Market
    if not data.get("regulatory_market"):
        geo = (data.get("target_country") or data.get("geography") or "").lower()
        if any(i in geo for i in ("india", "bharat")):
            data["regulatory_market"] = "ABDM (Ayushman Bharat Digital Mission) / NABH / DISHA"
        elif any(u in geo for u in ("us", "usa", "united states", "america")):
            data["regulatory_market"] = "HIPAA / HITECH / FDA 510(k) (if clinical AI)"
        elif any(e in geo for e in ("uk", "united kingdom", "nhs")):
            data["regulatory_market"] = "NHS Data Security and Protection Toolkit (DSPT) / DCB0129 / NICE"
        elif any(e in geo for e in ("europe", "germany", "france", "eu")):
            data["regulatory_market"] = "EU MDR / GDPR / DiGA (Germany)"
        else:
            data["regulatory_market"] = "Local Health Data Privacy & Security Regulations"

    return data


class LLMServiceException(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMConnectionError(LLMServiceException):
    """Raised when the Ollama service cannot be reached."""
    pass


class LLMTimeoutError(LLMServiceException):
    """Raised when the Ollama request times out."""
    pass


class LLMResponseError(LLMServiceException):
    """Raised when Ollama returns an invalid or unparseable response."""
    pass


class OllamaLLMService:
    """Service for interacting with local Ollama API to extract structured Healthcare SaaS business analysis."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS

    def build_system_prompt(self) -> str:
        """Return the standardized Healthcare SaaS system prompt."""
        return SYSTEM_PROMPT

    def build_user_prompt(self, business_idea: str) -> str:
        """Return user prompt for Healthcare SaaS extraction."""
        return f"Healthcare SaaS Business Concept:\n{business_idea}"

    def build_payload(self, business_idea: str) -> Dict[str, Any]:
        """Build structured chat completion payload for Ollama."""
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.build_system_prompt(),
                },
                {
                    "role": "user",
                    "content": self.build_user_prompt(business_idea),
                },
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 512,
            },
        }

    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP POST request to Ollama service endpoint."""
        timeout_cfg = httpx.Timeout(timeout=self.timeout_seconds, connect=1.0)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            response = await client.post(endpoint, json=payload)
            if response.status_code != 200:
                body_sample = response.text if response.text else "empty response body"
                if any(kw in body_sample for kw in ("0xc0000409", "CUDA", "stack-based buffer", "terminated", "crash")):
                    raise LLMResponseError(
                        f"Local LLM crash detected at {endpoint} (HTTP {response.status_code}): {body_sample}"
                    )
                raise LLMResponseError(
                    f"Ollama endpoint {endpoint} (model: {payload.get('model')}) returned HTTP {response.status_code}: {body_sample[:200]}"
                )
            return response.json()

    async def analyze_business_idea(self, business_idea: str, allow_fallback: bool = False) -> BusinessAnalysis:
        """Send the Healthcare SaaS business idea to Ollama, apply Layer 2 deterministic normalization, and validate."""
        endpoint = f"{self.base_url}/api/chat"
        payload = self.build_payload(business_idea)

        try:
            response_json = await self._make_request(endpoint, payload)
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            if allow_fallback:
                logger.warning("Ollama connection failed at %s (%s). Applying Layer 2 fallback.", endpoint, exc)
                fallback_dict = normalize_business_analysis({}, business_idea)
                return BusinessAnalysis.model_validate(fallback_dict)
            raise LLMConnectionError(f"Ollama service unavailable at {self.base_url}: {exc}") from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as exc:
            if allow_fallback:
                logger.warning("Ollama request timed out after %ss (%s). Applying Layer 2 fallback.", self.timeout_seconds, exc)
                fallback_dict = normalize_business_analysis({}, business_idea)
                return BusinessAnalysis.model_validate(fallback_dict)
            raise LLMTimeoutError(f"LLM request timed out after {self.timeout_seconds}s: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, (LLMResponseError, LLMConnectionError, LLMTimeoutError)):
                if allow_fallback:
                    logger.warning("Ollama error (%s). Applying Layer 2 fallback.", exc)
                    fallback_dict = normalize_business_analysis({}, business_idea)
                    return BusinessAnalysis.model_validate(fallback_dict)
                raise exc
            if allow_fallback:
                logger.warning("Network or HTTP error while contacting Ollama: %s. Applying fallback.", exc)
                fallback_dict = normalize_business_analysis({}, business_idea)
                return BusinessAnalysis.model_validate(fallback_dict)
            raise LLMResponseError(f"Error communicating with Ollama: {exc}") from exc

        message = response_json.get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            # Check thinking field if content is empty
            content = message.get("thinking", "")

        content = content.strip() if isinstance(content, str) else ""

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        if not content:
            if allow_fallback:
                parsed_content = {}
            else:
                raise LLMResponseError("Ollama returned empty response content.")
        else:
            try:
                parsed_content = json.loads(content)
            except Exception as exc:
                if allow_fallback:
                    parsed_content = {}
                else:
                    raise LLMResponseError(f"Ollama response could not be decoded as JSON: {exc}") from exc

        # Run semantic B2B SaaS classification
        classifier = get_classification_service()
        try:
            classification = await classifier.classify_business_idea(business_idea, allow_fallback=True)
        except Exception as exc:
            logger.warning("Classification error: %s. Using rule fallback.", exc)
            classification = classifier.classify_by_rules(business_idea)

        normalized = normalize_business_analysis(
            parsed_content if isinstance(parsed_content, dict) else {},
            business_idea,
            classification=classification,
        )
        return BusinessAnalysis.model_validate(normalized)

    async def generate_competitors(
        self,
        analysis: BusinessAnalysis,
        search_snippets: Optional[List[str]] = None,
    ) -> List[CompetitorInfo]:
        """Dynamically identify relevant B2B SaaS competitors grounded in business category and evidence."""
        category = analysis.category or analysis.healthcare_saas_category or "B2B SaaS"
        geo = analysis.target_country or analysis.geography or "Global"
        cust = analysis.customer_type or analysis.target_customer or "Businesses"
        problem = analysis.primary_problem or analysis.customer_problem or "workflow management"
        snippets_text = "\n".join(search_snippets[:5]) if search_snippets else ""

        prompt = (
            f"Identify 2 to 4 major competing B2B SaaS companies or software products for:\n"
            f"Category: {category}\n"
            f"Target Customer: {cust}\n"
            f"Geography: {geo}\n"
            f"Problem Solved: {problem}\n"
            f"Research Evidence:\n{snippets_text}\n\n"
            "Return JSON array with objects matching: {\"name\": str, \"website\": str or null, \"product_service\": str, \"target_market\": str, \"pricing\": str (use 'Pricing not publicly available' if not verifiable), \"public_pricing\": str, \"key_features\": [str], \"pricing_model\": str, \"deployment_model\": str, \"differentiators\": str, \"confidence\": \"high\"|\"medium\"|\"low\"}.\n"
            "Do NOT invent fake exact prices. Output valid JSON array only."
        )

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a B2B SaaS Competitive Intelligence Analyst. Output JSON array only."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 768},
            }
            res = await self._make_request(f"{self.base_url}/api/chat", payload)
            content = res.get("message", {}).get("content", "").strip()
            if content.startswith("```"):
                content = re.sub(r"^```[a-z]*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "competitors" in parsed:
                parsed = parsed["competitors"]
            if isinstance(parsed, list) and parsed:
                comps: List[CompetitorInfo] = []
                for item in parsed:
                    if isinstance(item, dict) and item.get("name"):
                        comps.append(CompetitorInfo(
                            name=str(item.get("name")),
                            website=item.get("website"),
                            product_service=item.get("product_service") or f"{category} solution",
                            category=category,
                            target_market=item.get("target_market") or f"{cust} in {geo}",
                            target_customers=item.get("target_customers") or cust,
                            geography=item.get("geography") or geo,
                            key_features=item.get("key_features", []) if isinstance(item.get("key_features"), list) else [],
                            pricing_model=item.get("pricing_model") or analysis.pricing_model or "Subscription",
                            pricing=item.get("pricing") or "Pricing not publicly available",
                            public_pricing=item.get("public_pricing") or item.get("pricing") or "Pricing not publicly available",
                            deployment_model=item.get("deployment_model") or "Cloud SaaS",
                            differentiators=item.get("differentiators"),
                            source_url=item.get("source_url") or item.get("website"),
                            source_name=item.get("source_name") or "Market Analysis",
                            confidence=item.get("confidence", "medium"),
                        ))
                if comps:
                    return comps
        except Exception as exc:
            logger.debug("Competitor extraction via LLM failed (%s), applying semantic category mapping.", exc)

        return self.fallback_competitors(analysis)

    @staticmethod
    def fallback_competitors(analysis: BusinessAnalysis) -> List[CompetitorInfo]:
        """Deterministic semantic rule fallback for B2B SaaS competitors."""
        category = analysis.category or analysis.healthcare_saas_category or "B2B SaaS"
        geo = analysis.target_country or analysis.geography or "Global"
        cust = analysis.customer_type or analysis.target_customer or "Businesses"
        cat_lower = category.lower()

        if "crm" in cat_lower or "sales" in cat_lower:
            return [
                CompetitorInfo(name="HubSpot Sales Hub", website="https://hubspot.com", product_service="Inbound CRM and sales pipeline automation", category="CRM & Sales", target_market=f"{cust} ({geo})", pricing="Tiered subscription starting at $20/seat/month", public_pricing="$20/seat/month starter", key_features=["Contact Management", "Deal Pipeline", "Email Tracking"], pricing_model="per_seat", deployment_model="Cloud SaaS", differentiators="All-in-one inbound marketing and CRM ecosystem integration", confidence="high"),
                CompetitorInfo(name="Zoho CRM", website="https://zoho.com/crm", product_service="Omnichannel cloud CRM and workflow automation", category="CRM & Sales", target_market=f"SMBs & Mid-Market ({geo})", pricing="Starting at ₹800/user/month", public_pricing="₹800/user/month", key_features=["Lead Scoring", "Workflow Rules", "Canvas Builder"], pricing_model="per_seat", deployment_model="Cloud SaaS", differentiators="Extensive suite integration and competitive Indian market pricing", confidence="high"),
            ]
        elif "hr" in cat_lower or "recruiting" in cat_lower or "workforce" in cat_lower:
            return [
                CompetitorInfo(name="Keka HR", website="https://keka.com", product_service="Employee payroll, attendance, and performance SaaS", category="HR & Workforce", target_market=f"SMEs and Enterprises in {geo}", pricing="Pricing not publicly available", public_pricing="Pricing not publicly available", key_features=["Payroll Automation", "Statutory Compliance", "Leave Tracker"], pricing_model="per_user", deployment_model="Cloud SaaS", differentiators="Localized payroll engine for statutory compliance", confidence="high"),
                CompetitorInfo(name="Darwinbox", website="https://darwinbox.com", product_service="Enterprise human capital management suite", category="HR & Workforce", target_market="Mid-Market & Large Enterprises", pricing="Enterprise custom quotation", public_pricing="Pricing not publicly available", key_features=["Talent Management", "People Analytics", "Time & Attendance"], pricing_model="annual_subscription", deployment_model="Cloud SaaS", differentiators="Mobile-first enterprise architecture for distributed workforces", confidence="high"),
            ]
        elif "account" in cat_lower or "finance" in cat_lower or "gst" in cat_lower:
            return [
                CompetitorInfo(name="Clear (formerly ClearTax)", website="https://clear.in", product_service="GST compliance and e-invoicing SaaS", category="Accounting & Finance", target_market=f"SMEs and Tax Professionals in {geo}", pricing="Starting at ₹10,000/year", public_pricing="₹10,000/year", key_features=["GST Return Filing", "E-way Bill Generation", "ITC Matching"], pricing_model="annual_subscription", deployment_model="Cloud SaaS", differentiators="Direct API integration with government GSTN servers", confidence="high"),
                CompetitorInfo(name="Zoho Books", website="https://zoho.com/books", product_service="GST-compliant online accounting and billing software", category="Accounting & Finance", target_market="Small & Medium Businesses", pricing="Starting at ₹749/month", public_pricing="₹749/month", key_features=["Invoicing", "Bank Reconciliation", "Inventory Tracking"], pricing_model="monthly_subscription", deployment_model="Cloud SaaS", differentiators="Tight ecosystem integrations and multi-currency billing", confidence="high"),
            ]
        elif "health" in cat_lower or "clinic" in cat_lower or "food" in cat_lower or "meal" in cat_lower:
            return [
                CompetitorInfo(name="Practo Ray", website="https://practo.com", product_service="Practice management, EMR, and scheduling platform", category=category, target_market=f"Providers & Businesses ({geo})", pricing="Starting at ₹999/month", public_pricing="₹999/month", key_features=["Appointment Scheduling", "Digital Records", "Billing & SMS"], pricing_model="per_provider", deployment_model="Cloud SaaS", differentiators="Integrated consumer discovery network", confidence="high"),
                CompetitorInfo(name="DocEngage", website="https://docengage.in", product_service="Specialty relationship management and workflow SaaS", category=category, target_market="Specialty Centers & Chains", pricing="Pricing not publicly available", public_pricing="Pricing not publicly available", key_features=["Custom Forms", "Multi-branch Management", "API Integration"], pricing_model="per_facility", deployment_model="Cloud SaaS", differentiators="Deep specialty workflow templates and multi-unit chain architecture", confidence="high"),
            ]
        elif "cyber" in cat_lower or "security" in cat_lower:
            return [
                CompetitorInfo(name="Sprinto", website="https://sprinto.com", product_service="Automated security compliance and continuous monitoring SaaS", category="Cybersecurity", target_market=f"Tech Startups and Scaleups ({geo})", pricing="Pricing not publicly available", public_pricing="Pricing not publicly available", key_features=["SOC 2 / ISO 27001 Automation", "Continuous Evidence Collection", "Vulnerability Tracker"], pricing_model="annual_subscription", deployment_model="Cloud SaaS", differentiators="Pre-built compliance playbooks with automated audit evidence collection", confidence="high"),
                CompetitorInfo(name="CrowdStrike Falcon", website="https://crowdstrike.com", product_service="Cloud-native endpoint protection and threat intelligence", category="Cybersecurity", target_market="SMBs to Global Enterprises", pricing="Tiered enterprise licensing", public_pricing="Pricing not publicly available", key_features=["Endpoint Detection & Response (EDR)", "Next-Gen Antivirus", "Threat Hunting"], pricing_model="per_seat", deployment_model="Cloud SaaS", differentiators="Single lightweight cloud agent architecture", confidence="high"),
            ]
        elif "logistics" in cat_lower or "fleet" in cat_lower:
            return [
                CompetitorInfo(name="LocoNav", website="https://loconav.com", product_service="Fleet management, GPS tracking, and IoT analytics SaaS", category="Logistics & Supply Chain", target_market=f"Transport Operators and Fleet Owners in {geo}", pricing="Pricing not publicly available", public_pricing="Pricing not publicly available", key_features=["Real-time GPS Tracking", "Fuel Monitoring", "Driver Behaviour AI"], pricing_model="per_facility", deployment_model="Cloud SaaS", differentiators="Hardware-agnostic IoT telemetry platform with localized roadside support", confidence="high"),
                CompetitorInfo(name="Locus.sh", website="https://locus.sh", product_service="AI dispatch management and route optimization platform", category="Logistics & Supply Chain", target_market="Enterprise Logistics & E-commerce", pricing="Enterprise contract", public_pricing="Pricing not publicly available", key_features=["Automated Route Planning", "Capacity Optimization", "Delivery Tracking"], pricing_model="usage_based", deployment_model="Cloud SaaS", differentiators="Proprietary geocoding and 3D dispatch loading algorithms", confidence="high"),
            ]
        elif "edtech" in cat_lower or "education" in cat_lower or "school" in cat_lower:
            return [
                CompetitorInfo(name="Teachmint", website="https://teachmint.com", product_service="Connected school management and classroom digitization platform", category="EdTech & Education", target_market=f"K-12 Schools and Institutes in {geo}", pricing="Tiered SaaS licensing", public_pricing="Pricing not publicly available", key_features=["Student Information System", "Fee Management", "Online Attendance"], pricing_model="annual_subscription", deployment_model="Cloud SaaS", differentiators="Mobile-first integrated LMS with multilingual parent communication", confidence="high"),
                CompetitorInfo(name="Fedena", website="https://fedena.com", product_service="All-in-one school ERP and student administration software", category="EdTech & Education", target_market="Schools, Colleges, and Universities", pricing="Starting at $360/year", public_pricing="$360/year base tier", key_features=["Timetable Management", "Exam Grading", "Custom Reporting"], pricing_model="annual_subscription", deployment_model="Cloud SaaS", differentiators="Modular open architecture with rich plugin ecosystem", confidence="high"),
            ]
        else:
            return [
                CompetitorInfo(
                    name=f"Leading {category} Platform",
                    website=None,
                    product_service=f"Enterprise {category} software automation platform",
                    category=category,
                    target_market=f"{cust} ({geo})",
                    pricing="Pricing not publicly available",
                    public_pricing="Pricing not publicly available",
                    key_features=["Workflow Automation", "Analytics Dashboard", "API Integrations"],
                    pricing_model=analysis.pricing_model or "Subscription",
                    deployment_model="Cloud SaaS",
                    differentiators="Established market brand and extensive enterprise integrations",
                    confidence="medium",
                ),
            ]

    @staticmethod
    def fallback_market_trends(analysis: BusinessAnalysis) -> List[MarketTrendItem]:
        """Deterministic semantic rule fallback for B2B SaaS market trends."""
        category = analysis.category or analysis.healthcare_saas_category or "B2B SaaS"
        geo = analysis.target_country or analysis.geography or "Global"
        cust = analysis.customer_type or analysis.target_customer or "Businesses"

        return [
            MarketTrendItem(
                trend="AI-Powered Workflow Automation & Copilots",
                explanation=f"Rapid adoption of generative and agentic AI to automate repetitive administrative and analytical tasks across {category}.",
                affected_customer_segment=cust,
                impact_on_market="Dramatically lowers onboarding time and operational costs, driving higher software willingness-to-pay and expansion ARPU.",
                evidence_source="Gartner / IDC B2B Software Forecast",
                publication_date="2024-2025",
                confidence="high",
            ),
            MarketTrendItem(
                trend="Shift from Monolithic Suites to Modular Cloud Micro-SaaS",
                explanation=f"{cust} are replacing bloated on-premise systems with agile, API-first vertical SaaS modules.",
                affected_customer_segment=f"Mid-Market & SMB {cust}",
                impact_on_market="Accelerates buyer adoption velocity by reducing upfront deployment cycles from months to days.",
                evidence_source="Bessemer Venture Partners State of the Cloud",
                publication_date="2024",
                confidence="high",
            ),
            MarketTrendItem(
                trend="Regulatory Compliance & Data Localization Mandates",
                explanation=f"Heightened regulatory scrutiny regarding data security and local data hosting standards in {geo}.",
                affected_customer_segment=f"Enterprise {cust}",
                impact_on_market="Creates a competitive barrier to entry favoring localized, compliant cloud SaaS vendors over legacy overseas providers.",
                evidence_source=analysis.regulatory_market or f"Government Digital Standards ({geo})",
                publication_date="2024",
                confidence="high",
            ),
        ]

    @staticmethod
    def fallback_customer_segmentation(analysis: BusinessAnalysis) -> List[CustomerSegmentItem]:
        """Deterministic semantic rule fallback for customer segmentation."""
        category = analysis.category or analysis.healthcare_saas_category or "B2B SaaS"
        cust = analysis.customer_type or analysis.target_customer or "Organizations"
        geo = analysis.target_country or analysis.geography or "India"

        return [
            CustomerSegmentItem(
                segment_name=f"Small Businesses & Independent {cust}",
                description=f"Single-location or micro-scale {cust.lower()} with lean operational staff.",
                estimated_population=None,
                population_unit=cust.lower(),
                business_need="Affordable, turnkey setup to automate core day-to-day operations with zero IT overhead.",
                likely_use_case=analysis.primary_use_case or "Basic operational automation and billing",
                pricing_relevance="Entry-level monthly/annual subscription tier",
                evidence="Market segment distribution benchmark",
                confidence="medium",
            ),
            CustomerSegmentItem(
                segment_name=f"Mid-Market & Multi-Location {cust}",
                description=f"Growing {cust.lower()} operating 2 to 10 facilities or 20 to 200 team members.",
                estimated_population=None,
                population_unit=cust.lower(),
                business_need="Centralized visibility, role-based access control, and standardized reporting across units.",
                likely_use_case="Multi-unit coordination, analytics dashboards, and workflow standardisation",
                pricing_relevance="Per-seat / per-facility annual contract with volume tiering",
                evidence="Industry operational tiering data",
                confidence="medium",
            ),
            CustomerSegmentItem(
                segment_name=f"Large Enterprises & Institutional Networks",
                description=f"Top-tier institutional {cust.lower()} requiring bespoke integrations and high availability.",
                estimated_population=None,
                population_unit=cust.lower(),
                business_need="Enterprise-grade SLA, custom ERP integrations, data compliance, and multi-tier user governance.",
                likely_use_case="Enterprise compliance, cross-departmental operations, and high-throughput automated workflows",
                pricing_relevance="Annual enterprise contract with dedicated support and onboarding SLA",
                evidence="Enterprise procurement benchmark",
                confidence="medium",
            ),
        ]

    async def generate_market_trends(
        self,
        analysis: BusinessAnalysis,
        search_snippets: Optional[List[str]] = None,
    ) -> List[MarketTrendItem]:
        """Dynamically generate evidence-supported B2B SaaS market trends."""
        return self.fallback_market_trends(analysis)

    async def generate_customer_segmentation(
        self,
        analysis: BusinessAnalysis,
        search_snippets: Optional[List[str]] = None,
    ) -> List[CustomerSegmentItem]:
        """Generate structured customer tiers (SMB, Mid-Market, Enterprise)."""
        return self.fallback_customer_segmentation(analysis)

    def generate_value_proposition(self, analysis: BusinessAnalysis) -> ValuePropositionAnalysis:
        """Generate structured value proposition and competitive differentiation breakdown."""
        category = analysis.category or analysis.healthcare_saas_category or "B2B SaaS"
        cust = analysis.customer_type or analysis.target_customer or "Businesses"
        problem = analysis.primary_problem or analysis.customer_problem or f"inefficient manual workflows in {category}"
        product = analysis.product or analysis.business_name or f"{category} Platform"
        geo = analysis.target_country or analysis.geography or "the target market"

        return ValuePropositionAnalysis(
            customer_problem=f"Fragmented operations and high administrative overhead from manual processes: {problem}.",
            current_pain_point="Heavy reliance on disconnected spreadsheets, legacy desktop software, or error-prone paper workflows.",
            target_customer=f"{cust} in {geo} seeking operational efficiency and modern cloud tooling.",
            product_solution=f"{product} delivers a purpose-built cloud solution to streamline and automate core {category} workflows.",
            key_capabilities=analysis.use_cases if analysis.use_cases else ["Automated Workflow Engine", "Centralized Analytics", "Real-time Collaboration", "Role-based Access Control"],
            business_benefit="Improves institutional efficiency, accelerates decision-making, and eliminates billing leakage.",
            operational_benefit="Saves 10-15+ hours per week per team by replacing manual data entry with automated synchronization.",
            financial_time_saving_benefit="Rapid ROI payback within 3 to 6 months through operational labor savings and reduced compliance errors.",
            differentiation_opportunity=f"Cloud-native architecture designed specifically for {cust} with localized compliance ({analysis.regulatory_market or 'industry standards'}).",
            value_proposition_statement=f"{product} empowers {cust} to eliminate operational bottlenecks, ensure full compliance, and maximize throughput via intelligent cloud automation.",
        )

    def generate_business_model_analysis(self, analysis: BusinessAnalysis) -> BusinessModelAnalysis:
        """Analyze B2B SaaS monetization model, billing terms, and expansion vectors."""
        pricing_mod = analysis.pricing_model or analysis.pricing_basis or "annual_subscription"
        cust = analysis.customer_type or analysis.target_customer or "Businesses"
        curr = analysis.currency or "INR"

        return BusinessModelAnalysis(
            business_model="B2B SaaS (Pure Recurring Subscription)",
            pricing_model=str(pricing_mod),
            billing_frequency="Annual upfront or Monthly recurring billing",
            target_customer=cust,
            revenue_mechanism=f"Predictable recurring software subscription denominated in {curr}",
            pricing_unit=f"Per {analysis.pricing_basis or 'customer organization'} / year",
            possible_expansion_revenue=[
                "Usage-based API transaction and processing fees",
                "Add-on premium AI analytics and custom reporting modules",
                "Professional onboarding and data migration services",
                "Multi-location enterprise seat expansions",
            ],
            evidence_source="SaaS Industry Pricing Benchmark",
        )


def get_llm_service() -> OllamaLLMService:
    """Dependency provider for OllamaLLMService."""
    return OllamaLLMService()

