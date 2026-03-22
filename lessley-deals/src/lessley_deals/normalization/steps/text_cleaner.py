from __future__ import annotations

from lessley_deals.normalization.hebrew_utils import strip_zero_width
from lessley_deals.normalization.text import collapse_whitespace, normalize_punctuation
from lessley_deals.normalization.types import NormalizationContext


class TextCleanerStep:
    """First pipeline step: basic text cleanup on both store name and deal description."""

    def apply(self, ctx: NormalizationContext) -> None:
        ctx.store_name = self._clean(ctx.store_name)
        ctx.deal_description = self._clean(ctx.deal_description)

    @staticmethod
    def _clean(text: str) -> str:
        text = strip_zero_width(text)
        text = collapse_whitespace(text)
        text = normalize_punctuation(text)
        return text
