import json
import logging
from typing import Optional, Set
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.fetching.base import BaseSourceFetcher
from app.fetching.html_utils import extract_text_from_html
from app.fetching.models import FetchedSource, FetchStatus
from app.fetching.security import is_safe_url
from app.schemas.discovery import DiscoveryLifecycleStage

logger = logging.getLogger(__name__)

SUPPORTED_HTML_TYPES: Set[str] = {
    "text/html",
    "application/xhtml+xml",
}

SUPPORTED_TEXT_TYPES: Set[str] = {
    "text/plain",
    "text/markdown",
    "text/csv",
}

SUPPORTED_JSON_TYPES: Set[str] = {
    "application/json",
    "text/json",
}


class HttpSourceFetcher(BaseSourceFetcher):
    """HTTP client fetcher with size limits, timeout guards, and SSRF security protections."""

    def __init__(
        self,
        timeout_seconds: Optional[float] = None,
        max_bytes: Optional[int] = None,
        user_agent: Optional[str] = None,
        allow_private_ips: bool = False,
    ) -> None:
        self.timeout_seconds = timeout_seconds or settings.SOURCE_FETCH_TIMEOUT_SECONDS
        self.max_bytes = max_bytes or settings.SOURCE_FETCH_MAX_BYTES
        self.user_agent = user_agent or settings.SOURCE_FETCH_USER_AGENT
        self.allow_private_ips = allow_private_ips

    async def fetch(
        self,
        url: str,
        title: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> FetchedSource:
        """Fetch, sanitize, and extract readable text from a target HTTP/HTTPS URL."""
        # 1. Security & SSRF check
        if not is_safe_url(url, allow_private_ips=self.allow_private_ips):
            logger.warning("Blocked unsafe URL fetch attempt: %s", url)
            return FetchedSource(
                original_url=url,
                title=title,
                source_name=source_name,
                fetch_status=FetchStatus.BLOCKED,
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                error_message="URL failed security validation (private, internal, or invalid address).",
            )

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    final_url = str(response.url)
                    http_status = response.status_code

                    if http_status >= 400:
                        logger.warning("Fetch returned HTTP %d for %s", http_status, url)
                        return FetchedSource(
                            original_url=url,
                            final_url=final_url,
                            title=title,
                            source_name=source_name,
                            http_status=http_status,
                            fetch_status=FetchStatus.FETCH_FAILED,
                            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                            error_message=f"HTTP request failed with status code {http_status}.",
                        )

                    # Content-type detection
                    content_type_header = response.headers.get("content-type", "").lower()
                    mime_type = content_type_header.split(";")[0].strip()

                    is_html = mime_type in SUPPORTED_HTML_TYPES
                    is_text = mime_type in SUPPORTED_TEXT_TYPES
                    is_json = mime_type in SUPPORTED_JSON_TYPES

                    if not (is_html or is_text or is_json):
                        logger.info("Unsupported content type '%s' for %s", mime_type, url)
                        return FetchedSource(
                            original_url=url,
                            final_url=final_url,
                            title=title,
                            source_name=source_name,
                            content_type=mime_type,
                            http_status=http_status,
                            fetch_status=FetchStatus.UNSUPPORTED_CONTENT,
                            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                            error_message=f"Unsupported MIME content-type: '{mime_type}'. Supported: HTML, plain text, JSON.",
                        )

                    # Download content with max byte enforcement
                    body_chunks = []
                    total_bytes = 0

                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > self.max_bytes:
                            logger.warning("Response for %s exceeded maximum limit of %d bytes", url, self.max_bytes)
                            return FetchedSource(
                                original_url=url,
                                final_url=final_url,
                                title=title,
                                source_name=source_name,
                                content_type=mime_type,
                                http_status=http_status,
                                content_length_bytes=total_bytes,
                                fetch_status=FetchStatus.OVERSIZED,
                                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                                error_message=f"Response exceeded maximum allowed size of {self.max_bytes} bytes.",
                            )
                        body_chunks.append(chunk)

                    raw_body = b"".join(body_chunks)
                    encoding = response.encoding or "utf-8"
                    decoded_text = raw_body.decode(encoding, errors="replace")

        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.TimeoutException) as exc:
            logger.warning("Fetch timed out after %s seconds for %s", self.timeout_seconds, url)
            return FetchedSource(
                original_url=url,
                title=title,
                source_name=source_name,
                fetch_status=FetchStatus.TIMEOUT,
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                error_message=f"Request timed out after {self.timeout_seconds} seconds: {exc}",
            )
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPError) as exc:
            logger.warning("Network connection failed for %s: %s", url, exc)
            return FetchedSource(
                original_url=url,
                title=title,
                source_name=source_name,
                fetch_status=FetchStatus.FETCH_FAILED,
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                error_message=f"Network connection failed: {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected error fetching %s: %s", url, exc)
            return FetchedSource(
                original_url=url,
                title=title,
                source_name=source_name,
                fetch_status=FetchStatus.FETCH_FAILED,
                lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
                error_message=f"Unexpected error during fetch: {exc}",
            )

        # 2. Extract textual content from supported formats
        orig_domain = urlparse(url).netloc.lower()
        final_domain = urlparse(final_url).netloc.lower() if final_url else orig_domain
        is_cross_domain = bool(final_domain and orig_domain and orig_domain != final_domain)

        extracted_content = ""
        extracted_title = title
        effective_source_name = None if is_cross_domain else source_name

        if is_html:
            clean_text, parsed_title = extract_text_from_html(decoded_text)
            extracted_content = clean_text
            if is_cross_domain and parsed_title:
                extracted_title = parsed_title
            elif not extracted_title and parsed_title:
                extracted_title = parsed_title
        elif is_json:
            try:
                parsed_json = json.loads(decoded_text)
                extracted_content = json.dumps(parsed_json, indent=2)
            except Exception:
                extracted_content = decoded_text
        else:
            extracted_content = decoded_text.strip()

        return FetchedSource(
            original_url=url,
            final_url=final_url,
            title=extracted_title,
            content=extracted_content,
            content_type=mime_type,
            http_status=http_status,
            content_length_bytes=len(raw_body),
            fetch_status=FetchStatus.SUCCESS,
            lifecycle_stage=DiscoveryLifecycleStage.FETCHED,
            source_name=effective_source_name,
            is_redirected=bool(final_url and final_url != url),
            is_cross_domain_redirect=is_cross_domain,
        )
