from __future__ import annotations

from dataclasses import dataclass, field

from lessley_deals.domain.models import PriceInfo, RawScrapedRecord


@dataclass
class NormalizationContext:
    """Mutable state threaded through the normalization pipeline."""

    raw: RawScrapedRecord
    store_name: str  # mutated through steps
    deal_description: str
    price: PriceInfo | None = None
    domain: str | None = None
    branch: str | None = None
    warnings: list[str] = field(default_factory=list)
