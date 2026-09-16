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
    CompetitorInfo,
    HealthcareCustomerType,
    HealthcareSaaSCategory,
    MarketStrategy,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Healthcare SaaS Market Research & Business Intelligence Analyst.
Analyze the user's Healthcare SaaS business concept and extract structured business attributes.
Output ONLY a valid JSON object matching these fields:
{
  "business_name": "string or null",
  "business_idea": "exact user input string",
  "product": "core product offering or null",
  "product_description": "short description or null",
  "sector": "Healthcare SaaS",
  "healthcare_saas_category": "one of: Clinic Management SaaS, Hospital Management SaaS, EHR/EMR SaaS, Telemedicine SaaS, Medical Billing & Revenue Cycle Management (RCM) SaaS, Patient Engagement & Portal SaaS, Pharmacy Management SaaS, Laboratory & Diagnostic Management SaaS, Dental Practice Management SaaS, Remote Patient Monitoring (RPM) SaaS, Healthcare Analytics & BI SaaS, Healthcare AI & Clinical Decision Support SaaS",
  "industry": "Healthcare Information Technology",
  "market_category": "sub-segment string or null",
  "target_country": "e.g. India, United States",
  "customer_type": "one of: Clinics, Hospitals, Diagnostic Laboratories, Pharmacies, Dental Clinics, Medical Practices, Telemedicine Providers",
  "business_model": "B2B SaaS",
  "pricing_model": "one of: per_facility, per_provider, per_user, monthly_subscription, annual_subscription or null",
  "clinical_use": boolean,
  "emr_ehr_integration_required": boolean,
  "regulatory_market": "e.g. ABDM / NABH for India, HIPAA for USA"
}

Do NOT output markdown code fences or conversational text. Output pure JSON only."""



def derive_market_strategy(analysis: BusinessAnalysis) -> MarketStrategy:
    """Derive dynamic Healthcare SaaS MarketStrategy from structured BusinessAnalysis."""
    product = (analysis.product or analysis.product_description or "Healthcare SaaS Solution").strip()
    category = (analysis.healthcare_saas_category or analysis.market_category or "Healthcare SaaS").strip()
    cust_type = (analysis.customer_type or "Healthcare Organizations").strip()
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
    elif any(k in pricing_mod for k in ("facility", "hospital", "clinic", "practice")):
        tam_method = "bottom_up_per_facility_pricing"
    else:
        tam_method = "bottom_up_customer_arpu"

    # Targeted Healthcare SaaS evidence requirements
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
        f"Realistically obtainable customer acquisition count across Years 1-3 based on sales capacity and healthcare procurement cycles",
        f"Near-term obtainable market share percentage within serviceable {target_cust}",
        f"Conservative, Base, and Optimistic adoption scenarios",
    ]

    terms_raw = f"{product} {category} {cust_type} {target_cust} healthcare saas hospital clinic medical emr ehr".lower()
    relevant_terms = [t for t in set(re.findall(r"[a-zA-Z]{3,}", terms_raw)) if t not in ("for", "the", "and", "with", "market", "service", "platform", "app")]

    return MarketStrategy(
        business_sector="Healthcare SaaS",
        industry="Healthcare Information Technology",
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
        segment_narrowing_dimensions=["geography", "facility_size", "clinical_specialty", "digital_maturity", "regulatory_compliance"],
    )


def normalize_business_analysis(data: Dict[str, Any], business_idea: str) -> Dict[str, Any]:
    """Layer 2: Safe deterministic normalization and fallback derived strictly from user input for Healthcare SaaS."""
    text = business_idea.strip()
    text_lower = text.lower()

    # Always enforce exact user input
    data["business_idea"] = text
    data["sector"] = "Healthcare SaaS"
    data["industry"] = "Healthcare Information Technology"

    # 1. Healthcare SaaS Category Classification
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
            data["healthcare_saas_category"] = data.get("healthcare_saas_category") or None

    # 2. Customer Type
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
        timeout_cfg = httpx.Timeout(timeout=self.timeout_seconds, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            response = await client.post(endpoint, json=payload)
            if response.status_code != 200:
                body_sample = response.text[:200] if response.text else "empty response body"
                raise LLMResponseError(
                    f"Ollama endpoint {endpoint} (model: {payload.get('model')}) returned HTTP {response.status_code}: {body_sample}"
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
                    raise LLMResponseError(f"Failed to decode Ollama JSON output: {exc}") from exc

        normalized = normalize_business_analysis(parsed_content if isinstance(parsed_content, dict) else {}, business_idea)
        return BusinessAnalysis.model_validate(normalized)


def get_llm_service() -> OllamaLLMService:
    """Dependency provider for OllamaLLMService."""
    return OllamaLLMService()
