import logging
import re
from typing import List, Optional, Tuple

from app.fetching.models import FetchedSource
from app.schemas.business import CompetitorInfo
from app.schemas.discovery import DiscoveryLifecycleStage
from app.schemas.evidence import ConfidenceLevel
from app.schemas.extraction import (
    ExtractedEvidenceCandidate,
    ExtractionMethod,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionStatus,
    MarketMetricType,
)

logger = logging.getLogger(__name__)

MULTIPLIERS = {
    "thousand": 1_000.0,
    "k": 1_000.0,
    "lakh": 100_000.0,
    "lac": 100_000.0,
    "lakhs": 100_000.0,
    "crore": 10_000_000.0,
    "cr": 10_000_000.0,
    "crores": 10_000_000.0,
    "million": 1_000_000.0,
    "mn": 1_000_000.0,
    "m": 1_000_000.0,
    "millions": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
    "b": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "trillion": 1_000_000_000_000.0,
    "tn": 1_000_000_000_000.0,
    "trillions": 1_000_000_000_000.0,
}

KNOWN_GEOGRAPHIES = [
    "India",
    "Chennai",
    "Bengaluru",
    "Bangalore",
    "Mumbai",
    "Delhi",
    "Hyderabad",
    "Pune",
    "Kolkata",
    "Ahmedabad",
    "Tamil Nadu",
    "Karnataka",
    "Maharashtra",
    "Kerala",
    "Gujarat",
    "Telangana",
    "Andhra Pradesh",
    "West Bengal",
    "Uttar Pradesh",
    "Punjab",
    "Rajasthan",
    "Haryana",
    "Madhya Pradesh",
    "Odisha",
    "Bihar",
    "Goa",
    "United States",
    "US",
    "USA",
    "North America",
    "Europe",
    "Asia",
    "Southeast Asia",
    "United Kingdom",
    "UK",
    "Germany",
    "Japan",
    "China",
    "Indonesia",
    "Thailand",
    "Brazil",
    "France",
    "Canada",
    "Australia",
    "Italy",
    "Spain",
    "Global",
    "Worldwide",
]

APPROX_QUALIFIERS = [
    "more than",
    "over",
    "greater than",
    "at least",
    "approximately",
    "around",
    "nearly",
    "up to",
    "about",
    "estimated",
]

# Strict taxonomy of recognized market demographic/population entities, institutions, and units
RECOGNIZED_MARKET_ENTITIES = {
    # Persons & Demographic Target Segments
    "student", "students", "undergraduate", "undergraduates", "postgraduate", "postgraduates",
    "learner", "learners", "user", "users", "subscriber", "subscribers",
    "developer", "developers", "programmer", "programmers", "coder", "coders", "engineer", "engineers",
    "professional", "professionals", "customer", "customers", "buyer", "buyers",
    "people", "population", "individual", "individuals", "person", "persons",
    "worker", "workers", "employee", "employees", "adult", "adults", "youth",
    "child", "children", "teen", "teens", "teenager", "teenagers",
    "patient", "patients", "citizen", "citizens", "consumer", "consumers",
    "graduate", "graduates", "teacher", "teachers",
    "educator", "educators", "instructor", "instructors", "tutor", "tutors",
    "reader", "readers", "member", "members", "client", "clients", "account", "accounts",
    "creator", "creators", "freelancer", "freelancers", "founder", "founders",

    # Healthcare Clinical & Professional Demographics
    "doctor", "doctors", "physician", "physicians", "clinician", "clinicians",
    "dentist", "dentists", "radiologist", "radiologists", "pathologist", "pathologists",
    "pharmacist", "pharmacists", "nurse", "nurses", "practitioner", "practitioners",
    "surgeon", "surgeons", "therapist", "therapists", "specialist", "specialists",

    # Institutional & Business Target Entities
    "enterprise", "enterprises", "company", "companies", "business", "businesses",
    "startup", "startups", "firm", "firms", "institution", "institutions",
    "school", "schools", "college", "colleges", "university", "universities",
    "household", "households", "organization", "organizations", "hospital", "hospitals",
    "clinic", "clinics", "pharmacy", "pharmacies", "laboratory", "laboratories",
    "lab", "labs", "polyclinic", "polyclinics", "practice", "practices",
    "nursing home", "nursing homes", "merchant", "merchants", "vendor", "vendors",
    "smb", "smbs", "sme", "smes", "msme", "msmes",
    "store", "stores", "shop", "shops", "hub", "hubs", "branch", "branches", "site", "sites",
    "bed", "beds", "facility", "facilities",

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
    "trillion", "trillions", "%", "pct", "percent", "percentage"
}

# Strict blacklist of listicle headings, tech specs, versions, time units, and non-market noise
NOISE_REJECTION_TERMS = {
    # Listicle & Article Noise (Generic & Category-Agnostic)
    "tip", "tips", "trick", "tricks", "way", "ways", "reason", "reasons",
    "factor", "factors", "driver", "drivers", "pillar", "pillars", "trend", "trends",
    "challenge", "challenges", "prediction", "predictions", "stat", "stats", "statistic", "statistics",
    "lesson", "lessons", "takeaway", "takeaways", "point", "points", "insight", "insights",
    "step", "steps", "idea", "ideas", "example", "examples", "thing", "things",
    "tool", "tools", "feature", "features", "item", "items", "plugin", "plugins",
    "distribution", "distributions", "distro", "distros", "framework", "frameworks",
    "library", "libraries", "package", "packages", "model", "models", "llm", "llms",
    "article", "articles", "post", "posts", "question", "questions", "faq", "faqs",
    "rule", "rules", "habit", "habits", "fact", "facts", "myth", "myths",
    "benefit", "benefits", "alternative", "alternatives", "finding", "findings",
    "option", "options", "method", "methods", "technique", "techniques",
    "strategy", "strategies", "ranking", "rankings", "list", "lists", "overview",
    "hack", "hacks", "shortcut", "shortcuts", "secret", "secrets",

    # Software Versions & Hardware/Tech Specifications
    "lts", "version", "v", "beta", "alpha", "rc", "release", "patch", "build",
    "ghz", "mhz", "gb", "mb", "kb", "tb", "byte", "bytes", "core", "cores",
    "thread", "threads", "bit", "bits", "fps", "dpi", "px", "watt", "watts",
    "volt", "volts", "hz", "khz", "ms", "ping", "ram", "cpu", "gpu", "vram",

    # Temporal Durations (when parsed as unit rather than market entity)
    "second", "seconds", "sec", "secs", "minute", "minutes", "min", "mins",
    "hour", "hours", "hr", "hrs", "day", "days", "week", "weeks", "month", "months",

    # Non-Market Entities (Flora/Fauna/Astronomical)
    "bird", "birds", "animal", "animals", "plant", "plants", "tree", "trees",
    "species", "planet", "planets", "star", "stars", "stone", "stones",

    # Bare Adjectives & Syntactic Noise
    "tired", "simple", "best", "top", "great", "awesome", "easy", "fast",
    "quick", "outstanding", "open", "free", "new", "latest", "good", "bad",
    "more", "less", "metric", "metrics", "number", "numbers", "total", "totals",
    "jump", "jump from", "to", "from", "rise", "rose", "drop", "fell", "grown",
    "increased from", "grew from", "rose from", "scaled from", "increase", "decrease"
}

# Regex identifying listicle headers and publication dates
LISTICLE_PATTERN = re.compile(
    r"^(?:top\s+\d+|\d+\s+(?:best|top|simple|easy|essential|great|outstanding|tips|ways|tricks|steps|rules|reasons|factors|drivers|challenges|trends|benefits|strategies|examples|predictions|pillars|myths|lessons|insights|takeaways|stats|statistics|points|distros|distributions|llms|tools|plugins|frameworks|libraries))\b",
    re.IGNORECASE,
)

TEMPORAL_RELEASE_PATTERN = re.compile(
    r"\b(?:released|founded|established|published|launched|since|dated|copyright|version|v\.?)\s+(?:in\s+)?(19\d\d|20[0-3]\d)\b",
    re.IGNORECASE,
)


class EvidenceExtractionService:
    """Deterministic and traceable extraction of candidate numerical metrics from fetched content."""

    def classify_market_metric_type(
        self,
        metric: str,
        unit: Optional[str] = None,
        context: Optional[str] = None,
        value: Optional[float] = None,
        multiplier: Optional[str] = None,
    ) -> Optional[MarketMetricType]:
        """Map extracted text metric, unit, and context to canonical MarketMetricType taxonomy."""
        m_lower = (metric or "").lower().strip()
        u_lower = (unit or "").lower().strip()
        ctx_lower = (context or "").lower().strip()

        # Reject commodity tariffs / usage rates from being misclassified as annual ARPU
        if any(c in ctx_lower or c in m_lower or c in u_lower for c in ("/kwh", "per kwh", "/watt", "per watt", "/kw", "tariff", "tariffs", "/km", "/hour", "/hr", "/gb", "/mb", "/token", "/call")):
            return None

        # Funding / Investment Amount (e.g. "raised $50M in Series B")
        FUNDING_TERMS = ("raised", "funding", "seed round", "series a", "series b", "series c", "venture funding", "invested", "investment round")
        if any(ft in ctx_lower or ft in m_lower for ft in FUNDING_TERMS) and not any(mm in m_lower for mm in ("market size", "industry size", "total market")):
            return MarketMetricType.FUNDING_AMOUNT

        # Company Revenue (single company revenue e.g. "Acme Corp reported revenue of $500M")
        COMPANY_REV_TERMS = ("reported revenue", "annual revenue of", "generated revenue of", "company revenue", "its revenue", "total sales of")
        if any(cr in ctx_lower or cr in m_lower for cr in COMPANY_REV_TERMS) and not any(mm in m_lower for mm in ("market size", "industry size", "sector size", "total market")):
            return MarketMetricType.COMPANY_REVENUE

        # Pricing & ARPU & Unit Economics
        EXPLICIT_UNIT_PRICING_TERMS = (
            "price per", "cost per", "fee per", "spending per", "spend per", "arpu",
            "per user", "per student", "per capita", "per head", "per household", "per animal", "per dog", "per cat",
            "per person", "per subscriber", "per learner", "per client", "per account", "per employee",
            "per transaction", "per order", "per delivery", "per meal", "per ride", "per lesson", "per session",
            "per consultation", "per item", "per garment", "per piece", "per provider", "per facility", "per seat",
            "/month", "/year", "/mo", "/yr", "subscription price", "annual plan", "monthly plan", "order value",
            "average order value", "aov", "unit price", "annual spend per", "annual expenditure per", "tuition", "fare", "ticket"
        )
        is_currency_unit = any(curr in u_lower for curr in ("usd", "inr", "eur", "gbp", "dollar", "rupee", "$", "₹", "€", "£"))
        has_macro_mult = multiplier and multiplier.lower() in ("million", "billion", "crore", "lakh", "trillion", "mn", "bn", "cr", "t", "m", "b")
        is_large_val = (value is not None and value >= 1_000_000.0) or has_macro_mult

        if is_currency_unit:
            if not is_large_val:
                if any(s in m_lower or s in ctx_lower for s in ("subscription", "monthly", "annual plan", "plan", "/mo", "/month")):
                    return MarketMetricType.SUBSCRIPTION_PRICE
                return MarketMetricType.AVERAGE_PRICE
            else:
                # Large scale currency value (>= 1M or macro multiplier)
                if any(p in m_lower or p in ctx_lower for p in EXPLICIT_UNIT_PRICING_TERMS):
                    return MarketMetricType.AVERAGE_PRICE
                return MarketMetricType.MARKET_SIZE

        # Market Share / Growth Rate / CAGR
        if "%" in u_lower or "percent" in u_lower or "pct" in u_lower:
            if "cagr" in m_lower or "cagr" in ctx_lower:
                return MarketMetricType.CAGR
            if any(g in m_lower or g in ctx_lower for g in ("growth", "growth rate", "yoy", "increase")):
                return MarketMetricType.GROWTH_RATE
            return MarketMetricType.MARKET_SHARE

        # Demographic / Customer Categories
        if any(s in u_lower or s in m_lower for s in ("student", "undergraduate", "postgraduate", "pupil")):
            return MarketMetricType.STUDENT_COUNT
        if any(e in u_lower or e in m_lower for e in ("enrollment", "registration", "enrolled")):
            return MarketMetricType.ENROLLMENT
        if any(u in u_lower or u in m_lower for u in ("user", "developer", "programmer", "coder", "engineer")):
            return MarketMetricType.USERS
        if any(h in u_lower or h in m_lower for h in ("household", "family", "home")):
            return MarketMetricType.HOUSEHOLDS
        if any(p in u_lower or p in m_lower for p in ("population", "people", "citizen", "individual", "adult", "youth", "child", "teen")):
            return MarketMetricType.POPULATION
        if any(c in u_lower or c in m_lower for c in ("customer", "buyer", "subscriber", "client", "enterprise", "company", "business", "startup", "smb", "sme", "plant", "factory", "firm", "manufacturer")):
            return MarketMetricType.CUSTOMER_COUNT

        return None

    def _find_all_geographies_with_spans(self, text: str) -> List[Tuple[int, int, str]]:
        """Find all recognized geographies in text along with their (start, end) spans."""
        cleaned_text = re.sub(r"[\u2018\u2019\u201a\u201b\ufffd]", "'", text)
        results: List[Tuple[int, int, str]] = []
        for geo in KNOWN_GEOGRAPHIES:
            pattern = rf"\b{re.escape(geo)}\b"
            for m in re.finditer(pattern, cleaned_text, re.IGNORECASE):
                canon_geo = geo
                if geo.upper() in ("US", "USA"):
                    canon_geo = "United States"
                elif geo.upper() == "UK":
                    canon_geo = "United Kingdom"
                results.append((m.start(), m.end(), canon_geo))
        return results

    def extract_geography_from_text(self, text: str) -> Optional[str]:
        """Identify explicit geographic references in text without hallucinating."""
        found = self._find_all_geographies_with_spans(text)
        if found:
            found.sort(key=lambda x: x[0])
            return found[0][2]
        return None

    def extract_geography_for_match(self, full_sentence: str, match_start: int, match_end: int) -> Optional[str]:
        """Extract geography prioritizing immediate local clause/proximity around the match.

        Prevents comparative country entities (e.g. 'trailing China's USD 43,400 million')
        from erroneously inheriting a distant subject country (e.g. 'India').
        """
        # 1. Check immediate prefix window (up to 60 chars before match)
        prefix_start = max(0, match_start - 60)
        prefix_window = full_sentence[prefix_start:match_start]
        prefix_geos = self._find_all_geographies_with_spans(prefix_window)
        if prefix_geos:
            # Pick the geography immediately closest to the match (highest start position in prefix)
            prefix_geos.sort(key=lambda x: x[0], reverse=True)
            return prefix_geos[0][2]

        # 2. Check immediate suffix window (up to 60 chars after match), excluding global/worldwide denominators
        suffix_end = min(len(full_sentence), match_end + 60)
        suffix_window = full_sentence[match_end:suffix_end]
        is_global_denominator = bool(re.search(r"^\s*(?:of\s+(?:the\s+)?(?:global|worldwide|world))", suffix_window, re.IGNORECASE))
        suffix_geos = self._find_all_geographies_with_spans(suffix_window)
        if suffix_geos:
            suffix_geos.sort(key=lambda x: x[0])
            first_suffix_geo = suffix_geos[0][2]
            if not (is_global_denominator and first_suffix_geo in ("Global", "Worldwide")):
                return first_suffix_geo

        # 3. Fallback to sentence-level geography (excluding denominator 'of the global')
        sentence_without_global_denominator = re.sub(r"\bof\s+(?:the\s+)?(?:global|worldwide|world)\b", "", full_sentence, flags=re.IGNORECASE)
        geo_sentence = self.extract_geography_from_text(sentence_without_global_denominator)
        if geo_sentence:
            return geo_sentence

        return self.extract_geography_from_text(full_sentence)

    def extract_year_from_text(self, text: str) -> Optional[int]:
        """Extract explicit 4-digit calendar year (1990-2035) from context."""
        matches = re.findall(r"\b(199\d|20[0-3]\d)\b", text)
        if matches:
            # Pick the year associated with temporal context
            return int(matches[0])
        return None

    def extract_year_for_match(self, full_sentence: str, match_start: int, match_end: int) -> Optional[int]:
        """Extract calendar year prioritizing immediate local syntactic attachment (suffix/prefix) then proximity."""
        # 1. Immediate suffix check: e.g. 'USD 8.6 Billion in 2025', 'USD 9.2 Billion (2026)', 'in 2025'
        suffix = full_sentence[match_end:min(len(full_sentence), match_end + 30)]
        m_suf = re.search(r"^\s*(?:in|by|for|during|of|to|target)?\s*\(?(19\d\d|20[0-3]\d)\b", suffix, re.IGNORECASE)
        if m_suf:
            return int(m_suf.group(1))

        # 2. Immediate prefix check: e.g. 'In 2025, USD 8.6 Billion', '2025 market: USD 8.6 Billion'
        prefix = full_sentence[max(0, match_start - 30):match_start]
        m_pre = re.search(r"\b(19\d\d|20[0-3]\d)\s*(?::|market|revenue|size|value|valuation|spending|reached|was|is)?\s*$", prefix, re.IGNORECASE)
        if m_pre:
            return int(m_pre.group(1))

        # 3. Proximity fallback
        matches = list(re.finditer(r"\b(199\d|20[0-3]\d)\b", full_sentence))
        if not matches:
            return None

        def _dist(m: re.Match) -> float:
            if m.end() <= match_start:
                return float(match_start - m.end())
            elif m.start() >= match_end:
                return float(m.start() - match_end)
            else:
                return 0.0

        matches.sort(key=_dist)
        return int(matches[0].group(1))

    def parse_number_with_multiplier(self, num_str: str, multiplier_str: Optional[str]) -> float:
        """Parse float and apply multiplier (million, billion, lakh, crore, etc.)."""
        val = float(num_str.replace(",", ""))
        if multiplier_str:
            mult = MULTIPLIERS.get(multiplier_str.lower(), 1.0)
            val *= mult
        return val

    def is_recognized_market_entity(self, word: str) -> bool:
        """Check if a word or entity is a recognized market demographic or institution."""
        w_lower = word.lower().strip()
        if not w_lower:
            return False
        if w_lower in NOISE_REJECTION_TERMS:
            return False
        if w_lower in RECOGNIZED_MARKET_ENTITIES:
            return True
        # Check singular form if ends with 's'
        if w_lower.endswith("s") and len(w_lower) > 3 and w_lower[:-1] in RECOGNIZED_MARKET_ENTITIES:
            return True
        return False

    def extract_candidates_from_sentence(
        self,
        sentence: str,
        source_url: str,
        source_name: Optional[str] = None,
    ) -> List[ExtractedEvidenceCandidate]:
        """Extract candidate metrics from an individual sentence using deterministic patterns."""
        candidates: List[ExtractedEvidenceCandidate] = []
        cleaned_sentence = re.sub(r"[\u2018\u2019\u201a\u201b\ufffd]", "'", sentence.strip())
        if not cleaned_sentence or len(cleaned_sentence) < 10:
            return candidates

        # Guard 1: Direct Listicle / Tutorial / Non-market Article Header Rejection
        if LISTICLE_PATTERN.search(cleaned_sentence):
            return candidates

        # Guard 2: Exclude pure temporal release statements (e.g. "Released in 2024", "Founded in 2021")
        if TEMPORAL_RELEASE_PATTERN.search(cleaned_sentence) and not any(curr in cleaned_sentence for curr in ("$", "USD", "INR", "₹", "crore", "billion", "million")):
            # If the only number in the sentence is a temporal release year, skip extraction
            all_numbers = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", cleaned_sentence)
            if len(all_numbers) == 1 and re.match(r"^(19\d\d|20[0-3]\d)$", all_numbers[0]):
                return candidates

        year = self.extract_year_from_text(cleaned_sentence)

        extracted_spans: List[Tuple[int, int]] = []

        def spans_overlap(start: int, end: int) -> bool:
            return any(not (end <= s_start or start >= s_end) for s_start, s_end in extracted_spans)

        # 1. Range Pattern: e.g. "10–15 million developers", "USD 2 - 3 billion", "jump from 128 to 150 million", "increased from 128 million to 150 million users"
        range_match = re.search(
            r"(\b(?:(?:from|between|ranged from|jump from|increased from|grew from|rose from)\s+)?(?:USD|\$|INR|₹|EUR|€|GBP|£)?\s*([0-9]+(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s*(?:–|-|to|and)\s*(?:USD|\$|INR|₹|EUR|€|GBP|£)?\s*([0-9]+(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s*([a-zA-Z%]+(?:\s+[a-zA-Z%]+){0,3})?\b)",
            cleaned_sentence,
            re.IGNORECASE,
        )
        if range_match and not spans_overlap(range_match.start(), range_match.end()):
            raw_expr = range_match.group(1).strip()
            min_str = range_match.group(2)
            min_multiplier = range_match.group(3)
            max_str = range_match.group(4)
            max_multiplier = range_match.group(5)
            raw_unit_candidate = range_match.group(6)
            cand_geo = self.extract_geography_for_match(cleaned_sentence, range_match.start(), range_match.end())
            cand_year = self.extract_year_for_match(cleaned_sentence, range_match.start(), range_match.end())

            is_min_year = min_multiplier is None and min_str.isdigit() and (1990 <= int(min_str) <= 2040)
            is_max_year = max_multiplier is None and max_str.isdigit() and (1990 <= int(max_str) <= 2040)

            if not is_min_year and not is_max_year:
                try:
                    min_val = self.parse_number_with_multiplier(min_str, min_multiplier or max_multiplier)
                    max_val = self.parse_number_with_multiplier(max_str, max_multiplier or min_multiplier)
                    if min_val > max_val:
                        min_val, max_val = max_val, min_val
                    
                    stop_words = {
                        "in", "on", "at", "by", "for", "from", "with", "to", "across",
                        "is", "are", "was", "were", "and", "or", "as", "during", "of", "who",
                        "which", "that", "over", "between",
                    }
                    trailing_verbs = {"enrolled", "registered", "operating", "living", "located", "based", "working", "contributing"}

                    noun_words = []
                    for word in (raw_unit_candidate or "").split():
                        w_lower = word.lower().strip(",.")
                        if w_lower in stop_words:
                            break
                        if w_lower in trailing_verbs and len(noun_words) > 0:
                            break
                        if w_lower in NOISE_REJECTION_TERMS:
                            continue
                        noun_words.append(word)

                    unit = noun_words[-1] if noun_words else "units"
                    if any(curr in raw_expr for curr in ("USD", "$", "DOLLAR")):
                        unit = "USD"
                    elif any(curr in raw_expr for curr in ("INR", "₹", "RUPEE")):
                        unit = "INR"
                    elif any(curr in raw_expr for curr in ("EUR", "€", "EURO")):
                        unit = "EUR"
                    elif any(curr in raw_expr for curr in ("GBP", "£", "POUND")):
                        unit = "GBP"
                    elif "%" in raw_expr or (raw_unit_candidate and "%" in raw_unit_candidate):
                        unit = "%"

                    # Filter noise
                    if unit.lower() not in NOISE_REJECTION_TERMS and (unit in ("USD", "INR", "EUR", "GBP", "%") or self.is_recognized_market_entity(unit)):
                        is_explicit_unit_spend = (
                            (max_val is None or max_val < 1_000_000)
                            and (
                                any(w in cleaned_sentence.lower() for w in (
                                    "per companion pet", "per pet", "per animal", "per dog", "per cat",
                                    "per user", "per student", "per customer", "per household", "per head",
                                    "per capita", "per subscriber", "per person", "per unit", "per vehicle",
                                    "per learner", "per account", "per client", "per employee", "per transaction",
                                    "annual expenditure", "annual spend", "expenditure per", "spending per",
                                    "spend per", "cost per", "fee per", "average expenditure", "average spend"
                                ))
                                or bool(re.search(r"\bper\s+(?:companion\s+)?(?:pet|dog|cat|animal|user|student|customer|household|head|capita|person|subscriber|learner|account|client|employee|vehicle|unit)\b", cleaned_sentence, re.IGNORECASE))
                            )
                        )
                        is_pricing_term = (
                            (max_val is None or max_val < 1_000_000)
                            and any(w in cleaned_sentence.lower() for w in ("price", "pricing", "fee", "cost", "subscription", "arpu", "tuition", "per user", "per student", "per year", "per month", "plan", "annual fee", "per pet", "per customer"))
                            and not any(w in cleaned_sentence.lower() for w in ("market", "industry", "sector", "total spending", "overall spending", "spending in", "market reached", "market size", "market value", "valuation", "revenues", "revenue"))
                        )
                        has_macro_keywords = any(w in cleaned_sentence.lower() for w in (
                            "market", "industry", "sector", "total spending", "overall spending", "spending in",
                            "market reached", "market size", "market value", "valuation", "revenues", "revenue",
                            "market was valued", "market is valued", "market worth"
                        ))
                        if unit in ("USD", "INR", "EUR", "GBP"):
                            has_macro_multiplier = (min_multiplier and min_multiplier.lower() in MULTIPLIERS and MULTIPLIERS[min_multiplier.lower()] >= 1_000_000.0) or (max_multiplier and max_multiplier.lower() in MULTIPLIERS and MULTIPLIERS[max_multiplier.lower()] >= 1_000_000.0)
                            is_macro_scale = has_macro_multiplier or (max_val is not None and max_val >= 1_000_000.0)
                            if is_explicit_unit_spend or is_pricing_term or not is_macro_scale:
                                m_title = "annual pricing / ARPU"
                                m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence, value=max_val) or MarketMetricType.AVERAGE_PRICE
                            else:
                                m_title = "market size / revenue"
                                m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence, value=max_val) or MarketMetricType.MARKET_SIZE
                        elif unit == "%":
                            is_growth = any(w in cleaned_sentence.lower() for w in ("growth", "cagr", "increase", "yoy", "year-on-year", "annual growth", "grew", "jump", "rise", "rose"))
                            if is_growth or (max_val is not None and max_val > 100.0):
                                m_title = "growth rate / CAGR"
                                m_type = MarketMetricType.GROWTH_RATE
                            else:
                                m_title = " ".join(noun_words) if noun_words else "market share / segment percentage"
                                m_type = MarketMetricType.MARKET_SHARE
                        else:
                            m_title = " ".join(noun_words) if noun_words else unit
                            m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence)

                        candidates.append(
                            ExtractedEvidenceCandidate(
                                metric=m_title,
                                metric_type=m_type,
                                value=None,
                                raw_value_expression=raw_expr,
                                unit=unit,
                                geography=cand_geo,
                                year=cand_year,
                                is_range_or_approximate=True,
                                range_min=min_val,
                                range_max=max_val,
                                source_name=source_name,
                                source_url=source_url,
                                source_context=cleaned_sentence,
                                extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                                extraction_confidence=ConfidenceLevel.MEDIUM,
                                lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                                notes=f"Extracted range: {min_val} to {max_val} {unit}",
                            )
                        )
                        extracted_spans.append((range_match.start(), range_match.end()))
                except Exception:
                    pass

        # 2. Approximate Pattern: e.g. "more than 10 million users", "approximately 500,000 college students"
        for approx_prefix in APPROX_QUALIFIERS:
            approx_regex = rf"\b({re.escape(approx_prefix)}\s+([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s+([a-zA-Z%]+(?:\s+[a-zA-Z%]+){{0,4}})?)\b"
            for approx_match in re.finditer(approx_regex, cleaned_sentence, re.IGNORECASE):
                raw_match_text = approx_match.group(1).strip()
                num_str = approx_match.group(2)
                multiplier = approx_match.group(3)
                approx_start = approx_match.start()
                if spans_overlap(approx_start, approx_start + len(num_str)):
                    continue
                raw_trailing_words = (approx_match.group(4) or "").split()
                cand_geo = self.extract_geography_for_match(cleaned_sentence, approx_match.start(), approx_match.end())
                cand_year = self.extract_year_for_match(cleaned_sentence, approx_match.start(), approx_match.end())

                stop_words = {
                    "in", "on", "at", "by", "for", "from", "with", "to", "across",
                    "is", "are", "was", "were", "and", "or", "as", "during", "of", "who",
                    "which", "that", "over", "between",
                }
                trailing_verbs = {
                    "enrolled", "registered", "operating", "living", "located", "based", "working",
                    "employing", "utilizing", "using", "deploying", "adopting", "subscribing",
                    "managing", "serving", "generating", "producing", "graduating", "spanning",
                    "deploy", "use", "utilize", "adopt", "subscribe", "operate", "live", "work", "employ",
                    "globally", "worldwide", "nationwide", "currently", "annually",
                }

                noun_words = []
                for word in raw_trailing_words:
                    w_lower = word.lower().strip(",.")
                    if w_lower in stop_words:
                        break
                    if w_lower in trailing_verbs and len(noun_words) > 0:
                        break
                    if w_lower in NOISE_REJECTION_TERMS:
                        noun_words = []
                        break
                    noun_words.append(word)
                    if len(noun_words) > 0 and self.is_recognized_market_entity(w_lower) and len(noun_words) >= 2:
                        break

                if noun_words:
                    unit_word = noun_words[-1].lower()
                    if not any(w.lower() in NOISE_REJECTION_TERMS for w in noun_words) and (self.is_recognized_market_entity(unit_word) or any(curr in raw_match_text for curr in ("USD", "$", "INR", "₹"))):
                        subject_noun = " ".join(noun_words)
                        mult_part = f" {multiplier}" if multiplier else ""
                        exact_raw_expr = f"{approx_prefix} {num_str}{mult_part} {subject_noun}".strip()
                        try:
                            base_val = self.parse_number_with_multiplier(num_str, multiplier)
                            unit = noun_words[-1]
                            if any(curr in raw_match_text for curr in ("USD", "$")):
                                unit = "USD"
                            elif any(curr in raw_match_text for curr in ("INR", "₹")):
                                unit = "INR"

                            m_type = self.classify_market_metric_type(metric=subject_noun, unit=unit, context=cleaned_sentence)
                            low_bnd = base_val if ("more" in approx_prefix or "at least" in approx_prefix) else (base_val * 0.9 if any(q in approx_prefix for q in ("approx", "around", "near", "about", "estim")) else base_val * 0.95)
                            high_bnd = base_val if ("up to" in approx_prefix or "less" in approx_prefix) else (base_val * 1.1 if any(q in approx_prefix for q in ("approx", "around", "near", "about", "estim")) else base_val * 1.05)
                            candidates.append(
                                ExtractedEvidenceCandidate(
                                    metric=subject_noun,
                                    metric_type=m_type,
                                    value=None,
                                    raw_value_expression=exact_raw_expr,
                                    unit=unit,
                                    geography=cand_geo,
                                    year=cand_year,
                                    is_range_or_approximate=True,
                                    range_min=low_bnd,
                                    range_max=high_bnd,
                                    source_name=source_name,
                                    source_url=source_url,
                                    source_context=cleaned_sentence,
                                    extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                                    extraction_confidence=ConfidenceLevel.MEDIUM,
                                    lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                                    notes=f"Approximate expression with qualifier '{approx_prefix}' (baseline {base_val})",
                                )
                            )
                            extracted_spans.append((approx_start, approx_start + len(exact_raw_expr)))
                        except Exception:
                            pass

        # 3. Currency Value Pattern: e.g. "USD 2.5 billion", "valued at $500 million", "$29.5 per customer", "revenue of INR 100 crore", "5,000 crore rupees", "10 billion USD"
        for currency_match in re.finditer(
            r"(?:(?:\b(?:valued at|revenue of|market size of|worth|spending of|cost of|fee of|price of)\s+)?(?:(USD|\$|INR|₹|EUR|€|GBP|£)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?|\b([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s*(USD|dollars?|INR|rupees?|EUR|euros?|GBP|pounds?))\b)",
            cleaned_sentence,
            re.IGNORECASE,
        ):
            if not spans_overlap(currency_match.start(), currency_match.end()):
                raw_expr = currency_match.group(0).strip()
                if currency_match.group(1):
                    curr_symbol = currency_match.group(1).upper()
                    num_str = currency_match.group(2)
                    multiplier = currency_match.group(3)
                else:
                    num_str = currency_match.group(4)
                    multiplier = currency_match.group(5)
                    curr_symbol = currency_match.group(6).upper()

                unit = (
                    "USD" if any(c in curr_symbol for c in ("USD", "$", "DOLLAR"))
                    else ("INR" if any(c in curr_symbol for c in ("INR", "₹", "RUPEE"))
                    else ("EUR" if any(c in curr_symbol for c in ("EUR", "€", "EURO"))
                    else ("GBP" if any(c in curr_symbol for c in ("GBP", "£", "POUND")) else curr_symbol)))
                )
                cand_geo = self.extract_geography_for_match(cleaned_sentence, currency_match.start(), currency_match.end())
                cand_year = self.extract_year_for_match(cleaned_sentence, currency_match.start(), currency_match.end())

                try:
                    resolved_val = self.parse_number_with_multiplier(num_str, multiplier)
                    has_macro_multiplier = multiplier is not None and multiplier.lower() in ("million", "billion", "crore", "lakh", "trillion", "mn", "bn", "cr", "t", "m", "b")
                    is_macro_scale = has_macro_multiplier or resolved_val >= 1_000_000.0

                    is_explicit_unit_spend = (
                        not is_macro_scale
                        or any(w in cleaned_sentence.lower() for w in (
                            "per companion pet", "per pet", "per animal", "per dog", "per cat",
                            "per user", "per student", "per customer", "per household", "per head",
                            "per capita", "per subscriber", "per person", "per unit", "per vehicle",
                            "per learner", "per account", "per client", "per employee", "per transaction",
                            "per order", "per delivery", "per meal", "per ride", "per item", "per piece",
                            "annual expenditure", "annual spend", "expenditure per", "spending per",
                            "spend per", "cost per", "fee per", "average expenditure", "average spend",
                            "average spending", "order value", "average order value", "aov", "unit price"
                        ))
                        or bool(re.search(r"\bper\s+(?:companion\s+)?(?:pet|dog|cat|animal|user|student|customer|household|head|capita|person|subscriber|learner|account|client|employee|vehicle|unit|order|delivery|meal|item|piece)\b", cleaned_sentence, re.IGNORECASE))
                    )

                    is_commodity_term = any(w in cleaned_sentence.lower() for w in ("tariff", "tariffs", "/kwh", "per kwh", "/watt", "per watt", "/km", "/hour", "/hr", "/gb", "/mb", "/token", "/call"))
                    if is_commodity_term:
                        m_title = "tariff / usage rate"
                        m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence, value=resolved_val, multiplier=multiplier)
                    elif not is_macro_scale or is_explicit_unit_spend:
                        m_type = self.classify_market_metric_type(metric="annual pricing / ARPU", unit=unit, context=cleaned_sentence, value=resolved_val, multiplier=multiplier) or MarketMetricType.AVERAGE_PRICE
                        m_title = "annual pricing / ARPU" if m_type == MarketMetricType.ANNUAL_SPEND else ("average order value" if m_type == MarketMetricType.AVERAGE_ORDER_VALUE else ("subscription price" if m_type == MarketMetricType.SUBSCRIPTION_PRICE else "unit price / average price"))
                    else:
                        m_title = "market size / revenue"
                        m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence, value=resolved_val, multiplier=multiplier) or MarketMetricType.MARKET_SIZE

                    candidates.append(
                        ExtractedEvidenceCandidate(
                            metric=m_title,
                            metric_type=m_type,
                            value=resolved_val,
                            raw_value_expression=raw_expr,
                            unit=unit,
                            geography=cand_geo,
                            year=cand_year,
                            is_range_or_approximate=False,
                            source_name=source_name,
                            source_url=source_url,
                            source_context=cleaned_sentence,
                            extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                            extraction_confidence=ConfidenceLevel.HIGH if cand_year and cand_geo else ConfidenceLevel.MEDIUM,
                            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                        )
                    )
                    extracted_spans.append((currency_match.start(), currency_match.end()))
                except Exception:
                    pass

        # 4. Count / Population Pattern: e.g. "43 million college students", "800 million active internet users", "45,000 charging stations"
        for count_match in re.finditer(
            r"\b([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,4})",
            cleaned_sentence,
            re.IGNORECASE,
        ):
            match_start = count_match.start()
            num_str = count_match.group(1)
            multiplier = count_match.group(2)
            prefix_char = cleaned_sentence[match_start - 1] if match_start > 0 else ""
            if prefix_char in ("$", "₹", "€", "£") or spans_overlap(match_start, match_start + len(num_str)):
                continue

            raw_trailing_words = count_match.group(3).split()
            cand_geo = self.extract_geography_for_match(cleaned_sentence, count_match.start(), count_match.end())
            cand_year = self.extract_year_for_match(cleaned_sentence, count_match.start(), count_match.end())

            # Guard: Standalone calendar year (e.g. "2024 college students graduated") check
            if not (multiplier is None and re.match(r"^(19\d\d|20[0-3]\d)$", num_str.replace(",", ""))):
                # Reject match if immediate trailing token is a known listicle/noise keyword (e.g., "6 Factors Propelling...", "10 Best CRM...")
                if raw_trailing_words and raw_trailing_words[0].lower().strip(",.") in NOISE_REJECTION_TERMS:
                    continue

                stop_words = {
                    "in", "on", "at", "by", "for", "from", "with", "to", "across",
                    "is", "are", "was", "were", "and", "or", "as", "during", "of", "who",
                    "which", "that", "over", "between",
                }
                trailing_verbs = {
                    "enrolled", "registered", "operating", "living", "located", "based", "working",
                    "employing", "utilizing", "using", "deploying", "adopting", "subscribing",
                    "managing", "serving", "generating", "producing", "graduating", "spanning",
                    "deploy", "use", "utilize", "adopt", "subscribe", "operate", "live", "work", "employ",
                    "globally", "worldwide", "nationwide", "currently", "annually",
                }

                noun_words = []
                for word in raw_trailing_words:
                    w_lower = word.lower().strip(",.")
                    if w_lower in stop_words:
                        break
                    if w_lower in trailing_verbs and len(noun_words) > 0:
                        break
                    if w_lower in NOISE_REJECTION_TERMS:
                        noun_words = []
                        break
                    noun_words.append(word)
                    if len(noun_words) > 0 and self.is_recognized_market_entity(w_lower) and len(noun_words) >= 2:
                        break

                if noun_words:
                    unit_word = noun_words[-1].lower().strip(",.")
                    if not any(w.lower().strip(",.") in NOISE_REJECTION_TERMS for w in noun_words) and self.is_recognized_market_entity(unit_word):
                        subject_noun = " ".join(noun_words)
                        mult_part = f" {multiplier}" if multiplier else ""
                        raw_expr = f"{num_str}{mult_part} {subject_noun}"

                        try:
                            resolved_val = self.parse_number_with_multiplier(num_str, multiplier)
                            m_type = self.classify_market_metric_type(metric=subject_noun, unit=unit_word, context=cleaned_sentence)

                            # Guard against small isolated integers (<50 without multiplier) falsely becoming macro population/customer count
                            if multiplier is None and resolved_val < 50 and m_type in (
                                MarketMetricType.POPULATION,
                                MarketMetricType.CUSTOMER_COUNT,
                                MarketMetricType.USERS,
                                MarketMetricType.STUDENT_COUNT,
                                MarketMetricType.HOUSEHOLDS,
                            ):
                                is_explicit_survey = any(s in cleaned_sentence.lower() for s in ("survey of", "sample of", "cohort of", "interviewed", "respondents", "participating"))
                                if not is_explicit_survey:
                                    continue

                            candidates.append(
                                ExtractedEvidenceCandidate(
                                    metric=subject_noun,
                                    metric_type=m_type,
                                    value=resolved_val,
                                    raw_value_expression=raw_expr,
                                    unit=unit_word,
                                    geography=cand_geo,
                                    year=cand_year,
                                    is_range_or_approximate=False,
                                    source_name=source_name,
                                    source_url=source_url,
                                    source_context=cleaned_sentence,
                                    extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                                    extraction_confidence=ConfidenceLevel.HIGH if cand_year and cand_geo else ConfidenceLevel.MEDIUM,
                                    lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                                )
                            )
                            extracted_spans.append((match_start, match_start + len(raw_expr)))
                        except Exception:
                            pass

        # 5. Percentage / Share Pattern: e.g. "5.41% of the global market", "51.1% of pet care service transactions", "market share of 73.00%", "accounting for 5.41%"
        for pct_match in re.finditer(
            r"([0-9]+(?:\.[0-9]+)?)\s*(%|percent|percentage)(?:\s+(?:of\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+){0,4}))?",
            cleaned_sentence,
            re.IGNORECASE,
        ):
            if not spans_overlap(pct_match.start(), pct_match.end()):
                pct_num_str = pct_match.group(1)
                raw_trailing = (pct_match.group(3) or "").strip()
                raw_expr = pct_match.group(0).strip()
                cand_geo = self.extract_geography_for_match(cleaned_sentence, pct_match.start(), pct_match.end())
                cand_year = self.extract_year_for_match(cleaned_sentence, pct_match.start(), pct_match.end())
                try:
                    pct_val = float(pct_num_str)
                    is_growth = any(w in cleaned_sentence.lower() for w in ("growth", "cagr", "increase", "yoy", "year-on-year", "annual growth", "grew", "jump", "rise", "rose", "scaled"))
                    
                    # Clean trailing words from prepositions and noise
                    trailing_words = [
                        w for w in raw_trailing.split()
                        if w.lower() not in NOISE_REJECTION_TERMS and w.lower() not in ("to", "and", "in", "by", "from", "for", "during", "between", "with", "while", "as", "of")
                    ]
                    cleaned_trailing = " ".join(trailing_words)

                    if is_growth or pct_val > 100.0:
                        m_title = "growth rate / CAGR"
                        m_type = MarketMetricType.GROWTH_RATE
                    else:
                        m_title = cleaned_trailing if cleaned_trailing else "market share / segment percentage"
                        m_type = MarketMetricType.MARKET_SHARE

                    candidates.append(
                        ExtractedEvidenceCandidate(
                            metric=m_title,
                            metric_type=m_type,
                            value=pct_val,
                            raw_value_expression=raw_expr,
                            unit="%",
                            geography=cand_geo,
                            year=cand_year,
                            is_range_or_approximate=False,
                            source_name=source_name,
                            source_url=source_url,
                            source_context=cleaned_sentence,
                            extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                            extraction_confidence=ConfidenceLevel.HIGH if cand_year and cand_geo else ConfidenceLevel.MEDIUM,
                            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                        )
                    )
                    extracted_spans.append((pct_match.start(), pct_match.end()))
                except Exception:
                    pass

        return candidates

    def extract_evidence_from_source(self, request: ExtractionRequest) -> ExtractionResponse:
        """Process a FetchedSource and extract candidate evidence metrics."""
        source = request.source
        url = source.original_url
        content = source.content or ""

        if not content.strip():
            return ExtractionResponse(
                source_url=url,
                status=ExtractionStatus.NO_METRICS_FOUND,
                candidates=[],
                total_candidates_found=0,
                lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                message="Source document contains no readable text content.",
            )

        # Split text into sentences
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", content)
        all_candidates: List[ExtractedEvidenceCandidate] = []

        for sent in raw_sentences:
            sent_candidates = self.extract_candidates_from_sentence(
                sentence=sent,
                source_url=url,
                source_name=source.source_name or source.title,
            )
            all_candidates.extend(sent_candidates)

        if not all_candidates:
            return ExtractionResponse(
                source_url=url,
                status=ExtractionStatus.NO_METRICS_FOUND,
                candidates=[],
                total_candidates_found=0,
                lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                message="No numerical market metrics or verifiable facts found in source content.",
            )

        return ExtractionResponse(
            source_url=url,
            status=ExtractionStatus.SUCCESS,
            candidates=all_candidates,
            total_candidates_found=len(all_candidates),
            lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
            message=f"Successfully extracted {len(all_candidates)} candidate evidence metric(s).",
        )

    def extract_competitors_from_source(self, source: FetchedSource) -> List[CompetitorInfo]:
        """Extract structured competitor mentions grounded in fetched document content."""
        content = source.content or ""
        if not content.strip():
            return []

        url = source.final_url or source.original_url
        source_name = source.source_name or source.title

        competitors: List[CompetitorInfo] = []
        seen_names = set()

        # Regex patterns looking for explicit competitor mentions
        comp_patterns = [
            r"(?:competitors|key players|leading players|major players|vendors|market participants|prominent players)\s+(?:include|are|such as|like)\s+([^.\n]{5,200})",
            r"(?:top competitors|main competitors|direct competitors)\s*[:\-]\s*([^.\n]{5,200})",
        ]

        for pat in comp_patterns:
            matches = re.finditer(pat, content, re.IGNORECASE)
            for m in matches:
                list_str = m.group(1).strip()
                # Split comma separated or 'and' separated items
                raw_items = re.split(r",\s*|\s+and\s+|\s*;\s*", list_str)
                for item in raw_items:
                    name_cand = re.sub(r"^(?:and\s+|the\s+|a\s+|such as\s+)", "", item.strip(), flags=re.IGNORECASE)
                    name_cand = re.sub(r"[\(\[].*?[\)\]]", "", name_cand).strip()
                    # Filter names
                    if len(name_cand) < 2 or len(name_cand) > 50:
                        continue
                    if any(w in name_cand.lower() for w in ("include", "such", "market", "industry", "table", "figure", "report", "percent", "%", "source")):
                        continue
                    if name_cand.lower() not in seen_names:
                        seen_names.add(name_cand.lower())
                        competitors.append(
                            CompetitorInfo(
                                name=name_cand,
                                product_service="Competitor identified in market intelligence report",
                                source_url=url,
                                source_name=source_name,
                                confidence="medium",
                            )
                        )

        return competitors


def get_extraction_service() -> EvidenceExtractionService:
    """Dependency provider for EvidenceExtractionService."""
    return EvidenceExtractionService()
