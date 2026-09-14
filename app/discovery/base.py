from abc import ABC, abstractmethod
from typing import List

from app.schemas.discovery import DiscoveredSource, ResearchQuery


class DiscoveryProviderException(Exception):
    """Base exception for discovery provider errors."""
    pass


class DiscoveryProviderUnavailableException(DiscoveryProviderException):
    """Raised when an external discovery provider is unreachable or times out."""
    pass


class BaseDiscoveryProvider(ABC):
    """Abstract base class for all market evidence search and discovery providers."""

    @abstractmethod
    def build_query_string(self, query: ResearchQuery) -> str:
        """Construct a formatted search query string from structured query parameters."""
        pass

    @abstractmethod
    async def search(self, query: ResearchQuery) -> List[DiscoveredSource]:
        """Execute a search against the provider and return discovered source records."""
        pass
