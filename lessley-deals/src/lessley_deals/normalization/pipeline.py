from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable, Protocol

from lessley_deals.domain.models import NameForms, NormalizedRecord, RawScrapedRecord
from lessley_deals.normalization.hebrew_utils import normalize_final_forms, normalize_hebrew
from lessley_deals.normalization.text import collapse_whitespace
from lessley_deals.normalization.types import NormalizationContext


class NormalizationStep(Protocol):
    def apply(self, ctx: NormalizationContext) -> None: ...


class NormalizationPipeline:
    """Runs a sequence of normalization steps over a raw record."""

    def __init__(self, steps: list[NormalizationStep]) -> None:
        self._steps = steps

    def normalize(self, raw: RawScrapedRecord) -> NormalizedRecord:
        ctx = NormalizationContext(
            raw=raw,
            store_name=raw.store_name,
            deal_description=raw.deal_description,
        )

        for step in self._steps:
            step.apply(ctx)

        name_forms = self._build_name_forms(ctx.store_name)

        return NormalizedRecord(
            raw_id=raw.id,
            source_id=raw.source_id,
            store_name_forms=name_forms,
            deal_description=ctx.deal_description,
            normalized_at=datetime.now(timezone.utc),
            price=ctx.price,
            domain=ctx.domain,
        )

    @staticmethod
    def _build_name_forms(store_name: str) -> NameForms:
        normalized = collapse_whitespace(normalize_hebrew(store_name)).lower()

        # compact: remove all spaces and punctuation, then normalize final forms
        compact = re.sub(r"[\s\W]+", "", normalized)
        compact = normalize_final_forms(compact)

        # tokens: sorted unique words longer than 1 character
        tokens = tuple(sorted({w for w in normalized.split() if len(w) > 1}))

        return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def create_default_pipeline() -> NormalizationPipeline:
    """Create a pipeline with all default normalization steps."""
    from lessley_deals.normalization.steps.deal_text_normalizer import DealTextNormalizerStep
    from lessley_deals.normalization.steps.hebrew_normalizer import HebrewNormalizerStep
    from lessley_deals.normalization.steps.price_normalizer import PriceNormalizerStep
    from lessley_deals.normalization.steps.store_name_normalizer import StoreNameNormalizerStep
    from lessley_deals.normalization.steps.text_cleaner import TextCleanerStep

    return NormalizationPipeline([
        TextCleanerStep(),
        HebrewNormalizerStep(),
        StoreNameNormalizerStep(),
        DealTextNormalizerStep(),
        PriceNormalizerStep(),
    ])
