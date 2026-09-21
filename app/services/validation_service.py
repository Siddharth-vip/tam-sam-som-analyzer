import hashlib
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.schemas.business import BusinessAnalysis
from app.schemas.discovery import DiscoveryLifecycleStage, SourceQualityTier
from app.schemas.extraction import ExtractedEvidenceCandidate
from app.schemas.validation import (
    ConflictGroup,
    ConflictSource,
    DeduplicationGroup,
    EvidenceConfidence,
    EvidenceRelevanceScore,
    EvidenceSuitability,
    EvidenceValidationResult,
    EvidenceValidationStatus,
    MarketDefinitionCompatibility,
    MarketScopeType,
    SourceProvenance,
    SuitabilityRating,
    TriangulationResult,
)


class ValidationServiceException(Exception):
    """Base exception for evidence validation and triangulation errors."""
    pass


class EvidenceValidationService:
    """Deterministic service for validating, deduplicating, detecting conflicts,

    and triangulating extracted market evidence candidates with strict 4-tier source quality rules.
    """

    # High-credibility domain taxonomy for transparent deterministic source scoring (5 Tiers)
    GOVERNMENT_DOMAINS: Set[str] = {
        "gov", "gov.in", "nic.in", "gov.uk", "gov.au", "gov.ca", "census.gov",
        "education.gov.in", "statistics.gov.in", "mospi.gov.in", "rbi.org.in",
        "trai.gov.in", "startupindia.gov.in", "sebi.gov.in", "ibef.org", "mca.gov.in",
        "sec.gov", "edgar.sec.gov", "aishe.gov.in", "msme.gov.in", "health.gov.in",
        "chennaicorporation.gov.in", "finra.org", "fca.org.uk", "ons.gov.uk",
    }

    REGULATORY_AND_FILINGS: Set[str] = {
        "sec.gov", "edgar.sec.gov", "mca.gov.in", "sebi.gov.in", "rbi.org.in",
        "bseindia.com", "nseindia.com", "annualreports.com",
    }

    INTL_ORGANIZATIONS: Set[str] = {
        "worldbank.org", "un.org", "unesco.org", "who.int", "oecd.org",
        "imf.org", "itu.int", "wto.org", "weforum.org", "adb.org", "europa.eu"
    }

    ACADEMIC_PATTERNS: Set[str] = {
        ".edu", ".ac.in", ".edu.in", ".ac.uk", ".edu.au", "university", "institute",
        "arxiv.org", "researchgate.net", "springer.com", "nature.com", "jstor.org",
        "sciencedirect.com", "wiley.com", "tandfonline.com", "cell.com", "acm.org",
    }

    INDUSTRY_ASSOCIATIONS: Set[str] = {
        "nasscom.in", "nasscom.org", "cii.in", "ficci.in", "gsma.com", "ieee.org",
        "siam.in", "assocham.org", "iamai.in"
    }

    RESEARCH_FIRMS: Set[str] = {
        "gartner.com", "idc.com", "statista.com", "forrester.com", "frost.com",
        "crisil.com", "grandviewresearch.com", "marketsandmarkets.com",
        "mordorintelligence.com", "pitchbook.com", "cbinsights.com", "technavio.com",
        "euromonitor.com"
    }

    CONSULTING_FIRMS: Set[str] = {
        "mckinsey.com", "bain.com", "bcg.com", "strategyand.pwc.com",
        "oliverwyman.com", "kearney.com"
    }

    FINANCIAL_INSTITUTIONS: Set[str] = {
        "goldmansachs.com", "morganstanley.com", "jpmorgan.com", "barclays.com",
        "ubs.com", "hsbc.com", "credit-suisse.com", "citi.com", "bankofamerica.com",
        "blackrock.com"
    }

    REPUTABLE_NEWS: Set[str] = {
        "reuters.com", "bloomberg.com", "wsj.com", "economictimes.indiatimes.com",
        "thehindu.com", "livemint.com", "techcrunch.com", "bbc.com", "ft.com",
        "forbes.com", "business-standard.com", "cnbc.com", "hindustantimes.com",
        "venturebeat.com", "fortune.com", "nytimes.com", "financialexpress.com",
        "indianexpress.com", "marketwatch.com", "barrons.com", "inc.com", "qz.com", "wired.com"
    }

    WEAK_BLOG_PATTERNS: Set[str] = {
        "medium.com", "wordpress.com", "blogspot.com", "wixsite.com", "substack.com",
        "hubspot.com", "blogger.com", "weebly.com"
    }

    UNUSABLE_DOMAINS_AND_FORUMS: Set[str] = {
        "twitter.com", "x.com", "facebook.com", "instagram.com", "tiktok.com",
        "reddit.com", "quora.com", "threads.net", "pinterest.com", "tumblr.com",
        "stackoverflow.com", "stackexchange.com", "answers.yahoo.com", "news.ycombinator.com"
    }

    # Supported measurement units and market entity concepts for structural validation
    RECOGNIZED_UNITS: Set[str] = {
        # Persons & Demographic Target Segments
        "student", "students", "undergraduate", "undergraduates", "postgraduate", "postgraduates",
        "learner", "learners", "user", "users", "subscriber", "subscribers",
        "developer", "developers", "programmer", "programmers", "coder", "coders", "engineer", "engineers",
        "professional", "professionals", "customer", "customers", "buyer", "buyers",
        "people", "population", "individual", "individuals", "person", "persons",
        "worker", "workers", "employee", "employees", "adult", "adults", "youth",
        "child", "children", "teen", "teens", "teenager", "teenagers",
        "patient", "patients", "citizen", "citizens", "consumer", "consumers",
        "driver", "drivers", "graduate", "graduates", "teacher", "teachers",
        "educator", "educators", "instructor", "instructors", "tutor", "tutors",
        "reader", "readers", "member", "members", "client", "clients", "account", "accounts",
        "creator", "creators", "freelancer", "freelancers", "founder", "founders",

        # Institutional & Business Target Entities
        "enterprise", "enterprises", "company", "companies", "business", "businesses",
        "startup", "startups", "firm", "firms", "institution", "institutions",
        "school", "schools", "college", "colleges", "university", "universities",
        "household", "households", "organization", "organizations", "hospital", "hospitals",
        "clinic", "clinics", "pharmacy", "pharmacies", "laboratory", "laboratories",
        "lab", "labs", "practice", "practices", "facility", "facilities", "bed", "beds",
        "merchant", "merchants", "vendor", "vendors",
        "smb", "smbs", "sme", "smes", "msme", "msmes",
        "store", "stores", "shop", "shops", "hub", "hubs", "branch", "branches", "site", "sites",

        # Market Volume, Hardware & Operational Units
        "unit", "units", "installation", "installations", "subscription", "subscriptions",
        "download", "downloads", "transaction", "transactions", "license", "licenses",
        "seat", "seats", "device", "devices", "vehicle", "vehicles", "course", "courses",
        "enrollment", "enrollments", "registration", "registrations",
        "station", "stations", "charger", "chargers", "point", "points", "outlet", "outlets",
        "ev", "evs", "car", "cars", "automobile", "automobiles", "fleet", "fleets",
        "two-wheeler", "two-wheelers", "three-wheeler", "three-wheelers", "bus", "buses", "truck", "trucks",
        "cab", "cabs", "taxi", "taxis", "ride", "rides", "trip", "trips", "session", "sessions",
        "kwh", "mwh", "gwh", "megawatt", "gigawatt", "kw",

        # Financial / Percentage Units
        "usd", "inr", "eur", "gbp", "jpy", "cny", "dollar", "dollars", "rupee", "rupees",
        "crore", "crores", "cr", "lakh", "lakhs", "lac", "million", "millions", "billion", "billions",
        "trillion", "trillions", "%", "pct", "percent", "percentage",
    }

    # Strict noise rejection terms for validation
    NOISE_TERMS: Set[str] = {
        "tip", "tips", "distribution", "distributions", "distro", "distros",
        "llm", "llms", "lts", "version", "tired", "bird", "birds", "animal", "animals",
        "plant", "plants", "tree", "trees", "species", "star", "stars",
        "feature", "features", "tool", "tools", "trick", "tricks", "plugin", "plugins",
        "framework", "frameworks", "library", "libraries", "package", "packages",
        "article", "articles", "post", "posts", "lesson", "lessons", "step", "steps",
        "reason", "reasons", "idea", "ideas", "thing", "things", "hack", "hacks",
        "factor", "factors", "driver", "drivers", "pillar", "pillars", "trend", "trends",
        "challenge", "challenges", "prediction", "predictions", "stat", "stats", "statistic", "statistics",
        "takeaway", "takeaways", "point", "points", "way", "ways", "benefit", "benefits",
        "finding", "findings", "strategy", "strategies", "ranking", "rankings", "list", "lists", "overview",
    }

    # Non-negative metrics whitelist concepts
    NON_NEGATIVE_CONCEPTS: Set[str] = {
        "student", "user", "population", "people", "household", "enterprise",
        "company", "developer", "school", "college", "market size", "revenue",
        "spend", "expenditure", "price", "count", "subscriber", "transaction",
        "cost", "adoption", "professional", "learner", "employee", "customer",
        "station", "charger", "vehicle", "car", "fleet", "unit", "device", "outlet"
    }

    # -----------------------------------------------------------------------
    # 1. Multi-Dimensional Evidence Relevance & Suitability Evaluation
    # -----------------------------------------------------------------------

    def evaluate_evidence_relevance(
        self,
        candidate: ExtractedEvidenceCandidate,
        business_analysis: Optional[BusinessAnalysis] = None,
        source_quality_score: float = 0.5,
    ) -> EvidenceRelevanceScore:
        """Deterministically evaluate the 8 dimensions of evidence relevance against the business idea.

        Dimensions:
          1. Source Quality (0-100)
          2. Industry Relevance (0-100)
          3. Geography Relevance (0-100)
          4. Customer Segment Relevance (0-100)
          5. Product/Service Specificity (0-100)
          6. Market Sizing Usefulness (0-100)
          7. Recency (0-100)
          8. Statistical/Market Sizing Claim Authenticity (0-100)
        """
        source_quality_pct = round(source_quality_score * 100.0, 1)

        metric_str = (candidate.metric or "").strip().lower()
        context_str = (candidate.source_context or "").strip().lower()
        unit_str = (candidate.unit or "").strip().lower()
        cand_geo = (candidate.geography or "").strip().lower()

        breakdown_notes: Dict[str, Any] = {}

        # -------------------------------------------------------------------
        # Dimension 1: Noise, Contact Info, Navigation & Boilerplate Filters
        # -------------------------------------------------------------------
        phone_patterns = [
            r"(\+91[\-\s]?)?[6789]\d{9}",
            r"1800[\-\s]?\d{3}[\-\s]?\d{3,4}",
            r"\b\d{3,5}[\-\s]?\d{6,8}\b",
            r"\b(tel|phone|mobile|fax|call|helpline|toll free)[:\s]+[\+\d\-\s\(\)]+",
        ]
        is_phone = (
            any(w in metric_str for w in ("phone", "mobile", "contact", "helpline", "call", "fax", "tel"))
            or (candidate.value is not None and 1_000_000_000 <= candidate.value <= 9_999_999_999 and unit_str in ("", "unit", "units"))
            or any(re.search(pat, context_str, re.IGNORECASE) for pat in phone_patterns)
        )

        contact_keywords = (
            "pin code", "pincode", "zip code", "postal code", "email", "email address",
            "office address", "registered office", "contact us", "reach us at", "support@",
            "info@", "@gmail.com", "contact number", "toll-free",
        )
        is_contact_info = (
            any(w in metric_str for w in ("pin code", "pincode", "zip code", "postal code", "email", "address", "contact number"))
            or any(w in context_str for w in contact_keywords)
        )

        nav_keywords = (
            "home >", "skip to content", "all rights reserved", "terms and conditions",
            "privacy policy", "terms of use", "cookie policy", "sign in / register",
            "click here to download", "click here to apply", "subscribe to newsletter",
            "menu >", "navigation menu", "search this site", "copyright ©",
            "frequently asked questions", "back to top", "table of contents",
        )
        is_navigation_text = (
            any(pat in context_str for pat in nav_keywords)
            or any(pat in metric_str for pat in ("privacy policy", "all rights reserved", "terms of use", "navigation", "cookie policy"))
        )

        # Isolated retail price / unrelated tool license noise
        is_unrelated_price = False
        if unit_str in ("usd", "inr", "eur", "gbp", "dollars", "rupees", "$", "€", "₹") and candidate.value is not None:
            retail_noise = ["per t-shirt", "hardcover book", "paperback", "iphone", "laptop price", "t-shirt", "mug", "shoes", "coffee cup", "hoodie"]
            if any(rn in context_str or rn in metric_str for rn in retail_noise):
                is_unrelated_price = True

        # Non-market sizing claims (version numbers, page numbers, ratings, coupon discounts)
        is_non_market_noise = (
            any(w in metric_str for w in ("page number", "version", "release", "rating", "stars", "discount coupon", "chapter", "ranking"))
            or unit_str in self.NOISE_TERMS
            or metric_str in self.NOISE_TERMS
        )

        if is_phone:
            return EvidenceRelevanceScore(
                source_quality_score=source_quality_pct,
                overall_relevance_score=0.0,
                is_accepted=False,
                rejection_reason="Evidence candidate is a phone number or contact helpline.",
                rejection_category="NOISE_CONTACT_INFO",
                dimensional_breakdown={"noise_type": "phone_number"},
            )

        if is_contact_info:
            return EvidenceRelevanceScore(
                source_quality_score=source_quality_pct,
                overall_relevance_score=0.0,
                is_accepted=False,
                rejection_reason="Evidence candidate contains contact information or address metadata rather than market statistics.",
                rejection_category="NOISE_CONTACT_INFO",
                dimensional_breakdown={"noise_type": "contact_info"},
            )

        if is_navigation_text:
            return EvidenceRelevanceScore(
                source_quality_score=source_quality_pct,
                overall_relevance_score=0.0,
                is_accepted=False,
                rejection_reason="Evidence snippet contains navigation, menu, or web boilerplate text.",
                rejection_category="NAVIGATION_TEXT",
                dimensional_breakdown={"noise_type": "navigation_text"},
            )

        if is_unrelated_price:
            return EvidenceRelevanceScore(
                source_quality_score=source_quality_pct,
                overall_relevance_score=10.0,
                market_scope=MarketScopeType.UNRELATED_MARKET.value,
                market_scope_explanation="Unrelated market: Evidence reports an isolated consumer product price unrelated to market size, ARPU, or target offering.",
                is_accepted=False,
                rejection_reason="Evidence reports an isolated consumer product price unrelated to market size, ARPU, or target offering.",
                rejection_category="UNRELATED_PRICE",
                dimensional_breakdown={"noise_type": "retail_price"},
            )

        if is_non_market_noise:
            return EvidenceRelevanceScore(
                source_quality_score=source_quality_pct,
                overall_relevance_score=5.0,
                market_scope=MarketScopeType.UNRELATED_MARKET.value,
                market_scope_explanation="Unrelated market: Evidence does not contain a verifiable market-size, customer count, or financial statistical claim.",
                is_accepted=False,
                rejection_reason="Evidence does not contain a verifiable market-size, customer count, or financial statistical claim.",
                rejection_category="NO_MARKET_SIZING_CLAIM",
                dimensional_breakdown={"noise_type": "non_market_noise"},
            )

        claim_type_score = 100.0

        # -------------------------------------------------------------------
        # Dimension 2: Recency Scoring (0-100)
        # -------------------------------------------------------------------
        if candidate.year is not None:
            if candidate.year >= 2023:
                recency_score = 100.0
                breakdown_notes["recency"] = f"Recent benchmark ({candidate.year})"
            elif candidate.year >= 2020:
                recency_score = 80.0
                breakdown_notes["recency"] = f"Contemporary benchmark ({candidate.year})"
            elif candidate.year >= 2015:
                recency_score = 50.0
                breakdown_notes["recency"] = f"Historical benchmark ({candidate.year})"
            else:
                recency_score = 25.0
                breakdown_notes["recency"] = f"Outdated benchmark ({candidate.year})"
        else:
            recency_score = 60.0
            breakdown_notes["recency"] = "Reference year unstated"

        # -------------------------------------------------------------------
        # Dimension 3: Geography Match Scoring (0-100)
        # -------------------------------------------------------------------
        target_geo = (business_analysis.geography or "").strip().lower() if business_analysis else ""
        if not target_geo or target_geo in ("global", "worldwide", "international"):
            geography_match_score = 90.0
            breakdown_notes["geography"] = "Global / broad geographic target"
        else:
            if target_geo in cand_geo or target_geo in context_str or target_geo in metric_str:
                geography_match_score = 100.0
                breakdown_notes["geography"] = f"Direct match with target geography '{target_geo}'"
            elif any(sub in context_str or sub in cand_geo for sub in ("chennai", "delhi", "bengaluru", "bangalore", "mumbai", "hyderabad", "tamil nadu", "karnataka", "maharashtra")) and target_geo == "india":
                geography_match_score = 100.0
                breakdown_notes["geography"] = f"Regional sub-geography matching '{target_geo}'"
            elif "global" in cand_geo or "worldwide" in cand_geo or "global" in context_str or "worldwide" in context_str:
                geography_match_score = 50.0
                breakdown_notes["geography"] = f"Global proxy benchmark for local target '{target_geo}'"
            elif any(other_geo in (cand_geo or context_str) for other_geo in ("united states", "usa", "uk", "united kingdom", "germany", "france", "brazil", "china", "japan", "australia")) and target_geo not in ("united states", "usa", "uk", "global"):
                geography_match_score = 10.0
                breakdown_notes["geography"] = f"Geographic mismatch: candidate targets foreign market while target is '{target_geo}'"
            else:
                geography_match_score = 70.0
                breakdown_notes["geography"] = f"Neutral geographic alignment with '{target_geo}'"

        # -------------------------------------------------------------------
        # Dimension 4: Industry Sector Match Scoring (0-100)
        # -------------------------------------------------------------------
        target_ind = (business_analysis.industry or "").strip().lower() if business_analysis else ""
        if not target_ind:
            industry_match_score = 80.0
            breakdown_notes["industry"] = "Industry unspecified in business analysis"
        else:
            ind_keywords = [w for w in re.split(r"[\s/,]+", target_ind) if len(w) > 2]
            metric_and_ctx = f"{metric_str} {context_str} {unit_str}"

            unrelated_industries = {
                "automotive": ["vehicle sales", "car dealership", "automobile manufacturer", "electric vehicle battery", "oem powertrain"],
                "mining": ["coal mining", "mineral extraction", "crude petroleum drill", "iron ore extraction"],
                "steel": ["steel production", "crude steel", "blast furnace", "smelting plant"],
                "real estate": ["real estate leasing", "sq ft commercial office", "residential luxury apartment"],
                "agriculture": ["fertilizer consumption", "crop yield per hectare", "wheat harvesting season", "chemical pesticide"],
            }

            matched_unrelated = False
            for un_name, un_keys in unrelated_industries.items():
                if un_name not in target_ind and any(k in metric_and_ctx for k in un_keys):
                    if not any(k in target_ind for k in un_keys):
                        industry_match_score = 0.0
                        breakdown_notes["industry"] = f"Completely unrelated industry sector: {un_name}"
                        matched_unrelated = True
                        break

            if matched_unrelated:
                return EvidenceRelevanceScore(
                    source_quality_score=source_quality_pct,
                    industry_match_score=0.0,
                    geography_match_score=geography_match_score,
                    customer_match_score=0.0,
                    product_match_score=0.0,
                    usefulness_score=0.0,
                    recency_score=recency_score,
                    claim_type_score=claim_type_score,
                    overall_relevance_score=0.0,
                    market_scope=MarketScopeType.UNRELATED_MARKET.value,
                    market_scope_explanation=f"Unrelated market: Evidence belongs to an unrelated industry sector and does not apply to '{business_analysis.industry if business_analysis else 'target'}'.",
                    is_accepted=False,
                    rejection_reason=f"Evidence belongs to an unrelated industry sector and does not apply to '{business_analysis.industry if business_analysis else 'target'}'.",
                    rejection_category="UNRELATED_INDUSTRY",
                    dimensional_breakdown=breakdown_notes,
                )

            match_count = sum(1 for kw in ind_keywords if kw in metric_and_ctx)
            if match_count >= 2 or target_ind in metric_and_ctx:
                industry_match_score = 95.0
                breakdown_notes["industry"] = f"Direct match with target industry '{target_ind}'"
            elif match_count == 1:
                industry_match_score = 75.0
                breakdown_notes["industry"] = f"Related industry sector for '{target_ind}'"
            elif any(w in metric_and_ctx for w in ("market", "industry", "sector", "revenue", "demand", "growth")):
                industry_match_score = 55.0
                breakdown_notes["industry"] = "Broad cross-sector market statistic"
            else:
                industry_match_score = 30.0
                breakdown_notes["industry"] = f"Low industry overlap with '{target_ind}'"

        # -------------------------------------------------------------------
        # Dimension 5: Customer Segment Match Scoring (0-100)
        # -------------------------------------------------------------------
        target_cust = (business_analysis.target_customer or "").strip().lower() if business_analysis else ""
        if not target_cust:
            customer_match_score = 75.0
            breakdown_notes["customer"] = "Target customer unspecified"
        else:
            geo_words = {"india", "us", "usa", "uk", "chennai", "delhi", "mumbai", "bengaluru", "global", "worldwide"}
            cust_segments = [seg.strip() for seg in re.split(r"[/,]+", target_cust) if seg.strip()]
            cust_keywords = [
                w for w in re.split(r"[\s/,]+", target_cust)
                if len(w) > 2 and w not in geo_words and w not in ("and", "the", "for", "with", "target", "customer")
            ]
            metric_and_ctx = f"{metric_str} {context_str} {unit_str}"

            if target_cust in metric_and_ctx or any(seg in metric_and_ctx for seg in cust_segments if len(seg) > 3 and not any(gw == seg for gw in geo_words)):
                customer_match_score = 100.0
                breakdown_notes["customer"] = f"Exact match with target customer segment '{target_cust}'"
            elif any(kw in metric_and_ctx for kw in cust_keywords):
                customer_match_score = 80.0
                breakdown_notes["customer"] = f"Partial match with target persona '{target_cust}'"
            elif any(w in metric_and_ctx for w in ("population", "people", "households", "users", "consumers", "subscribers", "students", "learners", "education", "market")):
                customer_match_score = 45.0
                breakdown_notes["customer"] = f"Broad demographic parent group (broader than '{target_cust}')"
            else:
                customer_match_score = 25.0
                breakdown_notes["customer"] = f"Divergent customer segment (does not reference '{target_cust}')"

        # -------------------------------------------------------------------
        # Dimension 6: Product / Service Specificity Scoring (0-100)
        # -------------------------------------------------------------------
        target_prod = (business_analysis.product or "").strip().lower() if business_analysis else ""
        if not target_prod:
            product_match_score = 75.0
            breakdown_notes["product"] = "Product unspecified"
        else:
            prod_segments = [seg.strip() for seg in re.split(r"[/,]+", target_prod) if seg.strip()]
            specific_prod_keywords = [w for w in re.split(r"[\s/,]+", target_prod) if len(w) > 2 and w not in ("online", "platform", "affordable", "app", "service", "education", "learning", "portal")]
            metric_and_ctx = f"{metric_str} {context_str}"

            is_broad_parent_market = (
                any(w in metric_and_ctx for w in ("total education market", "education market size", "education sector", "entire education"))
                and not any(w in metric_and_ctx for w in ("programming", "coding", "software engineer", "developer", "computer science"))
            )

            if is_broad_parent_market:
                product_match_score = 35.0
                breakdown_notes["product"] = "Broad macro parent market (overly broad for direct product TAM)"
            elif target_prod in metric_and_ctx or any(seg in metric_and_ctx for seg in prod_segments if len(seg) > 5 and any(k in seg for k in specific_prod_keywords)):
                product_match_score = 100.0
                breakdown_notes["product"] = f"Direct match with product offering '{target_prod}'"
            elif specific_prod_keywords and any(kw in metric_and_ctx for kw in specific_prod_keywords):
                product_match_score = 85.0
                breakdown_notes["product"] = f"High category overlap with '{target_prod}'"
            elif any(w in metric_and_ctx for w in ("online", "digital", "e-learning", "edtech", "software", "saas")):
                product_match_score = 65.0
                breakdown_notes["product"] = "Adjacent product / service category"
            elif any(w in metric_and_ctx for w in ("market size", "market revenue", "total market", "industry revenue")):
                product_match_score = 35.0
                breakdown_notes["product"] = "Broad macro parent market (overly broad for direct product TAM)"
            else:
                product_match_score = 25.0
                breakdown_notes["product"] = f"Low product alignment with '{target_prod}'"

        # -------------------------------------------------------------------
        # Dimension 7: TAM/SAM/SOM Market Sizing Usefulness (0-100)
        # -------------------------------------------------------------------
        if candidate.value is not None:
            if unit_str in ("%", "pct", "percent", "percentage"):
                usefulness_score = 90.0
                breakdown_notes["usefulness"] = "Directly applicable as segmentation / market share multiplier"
            elif any(w in metric_str for w in ("market size", "revenue", "valuation", "expenditure", "spend")):
                usefulness_score = 85.0
                breakdown_notes["usefulness"] = "Applicable as top-down market size benchmark"
            elif any(w in unit_str for w in ("student", "user", "developer", "customer", "people", "population", "subscriber", "learner", "enterprise", "household")):
                usefulness_score = 95.0
                breakdown_notes["usefulness"] = "Applicable as bottom-up target population base"
            elif any(w in metric_str for w in ("price", "arpu", "subscription", "fee", "cost", "annual spend")):
                usefulness_score = 90.0
                breakdown_notes["usefulness"] = "Applicable as pricing / ARPU benchmark"
            else:
                usefulness_score = 65.0
                breakdown_notes["usefulness"] = "General quantitative market benchmark"
        elif candidate.is_range_or_approximate:
            usefulness_score = 75.0
            breakdown_notes["usefulness"] = "Applicable as interval/bounded market benchmark"
        else:
            usefulness_score = 30.0
            breakdown_notes["usefulness"] = "Unquantified contextual claim"

        # -------------------------------------------------------------------
        # Composite Weighted Overall Relevance Score (0-100)
        # -------------------------------------------------------------------
        composite = (
            (industry_match_score * 0.20)
            + (product_match_score * 0.20)
            + (geography_match_score * 0.15)
            + (customer_match_score * 0.15)
            + (source_quality_pct * 0.15)
            + (usefulness_score * 0.10)
            + (recency_score * 0.05)
        )
        overall_score = round(min(100.0, max(0.0, composite)), 1)

        is_accepted = True
        rejection_reason = None
        rejection_category = None

        if geography_match_score < 15.0:
            is_accepted = False
            rejection_reason = f"Geographic scope mismatch with target '{target_geo}'."
            rejection_category = "GEOGRAPHY_MISMATCH"
        elif industry_match_score < 20.0:
            is_accepted = False
            rejection_reason = f"Industry sector mismatch with target '{target_ind}'."
            rejection_category = "UNRELATED_INDUSTRY"
        elif overall_score < 35.0:
            is_accepted = False
            rejection_reason = f"Overall relevance score ({overall_score}/100) is below acceptance threshold for market sizing."
            rejection_category = "LOW_RELEVANCE"

        # Deterministically classify evidence market scope
        market_scope, market_scope_explanation = self.classify_market_scope(
            candidate=candidate,
            business_analysis=business_analysis,
            product_match_score=product_match_score,
            customer_match_score=customer_match_score,
            industry_match_score=industry_match_score,
            geography_match_score=geography_match_score,
        )

        return EvidenceRelevanceScore(
            source_quality_score=source_quality_pct,
            industry_match_score=industry_match_score,
            geography_match_score=geography_match_score,
            customer_match_score=customer_match_score,
            product_match_score=product_match_score,
            usefulness_score=usefulness_score,
            recency_score=recency_score,
            claim_type_score=claim_type_score,
            overall_relevance_score=overall_score,
            market_scope=market_scope.value if isinstance(market_scope, MarketScopeType) else market_scope,
            market_scope_explanation=market_scope_explanation,
            is_accepted=is_accepted,
            rejection_reason=rejection_reason,
            rejection_category=rejection_category,
            dimensional_breakdown=breakdown_notes,
        )

    def classify_market_scope(
        self,
        candidate: ExtractedEvidenceCandidate,
        business_analysis: Optional[BusinessAnalysis] = None,
        product_match_score: float = 75.0,
        customer_match_score: float = 75.0,
        industry_match_score: float = 80.0,
        geography_match_score: float = 80.0,
    ) -> Tuple[MarketScopeType, str]:
        """Deterministically classify evidence into 7 market scope categories."""
        metric_str = (candidate.metric or "").lower()
        context_str = (candidate.source_context or "").lower()
        unit_str = (candidate.unit or "").lower()
        full_text = f"{metric_str} {context_str}"

        # 1. Unrelated Market
        if industry_match_score < 20.0:
            return (
                MarketScopeType.UNRELATED_MARKET,
                "Unrelated market: Data point belongs to an out-of-scope industry sector and does not apply to the target business offering.",
            )

        # 2. Adjacent Market (Geography Mismatch)
        if geography_match_score < 25.0:
            return (
                MarketScopeType.ADJACENT_MARKET,
                f"Adjacent market: Candidate data point targets a non-target geography ({candidate.geography or 'foreign'}) rather than the target market.",
            )

        # 3. Parent Market
        is_macro_indicator = any(
            w in full_text
            for w in (
                "total education market", "education market size", "entire education sector", "total healthcare market",
                "overall retail market", "total automotive industry", "total market size", "industry revenue",
                "macro market", "overall sector", "entire sector", "education sector"
            )
        )
        if (is_macro_indicator or product_match_score <= 45.0) and product_match_score < 70.0 and any(w in unit_str for w in ("usd", "inr", "eur", "gbp", "billion", "crore", "million", "dollar", "rupee")):
            val_str = candidate.raw_value_expression or (f"{candidate.value:,.0f} {candidate.unit}" if candidate.value else "")
            return (
                MarketScopeType.PARENT_MARKET,
                f"Parent market: Represents broad aggregate macro industry demand ({val_str}). Must not be directly used as narrow product TAM without segmentation adjustment to avoid parent-market inflation.",
            )

        # 4. Obtainable Market (SOM)
        is_som_indicator = (
            unit_str in ("%", "pct", "percent", "percentage", "share")
            or any(w in metric_str for w in ("som", "obtainable", "capture", "market share", "penetration", "obtainable market", "target share"))
            or (candidate.notes and "som" in candidate.notes.lower())
        )
        if is_som_indicator:
            return (
                MarketScopeType.OBTAINABLE_MARKET,
                "Obtainable market (SOM): Represents the realistic near-term capture rate, market share percentage, or operational capacity attainable by the business.",
            )

        # 5. Serviceable Market (SAM)
        is_sam_indicator = (
            any(w in metric_str for w in ("sam", "serviceable", "target segment", "target population", "serviceable addressable"))
            or (customer_match_score >= 80.0 and product_match_score >= 80.0 and any(w in metric_str for w in ("college students", "undergraduates", "subscribers", "target users", "active learners")))
        )
        if is_sam_indicator:
            return (
                MarketScopeType.SERVICEABLE_MARKET,
                "Serviceable market (SAM): Represents the specific portion of TAM that the business can realistically reach based on customer persona, geography, and distribution channels.",
            )

        # 6. Addressable Market (TAM)
        is_tam_indicator = (
            (product_match_score >= 80.0)
            or any(w in metric_str for w in ("tam", "total addressable", "coding education", "programming platform", "online coding"))
            or (any(w in unit_str for w in ("student", "user", "developer", "customer", "people", "population")) and customer_match_score >= 70.0)
        )
        if is_tam_indicator:
            return (
                MarketScopeType.ADDRESSABLE_MARKET,
                "Addressable market (TAM): Represents the maximum realistic total market demand for the specific product/service offering within the target geography.",
            )

        # 7. Relevant Market / Adjacent Default
        if product_match_score >= 60.0 or industry_match_score >= 70.0:
            return (
                MarketScopeType.RELEVANT_MARKET,
                "Relevant market: Directly relevant industry sub-segment aligned with the target sector.",
            )

        return (
            MarketScopeType.ADJACENT_MARKET,
            "Adjacent market: Related domain category adjacent to the primary target offering.",
        )

    # -----------------------------------------------------------------------
    # 2. Candidate Structural & Integrity Validation
    # -----------------------------------------------------------------------

    def validate_candidate(
        self,
        candidate: ExtractedEvidenceCandidate,
        business_analysis: Optional[BusinessAnalysis] = None,
    ) -> EvidenceValidationResult:
        """Deterministically validate an individual ExtractedEvidenceCandidate against domain rules and business relevance."""
        reasons: List[str] = []
        is_valid = True
        status = EvidenceValidationStatus.VALID
        year_note = None
        geo_note = None

        # Extract domain & evaluate 5-tier source quality
        domain = self._extract_domain(candidate.source_url)
        source_quality_score, source_quality_reasons, source_quality_tier = self.score_source_quality(
            url=candidate.source_url,
            domain=domain,
            source_name=candidate.source_name,
            year=candidate.year,
            context=candidate.source_context,
            raw_val=candidate.raw_value_expression,
        )

        # A. Numerical Integrity
        if candidate.is_range_or_approximate:
            if candidate.range_min is not None and candidate.range_max is not None:
                if candidate.range_min > candidate.range_max:
                    is_valid = False
                    status = EvidenceValidationStatus.INVALID
                    reasons.append(f"Invalid range bounds: range_min ({candidate.range_min}) > range_max ({candidate.range_max}).")
                else:
                    reasons.append("Range bounds preserved without arbitrary point interpolation.")
            elif candidate.range_min is None and candidate.range_max is None and candidate.value is None:
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append("Range/approximate candidate lacks bounds or value.")
        else:
            if candidate.value is None:
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append("Missing required numerical value for discrete candidate.")
            elif math.isnan(candidate.value) or math.isinf(candidate.value):
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append("Numerical value must be a finite number (NaN/Inf rejected).")
            else:
                # Check non-negativity
                if self._metric_must_be_non_negative(candidate.metric) and candidate.value < 0:
                    is_valid = False
                    status = EvidenceValidationStatus.INVALID
                    reasons.append(f"Negative value ({candidate.value}) is invalid for count/market metric '{candidate.metric}'.")

        # B. Unit & Semantic Market Entity Integrity
        if (candidate.value is not None or candidate.range_min is not None or candidate.range_max is not None):
            if not candidate.unit or not candidate.unit.strip():
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append("A unit of measurement is required when numerical metrics are present.")
            else:
                norm_unit = self.normalize_unit(candidate.unit)
                u_lower = candidate.unit.lower().strip()
                m_lower = (candidate.metric or "").lower().strip()

                if norm_unit in self.NOISE_TERMS or u_lower in self.NOISE_TERMS or any(t in m_lower for t in ("bird", "tips", "distributions", "lts", "tired", "open source llm")):
                    is_valid = False
                    status = EvidenceValidationStatus.INVALID
                    reasons.append(f"Unit/Metric '{candidate.unit}' is not a recognized market sizing entity or demographic concept.")
                elif norm_unit not in self.RECOGNIZED_UNITS and u_lower not in self.RECOGNIZED_UNITS:
                    is_valid = False
                    status = EvidenceValidationStatus.INVALID
                    reasons.append(f"Unit '{candidate.unit}' is not a recognized market sizing entity or metric category.")
                else:
                    reasons.append(f"Unit '{candidate.unit}' preserved.")

        # C. Temporal Integrity & Year Consistency
        if candidate.year is not None:
            if candidate.year < 1900 or candidate.year > 2100:
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append(f"Year {candidate.year} is out of realistic calendar bounds (1900-2100).")
            elif candidate.year < 2020:
                year_note = f"Prior baseline data ({candidate.year}): may reflect pre-2020 historical benchmarks."
                reasons.append(f"Historical benchmark year {candidate.year} documented.")
            else:
                year_note = f"Observation year: {candidate.year}"
                reasons.append(f"Explicit reference year {candidate.year} preserved without date hallucination.")

        # D. Geography Integrity & Consistency
        if candidate.geography:
            geo_note = f"Explicit geographic scope: {candidate.geography}"
            reasons.append(f"Explicit geography '{candidate.geography}' preserved without domain-based inference.")

        # E. Source & Context Integrity
        if not candidate.source_url or not candidate.source_url.strip():
            is_valid = False
            status = EvidenceValidationStatus.INVALID
            reasons.append("Source URL must not be empty.")
        else:
            parsed = urlparse(candidate.source_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                is_valid = False
                status = EvidenceValidationStatus.INVALID
                reasons.append(f"Source URL '{candidate.source_url}' is not a valid absolute HTTP/HTTPS address.")

        if not candidate.source_context or not candidate.source_context.strip():
            is_valid = False
            status = EvidenceValidationStatus.INVALID
            reasons.append("Source context snippet must not be empty for evidence traceability.")
        else:
            reasons.append("Direct source context snippet preserved.")

        # Check for Tier 5 unusable source
        if source_quality_tier == SourceQualityTier.TIER_5_UNUSABLE or source_quality_score < 0.25:
            is_valid = False
            status = EvidenceValidationStatus.REJECTED
            reasons.append("Rejection (UNUSABLE_SOURCE): Evidence candidate originates from an unusable Tier 5 source (social media, forum, or unverified claim without methodology).")

        # F. Multi-Dimensional Relevance & Noise Assessment
        relevance_score = self.evaluate_evidence_relevance(
            candidate=candidate,
            business_analysis=business_analysis,
            source_quality_score=source_quality_score,
        )

        if source_quality_tier == SourceQualityTier.TIER_5_UNUSABLE or source_quality_score < 0.25:
            relevance_score.is_accepted = False
            relevance_score.rejection_category = "UNUSABLE_SOURCE"
            relevance_score.rejection_reason = "Evidence candidate originates from an unusable Tier 5 source (social media, forum, or unverified claim without methodology)."

        if not is_valid:
            if status != EvidenceValidationStatus.REJECTED:
                status = EvidenceValidationStatus.INVALID
        elif not relevance_score.is_accepted:
            is_valid = False
            status = EvidenceValidationStatus.REJECTED
            reasons.append(f"Rejection ({relevance_score.rejection_category}): {relevance_score.rejection_reason}")
        else:
            reasons.append(f"Relevance verified (Score: {relevance_score.overall_relevance_score}/100, Scope: {relevance_score.market_scope.value if relevance_score.market_scope else 'Unclassified'}).")

        # Initial confidence for single-source validated candidate
        confidence = self._compute_single_source_confidence(is_valid, source_quality_score, candidate.extraction_confidence)

        # Invariant check: Single source candidate can ONLY be VALIDATED, never VERIFIED
        lifecycle_stage = DiscoveryLifecycleStage.VALIDATED if is_valid else DiscoveryLifecycleStage.EXTRACTED

        provenance = SourceProvenance(
            source_url=candidate.source_url,
            source_name=candidate.source_name,
            domain=domain,
            source_context=candidate.source_context,
            source_quality_score=source_quality_score,
            source_quality_reasons=source_quality_reasons,
            source_quality_tier=source_quality_tier,
            market_scope=relevance_score.market_scope,
            market_scope_explanation=relevance_score.market_scope_explanation,
        )

        # Evaluate transparent evidence suitability across geographic, customer, market, and definition dimensions
        suitability = self.evaluate_evidence_suitability(
            candidate=candidate,
            business_analysis=business_analysis,
            source_quality_tier=source_quality_tier,
        )

        return EvidenceValidationResult(
            candidate_id=candidate.candidate_id,
            metric=candidate.metric,
            metric_type=candidate.metric_type,
            value=candidate.value,
            raw_value_expression=candidate.raw_value_expression,
            unit=candidate.unit,
            geography=candidate.geography,
            year=candidate.year,
            is_range_or_approximate=candidate.is_range_or_approximate,
            range_min=candidate.range_min,
            range_max=candidate.range_max,
            source_name=candidate.source_name,
            source_url=candidate.source_url,
            source_context=candidate.source_context,
            source_quality_score=source_quality_score,
            source_quality_reasons=source_quality_reasons,
            source_quality_tier=source_quality_tier,
            market_scope=relevance_score.market_scope,
            market_scope_explanation=relevance_score.market_scope_explanation,
            extraction_method=candidate.extraction_method,
            extraction_confidence=candidate.extraction_confidence,
            validation_status=status,
            confidence=confidence,
            validation_reasons=reasons,
            duplicate_group_id=None,
            corroborating_source_count=1 if is_valid else 0,
            conflicting_source_count=0,
            corroborating_sources=[provenance] if is_valid else [],
            conflicting_sources=[],
            lifecycle_stage=lifecycle_stage,
            is_valid=is_valid,
            relevance_score=relevance_score.overall_relevance_score,
            relevance_breakdown=relevance_score,
            evidence_suitability=suitability,
            market_definition_compatibility=suitability.definition_compatibility,
            rejection_reason=relevance_score.rejection_reason,
            rejection_category=relevance_score.rejection_category,
            year_consistency_note=year_note,
            geography_consistency_note=geo_note,
            notes=candidate.notes,
        )

    def evaluate_evidence_suitability(
        self,
        candidate: ExtractedEvidenceCandidate,
        business_analysis: Optional[BusinessAnalysis] = None,
        source_quality_tier: Optional[SourceQualityTier] = None,
    ) -> EvidenceSuitability:
        """Transparently evaluate candidate evidence across geographic, customer, market, and definition dimensions."""
        if not business_analysis:
            return EvidenceSuitability(
                overall=SuitabilityRating.MEDIUM,
                geographic_match=True,
                customer_type_match=True,
                product_market_match=True,
                segment_match=True,
                temporal_match=True,
                metric_match=True,
                definition_compatibility=MarketDefinitionCompatibility.DIRECT_MATCH,
                source_quality_tier=source_quality_tier.value if source_quality_tier else None,
                reason="Baseline candidate validation without active business context overlay.",
            )

        target_geo = (business_analysis.target_country or business_analysis.geography or "India").lower()
        cand_geo = (candidate.geography or "").lower()
        metric_lower = (candidate.metric or "").lower()
        context_lower = (candidate.source_context or "").lower()
        url_lower = (candidate.source_url or "").lower()
        full_text = f"{metric_lower} {context_lower} {url_lower}"

        # 1. Geographic Relevance
        if not cand_geo or cand_geo in ("global", "worldwide"):
            geographic_match = target_geo in full_text or any(city in full_text for city in ("chennai", "mumbai", "delhi", "bangalore", "hyderabad", "pune", "india"))
        else:
            geographic_match = (target_geo in cand_geo or cand_geo in target_geo or any(city in cand_geo for city in ("chennai", "mumbai", "delhi", "bangalore", "hyderabad", "pune")))

        # 2. Customer Type Relevance
        target_cust = (str(business_analysis.customer_type.value if hasattr(business_analysis.customer_type, "value") else (business_analysis.customer_type or "Clinics"))).lower()

        is_clinic_target = "clinic" in target_cust or "practice" in target_cust
        is_hospital_target = "hospital" in target_cust
        is_lab_target = any(k in target_cust for k in ("diagnostic", "lab", "pathology"))
        is_pharmacy_target = "pharmacy" in target_cust or "chemist" in target_cust

        if is_clinic_target:
            has_clinic_mention = any(k in full_text for k in ("clinic", "clinics", "outpatient", "private practice", "medical practice", "primary care", "specialty clinic"))
            is_exclusive_hospital = ("hospital" in metric_lower or "hospitals" in metric_lower) and not any(k in metric_lower for k in ("clinic", "practice", "outpatient"))
            customer_type_match = has_clinic_mention and not is_exclusive_hospital
        elif is_hospital_target:
            customer_type_match = any(k in full_text for k in ("hospital", "hospitals", "bed", "beds", "inpatient", "hims", "his"))
        elif is_lab_target:
            customer_type_match = any(k in full_text for k in ("diagnostic", "laboratory", "laboratories", "lab", "labs", "pathology", "pacs", "imaging"))
        elif is_pharmacy_target:
            customer_type_match = any(k in full_text for k in ("pharmacy", "pharmacies", "chemist", "drugstore", "retail pharmacy"))
        else:
            customer_type_match = target_cust in full_text

        # 3. Market Definition Compatibility & Product Market Match
        cat = (str(business_analysis.healthcare_saas_category.value if hasattr(business_analysis.healthcare_saas_category, "value") else (business_analysis.healthcare_saas_category or "Clinic Management SaaS"))).lower()

        is_unrelated = any(k in full_text for k in ("pet care", "meal delivery", "solar", "ev charging", "food delivery", "retail e-commerce", "gaming", "automotive"))
        is_direct_clinic = any(k in full_text for k in ("clinic management", "practice management", "clinic software", "clinic saas", "emr for clinics", "outpatient clinic"))
        is_rcm_related = any(k in full_text for k in ("revenue cycle", "rcm", "medical billing", "billing software", "claims processing"))
        is_parent_market = any(k in full_text for k in ("healthcare it", "healthcare saas", "health tech", "digital health", "healthcare software", "hospital market", "total healthcare"))

        if is_unrelated:
            definition_compatibility = MarketDefinitionCompatibility.UNRELATED
            product_market_match = False
        elif is_direct_clinic or (is_clinic_target and ("clinic" in full_text and "software" in full_text)):
            definition_compatibility = MarketDefinitionCompatibility.DIRECT_MATCH
            product_market_match = True
        elif is_rcm_related or any(k in full_text for k in ("telemedicine", "ehr", "emr", "lis", "lims", "pacs", "workforce", "patient engagement")):
            definition_compatibility = MarketDefinitionCompatibility.RELATED_MARKET
            product_market_match = False
        elif is_parent_market:
            definition_compatibility = MarketDefinitionCompatibility.BROAD_PARENT_MARKET
            product_market_match = False
        else:
            definition_compatibility = MarketDefinitionCompatibility.RELATED_MARKET
            product_market_match = False

        # 4. Segment Relevance (SMB vs Enterprise vs Mixed)
        is_smb_indicator = any(k in full_text for k in ("small", "medium", "smb", "sme", "independent", "single doctor", "solo practitioner", "private practice"))
        is_large_enterprise = any(k in full_text for k in ("enterprise hospital", "500+ beds", "multi-chain", "hospital chain", "tertiary care", "corporate hospital"))
        segment_match = is_smb_indicator or (not is_large_enterprise and customer_type_match)

        # 5. Temporal Relevance
        target_year = business_analysis.preferred_year if hasattr(business_analysis, "preferred_year") and business_analysis.preferred_year else 2025
        cand_year = candidate.year or 2024
        temporal_match = abs(cand_year - target_year) <= 3

        # 6. Metric Match
        unit_str = (candidate.unit or "").lower()
        is_count_operand = any(k in unit_str or k in metric_lower for k in ("clinic", "hospital", "facility", "facilities", "organization", "practice", "center", "doctor", "unit"))
        is_price_operand = any(k in unit_str or k in metric_lower for k in ("inr", "usd", "price", "spend", "cost", "fee", "subscription", "arpu", "/year", "/month"))
        is_macro_operand = any(k in metric_lower for k in ("market", "industry", "revenue", "spending", "tam"))
        metric_match = is_count_operand or is_price_operand or is_macro_operand

        # 7. Overall Composite Rating
        tier_str = source_quality_tier.value if source_quality_tier else "Tier 4: General Web"

        reasons_list: List[str] = []
        if not geographic_match:
            overall = SuitabilityRating.UNSUITABLE
            reasons_list.append(f"Geographic mismatch: candidate refers to non-target geography rather than '{target_geo}'.")
        elif definition_compatibility == MarketDefinitionCompatibility.UNRELATED:
            overall = SuitabilityRating.UNSUITABLE
            reasons_list.append("Unrelated domain: source discusses out-of-scope market rather than Healthcare SaaS.")
        elif definition_compatibility == MarketDefinitionCompatibility.DIRECT_MATCH and customer_type_match:
            overall = SuitabilityRating.HIGH
            reasons_list.append(f"Direct match: Source specifically discusses target {target_cust} and {cat} in {target_geo}.")
        elif definition_compatibility == MarketDefinitionCompatibility.RELATED_MARKET or not customer_type_match:
            if is_rcm_related:
                overall = SuitabilityRating.LOW
                reasons_list.append(f"Related market (Revenue Cycle Management): Combines hospitals and healthcare practices; does not isolate target {target_cust}.")
            elif is_parent_market:
                overall = SuitabilityRating.LOW
                reasons_list.append(f"Broad parent market: Represents aggregate healthcare industry revenue/facilities; risks parent-market inflation if unadjusted.")
            elif customer_type_match:
                overall = SuitabilityRating.MEDIUM
                reasons_list.append(f"Customer match with adjacent healthcare software scope in {target_geo}.")
            else:
                overall = SuitabilityRating.LOW
                reasons_list.append(f"Partial match: Population discusses broader healthcare facilities rather than isolated {target_cust}.")
        else:
            overall = SuitabilityRating.MEDIUM
            reasons_list.append("General healthcare market evidence with moderate alignment.")

        if not temporal_match:
            reasons_list.append(f"Temporal caveat: Source reference year ({cand_year}) deviates >3 years from target ({target_year}).")

        reason_str = " ".join(reasons_list)

        return EvidenceSuitability(
            overall=overall,
            geographic_match=geographic_match,
            customer_type_match=customer_type_match,
            product_market_match=product_market_match,
            segment_match=segment_match,
            temporal_match=temporal_match,
            metric_match=metric_match,
            definition_compatibility=definition_compatibility,
            source_quality_tier=tier_str,
            reason=reason_str,
        )


    # -----------------------------------------------------------------------
    # 2. Source Quality Scoring (5-Tier Hierarchy)
    # -----------------------------------------------------------------------

    def score_source_quality(
        self,
        url: str,
        domain: Optional[str] = None,
        source_name: Optional[str] = None,
        year: Optional[int] = None,
        context: Optional[str] = None,
        raw_val: Optional[str] = None,
    ) -> Tuple[float, List[str], SourceQualityTier]:
        """Calculate a transparent deterministic source quality score (0.0 to 1.0) and assign 5-tier authority ranking."""
        reasons: List[str] = []
        dom = (domain or self._extract_domain(url)).lower()
        url_lower = (url or "").lower()
        src_lower = (source_name or "").lower()
        ctx_lower = (context or "").lower()

        is_filing_signal = (
            any(k in dom for k in self.REGULATORY_AND_FILINGS)
            or dom.startswith("investor.")
            or dom.startswith("ir.")
            or dom.startswith("investors.")
            or "annual-report" in url_lower
            or "investor-relations" in url_lower
            or "10-k" in url_lower
            or "10-q" in url_lower
            or any(k in src_lower for k in ("annual report", "investor presentation", "sec form", "10-k", "10-q", "statutory filing"))
        )

        is_unusable_signal = (
            any(u in dom for u in self.UNUSABLE_DOMAINS_AND_FORUMS)
            or "reddit.com" in url_lower
            or "quora.com" in url_lower
            or "twitter.com" in url_lower
            or "x.com" in url_lower
            or ("/posts/" in url_lower and "linkedin.com" in dom)
            or "/r/" in url_lower
            or "/forum/" in url_lower
            or "/thread/" in url_lower
            or "yahoo.com/answers" in url_lower
        )

        if is_unusable_signal:
            base_score = 0.10
            tier = SourceQualityTier.TIER_5_UNUSABLE
            reasons.append("Tier 5: Unusable source (social media post, discussion forum, or unverified user comment).")
        elif is_filing_signal:
            base_score = 0.92
            tier = SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
            reasons.append("Tier 1: Official corporate annual report, SEC/regulatory filing, or audited investor disclosure.")
        elif any(dom.endswith(g) or g in dom for g in self.GOVERNMENT_DOMAINS):
            base_score = 0.95
            tier = SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
            reasons.append("Tier 1: Official government or national statistics agency domain.")
        elif any(dom.endswith(org) or org in dom for org in self.INTL_ORGANIZATIONS):
            base_score = 0.90
            tier = SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
            reasons.append("Tier 1: Recognized international public statistical organization.")
        elif any(dom.endswith(ind) or ind in dom for ind in self.INDUSTRY_ASSOCIATIONS) or "trade association" in src_lower:
            base_score = 0.88
            tier = SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
            reasons.append("Tier 1: Official industry trade association.")
        elif any(pat in dom for pat in self.ACADEMIC_PATTERNS) or "university" in dom or "institute" in dom:
            base_score = 0.85
            tier = SourceQualityTier.TIER_2_ACADEMIC_TRADE
            reasons.append("Tier 2: Academic institution or peer-reviewed research repository.")
        elif any(dom.endswith(rf) or rf in dom for rf in self.RESEARCH_FIRMS):
            base_score = 0.82
            tier = SourceQualityTier.TIER_2_ACADEMIC_TRADE
            reasons.append("Tier 2: Established professional market research organization.")
        elif any(dom.endswith(cf) or cf in dom for cf in self.CONSULTING_FIRMS):
            base_score = 0.80
            tier = SourceQualityTier.TIER_2_ACADEMIC_TRADE
            reasons.append("Tier 2: Recognized top-tier management consulting firm.")
        elif any(dom.endswith(fi) or fi in dom for fi in self.FINANCIAL_INSTITUTIONS):
            base_score = 0.78
            tier = SourceQualityTier.TIER_2_ACADEMIC_TRADE
            reasons.append("Tier 2: Major financial institution equity / market research.")
        elif any(dom.endswith(nw) or nw in dom for nw in self.REPUTABLE_NEWS):
            base_score = 0.65
            tier = SourceQualityTier.TIER_3_ANALYST_PRESS
            reasons.append("Tier 3: Reputable mainstream business/financial news reporting.")
        elif any(bp in dom for bp in self.WEAK_BLOG_PATTERNS):
            base_score = 0.35
            tier = SourceQualityTier.TIER_4_GENERAL_UNVERIFIED
            reasons.append("Tier 4: Generic blog, content farm, or self-published web article.")
        else:
            base_score = 0.35
            tier = SourceQualityTier.TIER_4_GENERAL_UNVERIFIED
            reasons.append("Tier 4: General secondary web publication / unverified article.")

        # Bonus and penalty factors
        score = base_score

        # Methodology transparency bonus (+0.05)
        methodology_keywords = (
            "methodology", "sample size", "survey of", "n=", "margin of error",
            "audited", "annual report", "10-k", "10-q", "statutory filing",
            "respondents", "census", "peer-reviewed", "primary research", "sampling technique",
        )
        if any(mk in ctx_lower for mk in methodology_keywords):
            score += 0.05
            reasons.append("Methodology transparency bonus (+0.05): explicit survey/sampling/filing methodology documented.")

        # Unsourced / speculative rumor penalty (-0.15)
        rumor_keywords = (
            "rumor", "allegedly", "unconfirmed report", "some claim", "without evidence",
            "unverified rumor", "speculated that", "it is rumored", "unsubstantiated",
        )
        if any(rk in ctx_lower for rk in rumor_keywords):
            score -= 0.15
            reasons.append("Unsubstantiated claim penalty (-0.15): speculative/unverified phrasing detected.")

        # Recency bonus/penalty
        if year is not None:
            if year >= 2023:
                score += 0.03
                reasons.append("Recency bonus (+0.03): recent benchmark (>=2023).")
            elif year < 2018:
                score -= 0.05
                reasons.append("Stale benchmark penalty (-0.05): historical reference year (<2018).")
            else:
                score += 0.01
                reasons.append("Explicit reference year documented.")

        # Identifiable authoring organization
        if source_name and source_name.strip():
            score += 0.02
            reasons.append("Explicit authoring organization identified (+0.02).")

        # Verbatim numeric expression verified in context
        if context and raw_val and raw_val.lower() in ctx_lower:
            score += 0.03
            reasons.append("Verbatim numeric expression verified in source context (+0.03).")

        # Bounds enforcement
        if tier == SourceQualityTier.TIER_5_UNUSABLE:
            final_score = round(min(0.25, max(0.0, score)), 2)
        else:
            final_score = round(min(1.0, max(0.0, score)), 2)

        return final_score, reasons, tier

    # -----------------------------------------------------------------------
    # 3. Normalization & Deduplication
    # -----------------------------------------------------------------------

    def normalize_metric(self, metric: str) -> str:
        """Normalize metric names for comparison (lowercase, strip noise prefixes/suffixes)."""
        if not metric:
            return ""
        norm = metric.lower().strip()
        # Strip common redundant prefix noise
        norm = re.sub(r"^(total\s+|estimated\s+|approximate\s+|number\s+of\s+|count\s+of\s+)", "", norm)
        # Normalize whitespace and punctuation
        norm = re.sub(r"[\-_/\s]+", " ", norm).strip()
        return norm

    def normalize_unit(self, unit: Optional[str]) -> str:
        """Normalize units for comparison (e.g. students -> student, USD -> usd)."""
        if not unit:
            return ""
        norm = unit.lower().strip()
        # Currency aliases
        if norm in ("$", "dollar", "dollars", "usd"):
            return "usd"
        if norm in ("rs", "rs.", "rupee", "rupees", "inr"):
            return "inr"
        if norm in ("€", "euro", "euros", "eur"):
            return "eur"
        if norm in ("%", "pct", "percent", "percentage"):
            return "%"
        # Plural to singular normalization
        if norm.endswith("s") and len(norm) > 3 and not norm.endswith("ss"):
            return norm[:-1]
        return norm

    def normalize_geography(self, geography: Optional[str]) -> str:
        """Normalize geography string."""
        if not geography:
            return ""
        return geography.lower().strip()

    def deduplicate_candidates(
        self, candidates: List[ExtractedEvidenceCandidate]
    ) -> List[DeduplicationGroup]:
        """Group candidates that refer to substantially the same metric, unit, geography, year, and normalized value."""
        groups_map: Dict[str, DeduplicationGroup] = {}

        for cand in candidates:
            norm_metric = self.normalize_metric(cand.metric)
            norm_unit = self.normalize_unit(cand.unit)
            norm_geo = self.normalize_geography(cand.geography)
            norm_mtype = cand.metric_type.value if hasattr(cand.metric_type, "value") else str(cand.metric_type or "")
            norm_val = round(cand.value, 4) if cand.value is not None else None
            norm_min = round(cand.range_min, 4) if cand.range_min is not None else None
            norm_max = round(cand.range_max, 4) if cand.range_max is not None else None

            # Deduplication key strictly binds metric, metric_type, unit, geography, year, and value
            group_key = f"{norm_metric}|{norm_mtype}|{norm_geo}|{cand.year}|{norm_unit}|{norm_val}|{norm_min}|{norm_max}"

            if group_key not in groups_map:
                # Deterministic stable group ID
                group_id = hashlib.md5(group_key.encode("utf-8")).hexdigest()[:12]
                groups_map[group_key] = DeduplicationGroup(
                    group_id=f"dup_{group_id}",
                    canonical_metric=cand.metric,
                    canonical_value=cand.value,
                    canonical_unit=cand.unit,
                    canonical_geography=cand.geography,
                    canonical_year=cand.year,
                    candidates=[cand],
                    source_urls=[cand.source_url],
                    distinct_domains=[self._extract_domain(cand.source_url)],
                    distinct_source_count=1,
                )
            else:
                group = groups_map[group_key]
                group.candidates.append(cand)
                group.source_urls.append(cand.source_url)
                cand_domain = self._extract_domain(cand.source_url)
                if cand_domain not in group.distinct_domains:
                    group.distinct_domains.append(cand_domain)
                group.distinct_source_count = len(group.distinct_domains)

        return list(groups_map.values())

    # -----------------------------------------------------------------------
    # 4. Conflict Detection
    # -----------------------------------------------------------------------

    def detect_conflicts(
        self, deduplication_groups: List[DeduplicationGroup]
    ) -> List[ConflictGroup]:
        """Detect conflicts when candidates refer to the same metric, geography, and year,

        but report materially different values.
        """
        # Cluster groups by subject entity: (norm_metric, norm_mtype, norm_geo, year, norm_unit, scale_bucket)
        subject_map: Dict[str, List[DeduplicationGroup]] = {}

        for group in deduplication_groups:
            first_c = group.candidates[0] if group.candidates else None
            norm_mtype = (first_c.metric_type.value if hasattr(first_c.metric_type, "value") else str(first_c.metric_type or "")) if first_c else ""
            norm_metric = self.normalize_metric(group.canonical_metric)
            norm_geo = self.normalize_geography(group.canonical_geography)
            norm_unit = self.normalize_unit(group.canonical_unit)
            
            # Scale bucket prevents unit-level spend ($29.5) from conflicting with macro market ($14.8B)
            eff_v = group.canonical_value if group.canonical_value is not None else (group.candidates[0].range_min if group.candidates else None)
            scale_bucket = "macro" if (eff_v is not None and eff_v >= 1_000_000.0) else "micro"
            
            subject_key = f"{norm_metric}|{norm_mtype}|{norm_geo}|{group.canonical_year}|{norm_unit}|{scale_bucket}"
            subject_map.setdefault(subject_key, []).append(group)

        conflict_groups: List[ConflictGroup] = []

        for subject_key, groups in subject_map.items():
            if len(groups) > 1:
                # More than one distinct value reported for this subject
                all_candidates: List[ExtractedEvidenceCandidate] = []
                distinct_values: List[float] = []

                for g in groups:
                    all_candidates.extend(g.candidates)
                    if g.canonical_value is not None and g.canonical_value not in distinct_values:
                        distinct_values.append(g.canonical_value)

                # Check if values are materially different (e.g. not identical floating point)
                if len(distinct_values) > 1:
                    first_cand = all_candidates[0]
                    conflict_id = hashlib.md5(f"conflict_{subject_key}".encode("utf-8")).hexdigest()[:12]
                    conflict_groups.append(
                        ConflictGroup(
                            conflict_id=f"cnf_{conflict_id}",
                            metric=first_cand.metric,
                            geography=first_cand.geography,
                            year=first_cand.year,
                            unit=first_cand.unit,
                            conflicting_values=distinct_values,
                            candidates=all_candidates,
                            reason="Conflicting values reported by independent sources for the same metric, geography, and year.",
                        )
                    )

        return conflict_groups

    # -----------------------------------------------------------------------
    # 5. Multi-Source Triangulation
    # -----------------------------------------------------------------------

    def triangulate_evidence(
        self,
        candidates: List[ExtractedEvidenceCandidate],
        business_analysis: Optional[BusinessAnalysis] = None,
    ) -> TriangulationResult:
        """Execute full deterministic multi-source triangulation pipeline on a list of candidates.

        1. Validates each candidate structurally and against multi-dimensional business relevance.
        2. Segregates and preserves rejected evidence with audit reasons and scores.
        3. Deduplicates matching candidate claims into groups.
        4. Identifies independent domains supporting each claim.
        5. Detects syndicated copies and prevents syndication inflation.
        6. Detects conflicting claims across independent sources.
        7. Elevates items with >=2 independent domain corroborations and Tier 1-3 backing to VERIFIED.
        """
        if not candidates:
            return TriangulationResult(
                total_candidates_processed=0,
                validated_items=[],
                verified_items=[],
                duplicate_groups=[],
                conflict_groups=[],
                rejected_items=[],
                lifecycle_stage=DiscoveryLifecycleStage.VALIDATED,
                message="No candidate evidence items provided for triangulation.",
            )

        # 1. Structural & Relevance validation of each candidate
        validated_candidates: List[ExtractedEvidenceCandidate] = []
        validation_results_map: Dict[str, EvidenceValidationResult] = {}
        rejected_items: List[EvidenceValidationResult] = []

        for cand in candidates:
            res = self.validate_candidate(cand, business_analysis=business_analysis)
            validation_results_map[cand.candidate_id] = res
            if res.is_valid and res.validation_status == EvidenceValidationStatus.VALID:
                validated_candidates.append(cand)
            else:
                rejected_items.append(res)

        # 2. Deduplication into matching groups
        dup_groups = self.deduplicate_candidates(validated_candidates)

        # 3. Detect conflicts between groups
        conflict_groups = self.detect_conflicts(dup_groups)
        conflict_map: Dict[str, List[ConflictGroup]] = {}
        for cg in conflict_groups:
            norm_key = f"{self.normalize_metric(cg.metric)}|{self.normalize_geography(cg.geography)}|{cg.year}|{self.normalize_unit(cg.unit)}"
            conflict_map.setdefault(norm_key, []).append(cg)

        # 4. Form final validation and verified items
        all_validated_items: List[EvidenceValidationResult] = []
        all_verified_items: List[EvidenceValidationResult] = []

        for group in dup_groups:
            # Determine corroboration count: distinct domain hostnames
            distinct_domains = group.distinct_domains
            corroborating_count = len(distinct_domains)

            # Check if this group is in conflict
            norm_key = f"{self.normalize_metric(group.canonical_metric)}|{self.normalize_geography(group.canonical_geography)}|{group.canonical_year}|{self.normalize_unit(group.canonical_unit)}"
            has_conflict = norm_key in conflict_map

            # Build list of corroborating source provenances & check tiers
            corroborating_sources: List[SourceProvenance] = []
            seen_urls: Set[str] = set()
            max_quality_score = 0.0
            tiers_in_group: Set[SourceQualityTier] = set()
            snippets_seen: Set[str] = set()
            is_syndicated = False

            for cand in group.candidates:
                val_res = validation_results_map[cand.candidate_id]
                if cand.source_context:
                    clean_ctx = re.sub(r"\s+", " ", cand.source_context.strip().lower())
                    if len(clean_ctx) > 30:
                        if clean_ctx in snippets_seen:
                            is_syndicated = True
                        snippets_seen.add(clean_ctx)

                if cand.source_url not in seen_urls:
                    seen_urls.add(cand.source_url)
                    max_quality_score = max(max_quality_score, val_res.source_quality_score)
                    if val_res.source_quality_tier:
                        tiers_in_group.add(val_res.source_quality_tier)
                    corroborating_sources.append(
                        SourceProvenance(
                            source_url=cand.source_url,
                            source_name=cand.source_name,
                            domain=self._extract_domain(cand.source_url),
                            source_context=cand.source_context,
                            source_quality_score=val_res.source_quality_score,
                            source_quality_reasons=val_res.source_quality_reasons,
                            source_quality_tier=val_res.source_quality_tier,
                        )
                    )

            # Build list of conflicting sources if any
            conflicting_sources: List[ConflictSource] = []
            if has_conflict:
                for c_group in conflict_map[norm_key]:
                    for c_cand in c_group.candidates:
                        if c_cand.candidate_id not in [c.candidate_id for c in group.candidates]:
                            val_res = validation_results_map.get(c_cand.candidate_id)
                            q_score = val_res.source_quality_score if val_res else 0.0
                            q_tier = val_res.source_quality_tier if val_res else None
                            conflicting_sources.append(
                                ConflictSource(
                                    candidate_id=c_cand.candidate_id,
                                    value=c_cand.value,
                                    raw_value_expression=c_cand.raw_value_expression,
                                    unit=c_cand.unit,
                                    source_name=c_cand.source_name,
                                    source_url=c_cand.source_url,
                                    source_context=c_cand.source_context,
                                    source_quality_score=q_score,
                                    source_quality_tier=q_tier,
                                    )
                            )

            # Determine final status, lifecycle stage, and confidence for the group
            primary_cand = group.candidates[0]
            primary_res = validation_results_map[primary_cand.candidate_id]
            reasons = list(primary_res.validation_reasons)

            has_authoritative_tier = any(
                t in tiers_in_group for t in (
                    SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL,
                    SourceQualityTier.TIER_2_ACADEMIC_TRADE,
                    SourceQualityTier.TIER_3_ANALYST_PRESS,
                )
            )

            if is_syndicated:
                reasons.append("Detected syndicated/republished article copy across multiple URLs.")

            if has_conflict:
                final_status = EvidenceValidationStatus.CONFLICT
                final_lifecycle = DiscoveryLifecycleStage.VALIDATED
                reasons.append("Conflicting values reported by independent sources for the same metric, geography, and year.")
                confidence = EvidenceConfidence.MEDIUM if max_quality_score >= 0.70 else EvidenceConfidence.LOW
            elif corroborating_count >= 2:
                if has_authoritative_tier:
                    final_status = EvidenceValidationStatus.VALID
                    final_lifecycle = DiscoveryLifecycleStage.VERIFIED
                    reasons.append(f"Corroborated by {corroborating_count} independent source domains with authoritative backing.")
                    if max_quality_score >= 0.85 and corroborating_count >= 2:
                        confidence = EvidenceConfidence.VERY_HIGH
                    else:
                        confidence = EvidenceConfidence.HIGH
                else:
                    final_status = EvidenceValidationStatus.VALID
                    final_lifecycle = DiscoveryLifecycleStage.VALIDATED
                    reasons.append(f"Corroborated by {corroborating_count} Tier 4 general web sources (authoritative Tier 1-3 required for full verification).")
                    confidence = EvidenceConfidence.MEDIUM
            else:
                final_status = EvidenceValidationStatus.VALID
                final_lifecycle = DiscoveryLifecycleStage.VALIDATED
                reasons.append("Single source domain evidence (requires independent corroboration for verification).")
                confidence = EvidenceConfidence.MEDIUM if max_quality_score >= 0.70 else EvidenceConfidence.LOW

            item_result = EvidenceValidationResult(
                candidate_id=primary_cand.candidate_id,
                metric=group.canonical_metric,
                value=group.canonical_value,
                raw_value_expression=primary_cand.raw_value_expression,
                unit=group.canonical_unit,
                geography=group.canonical_geography,
                year=group.canonical_year,
                is_range_or_approximate=primary_cand.is_range_or_approximate,
                range_min=primary_cand.range_min,
                range_max=primary_cand.range_max,
                source_name=primary_cand.source_name,
                source_url=primary_cand.source_url,
                source_context=primary_cand.source_context,
                source_quality_score=max_quality_score,
                source_quality_reasons=primary_res.source_quality_reasons,
                source_quality_tier=primary_res.source_quality_tier,
                market_scope=primary_res.market_scope,
                market_scope_explanation=primary_res.market_scope_explanation,
                extraction_method=primary_cand.extraction_method,
                extraction_confidence=primary_cand.extraction_confidence,
                validation_status=final_status,
                confidence=confidence,
                validation_reasons=reasons,
                duplicate_group_id=group.group_id if len(group.candidates) > 1 else None,
                corroborating_source_count=corroborating_count,
                conflicting_source_count=len(conflicting_sources),
                corroborating_sources=corroborating_sources,
                conflicting_sources=conflicting_sources,
                lifecycle_stage=final_lifecycle,
                is_valid=True,
                is_syndicated_copy=is_syndicated,
                relevance_score=primary_res.relevance_score,
                relevance_breakdown=primary_res.relevance_breakdown,
                rejection_reason=primary_res.rejection_reason,
                rejection_category=primary_res.rejection_category,
                year_consistency_note=primary_res.year_consistency_note,
                geography_consistency_note=primary_res.geography_consistency_note,
                notes=primary_cand.notes,
            )

            all_validated_items.append(item_result)
            if final_lifecycle == DiscoveryLifecycleStage.VERIFIED:
                all_verified_items.append(item_result)

        # Include invalid and rejected candidate results in all_validated_items for backwards compatibility and auditability
        for rej in rejected_items:
            all_validated_items.append(rej)

        summary_msg = (
            f"Triangulated {len(candidates)} candidates: "
            f"{len(all_verified_items)} verified, {len(dup_groups)} unique claim groups, "
            f"{len(rejected_items)} rejected, {len(conflict_groups)} conflicts detected."
        )

        overall_stage = (
            DiscoveryLifecycleStage.VERIFIED
            if len(all_verified_items) > 0 and len(conflict_groups) == 0
            else DiscoveryLifecycleStage.VALIDATED
        )

        return TriangulationResult(
            total_candidates_processed=len(candidates),
            validated_items=all_validated_items,
            verified_items=all_verified_items,
            duplicate_groups=dup_groups,
            conflict_groups=conflict_groups,
            rejected_items=rejected_items,
            lifecycle_stage=overall_stage,
            message=summary_msg,
        )


    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _extract_domain(self, url: str) -> str:
        """Extract normalized domain hostname from a URL."""
        if not url:
            return ""
        parsed = urlparse(url)
        return (parsed.netloc or "").lower()

    def _metric_must_be_non_negative(self, metric: str) -> bool:
        """Check whether the metric logically represents a non-negative quantity."""
        if not metric:
            return False
        m_lower = metric.lower()
        return any(concept in m_lower for concept in self.NON_NEGATIVE_CONCEPTS)

    def _compute_single_source_confidence(
        self, is_valid: bool, quality_score: float, extraction_confidence: Optional[str]
    ) -> EvidenceConfidence:
        """Compute confidence for an un-corroborated single candidate."""
        if not is_valid:
            return EvidenceConfidence.LOW
        if quality_score >= 0.70:
            return EvidenceConfidence.MEDIUM
        return EvidenceConfidence.LOW

    def evaluate_overall_evidence_quality(
        self,
        items: List[EvidenceValidationResult],
        has_conflicts: bool = False,
    ) -> Tuple[str, List[str]]:
        """Determine overall Evidence Quality rating (HIGH, MEDIUM, LOW, INSUFFICIENT)."""
        if not items:
            return "INSUFFICIENT", ["No validated market evidence available."]

        reasons: List[str] = []
        valid_items = [i for i in items if i.is_valid]
        if not valid_items:
            return "INSUFFICIENT", ["All candidate evidence items were invalid or rejected."]

        tier_1_count = sum(
            1 for i in valid_items
            if i.source_quality_tier in (SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL, "Tier 1: Government & Official Statistics")
        )
        tier_2_count = sum(
            1 for i in valid_items
            if i.source_quality_tier in (SourceQualityTier.TIER_2_ACADEMIC_TRADE, "Tier 2: Academic & Industry Trade Associations")
        )
        tier_3_count = sum(
            1 for i in valid_items
            if i.source_quality_tier in (SourceQualityTier.TIER_3_ANALYST_PRESS, "Tier 3: Market Analysts & Financial Press")
        )
        verified_count = sum(
            1 for i in valid_items
            if i.lifecycle_stage in ("verified", DiscoveryLifecycleStage.VERIFIED)
        )

        if has_conflicts:
            reasons.append("Evidence pool contains active factual contradictions across sources.")
            return "LOW", reasons

        if tier_1_count >= 1 and verified_count >= 1:
            reasons.append("Includes Tier 1 official government/statistics sources with multi-domain corroboration.")
            return "HIGH", reasons

        if (tier_1_count >= 1 or tier_2_count >= 1) and len(valid_items) >= 2:
            reasons.append("Includes authoritative Tier 1/2 sources across key market operands.")
            return "HIGH" if verified_count >= 1 else "MEDIUM", reasons

        if tier_3_count >= 1 or len(valid_items) >= 2:
            reasons.append("Evidence is supported by established industry research firms / financial press.")
            return "MEDIUM", reasons

        reasons.append("Evidence is limited to single or unverified secondary web sources.")
        return "LOW", reasons



_validation_service_instance: Optional[EvidenceValidationService] = None


def get_validation_service() -> EvidenceValidationService:
    """Dependency provider returning singleton EvidenceValidationService."""
    global _validation_service_instance
    if _validation_service_instance is None:
        _validation_service_instance = EvidenceValidationService()
    return _validation_service_instance
