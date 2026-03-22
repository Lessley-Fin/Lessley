from __future__ import annotations

import re

from lessley_deals.normalization.text import collapse_whitespace
from lessley_deals.normalization.types import NormalizationContext


class DealTextNormalizerStep:
    """Clean deal description: collapse whitespace, strip leading/trailing punctuation."""

    def apply(self, ctx: NormalizationContext) -> None:
        text = collapse_whitespace(ctx.deal_description)
        # Strip leading and trailing punctuation (keep Hebrew, Latin, digits)
        text = re.sub(r"^[\s\W]+", "", text)
        text = re.sub(r"[\s\W]+$", "", text)
        ctx.deal_description = text
