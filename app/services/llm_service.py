import json
import logging
import re
from typing import Any, Dict, Optional
import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas.business import BusinessAnalysis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert business concept and market research analysis assistant.
Your task is to extract structured business attributes from the user's business idea into the requested JSON schema with high factual precision.

Extraction Guidelines:
1. PRODUCT:
   - Extract the meaningful product, platform, or service name/concept from the text (e.g., 'Affordable online programming platform', 'Healthy meal delivery service', 'SaaS accounting platform').
   - Do NOT reduce the product to a generic word like 'app' or 'platform' when specific descriptors are in the input.

2. TARGET CUSTOMER:
   - Extract explicit target users, demographics, or customer segments explicitly mentioned in the text (e.g., 'for college students in India' -> 'College students', 'for urban families in Chennai' -> 'Urban families', 'for small businesses' -> 'Small businesses').
   - If no target customer or audience is stated, return null.

3. GEOGRAPHY:
   - Extract explicit geographical regions, countries, or cities mentioned in the text (e.g., 'in India' -> 'India', 'in Chennai' -> 'Chennai', 'in North America' -> 'North America').
   - If NO geographic location is stated in the input, return null. NEVER guess or invent geography.

4. INDUSTRY:
   - Semantically infer and classify the primary industry, sector, or market domain based on the product and concept (e.g., 'online programming platform' -> 'EdTech / Online Education / Software Training', 'healthy meal delivery' -> 'Food Delivery / Food Service', 'accounting SaaS' -> 'Accounting Software / FinTech').
   - If the domain is completely ambiguous, return null.

5. BUSINESS MODEL:
   - Extract or high-confidence classify the business model (e.g., 'B2C' for consumer or student applications, 'B2B' for enterprise or business tools, 'Subscription' for subscription services, 'B2B2C', 'Marketplace', 'SaaS').
   - If completely ambiguous, return null.

6. PRICING MODEL:
   - Extract ONLY when explicit pricing or monetization mechanisms are stated in the text (e.g., 'Recurring Subscription', 'Freemium', '$10/month', 'Commission-based', 'One-time Purchase', 'Pay-per-seat').
   - Descriptive terms like 'affordable', 'cheap', 'premium', 'luxury', or 'low-cost' describe price positioning, NOT a pricing model. Do NOT assume 'Subscription' or 'Free' merely because a product is described as 'affordable'. If no specific pricing mechanism is stated, return null.

7. CUSTOMER PROBLEM:
   - Infer a concise customer problem statement supported by the business idea wording (e.g., 'affordable online programming platform for college students' -> 'Need for accessible and affordable programming education'; 'healthy meal delivery for college students' -> 'Lack of convenient, healthy, and reliable meal options for college students').
   - If the input lacks sufficient detail, return null.

8. VALUE PROPOSITION:
   - Infer a concise value proposition supported by the business idea wording (e.g., 'affordable online programming platform for college students' -> 'High quality affordable online coding training for college students'; 'healthy meal delivery service' -> 'Convenient and nutritious meal delivery for college students').
   - If the input lacks sufficient detail, return null.

9. EPISTEMIC RULE - UNKNOWN != ASSUMED:
   - If an attribute is not present and cannot be determined with high confidence, set that field to null.
   - Do NOT invent geography, pricing, revenue, market size, competitors, customer numbers, or statistics.
   - Do NOT calculate TAM, SAM, or SOM.
   - Return only the structured JSON object complying with the schema."""


def normalize_business_analysis(data: Dict[str, Any], business_idea: str) -> Dict[str, Any]:
    """Layer 2: Safe deterministic normalization and fallback derived strictly from user input.
    
    Fills/repairs missing fields (null/empty) that are clearly and unambiguously supported
    by the raw business idea without inventing unsupported facts or hallucinating figures.
    """
    text = business_idea.strip()
    text_lower = text.lower()

    # Always enforce exact user input
    data["business_idea"] = text

    # 1. Product extraction fallback
    if not data.get("product"):
        prod_match = re.search(
            r"(?:build|create|launch|start|develop|make)\s+(?:an?|the)?\s*([a-zA-Z0-9\s\-]+?)(?:\s+for\s+|\s+in\s+|\s+with\s+|\s+that\s+|\.|\,|$)",
            text,
            re.IGNORECASE,
        )
        if prod_match:
            candidate = prod_match.group(1).strip()
            if len(candidate) > 2 and candidate.lower() not in ("app", "platform", "service", "business", "company"):
                data["product"] = candidate[0].upper() + candidate[1:]

    # 2. Target customer extraction fallback
    if not data.get("target_customer"):
        target_match = re.search(
            r"(?:for|targeting|aimed at|designed for|serving)\s+([a-zA-Z0-9\s]+?)(?:\s+in\s+|\s+with\s+|\s+using\s+|\s+at\s+|\.|\,|$)",
            text,
            re.IGNORECASE,
        )
        if target_match:
            cand = target_match.group(1).strip()
            cand_lower = cand.lower()
            if "college student" in cand_lower or "university student" in cand_lower or "students" in cand_lower:
                data["target_customer"] = "College students" if "college" in cand_lower else "Students"
            elif "urban famil" in cand_lower or "families" in cand_lower:
                data["target_customer"] = "Urban families" if "urban" in cand_lower else "Families"
            elif "small business" in cand_lower or "sme" in cand_lower:
                data["target_customer"] = "Small businesses"
            elif "developer" in cand_lower or "programmer" in cand_lower or "engineer" in cand_lower:
                data["target_customer"] = "Software developers"
            elif len(cand) > 2 and cand_lower not in ("india", "chennai", "usa", "uk", "market", "world"):
                data["target_customer"] = cand[0].upper() + cand[1:]

    # 3. Geography extraction fallback
    if not data.get("geography"):
        geo_match = re.search(
            r"(?:in|across|throughout|within)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            text,
        )
        if geo_match:
            cand_geo = geo_match.group(1).strip()
            if cand_geo.lower() not in ("the", "this", "our", "a", "an", "all", "order", "addition"):
                data["geography"] = cand_geo
        else:
            for known_geo in ["India", "Chennai", "Bangalore", "Mumbai", "Delhi", "United States", "USA", "UK", "Europe"]:
                if re.search(rf"\b(?:in|across)\s+{known_geo}\b", text, re.IGNORECASE) or text_lower.endswith(f"in {known_geo.lower()}"):
                    data["geography"] = known_geo
                    break

    # 4. Industry semantic classification fallback
    if not data.get("industry"):
        if any(w in text_lower for w in ["programming", "coding", "software training", "edtech", "tutoring", "course", "education", "student learning"]):
            data["industry"] = "EdTech / Online Education / Software Training"
        elif any(w in text_lower for w in ["meal delivery", "healthy meal", "food delivery", "restaurant", "cloud kitchen", "catering", "dining"]):
            data["industry"] = "Food Delivery / Food Service"
        elif any(w in text_lower for w in ["accounting", "bookkeeping", "invoice", "payroll", "fintech", "banking", "tax filing"]):
            data["industry"] = "Accounting Software / FinTech"
        elif any(w in text_lower for w in ["telemedicine", "doctor consultation", "health clinic", "fitness app", "mental health", "wellness"]):
            data["industry"] = "Healthcare / HealthTech"
        elif any(w in text_lower for w in ["real estate", "property listing", "apartment rental", "house rental", "coworking"]):
            data["industry"] = "Real Estate / PropTech"
        elif any(w in text_lower for w in ["rideshare", "taxi", "carpool", "logistics", "courier", "freight shipping"]):
            data["industry"] = "Transportation / Logistics"
        elif any(w in text_lower for w in ["e-commerce", "marketplace", "online store", "direct to consumer", "d2c"]):
            data["industry"] = "E-Commerce / Marketplace"

    # 5. Pricing model normalization: qualitative words MUST NOT become pricing models
    curr_pricing = data.get("pricing_model")
    if curr_pricing:
        pricing_lower = str(curr_pricing).lower().strip()
        # Strip out purely qualitative descriptors if they were set as pricing_model
        if pricing_lower in ("affordable", "cheap", "premium", "luxury", "low-cost", "budget", "expensive", "affordable pricing", "low cost"):
            data["pricing_model"] = None

    if not data.get("pricing_model"):
        if any(w in text_lower for w in ["subscription-based", "monthly subscription", "annual subscription", "recurring subscription", "subscription"]):
            data["pricing_model"] = "Recurring Subscription"
        elif any(w in text_lower for w in ["one-time payment", "one-time purchase", "one time fee", "pay once"]):
            data["pricing_model"] = "One-time Purchase"
        elif "freemium" in text_lower:
            data["pricing_model"] = "Freemium"
        elif any(w in text_lower for w in ["commission-based", "commission", "take rate"]):
            data["pricing_model"] = "Commission-based"
        elif any(w in text_lower for w in ["ad-supported", "ads-based", "advertising"]):
            data["pricing_model"] = "Ad-supported"
        elif any(w in text_lower for w in ["pay-as-you-go", "usage-based", "pay per use"]):
            data["pricing_model"] = "Usage-based"
        else:
            # Epistemic safety: remain None
            data["pricing_model"] = None

    # 6. Business model normalization
    if not data.get("business_model"):
        if "b2b" in text_lower:
            data["business_model"] = "B2B"
        elif "b2c" in text_lower:
            data["business_model"] = "B2C"
        elif "subscription" in text_lower or "subscription-based" in text_lower:
            data["business_model"] = "Subscription"
        elif "marketplace" in text_lower:
            data["business_model"] = "Marketplace"
        elif "saas" in text_lower:
            data["business_model"] = "SaaS"
        elif data.get("target_customer") in ("College students", "Students", "Urban families", "Consumers", "Parents"):
            data["business_model"] = "B2C"
        elif data.get("target_customer") in ("Small businesses", "SMEs", "Enterprises", "Companies"):
            data["business_model"] = "B2B"

    # 7. Customer problem fallback (grounded in user input)
    if not data.get("customer_problem"):
        cust_str = f" for {data.get('target_customer')}" if data.get("target_customer") else ""
        if "affordable" in text_lower or "low-cost" in text_lower or "accessible" in text_lower:
            if any(w in text_lower for w in ["programming", "coding", "software"]):
                data["customer_problem"] = "Need for accessible and affordable programming education"
            elif any(w in text_lower for w in ["meal", "food"]):
                data["customer_problem"] = f"High cost or limited affordability of quality meals{cust_str}"
            else:
                prod_name = data.get("product") or "services"
                data["customer_problem"] = f"High cost and limited accessibility of {prod_name.lower()}{cust_str}"
        elif any(w in text_lower for w in ["healthy meal", "meal delivery", "healthy food"]):
            data["customer_problem"] = f"Lack of convenient, healthy, and reliable meal options{cust_str}"
        elif any(w in text_lower for w in ["accounting", "bookkeeping", "invoice"]):
            data["customer_problem"] = f"Complexity and time-consuming manual processes in financial management{cust_str}"
        elif any(w in text_lower for w in ["food delivery", "food app", "online ordering"]):
            data["customer_problem"] = f"Inconvenience and friction in ordering and receiving meals{cust_str}"

    # 8. Value proposition fallback (grounded in user input)
    if not data.get("value_proposition"):
        cust_str = f" for {data.get('target_customer')}" if data.get("target_customer") else ""
        if ("affordable" in text_lower or "low-cost" in text_lower) and any(w in text_lower for w in ["programming", "coding", "software"]):
            data["value_proposition"] = f"High quality affordable online coding training{cust_str}"
        elif any(w in text_lower for w in ["healthy meal", "meal delivery", "healthy food"]):
            data["value_proposition"] = f"Convenient and nutritious meal delivery{cust_str}"
        elif any(w in text_lower for w in ["accounting", "bookkeeping", "invoice"]):
            data["value_proposition"] = f"Automated and streamlined financial management{cust_str}"
        elif data.get("product"):
            data["value_proposition"] = f"Accessible and reliable {data['product'].lower()}{cust_str}"

    return data


class LLMServiceException(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMConnectionError(LLMServiceException):
    """Raised when the Ollama service cannot be reached or connection is refused."""
    pass


class LLMTimeoutError(LLMServiceException):
    """Raised when the Ollama request times out."""
    pass


class LLMResponseError(LLMServiceException):
    """Raised when Ollama returns an invalid, empty, or unparseable response."""
    pass


class OllamaLLMService:
    """Service for interacting with local Ollama API to extract structured business analysis."""

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
        """Return the standardized system prompt for business extraction."""
        return SYSTEM_PROMPT

    def build_user_prompt(self, business_idea: str) -> str:
        """Return the standardized user prompt containing the business idea."""
        return f"Business Idea:\n{business_idea}"

    def build_payload(self, business_idea: str) -> Dict[str, Any]:
        """Build the structured chat completion payload for Ollama."""
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
            "format": BusinessAnalysis.model_json_schema(),
            "think": False,
            "options": {
                "temperature": 0.0,
            },
        }

    async def analyze_business_idea(self, business_idea: str) -> BusinessAnalysis:
        """Send the business idea to Ollama, apply Layer 2 deterministic normalization, and validate."""
        endpoint = f"{self.base_url}/api/chat"
        payload = self.build_payload(business_idea)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error("Failed to connect to Ollama at %s: %s", endpoint, exc)
            raise LLMConnectionError("Ollama service is unavailable. Please ensure Ollama is running locally.") from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as exc:
            logger.error("Ollama request timed out after %s seconds: %s", self.timeout_seconds, exc)
            raise LLMTimeoutError(f"LLM request timed out after {self.timeout_seconds} seconds.") from exc
        except Exception as exc:
            logger.error("Unexpected network error while contacting Ollama: %s", exc)
            raise LLMConnectionError(f"Failed to communicate with Ollama: {exc}") from exc

        if response.status_code != 200:
            err_body = response.text
            diag = ""
            if "0xc0000409" in err_body or "CUDA error" in err_body or "llama-server process has terminated" in err_body:
                diag = " (Local LLM crash detected: CUDA runtime or stack buffer overrun in llama-server. Check Ollama GPU/CPU configuration)."
            elif response.status_code == 404 or "model not found" in err_body.lower():
                diag = f" (Configured model '{self.model}' was not found in local Ollama. Ensure model is pulled via `ollama pull {self.model}`)."
            elif response.status_code == 500:
                diag = " (Ollama internal server execution error)."
            logger.error("Ollama returned non-200 status code %d%s: %s", response.status_code, diag, err_body)
            raise LLMResponseError(f"Ollama returned HTTP error {response.status_code}{diag}: {err_body}")

        try:
            response_json = response.json()
        except Exception as exc:
            logger.error("Failed to parse Ollama response as JSON: %s", exc)
            raise LLMResponseError("Ollama returned a malformed response body.") from exc

        message = response_json.get("message")
        if not message or not isinstance(message, dict):
            logger.error("Ollama response missing 'message' field: %s", response_json)
            raise LLMResponseError("Ollama response missing message object.")

        content = message.get("content")
        if not content or not isinstance(content, str) or not content.strip():
            logger.error("Ollama returned an empty message content: %s", response_json)
            raise LLMResponseError("LLM returned an empty response.")

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode model JSON content: %s", content)
            raise LLMResponseError("LLM output could not be decoded as JSON.") from exc

        if not isinstance(parsed_content, dict):
            logger.error("Model JSON content is not an object: %s", parsed_content)
            raise LLMResponseError("LLM output is not a valid JSON object.")

        # Layer 2: Safe deterministic normalization and fallback
        normalized_content = normalize_business_analysis(parsed_content, business_idea)

        try:
            validated_analysis = BusinessAnalysis.model_validate(normalized_content)
        except ValidationError as exc:
            logger.error("Validation failed for model output %s: %s", normalized_content, exc)
            raise LLMResponseError(f"LLM output failed schema validation: {exc}") from exc

        return validated_analysis


def get_llm_service() -> OllamaLLMService:
    """Dependency provider for OllamaLLMService."""
    return OllamaLLMService()
