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
        """Retrieve content from a DiscoveredSource schema record."""
        if source.is_mock:
            content_to_use = source.mock_content or source.snippet or (
                f"Statistical and market report for {source.title}. "
                f"Source reference documentation covering {source.source_name or 'official sources'}."
            )
            logger.info("Serving local mock fixture content for: %s", source.url)
            from app.fetching.models import FetchStatus
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
        return await self.fetcher.fetch(
            url=source.url,
            title=source.title,
            source_name=source.source_name,
        )


def get_fetch_service() -> SourceFetchService:
    """Dependency provider for SourceFetchService."""
    return SourceFetchService()
