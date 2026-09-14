from abc import ABC, abstractmethod
from typing import Optional

from app.fetching.models import FetchedSource


class BaseSourceFetcher(ABC):
    """Abstract base class for all document fetching implementations."""

    @abstractmethod
    async def fetch(
        self,
        url: str,
        title: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> FetchedSource:
        """Retrieve and process content from a target URL."""
        pass
