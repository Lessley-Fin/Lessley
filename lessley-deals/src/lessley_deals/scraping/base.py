from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from lessley_deals.domain.models import RawScrapedRecord, RawStore


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0


@dataclass(frozen=True)
class SourceConfig:
    """Per-source configuration for a scraper adapter."""

    base_url: str
    rate_limit_rps: float = 2.0
    timeout_seconds: float = 30.0
    retry: RetryConfig = field(default_factory=RetryConfig)
    headers: dict[str, str] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    """Abstract base class every scraper source must implement."""

    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this data source (e.g. ``"shufersal"``)."""
        ...

    @abstractmethod
    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Run the scraping process and return discovered stores and deals."""
        ...

    async def health_check(self) -> bool:
        """Optional connectivity / readiness check.  Defaults to *True*."""
        return True
