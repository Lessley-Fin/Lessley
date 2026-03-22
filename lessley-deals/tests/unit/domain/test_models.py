from __future__ import annotations

import pytest
from decimal import Decimal

from lessley_deals.domain.models import NameForms, PriceInfo, RawScrapedRecord
from tests.factories import make_raw_deal


class TestRawScrapedRecordFingerprint:
    """fingerprint is a SHA-256 of source_id|store_name|deal_description|price_text."""

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs always produce the same fingerprint."""
        kwargs = dict(
            id="id_1",
            source_id="src",
            store_name="Store A",
            deal_description="deal",
            price_text="10",
        )
        r1 = make_raw_deal(**kwargs)
        r2 = make_raw_deal(**kwargs)
        assert r1.fingerprint == r2.fingerprint

    def test_differs_when_store_name_changes(self) -> None:
        base = dict(source_id="src", store_name="Store A", deal_description="d", price_text="10")
        r1 = make_raw_deal(**base)
        r2 = make_raw_deal(**{**base, "store_name": "Store B"})
        assert r1.fingerprint != r2.fingerprint

    def test_differs_when_deal_description_changes(self) -> None:
        base = dict(source_id="src", store_name="Store", deal_description="d1", price_text="10")
        r1 = make_raw_deal(**base)
        r2 = make_raw_deal(**{**base, "deal_description": "d2"})
        assert r1.fingerprint != r2.fingerprint

    def test_differs_when_price_text_changes(self) -> None:
        base = dict(source_id="src", store_name="Store", deal_description="d", price_text="10")
        r1 = make_raw_deal(**base)
        r2 = make_raw_deal(**{**base, "price_text": "20"})
        assert r1.fingerprint != r2.fingerprint

    def test_differs_when_source_id_changes(self) -> None:
        base = dict(source_id="src_a", store_name="Store", deal_description="d", price_text="10")
        r1 = make_raw_deal(**base)
        r2 = make_raw_deal(**{**base, "source_id": "src_b"})
        assert r1.fingerprint != r2.fingerprint


class TestFrozenDataclassImmutability:
    """Frozen dataclasses must raise AttributeError on field assignment."""

    def test_raw_scraped_record_is_frozen(self) -> None:
        record = make_raw_deal()
        with pytest.raises(AttributeError):
            record.store_name = "new name"  # type: ignore[misc]

    def test_name_forms_is_frozen(self) -> None:
        nf = NameForms(normalized="test", compact="test", tokens=("test",))
        with pytest.raises(AttributeError):
            nf.normalized = "other"  # type: ignore[misc]

    def test_price_info_is_frozen(self) -> None:
        pi = PriceInfo(expression="10")
        with pytest.raises(AttributeError):
            pi.expression = "20"  # type: ignore[misc]


class TestNameForms:
    def test_creation(self) -> None:
        nf = NameForms(normalized="test store", compact="teststore", tokens=("store", "test"))
        assert nf.normalized == "test store"
        assert nf.compact == "teststore"
        assert nf.tokens == ("store", "test")

    def test_tokens_are_tuple(self) -> None:
        nf = NameForms(normalized="a", compact="a", tokens=("a",))
        assert isinstance(nf.tokens, tuple)


class TestPriceInfo:
    def test_defaults(self) -> None:
        pi = PriceInfo(expression="test")
        assert pi.unit_price is None
        assert pi.quantity == 1
        assert pi.total is None
        assert pi.currency == "ILS"

    def test_with_all_fields(self) -> None:
        pi = PriceInfo(
            expression="2 ב-30",
            unit_price=Decimal("15"),
            quantity=2,
            total=Decimal("30"),
            currency="ILS",
        )
        assert pi.unit_price == Decimal("15")
        assert pi.quantity == 2
        assert pi.total == Decimal("30")
