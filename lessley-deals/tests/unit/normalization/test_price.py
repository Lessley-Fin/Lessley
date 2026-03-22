from __future__ import annotations

from decimal import Decimal

import pytest

from lessley_deals.domain.models import PriceInfo, RawScrapedRecord
from lessley_deals.normalization.steps.price_normalizer import PriceNormalizerStep
from lessley_deals.normalization.types import NormalizationContext
from tests.factories import make_raw_deal


def _make_ctx(price_text: str) -> NormalizationContext:
    raw = make_raw_deal(price_text=price_text)
    return NormalizationContext(
        raw=raw,
        store_name=raw.store_name,
        deal_description=raw.deal_description,
    )


class TestPriceNormalizerStep:
    """Test the PriceNormalizerStep on various input formats."""

    def setup_method(self) -> None:
        self.step = PriceNormalizerStep()

    def test_plain_shekel_price(self) -> None:
        ctx = _make_ctx("\u20aa29.90")
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.unit_price == Decimal("29.90")

    def test_quantity_deal(self) -> None:
        ctx = _make_ctx("2 \u05d1-30")
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.quantity == 2
        assert ctx.price.total == Decimal("30")
        assert ctx.price.unit_price == Decimal("15")

    def test_bogo(self) -> None:
        ctx = _make_ctx("1+1")
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.quantity == 2
        assert ctx.price.expression == "1+1"

    def test_free_item(self) -> None:
        ctx = _make_ctx("\u05d7\u05d9\u05e0\u05dd")  # חינם
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.unit_price == Decimal("0")

    def test_gift_item(self) -> None:
        ctx = _make_ctx("\u05de\u05ea\u05e0\u05d4")  # מתנה
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.unit_price == Decimal("0")

    def test_empty_price_text(self) -> None:
        ctx = _make_ctx("")
        self.step.apply(ctx)
        assert ctx.price is None

    def test_unparseable_produces_warning(self) -> None:
        ctx = _make_ctx("no price here at all xyz")
        self.step.apply(ctx)
        assert ctx.price is None
        assert any("Could not parse price" in w for w in ctx.warnings)

    def test_shekel_suffix(self) -> None:
        ctx = _make_ctx("29.90\u20aa")
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.unit_price == Decimal("29.90")

    def test_second_at_discount(self) -> None:
        ctx = _make_ctx("\u05d4\u05e9\u05e0\u05d9 \u05d1-50%")  # השני ב-50%
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.expression == "\u05d4\u05e9\u05e0\u05d9 \u05d1-50%"

    @pytest.mark.parametrize(
        "price_text,expected_unit",
        [
            ("\u20aa10", Decimal("10")),
            ("\u20aa 5.50", Decimal("5.50")),
            ("100", Decimal("100")),
        ],
    )
    def test_various_plain_prices(self, price_text: str, expected_unit: Decimal) -> None:
        ctx = _make_ctx(price_text)
        self.step.apply(ctx)
        assert ctx.price is not None
        assert ctx.price.unit_price == expected_unit
