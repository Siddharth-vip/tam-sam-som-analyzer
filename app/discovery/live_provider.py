from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.discovery.base import (
    BaseDiscoveryProvider,
    DiscoveryProviderException,
    DiscoveryProviderUnavailableException,
)
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    ResearchQuery,
    SourceCategory,
    SourceQualityTier,
)

logger = logging.getLogger(__name__)


def infer_source_quality_tier(category: SourceCategory, domain: Optional[str] = None, url: Optional[str] = None) -> SourceQualityTier:
    """Classify discovered source into deterministic 5-tier quality hierarchy."""
    domain_lower = (domain or "").lower()
    url_lower = (url or "").lower()

    if (
        any(
            u in domain_lower
            for u in (
                "twitter.com", "x.com", "reddit.com", "quora.com", "facebook.com",
                "instagram.com", "tiktok.com", "threads.net", "pinterest.com",
                "tumblr.com", "stackoverflow.com", "answers.yahoo.com",
            )
        )
        or "/posts/" in url_lower and "linkedin.com" in domain_lower
        or "/r/" in url_lower
        or "/forum/" in url_lower
    ):
        return SourceQualityTier.TIER_5_UNUSABLE

    if category in (SourceCategory.OFFICIAL_GOVERNMENT, SourceCategory.COMPANY_FILING, SourceCategory.TRADE_ASSOCIATION):
        return SourceQualityTier.TIER_1_GOVERNMENT_OFFICIAL
    if category in (SourceCategory.ACADEMIC_INSTITUTION, SourceCategory.FINANCIAL_MARKET_RESEARCH, SourceCategory.INDUSTRY_ANALYST):
        return SourceQualityTier.TIER_2_ACADEMIC_TRADE
    if category == SourceCategory.REPUTABLE_NEWS:
        return SourceQualityTier.TIER_3_ANALYST_PRESS
    return SourceQualityTier.TIER_4_GENERAL_UNVERIFIED


def calculate_domain_authority_score(domain: Optional[str], category: SourceCategory) -> float:
    """Calculate baseline domain authority score (0.0 - 1.0) based on verified institutional prestige."""
    if not domain:
        return 0.4

    domain_lower = domain.lower()

    if any(
        u in domain_lower
        for u in (
            "twitter.com", "x.com", "reddit.com", "quora.com", "facebook.com",
            "instagram.com", "tiktok.com", "threads.net", "pinterest.com",
            "tumblr.com", "stackoverflow.com", "answers.yahoo.com",
        )
    ):
        return 0.10

    if category == SourceCategory.OFFICIAL_GOVERNMENT:
        return 0.95
    if category == SourceCategory.ACADEMIC_INSTITUTION:
        return 0.90
    if category == SourceCategory.COMPANY_FILING:
        return 0.90
    if category == SourceCategory.TRADE_ASSOCIATION:
        return 0.88
    if category == SourceCategory.FINANCIAL_MARKET_RESEARCH:
        return 0.80
    if category == SourceCategory.INDUSTRY_ANALYST:
        if any(top in domain_lower for top in ("gartner", "idc", "forrester", "mckinsey", "bain", "bcg", "statista")):
            return 0.88
        return 0.80
    if category == SourceCategory.REPUTABLE_NEWS:
        if any(top in domain_lower for top in ("reuters", "bloomberg", "wsj", "ft.com")):
            return 0.85
        return 0.75

    return 0.50


def infer_source_category(domain: Optional[str], url: Optional[str] = None) -> SourceCategory:
    """Infer institutional source category heuristically from domain name without fabricating authority."""
    if not domain:
        return SourceCategory.OTHER

    domain_lower = domain.lower()

    if (
        "sec.gov" in domain_lower
        or "edgar" in domain_lower
        or domain_lower.startswith("investor.")
        or "mca.gov.in" in domain_lower
        or "sebi.gov.in" in domain_lower
    ):
        return SourceCategory.COMPANY_FILING

    if (
        domain_lower.endswith(".gov")
        or ".gov." in domain_lower
        or domain_lower.endswith(".nic.in")
        or domain_lower.endswith(".gov.in")
        or any(
            gov in domain_lower
            for gov in [
                "worldbank.org",
                "imf.org",
                "oecd.org",
                "un.org",
                "who.int",
                "census.gov",
                "rbi.org.in",
                "europa.eu",
                "ons.gov.uk",
            ]
        )
    ):
        return SourceCategory.OFFICIAL_GOVERNMENT

    if (
        domain_lower.endswith(".edu")
        or ".edu." in domain_lower
        or domain_lower.endswith(".ac.in")
        or domain_lower.endswith(".ac.uk")
        or "arxiv.org" in domain_lower
        or "researchgate.net" in domain_lower
    ):
        return SourceCategory.ACADEMIC_INSTITUTION

    if any(
        analyst in domain_lower
        for analyst in [
            "statista.com",
            "gartner.com",
            "forrester.com",
            "idc.com",
            "mckinsey.com",
            "bain.com",
            "bcg.com",
            "grandviewresearch.com",
            "marketsandmarkets.com",
            "mordorintelligence.com",
            "nasscom.in",
            "nasscom.org",
            "frost.com",
            "pitchbook.com",
            "cbinsights.com",
        ]
    ):
        return SourceCategory.INDUSTRY_ANALYST

    if any(
        news in domain_lower
        for news in [
            "reuters.com",
            "bloomberg.com",
            "wsj.com",
            "ft.com",
            "techcrunch.com",
            "economictimes.indiatimes.com",
            "livemint.com",
            "business-standard.com",
            "forbes.com",
            "cnbc.com",
            "thehindu.com",
            "hindustantimes.com",
        ]
    ):
        return SourceCategory.REPUTABLE_NEWS

    return SourceCategory.OTHER


class LiveDiscoveryProvider(BaseDiscoveryProvider):
    """Production-grade external web search discovery provider.
    
    Connects to configured external search backends (e.g. Tavily, SearXNG,
    or generic JSON search APIs) and converts search responses into canonical
    DiscoveredSource objects in the DISCOVERED lifecycle stage.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider_type: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.provider_type = (provider_type or settings.SEARCH_PROVIDER or "live").lower()
        self.api_url = api_url or settings.SEARCH_API_URL
        import os
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if tavily_key is None:
            tavily_key = getattr(settings, "TAVILY_API_KEY", None)

        search_key = os.environ.get("SEARCH_API_KEY")
        if search_key is None:
            search_key = getattr(settings, "SEARCH_API_KEY", None)

        resolved_key = (
            (tavily_key.strip() if tavily_key and tavily_key.strip() else None)
            or (search_key.strip() if search_key and search_key.strip() else None)
        )
        self.api_key = api_key if api_key is not None else resolved_key
        self.timeout_seconds = timeout_seconds or settings.SEARCH_TIMEOUT_SECONDS
        self.custom_headers = custom_headers or {}

        # Default Tavily endpoint if provider is tavily or live without explicit URL
        if not self.api_url and self.provider_type in ("tavily", "live"):
            self.api_url = "https://api.tavily.com/search"

    def build_query_string(self, query: ResearchQuery) -> str:
        """Construct a standardized search query string from structured research query parameters."""
        parts: List[str] = [query.metric_required.strip()]
        if query.target_population:
            parts.append(query.target_population.strip())
        if query.industry_topic:
            parts.append(query.industry_topic.strip())
        if query.geography:
            parts.append(query.geography.strip())
        if query.year:
            parts.append(str(query.year))
        return " ".join(parts)

    def _mask_api_key(self, key: Optional[str]) -> str:
        """Mask API key for safe logging."""
        if not key:
            return "<none>"
        if len(key) <= 6:
            return "***"
        return f"{key[:3]}...{key[-3:]}"

    async def search(self, query: ResearchQuery) -> List[DiscoveredSource]:
        """Execute a live search against the configured provider and return DiscoveredSource records."""
        query_string = self.build_query_string(query)
        logger.info(
            "Executing live search discovery [provider=%s, url=%s, key=%s] for query: '%s'",
            self.provider_type,
            self.api_url or "<not configured>",
            self._mask_api_key(self.api_key),
            query_string,
        )

        if not self.api_url:
            raise DiscoveryProviderUnavailableException(
                f"Search provider '{self.provider_type}' is missing SEARCH_API_URL configuration."
            )

        # Build request parameters based on provider type
        headers = {
            "User-Agent": settings.SOURCE_FETCH_USER_AGENT,
            "Accept": "application/json",
            **self.custom_headers,
        }

        request_method = "POST"
        request_kwargs: Dict[str, Any] = {"headers": headers}

        if self.provider_type in ("tavily", "live"):
            if not self.api_key:
                raise DiscoveryProviderException(
                    f"Search provider '{self.provider_type}' requires TAVILY_API_KEY or SEARCH_API_KEY to be configured."
                )
            request_kwargs["json"] = {
                "api_key": self.api_key,
                "query": query_string,
                "max_results": query.max_results,
                "search_depth": "basic",
                "include_answer": False,
            }
        elif self.provider_type == "searxng":
            request_method = "GET"
            params = {
                "q": query_string,
                "format": "json",
                "categories": "general",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            request_kwargs["params"] = params
        else:
            # Generic / Custom JSON provider
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["X-API-Key"] = self.api_key
            request_kwargs["json"] = {
                "query": query_string,
                "max_results": query.max_results,
            }

        try:
            transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=1)
            async with httpx.AsyncClient(
                transport=transport,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                if request_method == "POST":
                    response = await client.post(self.api_url, **request_kwargs)
                else:
                    response = await client.get(self.api_url, **request_kwargs)

                if response.status_code == 429:
                    raise DiscoveryProviderUnavailableException(
                        "Search provider rate limit reached (HTTP 429). Please retry later."
                    )
                if response.status_code in (401, 403):
                    raise DiscoveryProviderException(
                        f"Search provider authentication failed (HTTP {response.status_code}). "
                        "Please verify your SEARCH_API_KEY."
                    )
                if response.status_code >= 500:
                    raise DiscoveryProviderUnavailableException(
                        f"Search provider server error (HTTP {response.status_code})."
                    )
                if response.status_code != 200:
                    raise DiscoveryProviderException(
                        f"Search provider returned unexpected status HTTP {response.status_code}: {response.text[:200]}"
                    )

                try:
                    payload = response.json()
                except Exception as json_err:
                    raise DiscoveryProviderException(
                        f"Failed to parse JSON response from search provider: {json_err}"
                    ) from json_err

        except httpx.TimeoutException as exc:
            logger.error("Live discovery timed out after %ss for query: '%s'", self.timeout_seconds, query_string)
            raise DiscoveryProviderUnavailableException(
                f"Discovery search request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except (DiscoveryProviderException, DiscoveryProviderUnavailableException):
            raise
        except httpx.RequestError as exc:
            logger.error("HTTP request error during live discovery for '%s': %s", query_string, exc)
            raise DiscoveryProviderUnavailableException(
                f"Network communication error connecting to search provider: {exc}"
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during live search discovery: %s", exc)
            raise DiscoveryProviderException(f"Unexpected live search failure: {exc}") from exc

        return self._parse_results(payload, query_string=query_string, max_results=query.max_results)

    def _parse_results(
        self,
        payload: Any,
        query_string: str,
        max_results: int,
    ) -> List[DiscoveredSource]:
        """Extract and normalize candidate DiscoveredSource records from raw provider response."""
        raw_items: List[Dict[str, Any]] = []

        if isinstance(payload, list):
            raw_items = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            # Inspect common JSON search result keys
            for key in ("results", "organic_results", "items", "data", "webPages"):
                val = payload.get(key)
                if isinstance(val, list):
                    raw_items = [item for item in val if isinstance(item, dict)]
                    break
                if isinstance(val, dict) and isinstance(val.get("value"), list):
                    raw_items = [item for item in val.get("value") if isinstance(item, dict)]
                    break

        if not raw_items:
            logger.info("Search provider returned 0 results for query: '%s'", query_string)
            return []

        results: List[DiscoveredSource] = []
        for raw in raw_items:
            # Extract URL
            url = raw.get("url") or raw.get("link") or raw.get("formattedUrl")
            if not url or not isinstance(url, str):
                continue
            url = url.strip()
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                logger.debug("Skipping result with invalid or non-http(s) URL: '%s'", url)
                continue

            # Extract Title
            title = raw.get("title") or raw.get("name") or raw.get("heading")
            if not title or not isinstance(title, str) or not title.strip():
                title = f"Document at {parsed.netloc}"
            title = title.strip()

            # Extract Snippet
            snippet = raw.get("content") or raw.get("snippet") or raw.get("description") or raw.get("body")
            if snippet is not None and not isinstance(snippet, str):
                snippet = str(snippet)
            if snippet:
                snippet = snippet.strip()

            # Extract Source Name
            source_name = raw.get("source") or raw.get("source_name") or raw.get("publisher") or parsed.netloc

            # Extract Publication Date
            pub_date = raw.get("published_date") or raw.get("publishedDate") or raw.get("date")
            if pub_date is not None and not isinstance(pub_date, str):
                pub_date = str(pub_date)

            # Extract Relevance Score
            score_raw = raw.get("score") or raw.get("relevance") or raw.get("relevance_score")
            relevance_score: Optional[float] = None
            if score_raw is not None:
                try:
                    score_val = float(score_raw)
                    relevance_score = max(0.0, min(1.0, score_val))
                except (ValueError, TypeError):
                    relevance_score = None

            domain = parsed.netloc.lower()
            category = infer_source_category(domain=domain, url=url)
            if relevance_score is None:
                relevance_score = calculate_domain_authority_score(domain, category)

            try:
                tier = infer_source_quality_tier(category, domain)
                source_record = DiscoveredSource(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_name=source_name,
                    domain=domain,
                    publication_date=pub_date,
                    category=category,
                    source_quality_tier=tier,
                    lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                    discovery_timestamp=datetime.now(timezone.utc).isoformat(),
                    relevance_score=relevance_score,
                    query_used=query_string,
                )
                results.append(source_record)
            except Exception as item_err:
                logger.debug("Skipping item due to validation error: %s", item_err)
                continue

            if len(results) >= max_results:
                break

        return results
