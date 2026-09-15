import logging
from typing import Optional

from app.fetching.base import BaseSourceFetcher
from app.fetching.http_fetcher import HttpSourceFetcher
from app.fetching.models import FetchedSource, FetchRequest
from app.schemas.discovery import DiscoveredSource

logger = logging.getLogger(__name__)


class SourceFetchService:
    """Service orchestrating safe content retrieval from discovered evidence sources."""

    def __init__(self, fetcher: Optional[BaseSourceFetcher] = None) -> None:
        self.fetcher = fetcher or HttpSourceFetcher()

    async def fetch_source(self, request: FetchRequest) -> FetchedSource:
        """Retrieve and process content for a FetchRequest."""
        logger.info("Executing source fetch for URL: %s", request.url)
        return await self.fetcher.fetch(
            url=request.url,
            title=request.title,
            source_name=request.source_name,
        )

    async def fetch_discovered_source(self, source: DiscoveredSource) -> FetchedSource:
        """Retrieve content from a DiscoveredSource schema record.
        
        If direct HTTP retrieval fails (e.g. HTTP 403/401, Cloudflare bot wall, timeout, or blocked)
        and a non-empty discovery snippet was returned by the search provider, the snippet is used
        as fallback evidence content with status SNIPPET_FALLBACK.
        """
        from app.fetching.models import FetchStatus

        if source.is_mock:
            content_to_use = source.mock_content or source.snippet or (
                f"Statistical and market report for {source.title}. "
                f"Source reference documentation covering {source.source_name or 'official sources'}."
            )
            logger.info("Serving local mock fixture content for: %s", source.url)
            return FetchedSource(
                original_url=source.url,
                url=source.url,
                fetch_status=FetchStatus.SUCCESS,
                http_status_code=200,
                content=content_to_use,
                extracted_text=content_to_use,
                source_name=source.source_name,
                title=source.title,
                content_type="text/html",
                content_length_bytes=len(content_to_use.encode("utf-8")),
            )

        fetched = await self.fetcher.fetch(
            url=source.url,
            title=source.title,
            source_name=source.source_name,
        )

        # Check if direct fetch failed / returned empty content
        is_failed = (
            fetched.fetch_status != FetchStatus.SUCCESS
            or not fetched.content
            or not fetched.content.strip()
            or (fetched.http_status is not None and fetched.http_status >= 400)
        )

        if is_failed and source.snippet and source.snippet.strip():
            snippet_clean = source.snippet.strip()
            logger.info(
                "Direct HTTP fetch failed (status=%s, http=%s) for %s; using discovered search snippet fallback (%d chars).",
                fetched.fetch_status,
                fetched.http_status,
                source.url,
                len(snippet_clean),
            )
            return FetchedSource(
                original_url=source.url,
                final_url=fetched.final_url or source.url,
                title=source.title,
                source_name=source.source_name,
                domain=source.domain,
                content=snippet_clean,
                content_type="text/plain",
                http_status=fetched.http_status,
                content_length_bytes=len(snippet_clean.encode("utf-8")),
                fetch_status=FetchStatus.SNIPPET_FALLBACK,
                lifecycle_stage="fetched",
                error_message=(
                    f"Direct fetch returned status '{fetched.fetch_status}' "
                    f"(HTTP {fetched.http_status}). Discovered search snippet used as fallback."
                ),
            )

        return fetched


def get_fetch_service() -> SourceFetchService:
    """Dependency provider for SourceFetchService."""
    return SourceFetchService()
