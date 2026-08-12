from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from lessley_deals.domain.models import PriceInfo
from lessley_deals.normalization.types import NormalizationContext

# Pattern: "₪29.90" or "29.90₪" or "29.90 ש"ח" or "₪ 29.90"
_PLAIN_PRICE_RE = re.compile(
    r"""(?:₪\s*|ש"ח\s*)?(\d+(?:[.,]\d+)?)(?:\s*₪|\s*ש"ח)?""",
    re.VERBOSE,
)

# Pattern: "2 ב-30" or "2 ב30" or "3 ב-₪30"
_QUANTITY_DEAL_RE = re.compile(
    r"""(\d+)\s*ב-?\s*(?:₪\s*)?(\d+(?:[.,]\d+)?)""",
)

# Pattern: "1+1"
_BOGO_RE = re.compile(r"^1\s*\+\s*1$")

# Pattern: "השני ב-50%" or "השני ב50%"
_SECOND_DISCOUNT_RE = re.compile(r"השני\s+ב-?\s*\d+%")

# Pattern: "חינם" or "מתנה"
_FREE_RE = re.compile(r"חינם|מתנה")


class PriceNormalizerStep:
    """Parse raw price text into a structured PriceInfo."""

    def apply(self, ctx: NormalizationContext) -> None:
        price_text = (ctx.raw.price_text or "").strip()
        if not price_text:
            ctx.price = None
            return

        parsed = self._parse(price_text)
        if parsed is not None:
            ctx.price = parsed
        else:
            ctx.price = None
            ctx.warnings.append(f"Could not parse price: {price_text!r}")

    def _parse(self, text: str) -> PriceInfo | None:
        # Free items
        if _FREE_RE.search(text):
            return PriceInfo(
                expression=text,
                unit_price=Decimal("0"),
            )

        # Buy one get one: "1+1"
        if _BOGO_RE.match(text.strip()):
            return PriceInfo(
                expression="1+1",
                quantity=2,
            )

        # Second at discount: "השני ב-50%"
        if _SECOND_DISCOUNT_RE.search(text):
            return PriceInfo(expression=text)

        # Quantity deal: "2 ב-30"
        m = _QUANTITY_DEAL_RE.search(text)
        if m:
            qty = int(m.group(1))
            total = self._to_decimal(m.group(2))
            if total is not None and qty > 0:
                unit = total / qty
                return PriceInfo(
                    expression=text,
                    unit_price=unit,
                    quantity=qty,
                    total=total,
                )

        # Plain price: "₪29.90" or "29.90 ש"ח"
        m = _PLAIN_PRICE_RE.fullmatch(text.strip())
        if m and m.group(1):
            price = self._to_decimal(m.group(1))
            if price is not None:
                return PriceInfo(
                    expression=text,
                    unit_price=price,
                )

        # Fallback: try to find any number in the text
        m = re.search(r"(\d+(?:[.,]\d+)?)", text)
        if m:
            price = self._to_decimal(m.group(1))
            if price is not None:
                return PriceInfo(
                    expression=text,
                    unit_price=price,
                )

        return None

    @staticmethod
    def _to_decimal(s: str) -> Decimal | None:
        try:
            return Decimal(s.replace(",", "."))
        except InvalidOperation:
            return None
