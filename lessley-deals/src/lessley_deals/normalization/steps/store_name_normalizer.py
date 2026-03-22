from __future__ import annotations

from lessley_deals.normalization.text import extract_branch, extract_domain, strip_legal_suffixes
from lessley_deals.normalization.types import NormalizationContext


class StoreNameNormalizerStep:
    """Normalize store name: strip legal suffixes, extract branch, extract domain."""

    def apply(self, ctx: NormalizationContext) -> None:
        ctx.store_name = strip_legal_suffixes(ctx.store_name)
        ctx.store_name, ctx.branch = extract_branch(ctx.store_name)
        ctx.domain = extract_domain(ctx.raw.url)
