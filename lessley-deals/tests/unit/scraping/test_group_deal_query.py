"""Tests for group_deal_query helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lessley_deals.domain.models import RawScrapedRecord
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.helpers.group_deal_query import (
    get_deals_for_store,
    get_group_member_stores,
    is_group_wide_deal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _deal(
    store_name: str,
    *,
    group_member_stores: list[str] | None = None,
    deal_id: str | None = None,
) -> RawScrapedRecord:
    payload: dict = {}
    if group_member_stores is not None:
        payload["group_member_stores"] = group_member_stores
    return RawScrapedRecord(
        id=deal_id or generate_id(),
        source_id="hot",
        store_name=store_name,
        deal_description="test deal",
        price_text="10%",
        scraped_at=_NOW,
        raw_payload=payload,
        url=None,
    )


# ---------------------------------------------------------------------------
# get_deals_for_store
# ---------------------------------------------------------------------------


class TestGetDealsForStore:
    def test_direct_deal_returned(self) -> None:
        deals = [_deal("sabon"), _deal("kitan"), _deal("fox")]
        result = get_deals_for_store("sabon", deals)
        assert len(result) == 1
        assert result[0].store_name == "sabon"

    def test_direct_match_is_case_insensitive(self) -> None:
        deals = [_deal("SABON"), _deal("kitan")]
        result = get_deals_for_store("sabon", deals)
        assert len(result) == 1

    def test_group_wide_deal_returned_for_member_store(self) -> None:
        group_deal = _deal("קבוצת גולף", group_member_stores=["sabon", "kitan", "golf"])
        direct = _deal("sabon")
        result = get_deals_for_store("sabon", [group_deal, direct])
        assert len(result) == 2
        assert group_deal in result
        assert direct in result

    def test_group_member_match_is_case_insensitive(self) -> None:
        group_deal = _deal("קבוצת גולף", group_member_stores=["Sabon", "kitan"])
        result = get_deals_for_store("sabon", [group_deal])
        assert len(result) == 1

    def test_no_false_positives_for_unrelated_store(self) -> None:
        deals = [_deal("sabon"), _deal("קבוצת גולף", group_member_stores=["sabon", "kitan"])]
        result = get_deals_for_store("fox", deals)
        assert result == []

    def test_deduplication_when_both_direct_and_group(self) -> None:
        """A deal that matches both a direct store AND appears in group members must appear once."""
        shared_id = generate_id()
        deal = _deal("sabon", group_member_stores=["sabon", "kitan"], deal_id=shared_id)
        result = get_deals_for_store("sabon", [deal, deal])
        assert len(result) == 1

    def test_empty_store_name_returns_empty(self) -> None:
        deals = [_deal("sabon")]
        result = get_deals_for_store("", deals)
        assert result == []

    def test_empty_deal_list_returns_empty(self) -> None:
        result = get_deals_for_store("sabon", [])
        assert result == []

    def test_multiple_group_deals_appended(self) -> None:
        group_a = _deal("קבוצת גולף", group_member_stores=["sabon", "kitan"])
        group_b = _deal("קבוצת פוקס", group_member_stores=["fox", "sabon"])
        direct = _deal("sabon")
        result = get_deals_for_store("sabon", [group_a, group_b, direct])
        assert len(result) == 3

    def test_original_order_preserved(self) -> None:
        d1 = _deal("sabon")
        d2 = _deal("קבוצת גולף", group_member_stores=["sabon"])
        d3 = _deal("sabon")
        result = get_deals_for_store("sabon", [d1, d2, d3])
        assert result == [d1, d2, d3]


# ---------------------------------------------------------------------------
# is_group_wide_deal
# ---------------------------------------------------------------------------


class TestIsGroupWideDeal:
    def test_group_wide_true(self) -> None:
        deal = _deal("קבוצת גולף", group_member_stores=["sabon", "kitan"])
        assert is_group_wide_deal(deal) is True

    def test_specific_store_false(self) -> None:
        deal = _deal("sabon")
        assert is_group_wide_deal(deal) is False

    def test_empty_group_member_stores_false(self) -> None:
        deal = _deal("קבוצת גולף", group_member_stores=[])
        assert is_group_wide_deal(deal) is False


# ---------------------------------------------------------------------------
# get_group_member_stores
# ---------------------------------------------------------------------------


class TestGetGroupMemberStores:
    def test_returns_member_list(self) -> None:
        deal = _deal("קבוצת גולף", group_member_stores=["sabon", "kitan"])
        assert get_group_member_stores(deal) == ["sabon", "kitan"]

    def test_non_group_deal_returns_empty(self) -> None:
        deal = _deal("sabon")
        assert get_group_member_stores(deal) == []

    def test_filters_non_string_members(self) -> None:
        """Non-string entries in the list are silently dropped."""
        deal = _deal("group")
        deal.raw_payload["group_member_stores"] = ["sabon", 42, None, "kitan"]  # type: ignore[list-item]
        members = get_group_member_stores(deal)
        assert members == ["sabon", "kitan"]
