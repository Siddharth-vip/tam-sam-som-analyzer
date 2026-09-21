import logging
from typing import List, Optional, Tuple

from app.config import settings
from app.discovery.base import (
    BaseDiscoveryProvider,
    DiscoveryProviderException,
    DiscoveryProviderUnavailableException,
)
from app.discovery.live_provider import LiveDiscoveryProvider
from app.discovery.mock_provider import MockDiscoveryProvider
from app.schemas.discovery import (
    DiscoveredSource,
    DiscoveryLifecycleStage,
    DiscoveryResponse,
    DiscoveryStatus,
    ResearchQuery,
    SourceCategory,
)

logger = logging.getLogger(__name__)


class DiscoveryServiceException(Exception):
    """Base exception for discovery service failures."""
    pass


def get_discovery_provider(provider_type: Optional[str] = None) -> BaseDiscoveryProvider:
    """Factory creating the configured discovery provider instance."""
    selected = (provider_type or settings.SEARCH_PROVIDER or "mock").strip().lower()
    if selected in ("live", "tavily", "searxng", "custom"):
        return LiveDiscoveryProvider(provider_type=selected)
    return MockDiscoveryProvider()


REJECTED_SOURCE_TOPICS = [
    "linux distribution", "linux distributions", "linux distro", "linux distros", "ubuntu lts",
    "open source llm", "top llms", "llm model", "llm list",
    "wordpress speed", "wordpress optimization", "wordpress tips", "wordpress plugin",
    "apache kafka", "kafka beginner", "kafka tutorial",
    "bird", "birds", "wildlife", "animal species",
    "10 simple tips", "16 best linux", "14 top outstanding",
    "top 10 best", "10 best tools", "top 20 tools", "7 reasons to", "5 factors driving",
    "6 factors propelling", "5 trends shaping", "8 challenges in",
]


def is_source_relevant(
    source: DiscoveredSource,
    query: ResearchQuery,
) -> tuple[bool, str]:
    """Deterministically and semantically assess if a discovered source is relevant to the research query.
    
    Evaluates:
    1. Rejection of listicle patterns, tech tutorial articles, software versioning notes, and flora/fauna.
    2. Semantic topical alignment with the query's business domain, target population, geography, and metric intent.
    """
    text_corpus = f"{source.title} {source.snippet or ''} {source.url}".lower()

    # 1. Reject specific irrelevant technology tutorials, listicles, or non-market topics
    for topic in REJECTED_SOURCE_TOPICS:
        if topic in text_corpus:
            return False, f"Source rejected: matches irrelevant topic/listicle pattern '{topic}'."

    # 2. Extract significant query concepts (removing generic stop words)
    stop_words = {
        "and", "the", "for", "with", "from", "that", "this", "about", "into",
        "over", "under", "count", "number", "data", "report", "survey", "stats",
        "statistics", "study", "analysis", "market", "annual",
    }
    raw_query_words = (
        f"{query.metric_required} {query.target_population or ''} {query.industry_topic or ''} {query.geography or ''}"
    ).lower().split()
    
    domain_terms = [w.strip(".,;:()[]\"'") for w in raw_query_words if len(w) > 2 and w not in stop_words]

    # Demographic / target population terms
    pop_terms = [
        w for w in (query.target_population or query.metric_required).lower().split()
        if len(w) > 2 and w not in stop_words
    ]
    # Industry / topic terms
    topic_terms = [
        w for w in (query.industry_topic or "").lower().split()
        if len(w) > 2 and w not in stop_words
    ]
    # Geography terms
    geo_terms = [
        w for w in (query.geography or "").lower().split()
        if len(w) > 2 and w not in stop_words
    ]

    matched_pop = any(t in text_corpus for t in pop_terms) if pop_terms else True
    matched_topic = any(t in text_corpus for t in topic_terms) if topic_terms else True
    matched_geo = any(t in text_corpus for t in geo_terms) if geo_terms else True
    all_matched_terms = [t for t in domain_terms if t in text_corpus]

    # High authority official / academic / analyst sources
    is_authoritative_domain = source.category in (
        SourceCategory.OFFICIAL_GOVERNMENT,
        SourceCategory.NATIONAL_STATISTICS,
        SourceCategory.INDUSTRY_ANALYST,
        SourceCategory.ACADEMIC_INSTITUTION,
    )

    if is_authoritative_domain:
        # Must have at least some topical or geographic alignment
        if len(all_matched_terms) > 0 or matched_pop or matched_topic or matched_geo:
            return True, f"Accepted: Authoritative domain source with domain keyword overlap ({', '.join(all_matched_terms[:3]) or 'topical'})."
        return False, "Source rejected: Authoritative domain but lacks topical/geographic overlap with research query."

    # General web sources require sufficient keyword alignment
    if len(all_matched_terms) >= 2 or (matched_pop and matched_topic) or (matched_pop and matched_geo):
        return True, f"Accepted: Semantically relevant to research intent ({', '.join(all_matched_terms[:3])})."

    if source.relevance_score is not None and source.relevance_score >= 0.7 and len(all_matched_terms) >= 1:
        return True, f"Accepted: High relevance score ({source.relevance_score}) with query term match."

    return False, "Source rejected: Insufficient semantic overlap with business concept and research query."


def filter_relevant_sources(
    sources: List[DiscoveredSource],
    query: ResearchQuery,
) -> tuple[List[DiscoveredSource], List[DiscoveredSource]]:
    """Separate discovered sources into relevant and rejected subsets."""
    relevant: List[DiscoveredSource] = []
    rejected: List[DiscoveredSource] = []

    for src in sources:
        is_rel, reason = is_source_relevant(src, query)
        if is_rel:
            src.relevance_status = "accepted"
            src.relevance_reason = reason
            relevant.append(src)
        else:
            src.relevance_status = "rejected"
            src.relevance_reason = reason
            rejected.append(src)

    return relevant, rejected


class DiscoveryService:
    """Service responsible for orchestrating external source discovery for market research."""

    def __init__(self, provider: Optional[BaseDiscoveryProvider] = None) -> None:
        self.provider = provider or get_discovery_provider()

    def build_query_string(self, query: ResearchQuery) -> str:
        """Construct the search query string from research query parameters."""
        return self.provider.build_query_string(query)

    def is_source_relevant(
        self,
        source: DiscoveredSource,
        query: ResearchQuery,
    ) -> tuple[bool, str]:
        """Deterministically assess if a discovered source is relevant to the research query."""
        return is_source_relevant(source, query)

    def filter_relevant_sources(
        self,
        sources: List[DiscoveredSource],
        query: ResearchQuery,
    ) -> tuple[List[DiscoveredSource], List[DiscoveredSource]]:
        """Separate discovered sources into relevant and rejected subsets."""
        return filter_relevant_sources(sources, query)

    async def discover_sources(self, query: ResearchQuery) -> DiscoveryResponse:
        """Execute source discovery for a structured research query."""
        query_string = self.build_query_string(query)

        try:
            discovered_sources = await self.provider.search(query)
        except DiscoveryProviderUnavailableException as exc:
            logger.error("Discovery provider is unavailable for query '%s': %s", query_string, exc)
            return DiscoveryResponse(
                query=query,
                query_string=query_string,
                status=DiscoveryStatus.FAILED,
                total_results_found=0,
                sources=[],
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                message=f"Discovery provider is currently unavailable: {exc}",
            )
        except DiscoveryProviderException as exc:
            logger.error("Discovery provider error for query '%s': %s", query_string, exc)
            return DiscoveryResponse(
                query=query,
                query_string=query_string,
                status=DiscoveryStatus.FAILED,
                total_results_found=0,
                sources=[],
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                message=f"Discovery provider failed: {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected error during source discovery for query '%s': %s", query_string, exc)
            raise DiscoveryServiceException(f"Discovery search failed unexpectedly: {exc}") from exc

        if not discovered_sources:
            return DiscoveryResponse(
                query=query,
                query_string=query_string,
                status=DiscoveryStatus.NO_RESULTS,
                total_results_found=0,
                sources=[],
                lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
                message="No sources discovered for the specified research query.",
            )

        # Enforce lifecycle boundary: ensure all sources are tagged DISCOVERED
        is_mock_provider = isinstance(self.provider, MockDiscoveryProvider)
        for source in discovered_sources:
            source.lifecycle_stage = DiscoveryLifecycleStage.DISCOVERED
            source.is_mock = is_mock_provider
            if not source.query_used:
                source.query_used = query_string

        return DiscoveryResponse(
            query=query,
            query_string=query_string,
            status=DiscoveryStatus.SUCCESS,
            total_results_found=len(discovered_sources),
            sources=discovered_sources,
            lifecycle_stage=DiscoveryLifecycleStage.DISCOVERED,
            message=f"Successfully discovered {len(discovered_sources)} potential evidence source(s).",
        )


def get_discovery_service() -> DiscoveryService:
    """Dependency provider for DiscoveryService."""
    return DiscoveryService(provider=get_discovery_provider())
