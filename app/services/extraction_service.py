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
    "United States",
    "US",
    "USA",
    "North America",
    "Europe",
    "Asia",
    "Southeast Asia",
    "Global",
    "Worldwide",
    "United Kingdom",
    "UK",
    "Germany",
    "Japan",
    "China",
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
    "driver", "drivers", "graduate", "graduates", "teacher", "teachers",
    "educator", "educators", "instructor", "instructors", "tutor", "tutors",
    "reader", "readers", "member", "members", "client", "clients", "account", "accounts",
    "creator", "creators", "freelancer", "freelancers", "founder", "founders",

    # Institutional & Business Target Entities
    "enterprise", "enterprises", "company", "companies", "business", "businesses",
    "startup", "startups", "firm", "firms", "institution", "institutions",
    "school", "schools", "college", "colleges", "university", "universities",
    "household", "households", "organization", "organizations", "hospital", "hospitals",
    "clinic", "clinics", "merchant", "merchants", "vendor", "vendors",
    "smb", "smbs", "sme", "smes", "msme", "msmes",
    "store", "stores", "shop", "shops", "hub", "hubs", "branch", "branches", "site", "sites",

    # Market Volume, Hardware & Operational Units
    "unit", "units", "installation", "installations", "subscription", "subscriptions",
    "download", "downloads", "transaction", "transactions", "license", "licenses",
    "seat", "seats", "device", "devices", "vehicle", "vehicles", "course", "courses",
    "enrollment", "enrollments", "registration", "registrations",
    "station", "stations", "charger", "chargers", "port", "ports", "point", "points", "outlet", "outlets",
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
    # Listicle & Article Noise
    "tip", "tips", "trick", "tricks", "way", "ways", "reason", "reasons",
    "step", "steps", "idea", "ideas", "example", "examples", "thing", "things",
    "tool", "tools", "feature", "features", "item", "items", "plugin", "plugins",
    "distribution", "distributions", "distro", "distros", "framework", "frameworks",
    "library", "libraries", "package", "packages", "model", "models", "llm", "llms",
    "article", "articles", "post", "posts", "question", "questions", "faq", "faqs",
    "rule", "rules", "habit", "habits", "fact", "facts", "myth", "myths",
    "benefit", "benefits", "trend", "trends", "alternative", "alternatives",
    "option", "options", "method", "methods", "technique", "techniques",
    "strategy", "strategies", "lesson", "lessons", "ranking", "rankings",
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
    "more", "less", "metric", "metrics", "number", "numbers", "total", "totals"
}

# Regex identifying listicle headers and publication dates
LISTICLE_PATTERN = re.compile(
    r"^(?:top\s+\d+|\d+\s+(?:best|top|simple|easy|essential|great|outstanding|tips|ways|tricks|steps|rules|reasons|distros|distributions|llms|tools|plugins|frameworks|libraries))\b",
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
    ) -> Optional[MarketMetricType]:
        """Map extracted text metric, unit, and context to canonical MarketMetricType taxonomy."""
        m_lower = (metric or "").lower().strip()
        u_lower = (unit or "").lower().strip()
        ctx_lower = (context or "").lower().strip()

        # Pricing & ARPU
        if any(p in m_lower or p in ctx_lower for p in ("price", "pricing", "arpu", "subscription", "fee", "cost per", "rate", "/month", "/year", "annual fee")):
            if any(curr in u_lower for curr in ("usd", "inr", "eur", "gbp", "dollar", "rupee")):
                return MarketMetricType.SUBSCRIPTION_PRICE if any(s in m_lower or s in ctx_lower for s in ("subscription", "monthly", "annual", "plan")) else MarketMetricType.AVERAGE_PRICE

        # Market Size / Revenue
        if any(curr in u_lower for curr in ("usd", "inr", "eur", "gbp", "dollar", "rupee")):
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
        if any(c in u_lower or c in m_lower for c in ("customer", "buyer", "subscriber", "client", "enterprise", "company", "business", "startup", "smb", "sme")):
            return MarketMetricType.CUSTOMER_COUNT

        return None

    def extract_geography_from_text(self, text: str) -> Optional[str]:
        """Identify explicit geographic references in text without hallucinating."""
        for geo in KNOWN_GEOGRAPHIES:
            pattern = rf"\b{re.escape(geo)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                # Standardize acronyms / canonical casing
                if geo.upper() in ("US", "USA"):
                    return "United States"
                if geo.upper() == "UK":
                    return "United Kingdom"
                return geo
        return None

    def extract_year_from_text(self, text: str) -> Optional[int]:
        """Extract explicit 4-digit calendar year (1990-2035) from context."""
        matches = re.findall(r"\b(199\d|20[0-3]\d)\b", text)
        if matches:
            # Pick the year associated with temporal context
            return int(matches[0])
        return None

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
        cleaned_sentence = sentence.strip()
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

        geo = self.extract_geography_from_text(cleaned_sentence)
        year = self.extract_year_from_text(cleaned_sentence)

        extracted_spans: List[Tuple[int, int]] = []

        def spans_overlap(start: int, end: int) -> bool:
            return any(not (end <= s_start or start >= s_end) for s_start, s_end in extracted_spans)

        # 1. Range Pattern: e.g. "10–15 million developers", "USD 2 - 3 billion"
        range_match = re.search(
            r"(\b(?:USD|\$|INR|₹|EUR|€)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:–|-|to)\s*([0-9]+(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s*([a-zA-Z%]+)?\b)",
            cleaned_sentence,
            re.IGNORECASE,
        )
        if range_match and not spans_overlap(range_match.start(), range_match.end()):
            raw_expr = range_match.group(1).strip()
            min_str = range_match.group(2)
            max_str = range_match.group(3)
            multiplier = range_match.group(4)
            unit_candidate = range_match.group(5)

            try:
                min_val = self.parse_number_with_multiplier(min_str, multiplier)
                max_val = self.parse_number_with_multiplier(max_str, multiplier)
                unit = unit_candidate.strip() if unit_candidate else "units"
                if any(curr in raw_expr for curr in ("USD", "$")):
                    unit = "USD"
                elif any(curr in raw_expr for curr in ("INR", "₹")):
                    unit = "INR"

                # Filter noise
                if unit.lower() not in NOISE_REJECTION_TERMS and (unit in ("USD", "INR") or self.is_recognized_market_entity(unit)):
                    is_pricing_term = any(w in cleaned_sentence.lower() for w in ("price", "pricing", "fee", "cost", "subscription", "arpu", "spend", "tuition", "per user", "per student", "per year", "per month", "plan"))
                    if unit in ("USD", "INR"):
                        if is_pricing_term or (max_val < 1_000_000 and not any(w in cleaned_sentence.lower() for w in ("market size", "market revenue", "market valuation", "industry size", "total market"))):
                            m_title = "annual pricing / ARPU"
                            m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence) or MarketMetricType.AVERAGE_PRICE
                        else:
                            m_title = "market size / revenue"
                            m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence) or MarketMetricType.MARKET_SIZE
                    else:
                        m_title = unit
                        m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence)

                    mid_val = (min_val + max_val) / 2.0 if (min_val is not None and max_val is not None) else (min_val or max_val)
                    candidates.append(
                        ExtractedEvidenceCandidate(
                            metric=m_title,
                            metric_type=m_type,
                            value=None,
                            raw_value_expression=raw_expr,
                            unit=unit,
                            geography=geo,
                            year=year,
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
            approx_match = re.search(approx_regex, cleaned_sentence, re.IGNORECASE)
            if approx_match and not spans_overlap(approx_match.start(), approx_match.end()):
                raw_expr = approx_match.group(1).strip()
                num_str = approx_match.group(2)
                multiplier = approx_match.group(3)
                raw_trailing_words = (approx_match.group(4) or "").split()

                stop_words = {
                    "in", "on", "at", "by", "for", "from", "with", "to", "across",
                    "is", "are", "was", "were", "and", "or", "as", "during", "of", "who",
                    "which", "that", "over", "between",
                }
                trailing_verbs = {"enrolled", "registered", "operating", "living", "located", "based", "working"}

                noun_words = []
                for word in raw_trailing_words:
                    w_lower = word.lower()
                    if w_lower in stop_words:
                        break
                    if w_lower in trailing_verbs and len(noun_words) > 0:
                        break
                    noun_words.append(word)

                if noun_words:
                    unit_word = noun_words[-1].lower()
                    if not any(w.lower() in NOISE_REJECTION_TERMS for w in noun_words) and (self.is_recognized_market_entity(unit_word) or any(curr in raw_expr for curr in ("USD", "$", "INR", "₹"))):
                        subject_noun = " ".join(noun_words)
                        try:
                            base_val = self.parse_number_with_multiplier(num_str, multiplier)
                            unit = noun_words[-1]
                            if any(curr in raw_expr for curr in ("USD", "$")):
                                unit = "USD"
                            elif any(curr in raw_expr for curr in ("INR", "₹")):
                                unit = "INR"

                            m_type = self.classify_market_metric_type(metric=subject_noun, unit=unit, context=cleaned_sentence)
                            low_bnd = base_val if ("more" in approx_prefix or "at least" in approx_prefix) else (base_val * 0.9 if any(q in approx_prefix for q in ("approx", "around", "near", "about", "estim")) else base_val * 0.95)
                            high_bnd = base_val if ("up to" in approx_prefix or "less" in approx_prefix) else (base_val * 1.1 if any(q in approx_prefix for q in ("approx", "around", "near", "about", "estim")) else base_val * 1.05)
                            candidates.append(
                                ExtractedEvidenceCandidate(
                                    metric=subject_noun,
                                    metric_type=m_type,
                                    value=None,
                                    raw_value_expression=raw_expr,
                                    unit=unit,
                                    geography=geo,
                                    year=year,
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
                            extracted_spans.append((approx_match.start(), approx_match.end()))
                            break
                        except Exception:
                            pass

        # 3. Currency Value Pattern: e.g. "USD 2.5 billion", "valued at $500 million", "revenue of INR 100 crore", "5,000 crore rupees", "10 billion USD"
        for currency_match in re.finditer(
            r"(\b(?:valued at|revenue of|market size of|worth|spending of|cost of|fee of|price of)?\s*(?:(USD|\$|INR|₹|EUR|€)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?|([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(thousand|million|billion|trillion|crore|lakh|mn|bn|k|b|m)?\s*(USD|dollars?|INR|rupees?|EUR|euros?|GBP|pounds?))\b)",
            cleaned_sentence,
            re.IGNORECASE,
        ):
            if not spans_overlap(currency_match.start(), currency_match.end()):
                raw_expr = currency_match.group(1).strip()
                if currency_match.group(2):
                    curr_symbol = currency_match.group(2).upper()
                    num_str = currency_match.group(3)
                    multiplier = currency_match.group(4)
                else:
                    num_str = currency_match.group(5)
                    multiplier = currency_match.group(6)
                    curr_symbol = currency_match.group(7).upper()

                unit = (
                    "USD" if any(c in curr_symbol for c in ("USD", "$", "DOLLAR"))
                    else ("INR" if any(c in curr_symbol for c in ("INR", "₹", "RUPEE"))
                    else ("EUR" if any(c in curr_symbol for c in ("EUR", "€", "EURO"))
                    else ("GBP" if any(c in curr_symbol for c in ("GBP", "POUND")) else curr_symbol)))
                )
                try:
                    resolved_val = self.parse_number_with_multiplier(num_str, multiplier)
                    is_pricing_term = any(w in cleaned_sentence.lower() for w in ("price", "pricing", "fee", "cost", "subscription", "arpu", "spend", "tuition", "per user", "per student", "per year", "per month", "plan", "annual fee"))
                    if is_pricing_term or (resolved_val < 1_000_000 and not any(w in cleaned_sentence.lower() for w in ("market size", "market revenue", "market valuation", "industry size", "total market"))):
                        m_title = "annual pricing / ARPU"
                        m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence) or MarketMetricType.AVERAGE_PRICE
                    else:
                        m_title = "market size / revenue"
                        m_type = self.classify_market_metric_type(metric=m_title, unit=unit, context=cleaned_sentence) or MarketMetricType.MARKET_SIZE

                    candidates.append(
                        ExtractedEvidenceCandidate(
                            metric=m_title,
                            metric_type=m_type,
                            value=resolved_val,
                            raw_value_expression=raw_expr,
                            unit=unit,
                            geography=geo,
                            year=year,
                            is_range_or_approximate=False,
                            source_name=source_name,
                            source_url=source_url,
                            source_context=cleaned_sentence,
                            extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                            extraction_confidence=ConfidenceLevel.HIGH if year and geo else ConfidenceLevel.MEDIUM,
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
            if not spans_overlap(count_match.start(), count_match.end()):
                num_str = count_match.group(1)
                multiplier = count_match.group(2)
                raw_trailing_words = count_match.group(3).split()

                # Guard: Standalone calendar year (e.g. "2024 college students graduated") check
                if not (multiplier is None and re.match(r"^(19\d\d|20[0-3]\d)$", num_str.replace(",", ""))):
                    stop_words = {
                        "in", "on", "at", "by", "for", "from", "with", "to", "across",
                        "is", "are", "was", "were", "and", "or", "as", "during", "of", "who",
                        "which", "that", "over", "between",
                    }
                    trailing_verbs = {"enrolled", "registered", "operating", "living", "located", "based", "working"}

                    noun_words = []
                    for word in raw_trailing_words:
                        w_lower = word.lower()
                        if w_lower in stop_words:
                            break
                        if w_lower in trailing_verbs and len(noun_words) > 0:
                            break
                        noun_words.append(word)

                    if noun_words:
                        unit_word = noun_words[-1].lower()
                        if not any(w.lower() in NOISE_REJECTION_TERMS for w in noun_words) and self.is_recognized_market_entity(unit_word):
                            subject_noun = " ".join(noun_words)
                            mult_part = f" {multiplier}" if multiplier else ""
                            raw_expr = f"{num_str}{mult_part} {subject_noun}"

                            try:
                                resolved_val = self.parse_number_with_multiplier(num_str, multiplier)
                                m_type = self.classify_market_metric_type(metric=subject_noun, unit=noun_words[-1], context=cleaned_sentence)
                                candidates.append(
                                    ExtractedEvidenceCandidate(
                                        metric=subject_noun,
                                        metric_type=m_type,
                                        value=resolved_val,
                                        raw_value_expression=raw_expr,
                                        unit=noun_words[-1],
                                        geography=geo,
                                        year=year,
                                        is_range_or_approximate=False,
                                        source_name=source_name,
                                        source_url=source_url,
                                        source_context=cleaned_sentence,
                                        extraction_method=ExtractionMethod.DETERMINISTIC_PATTERN,
                                        extraction_confidence=ConfidenceLevel.HIGH if year and geo else ConfidenceLevel.MEDIUM,
                                        lifecycle_stage=DiscoveryLifecycleStage.EXTRACTED,
                                    )
                                )
                                extracted_spans.append((count_match.start(), count_match.end()))
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
