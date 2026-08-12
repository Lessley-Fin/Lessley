from __future__ import annotations

import asyncio
import logging
from types import TracebackType

import httpx

from lessley_deals.scraping.base import RetryConfig, SourceConfig

logger = logging.getLogger(__name__)


class HttpClient:
    """Rate-limited async HTTP client with exponential-backoff retry.

    Designed to be used as an async context manager::

        async with HttpClient(config) as client:
            resp = await client.get("https://example.com/api")
    """

    def __init__(self, config: SourceConfig) -> None:
        self._config = config
        # Concurrency gate – limits in-flight requests to ~rate_limit_rps
        max_concurrent = max(1, int(config.rate_limit_rps))
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._min_interval = 1.0 / config.rate_limit_rps if config.rate_limit_rps > 0 else 0.0
        self._client: httpx.AsyncClient | None = None

    # -- context-manager support ------------------------------------------

    async def __aenter__(self) -> HttpClient:
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            headers=self._config.headers,
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- public API -------------------------------------------------------

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a GET request through the rate-limiter with retry."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a POST request through the rate-limiter with retry."""
        return await self._request("POST", url, **kwargs)

    # -- internals --------------------------------------------------------

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("HttpClient must be used as an async context manager")

        retry_cfg: RetryConfig = self._config.retry
        last_exc: Exception | None = None

        for attempt in range(1 + retry_cfg.max_retries):
            async with self._semaphore:
                try:
                    response = await self._client.request(method, url, **kwargs)  # type: ignore[arg-type]
                    response.raise_for_status()
                    return response
                except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                    last_exc = exc
                    if attempt < retry_cfg.max_retries:
                        delay = min(
                            retry_cfg.base_delay * (2 ** attempt),
                            retry_cfg.max_delay,
                        )
                        logger.warning(
                            "Request %s %s failed (attempt %d/%d): %s – retrying in %.1fs",
                            method,
                            url,
                            attempt + 1,
                            1 + retry_cfg.max_retries,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "Request %s %s failed after %d attempts: %s",
                            method,
                            url,
                            1 + retry_cfg.max_retries,
                            exc,
                        )

                # Respect rate-limit between consecutive requests
                if self._min_interval > 0:
                    await asyncio.sleep(self._min_interval)

        # Should not be reachable, but keeps mypy happy
        raise last_exc  # type: ignore[misc]
