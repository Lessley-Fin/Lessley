from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lessley_deals.domain.enums import AliasSource, MatchDecision, ReviewStatus
from lessley_deals.domain.models import (
    CanonicalStore,
    Deal,
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    PriceInfo,
    RawScrapedRecord,
    ReviewItem,
    StoreAlias,
)
from lessley_deals.persistence.serialization import (
    alias_from_dict,
    canonical_store_from_dict,
    deal_from_dict,
    raw_deal_from_dict,
    review_item_from_dict,
    to_dict,
)
from tests.factories import (
    make_alias,
    make_deal,
    make_raw_deal,
    make_review_item,
    make_store,
)


class TestRawScrapedRecordRoundTrip:
    def test_round_trip(self) -> None:
        original = make_raw_deal(
            id="r1",
            source_id="src",
            store_name="Store",
            deal_description="deal",
            price_text="10",
            url="https://example.com",
        )
        d = to_dict(original)
        restored = raw_deal_from_dict(d)

        assert restored.id == original.id
        assert restored.source_id == original.source_id
        assert restored.store_name == original.store_name
        assert restored.deal_description == original.deal_description
        assert restored.price_text == original.price_text
        assert restored.url == original.url
        assert restored.raw_payload == original.raw_payload


class TestCanonicalStoreRoundTrip:
    def test_round_trip(self) -> None:
        original = make_store(id="s1", name="Test Store")
        d = to_dict(original)
        restored = canonical_store_from_dict(d)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.name_forms.normalized == original.name_forms.normalized
        assert restored.name_forms.compact == original.name_forms.compact
        assert restored.name_forms.tokens == original.name_forms.tokens


class TestStoreAliasRoundTrip:
    def test_round_trip(self) -> None:
        original = make_alias("store_1", "Test Alias")
        d = to_dict(original)
        restored = alias_from_dict(d)

        assert restored.id == original.id
        assert restored.store_id == original.store_id
        assert restored.alias == original.alias
        assert restored.alias_forms.compact == original.alias_forms.compact
        assert restored.source == original.source


class TestDealRoundTrip:
    def test_round_trip_without_price(self) -> None:
        original = make_deal(id="d1", store_id="s1", raw_id="r1")
        d = to_dict(original)
        restored = deal_from_dict(d)

        assert restored.id == original.id
        assert restored.store_id == original.store_id
        assert restored.raw_id == original.raw_id
        assert restored.description == original.description
        assert restored.price is None

    def test_round_trip_with_price(self) -> None:
        price = PriceInfo(
            expression="2 ב-30",
            unit_price=Decimal("15"),
            quantity=2,
            total=Decimal("30"),
        )
        original = make_deal(id="d2", price=price)
        d = to_dict(original)
        restored = deal_from_dict(d)

        assert restored.price is not None
        assert restored.price.unit_price == Decimal("15")
        assert restored.price.quantity == 2
        assert restored.price.total == Decimal("30")
        assert restored.price.expression == "2 ב-30"


class TestReviewItemRoundTrip:
    def test_round_trip(self) -> None:
        original = make_review_item(raw_id="r1", input_name="test store")
        d = to_dict(original)
        restored = review_item_from_dict(d)

        assert restored.id == original.id
        assert restored.raw_id == original.raw_id
        assert restored.input_name == original.input_name
        assert restored.status == original.status
        assert restored.input_name_forms.compact == original.input_name_forms.compact
        assert restored.raw_input_name == original.raw_input_name
        assert restored.verdict.decision == original.verdict.decision
        assert restored.verdict.record_id == original.verdict.record_id

    def test_round_trip_with_raw_input_name(self) -> None:
        original = make_review_item(
            raw_id="r1",
            input_name="חנ",
            raw_input_name="חן",
        )
        d = to_dict(original)
        restored = review_item_from_dict(d)

        assert restored.raw_input_name == "חן"

    def test_backwards_compatible_without_raw_input_name(self) -> None:
        original = make_review_item(raw_id="r1", input_name="test store")
        d = to_dict(original)
        d.pop("raw_input_name", None)

        restored = review_item_from_dict(d)

        assert restored.raw_input_name is None


class TestToDict:
    def test_datetime_serialized_as_iso(self) -> None:
        record = make_raw_deal()
        d = to_dict(record)
        assert isinstance(d["scraped_at"], str)
        # Should be parseable back
        datetime.fromisoformat(d["scraped_at"])

    def test_decimal_serialized_as_string(self) -> None:
        price = PriceInfo(expression="test", unit_price=Decimal("29.90"))
        d = to_dict(price)
        assert d["unit_price"] == "29.90"
        assert isinstance(d["unit_price"], str)

    def test_tuple_serialized_as_list(self) -> None:
        nf = NameForms(normalized="a", compact="a", tokens=("x", "y"))
        d = to_dict(nf)
        assert isinstance(d["tokens"], list)
        assert d["tokens"] == ["x", "y"]
