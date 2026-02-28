"""Base HTTP crawler with encoding support and retry logic."""

import asyncio
from typing import Optional

import httpx
import structlog

from dich_truyen.config import CrawlerConfig, get_config
from dich_truyen.utils.encoding import decode_content, detect_encoding

logger = structlog.get_logger()


class BaseCrawler:
    """HTTP client with encoding support and retry logic."""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """Initialize the crawler.

        Args:
            config: Crawler configuration, uses global config if None
        """
        self.config = config or get_config().crawler
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BaseCrawler":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raise if not initialized."""
        if self._client is None:
            raise RuntimeError("Crawler not initialized. Use 'async with' context manager.")
        return self._client

    async def fetch_raw(self, url: str) -> bytes:
        """Fetch URL content as raw bytes.

        Args:
            url: URL to fetch

        Returns:
            Raw bytes content
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                return response.content

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning("http_error", status=e.response.status_code, url=url)
                if e.response.status_code in (403, 404, 410):
                    raise  # Don't retry these

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning("fetch_retry", attempt=attempt + 1, error=str(e), url=url)

            if attempt < self.config.max_retries:
                delay = self.config.delay_ms / 1000 * (attempt + 1)
                await asyncio.sleep(delay)

        raise last_error or RuntimeError(f"Failed to fetch {url}")

    async def fetch(self, url: str, encoding: Optional[str] = None) -> str:
        """Fetch URL content as decoded string.

        Args:
            url: URL to fetch
            encoding: Optional explicit encoding, auto-detect if None

        Returns:
            Decoded string content
        """
        content = await self.fetch_raw(url)

        if encoding is None:
            encoding = detect_encoding(content)

        return decode_content(content, encoding)

    async def delay(self) -> None:
        """Wait for the configured delay between requests."""
        await asyncio.sleep(self.config.delay_ms / 1000)


async def fetch_page(url: str, encoding: Optional[str] = None) -> str:
    """Convenience function to fetch a single page.

    Args:
        url: URL to fetch
        encoding: Optional explicit encoding

    Returns:
        Decoded page content
    """
    async with BaseCrawler() as crawler:
        return await crawler.fetch(url, encoding)
