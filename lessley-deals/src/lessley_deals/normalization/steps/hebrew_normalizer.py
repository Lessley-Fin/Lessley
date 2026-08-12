from __future__ import annotations

from lessley_deals.normalization.hebrew_utils import normalize_hebrew
from lessley_deals.normalization.types import NormalizationContext


class HebrewNormalizerStep:
    """Apply Hebrew-specific text normalization to store name and deal description."""

    def apply(self, ctx: NormalizationContext) -> None:
        ctx.store_name = normalize_hebrew(ctx.store_name)
        ctx.deal_description = normalize_hebrew(ctx.deal_description)
