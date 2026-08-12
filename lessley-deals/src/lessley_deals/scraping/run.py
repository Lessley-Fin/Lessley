from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from lessley_deals.domain.models import RawScrapedRecord, RawStore


@dataclass
class SourceRunResult:
    """Outcome of scraping a single source."""

    source_id: str
    stores: list[RawStore]
    deals: list[RawScrapedRecord]
    errors: list[str]
    started_at: datetime
    finished_at: datetime

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


@dataclass
class ScrapeRun:
    """Outcome of a full orchestrated scrape across all sources."""

    run_id: str
    started_at: datetime
    finished_at: datetime | None
    results: list[SourceRunResult] = field(default_factory=list)

    @property
    def total_stores(self) -> int:
        return sum(len(r.stores) for r in self.results)

    @property
    def total_deals(self) -> int:
        return sum(len(r.deals) for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results)
