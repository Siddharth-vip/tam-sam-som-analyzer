import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.config import settings
from app.schemas.classification import (
    B2BSaaSClassification,
    BusinessModelType,
    ClassificationProvenance,
    ClassificationStatus,
)
from app.taxonomy.b2b_saas import (
    B2B_SAAS_TAXONOMY,
    TaxonomyCategory,
    get_all_categories,
    normalize_category_name,
)

logger = logging.getLogger(__name__)

B2B_SAAS_CLASSIFICATION_SYSTEM_PROMPT = """You are a senior B2B SaaS Business Intelligence & Classification Analyst.
Analyze the user's business idea and produce a structured classification in valid JSON.

Evaluate:
1. Is the business idea Business-to-Business (B2B) or Business-to-Consumer (B2C)?
2. Is the product Software-as-a-Service (SaaS) or non-SaaS (marketplace, consumer app, hardware, manual service)?
3. If B2B SaaS, identify the canonical category from this taxonomy:
   - CRM & Sales
   - HR & Workforce Management
   - Accounting & Finance
   - Project & Task Management
   - Marketing & Marketing Automation
   - Customer Support & Helpdesk
   - ERP & Business Operations
   - Procurement & Supply Chain
   - Cybersecurity
   - IT Management & IT Service Management
   - Collaboration & Communication
   - Legal & Compliance
   - Data & Analytics / Business Intelligence
   - Developer Tools
   - Productivity & Workflow Automation
   - E-commerce & Retail Operations
   - Education & Learning Management
   - Healthcare Business Software
   - Real Estate & Property Management
   - Construction & Field Service Management
   - Logistics & Transportation Management
   - Industry-Specific Vertical SaaS
   - Other B2B SaaS
4. Identify subcategory (e.g. "Recruitment / ATS", "Sales CRM", "Billing & Invoicing", "Clinic / Practice Management").
5. Identify target customer organization type and size segment (e.g. SMB, Mid-Market, Enterprise, Startups).
6. Identify primary buyer persona / department.
7. Identify 2-4 major enterprise use cases.
8. Assess confidence score (0.00 to 1.00).

Output JSON format strictly:
{
  "is_b2b": true,
  "is_saas": true,
  "sector": "B2B SaaS",
  "category": "Canonical Category Name",
  "subcategory": "Subcategory Name",
  "business_model": "B2B SaaS",
  "customer_type": "B2B",
  "target_segment": "SMB / Mid-Market / Enterprise / Startups",
  "target_customer": "target customer persona",
  "primary_buyer": "department or buyer title",
  "use_cases": ["use case 1", "use case 2"],
  "confidence": 0.92,
  "reasoning": "brief explanation"
}

If the product is clearly for consumers (e.g., fitness tracker, movie streaming, personal budget app, consumer social):
Set is_b2b=false, is_saas=false (or true if consumer subscription), sector="NON_B2B_SAAS", and explain in reasoning.

If the prompt is ambiguous or lacks business details (e.g., "An AI platform"):
Set confidence below 0.60 and note missing details in reasoning.

Return ONLY pure JSON. Do NOT include markdown fences, comments, or market calculations."""


class B2BSaaSClassificationService:
    """Semantic and deterministic classification engine for B2B SaaS business concepts."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS

    # -----------------------------------------------------------------------
    # Deterministic Pre-Classification & Scope Guards
    # -----------------------------------------------------------------------

    def check_ambiguity(self, text: str) -> Tuple[bool, Optional[str]]:
        """Check if business idea is too vague or underspecified to classify with high confidence."""
        cleaned = text.strip()
        words = [w for w in re.findall(r"\b\w+\b", cleaned) if len(w) > 1]
        
        if len(words) < 4 and any(g in cleaned.lower() for g in ["ai platform", "app", "saas", "software", "platform", "website", "ai"]):
            return True, "The provided business concept is overly generic without target customer, workflow, or industry context."
        
        return False, None

    def check_consumer_scope(self, text: str) -> Tuple[bool, Optional[str]]:
        """Deterministically detect explicit non-B2B consumer / individual consumer products."""
        text_lower = text.lower()

        # Obvious consumer patterns
        consumer_patterns = [
            (r"\b(?:fitness|workout|calorie|diet|gym)\b.*?\b(?:individual|personal|consumer|consumers|users)\b", "Fitness/workout application targeting individual consumers"),
            (r"\b(?:movie|music|video|gaming|game|entertainment)\b.*?\b(?:streaming|subscription)\b.*?\b(?:subscriber|subscribers|consumer|consumers|individual|individuals)\b", "Consumer media streaming / entertainment service"),
            (r"\b(?:personal expense|personal budget|personal finance|wallet tracker|personal calorie)\b", "Personal consumer finance / expense / habit tracker"),
            (r"\b(?:dating app|matchmaking for singles|social network for friends)\b", "Consumer social / dating application"),
            (r"\b(?:mobile fitness|fitness app|calorie tracker)\b", "Mobile fitness/wellness application for individual users"),
            (r"\b(?:photo edit|selfie|camera app|filter app)\b.*?\b(?:users|consumers|individuals)\b", "Consumer mobile photo / media utility"),
            (r"\b(?:food delivery|meal ordering|grocery delivery)\b.*?\b(?:consumers|users|hungry)\b", "Consumer food ordering / delivery application"),
        ]

        for pat, desc in consumer_patterns:
            if re.search(pat, text_lower):
                return True, desc

        # Direct phrase matches
        direct_consumer_phrases = [
            "for individual users",
            "for individual consumers",
            "for consumers",
            "for end consumers",
            "for individual subscribers",
            "consumer photo editing",
            "fitness app for individual",
            "movie streaming platform for individual",
            "personal expense tracker",
        ]
        for phrase in direct_consumer_phrases:
            if phrase in text_lower:
                return True, f"Identified consumer-facing intent: '{phrase}'"

        return False, None

    # -----------------------------------------------------------------------
    # Rule-Based Deterministic Classification Fallback
    # -----------------------------------------------------------------------

    def classify_by_rules(self, text: str) -> B2BSaaSClassification:
        """Deterministic rule-based classification fallback when LLM is unavailable."""
        text_lower = text.lower()

        # 1. Ambiguity check
        is_ambiguous, ambig_reason = self.check_ambiguity(text)
        if is_ambiguous:
            return B2BSaaSClassification(
                sector="B2B SaaS",
                classification_status=ClassificationStatus.AMBIGUOUS,
                sector_confidence=0.45,
                category_confidence=0.40,
                business_model="B2B SaaS",
                customer_type="B2B",
                reasoning=ambig_reason or "Input concept is ambiguous or underspecified.",
                missing_information=["Target customer industry", "Primary workflow / use case", "Pricing or deployment model"],
                provenance=ClassificationProvenance(
                    data_type="AI_CLASSIFIED",
                    source="Deterministic Rule Classifier",
                    model="rule_based_fallback",
                    confidence=0.45,
                ),
            )

        # 2. Consumer / Out-of-Scope check
        is_consumer, cons_reason = self.check_consumer_scope(text)
        if is_consumer:
            return B2BSaaSClassification(
                sector="NON_B2B_SAAS",
                classification_status=ClassificationStatus.OUT_OF_SCOPE,
                sector_confidence=0.95,
                category=None,
                category_id=None,
                subcategory=None,
                category_confidence=0.0,
                business_model="Consumer Application",
                customer_type="B2C",
                target_segment="Consumers",
                primary_buyer="Individual Consumer",
                use_cases=[],
                reasoning=f"The product primarily targets individual consumers rather than businesses. ({cons_reason})",
                provenance=ClassificationProvenance(
                    data_type="AI_CLASSIFIED",
                    source="Deterministic Rule Classifier",
                    model="rule_based_fallback",
                    confidence=0.95,
                ),
            )

        # 3. Match against taxonomy with domain specificity scoring
        category_scores: Dict[str, float] = {}
        generic_keywords = {"scheduling", "workflow", "automation", "dashboard", "analytics", "platform", "management", "tools", "saas", "software", "app"}

        for cat in get_all_categories():
            score = 0.0
            # Match subcategories (high weight)
            for sub in cat.related_subcategories:
                sub_lower = sub.lower()
                clean_sub = re.sub(r"\b(saas|software|platform|system|tools|tool)\b", "", sub_lower).strip()
                if sub_lower in text_lower:
                    score += 15.0
                elif len(clean_sub) >= 4 and clean_sub in text_lower:
                    score += 12.0

            # Match keywords
            for kw in cat.keywords:
                kw_lower = kw.lower()
                if re.search(rf"\b{re.escape(kw_lower)}\b", text_lower):
                    if kw_lower in generic_keywords:
                        score += 1.0
                    elif " " in kw_lower:
                        score += 10.0
                    else:
                        score += max(4.0, len(kw_lower) * 1.0)

            if score > 0:
                category_scores[cat.category_id] = score

        if category_scores:
            best_cat_id = max(category_scores.items(), key=lambda x: x[1])[0]
            matched_cat = B2B_SAAS_TAXONOMY[best_cat_id]
        else:
            matched_cat = normalize_category_name(text_lower) or B2B_SAAS_TAXONOMY["other_b2b_saas"]

        # Derive subcategory if possible
        subcat = matched_cat.related_subcategories[0] if matched_cat.related_subcategories else matched_cat.category_name
        for sub in matched_cat.related_subcategories:
            if any(w in text_lower for w in sub.lower().split() if len(w) > 3):
                subcat = sub
                break

        return B2BSaaSClassification(
            sector="B2B SaaS",
            classification_status=ClassificationStatus.IN_SCOPE,
            sector_confidence=0.90,
            category=matched_cat.category_name,
            category_id=matched_cat.category_id,
            subcategory=subcat,
            category_confidence=0.85,
            business_model="B2B SaaS",
            customer_type="B2B",
            target_segment="SMB / Enterprise",
            target_customer=matched_cat.typical_buyers[0] if matched_cat.typical_buyers else "Businesses",
            primary_buyer=matched_cat.typical_buyers[0] if matched_cat.typical_buyers else "Department Head",
            use_cases=matched_cat.typical_use_cases[:3],
            reasoning=f"Classified as B2B SaaS under '{matched_cat.category_name}' based on business workflow keywords.",
            provenance=ClassificationProvenance(
                data_type="AI_CLASSIFIED",
                source="Deterministic Rule Classifier",
                model="rule_based_fallback",
                confidence=0.88,
            ),
        )

    # -----------------------------------------------------------------------
    # Semantic LLM Classification with Ollama
    # -----------------------------------------------------------------------

    async def classify_business_idea(
        self,
        business_idea: str,
        allow_fallback: bool = True,
    ) -> B2BSaaSClassification:
        """Classify business idea into B2B SaaS taxonomy using Ollama qwen3:8b with deterministic safety post-processing."""
        text = business_idea.strip()

        # Step 0: Fast deterministic check for unambiguous consumer patterns or extreme ambiguity
        is_consumer, cons_reason = self.check_consumer_scope(text)
        if is_consumer:
            logger.info("Deterministic consumer scope detected for: %s", text[:60])
            return B2BSaaSClassification(
                sector="NON_B2B_SAAS",
                classification_status=ClassificationStatus.OUT_OF_SCOPE,
                sector_confidence=0.96,
                category=None,
                category_id=None,
                subcategory=None,
                category_confidence=0.0,
                business_model="Consumer Application",
                customer_type="B2C",
                target_segment="Consumers",
                primary_buyer="Individual Consumer",
                use_cases=[],
                reasoning=f"The product primarily targets individual consumers rather than businesses. ({cons_reason})",
                provenance=ClassificationProvenance(
                    data_type="AI_CLASSIFIED",
                    source=f"Ollama {self.model}",
                    model=self.model,
                    confidence=0.96,
                ),
            )

        is_ambiguous, ambig_reason = self.check_ambiguity(text)
        if is_ambiguous:
            logger.info("Deterministic ambiguity detected for: %s", text[:60])
            return B2BSaaSClassification(
                sector="B2B SaaS",
                classification_status=ClassificationStatus.AMBIGUOUS,
                sector_confidence=0.45,
                category=None,
                category_id=None,
                subcategory=None,
                category_confidence=0.40,
                business_model="B2B SaaS",
                customer_type="B2B",
                reasoning=ambig_reason or "Input concept is ambiguous or underspecified.",
                missing_information=["Target customer organization type", "Core enterprise workflow", "Industry vertical"],
                provenance=ClassificationProvenance(
                    data_type="AI_CLASSIFIED",
                    source=f"Ollama {self.model}",
                    model=self.model,
                    confidence=0.45,
                ),
            )

        # Step 1: Query Ollama LLM
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": B2B_SAAS_CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Business Idea to classify:\n\"{text}\""},
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 512,
            },
        }

        parsed_json: Dict[str, Any] = {}
        try:
            timeout_cfg = httpx.Timeout(timeout=min(self.timeout_seconds, 15.0), connect=0.2)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    resp_data = res.json()
                    raw_content = resp_data.get("message", {}).get("content", "")
                    if not raw_content and "thinking" in resp_data.get("message", {}):
                        raw_content = resp_data.get("message", {}).get("thinking", "")
                    
                    # Clean markdown code fences if present
                    if raw_content.startswith("```"):
                        lines = raw_content.splitlines()
                        if lines and lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        raw_content = "\n".join(lines).strip()
                    
                    if raw_content:
                        parsed_json = json.loads(raw_content)
        except Exception as exc:
            logger.warning("Ollama classification request failed: %s. Falling back to rules.", exc)
            if not allow_fallback:
                raise exc
            return self.classify_by_rules(text)

        if not parsed_json and allow_fallback:
            return self.classify_by_rules(text)

        # Step 2: Post-process and normalize LLM outputs
        is_b2b = bool(parsed_json.get("is_b2b", True))
        is_saas = bool(parsed_json.get("is_saas", True))
        raw_sector = str(parsed_json.get("sector", "B2B SaaS")).strip()
        raw_cat = parsed_json.get("category")
        raw_subcat = parsed_json.get("subcategory")
        confidence = float(parsed_json.get("confidence", 0.90))

        # Check out-of-scope conditions
        if not is_b2b or "non_b2b" in raw_sector.lower() or "consumer" in str(parsed_json.get("business_model", "")).lower():
            return B2BSaaSClassification(
                sector="NON_B2B_SAAS",
                classification_status=ClassificationStatus.OUT_OF_SCOPE,
                sector_confidence=confidence,
                category=None,
                category_id=None,
                subcategory=None,
                category_confidence=0.0,
                business_model=str(parsed_json.get("business_model") or "Consumer Application"),
                customer_type="B2C",
                target_segment="Consumers",
                primary_buyer=str(parsed_json.get("primary_buyer") or "Individual Consumer"),
                use_cases=parsed_json.get("use_cases", []),
                reasoning=str(parsed_json.get("reasoning") or "The product primarily targets individual consumers rather than businesses."),
                provenance=ClassificationProvenance(
                    data_type="AI_CLASSIFIED",
                    source=f"Ollama {self.model}",
                    model=self.model,
                    confidence=confidence,
                ),
            )

        # Normalize category to canonical taxonomy
        norm_cat: Optional[TaxonomyCategory] = normalize_category_name(raw_cat) if raw_cat else None
        if not norm_cat:
            # Try normalizing using subcategory or full text
            norm_cat = normalize_category_name(raw_subcat) or normalize_category_name(text) or B2B_SAAS_TAXONOMY["other_b2b_saas"]

        final_category_name = norm_cat.category_name
        final_category_id = norm_cat.category_id

        # Subcategory refinement
        final_subcat = raw_subcat or (norm_cat.related_subcategories[0] if norm_cat.related_subcategories else norm_cat.category_name)

        use_cases = parsed_json.get("use_cases")
        if not isinstance(use_cases, list) or not use_cases:
            use_cases = norm_cat.typical_use_cases[:3]

        target_cust = parsed_json.get("target_customer") or (norm_cat.typical_buyers[0] if norm_cat.typical_buyers else "Enterprise Organizations")
        primary_buyer = parsed_json.get("primary_buyer") or (norm_cat.typical_buyers[0] if norm_cat.typical_buyers else "Department Head")
        target_seg = parsed_json.get("target_segment") or "SMB / Enterprise"
        reasoning = parsed_json.get("reasoning") or f"Classified under '{final_category_name}' based on business workflows and target buyers."

        return B2BSaaSClassification(
            sector="B2B SaaS",
            classification_status=ClassificationStatus.IN_SCOPE,
            sector_confidence=confidence,
            category=final_category_name,
            category_id=final_category_id,
            subcategory=str(final_subcat),
            category_confidence=min(confidence, 0.95),
            business_model="B2B SaaS",
            customer_type="B2B",
            target_segment=str(target_seg),
            target_customer=str(target_cust),
            primary_buyer=str(primary_buyer),
            use_cases=[str(u) for u in use_cases],
            reasoning=str(reasoning),
            provenance=ClassificationProvenance(
                data_type="AI_CLASSIFIED",
                source=f"Ollama {self.model}",
                model=self.model,
                confidence=confidence,
            ),
        )


# Global singleton instance
_classification_service: Optional[B2BSaaSClassificationService] = None


def get_classification_service() -> B2BSaaSClassificationService:
    """Dependency provider for B2BSaaSClassificationService."""
    global _classification_service
    if _classification_service is None:
        _classification_service = B2BSaaSClassificationService()
    return _classification_service
