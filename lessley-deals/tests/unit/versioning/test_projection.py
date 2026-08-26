"""Tests for the head table → ``deals`` projection.

The ingestion's classification is already covered by ``test_ingestion.py``.
What matters here is the consequence of it: whether the collection every
consumer reads actually stops serving deals the source stopped offering.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lessley_deals.domain.enums import DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, Deal
from lessley_deals.versioning.hashing import (
    DealIdentityResolver,
    compute_content_hash,
    deal_snapshot,
)
from lessley_deals.versioning.projection import DealProjector, stale_deal_ids

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
RESOLVER = DealIdentityResolver()


class FakeDealRepo:
    """In-memory stand-in with the two methods the projector uses."""

    def __init__(self) -> None:
        self.rows: dict[str, Deal] = {}

    def bulk_upsert(self, deals) -> int:
        for deal in deals:
            self.rows[deal.id] = deal
        return len(deals)

    def delete_by_ids(self, deal_ids) -> int:
        removed = 0
        for deal_id in deal_ids:
            if self.rows.pop(deal_id, None) is not None:
                removed += 1
        return removed


def make_deal(*, deal_id: str = "d1", title: str = "20% off") -> Deal:
    return Deal(
        id=deal_id,
        store_id="s1",
        raw_id=f"raw_{deal_id}",
        source_id="hot",
        scraped_at=NOW,
        resolved_at=NOW,
        title=title,
        deal_description="20% off everything",
        url="https://hot.co.il/deal/1",
        currency="ILS",
    )


def make_head(
    deal: Deal,
    *,
    status: DealLifecycleStatus = DealLifecycleStatus.ACTIVE,
    **overrides,
) -> CurrentDeal:
    defaults = dict(
        deal_key=RESOLVER.deal_key(deal),
        deal_id=deal.id,
        store_id=deal.store_id,
        source_id=deal.source_id,
        version=1,
        content_hash=compute_content_hash(deal),
        status=status,
        first_seen_at=NOW - timedelta(days=10),
        last_seen_at=NOW,
        valid_from=NOW - timedelta(days=10),
        snapshot=deal_snapshot(deal),
    )
    defaults.update(overrides)
    return CurrentDeal(**defaults)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# The point of the whole module                                               #
# --------------------------------------------------------------------------- #

def test_active_head_becomes_an_on_offer_row() -> None:
    repo = FakeDealRepo()
    deal = make_deal()

    DealProjector(repo).apply([make_head(deal)])

    row = repo.rows["d1"]
    assert row.status == DealLifecycleStatus.ACTIVE
    assert row.title == "20% off"
    assert row.last_seen_at == NOW


def test_expired_head_flags_the_row_instead_of_leaving_it_on_offer() -> None:
    repo = FakeDealRepo()
    deal = make_deal()
    head = make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW)

    report = DealProjector(repo).apply([head])

    assert report.expired == 1
    assert repo.rows["d1"].status == DealLifecycleStatus.EXPIRED
    assert repo.rows["d1"].expired_at == NOW


def test_expired_head_deletes_the_row_when_asked_to() -> None:
    repo = FakeDealRepo()
    deal = make_deal()
    repo.rows["d1"] = deal

    report = DealProjector(repo, delete_expired=True).apply(
        [make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW)]
    )

    assert report.deleted == 1
    assert "d1" not in repo.rows


def test_reprojecting_an_offer_replaces_its_row_rather_than_adding_one() -> None:
    """The whole reason ``deals`` grew stale copies: a new id per run."""
    repo = FakeDealRepo()
    projector = DealProjector(repo)
    deal = make_deal()

    projector.apply([make_head(deal)])
    reworded = make_deal(title="25% off")
    projector.apply([make_head(reworded, last_seen_at=NOW + timedelta(days=1))])

    assert list(repo.rows) == ["d1"]
    assert repo.rows["d1"].title == "25% off"


def test_an_expired_row_comes_back_active_under_the_same_id() -> None:
    """A source that goes quiet and returns must not orphan saved references."""
    repo = FakeDealRepo()
    projector = DealProjector(repo)
    deal = make_deal()

    projector.apply([make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW)])
    assert repo.rows["d1"].status == DealLifecycleStatus.EXPIRED

    projector.apply([make_head(deal, version=2)])

    assert repo.rows["d1"].status == DealLifecycleStatus.ACTIVE
    assert repo.rows["d1"].expired_at is None


def test_the_head_id_wins_over_whatever_the_snapshot_carries() -> None:
    """``deal_id`` is the key consumers reference; a snapshot's own id may be older."""
    repo = FakeDealRepo()
    deal = make_deal()
    head = make_head(deal, deal_id="stable-id")

    DealProjector(repo).apply([head])

    assert list(repo.rows) == ["stable-id"]
    assert repo.rows["stable-id"].deal_key == head.deal_key


@pytest.mark.parametrize("snapshot", [{}, {"id": "d1"}], ids=["empty", "unparseable"])
def test_a_broken_snapshot_is_skipped_not_fatal(snapshot: dict) -> None:
    """One bad row must never cost a whole run its projection."""
    repo = FakeDealRepo()
    head = make_head(make_deal(), snapshot=snapshot)

    report = DealProjector(repo).apply([head])

    assert report.skipped == 1
    assert repo.rows == {}


def test_lifecycle_fields_stay_out_of_the_version_snapshot() -> None:
    """The head owns them; a second stale copy in the snapshot would rot."""
    from dataclasses import replace

    deal = replace(
        make_deal(),
        status=DealLifecycleStatus.EXPIRED,
        deal_key="whatever",
        last_seen_at=NOW,
    )

    snapshot = deal_snapshot(deal)

    assert "status" not in snapshot
    assert "deal_key" not in snapshot
    assert "last_seen_at" not in snapshot


# --------------------------------------------------------------------------- #
# Leftovers from before the projector existed                                 #
# --------------------------------------------------------------------------- #

def test_stale_ids_are_the_rows_no_head_accounts_for() -> None:
    heads = [make_head(make_deal(deal_id="live"))]

    orphans = stale_deal_ids({"live", "orphan-a", "orphan-b"}, heads)

    assert orphans == {"orphan-a", "orphan-b"}


def test_nothing_is_stale_when_every_row_has_a_head() -> None:
    heads = [make_head(make_deal(deal_id="live"))]

    assert stale_deal_ids({"live"}, heads) == set()


# --------------------------------------------------------------------------- #
# Rebuilds (``deals process``) are not observations                           #
# --------------------------------------------------------------------------- #

def test_a_rebuild_does_not_resurrect_a_retired_offer() -> None:
    """The raw archive still holds every record ever scraped.

    Replaying it must not read as "the source is offering this again", or a
    single ``deals process`` puts every retired deal back in front of users.
    """
    from lessley_deals.versioning.ingestion import IngestionConfig, plan_ingestion

    deal = make_deal()
    head = make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW)

    plan = plan_ingestion(
        source_id="hot",
        incoming=[deal],
        heads=[head],
        config=IngestionConfig(enable_expiry_sweep=False, allow_reactivation=False),
        now=NOW + timedelta(days=1),
    )

    assert plan.report.reactivated == 0
    assert plan.report.reactivation_suppressed == 1
    assert plan.versions == ()


def test_a_rebuild_still_adds_offers_that_are_new_to_us() -> None:
    from lessley_deals.versioning.ingestion import IngestionConfig, plan_ingestion

    plan = plan_ingestion(
        source_id="hot",
        incoming=[make_deal(deal_id="fresh")],
        heads=[],
        config=IngestionConfig(enable_expiry_sweep=False, allow_reactivation=False),
        now=NOW,
    )

    assert plan.report.new == 1
    assert plan.heads[0].status == DealLifecycleStatus.ACTIVE


def test_a_scrape_still_reactivates_by_default() -> None:
    """The suppression must be opt-in — a real scrape *is* fresh evidence."""
    from lessley_deals.versioning.ingestion import plan_ingestion

    deal = make_deal()
    plan = plan_ingestion(
        source_id="hot",
        incoming=[deal],
        heads=[make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW)],
        now=NOW + timedelta(days=1),
    )

    assert plan.report.reactivated == 1
