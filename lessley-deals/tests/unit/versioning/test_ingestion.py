"""Tests for the SCD Type 2 classification — the part that must never be wrong.

``plan_ingestion`` is pure, so every scenario is expressible without a database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lessley_deals.domain.enums import DealChangeType, DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, Deal
from lessley_deals.versioning.hashing import (
    DealIdentityResolver,
    compute_content_hash,
    deal_snapshot,
    extract_source_expiry,
)
from lessley_deals.versioning.ingestion import IngestionConfig, plan_ingestion

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
RESOLVER = DealIdentityResolver()


def make_deal(
    *,
    deal_id: str = "d1",
    store_id: str = "s1",
    source_id: str = "hot",
    title: str = "20% off",
    description: str = "20% off everything",
    url: str = "https://hot.co.il/deal/1",
    **extra: object,
) -> Deal:
    return Deal(
        id=deal_id,
        store_id=store_id,
        raw_id=f"raw_{deal_id}",
        source_id=source_id,
        scraped_at=NOW,
        resolved_at=NOW,
        title=title,
        deal_description=description,
        url=url,
        currency="ILS",
        **extra,  # type: ignore[arg-type]
    )


def make_head(deal: Deal, *, status: DealLifecycleStatus = DealLifecycleStatus.ACTIVE, **overrides):
    defaults = dict(
        deal_key=RESOLVER.deal_key(deal),
        deal_id=deal.id,
        store_id=deal.store_id,
        source_id=deal.source_id,
        version=1,
        content_hash=compute_content_hash(deal),
        status=status,
        first_seen_at=NOW - timedelta(days=10),
        last_seen_at=NOW - timedelta(days=1),
        valid_from=NOW - timedelta(days=10),
        snapshot=deal_snapshot(deal),
    )
    defaults.update(overrides)
    return CurrentDeal(**defaults)  # type: ignore[arg-type]


def plan(**kwargs):
    kwargs.setdefault("source_id", "hot")
    kwargs.setdefault("identity", RESOLVER)
    kwargs.setdefault("now", NOW)
    return plan_ingestion(**kwargs)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def test_first_sighting_creates_version_1() -> None:
    result = plan(incoming=[make_deal()], heads=[])

    assert result.report.new == 1
    assert len(result.versions) == 1
    version = result.versions[0]
    assert version.version == 1
    assert version.change_type is DealChangeType.NEW
    assert version.status is DealLifecycleStatus.ACTIVE
    assert version.is_current and version.valid_to is None
    assert not result.closures


def test_identical_rescrape_writes_no_version() -> None:
    deal = make_deal()
    result = plan(incoming=[deal], heads=[make_head(deal)])

    assert result.report.unchanged == 1
    assert result.versions == ()
    assert result.closures == ()
    # ...but the head is still touched, so absence bookkeeping stays correct.
    assert result.heads[0].last_seen_at == NOW


def test_content_change_opens_a_new_version_and_closes_the_old_one() -> None:
    old = make_deal(description="20% off everything")
    new = make_deal(description="35% off everything")

    result = plan(incoming=[new], heads=[make_head(old)])

    assert result.report.updated == 1
    version = result.versions[0]
    assert version.version == 2
    assert version.change_type is DealChangeType.UPDATED
    assert "deal_description" in version.changed_fields
    assert result.closures == ((version.deal_key, NOW),)


def test_deal_id_is_stable_across_versions() -> None:
    """Downstream references (saved deals, notifications) must survive edits."""
    old = make_deal(deal_id="original-id")
    # The pipeline generates a fresh Deal.id on every run — it must be ignored.
    new = make_deal(deal_id="regenerated-id", description="new text")

    result = plan(incoming=[new], heads=[make_head(old)])

    assert result.heads[0].deal_id == "original-id"
    assert result.versions[0].snapshot["id"] == "original-id"


def test_cosmetic_whitespace_change_is_not_an_update() -> None:
    old = make_deal(description="20%  off   everything")
    new = make_deal(description="20% off everything")

    result = plan(incoming=[new], heads=[make_head(old)])

    assert result.report.unchanged == 1
    assert result.versions == ()


def test_tracking_params_in_the_url_are_not_an_update() -> None:
    old = make_deal(url="https://hot.co.il/deal/1")
    new = make_deal(url="https://www.hot.co.il/deal/1?utm_source=newsletter")

    result = plan(incoming=[new], heads=[make_head(old)])

    assert result.report.unchanged == 1


def test_expired_deal_seen_again_is_reactivated() -> None:
    deal = make_deal()
    head = make_head(deal, status=DealLifecycleStatus.EXPIRED, valid_to=NOW - timedelta(days=2))

    result = plan(incoming=[deal], heads=[head])

    assert result.report.reactivated == 1
    assert result.versions[0].change_type is DealChangeType.REACTIVATED
    assert result.heads[0].status is DealLifecycleStatus.ACTIVE


def test_duplicates_within_one_batch_collapse() -> None:
    deal = make_deal()
    result = plan(incoming=[deal, deal, deal], heads=[])

    assert result.report.new == 1
    assert result.report.duplicates_dropped == 2


# ---------------------------------------------------------------------------
# Expiry — and the guards around it
# ---------------------------------------------------------------------------

def _absent_head(deal: Deal, *, missing_runs: int, missing_days: float) -> CurrentDeal:
    return make_head(
        deal,
        missing_runs=missing_runs,
        missing_since=NOW - timedelta(days=missing_days),
    )


def test_a_single_miss_does_not_expire() -> None:
    """One bad page must never wipe a deal out."""
    gone = make_deal(deal_id="gone", url="https://hot.co.il/deal/gone")
    still_there = [make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}") for i in range(5)]

    result = plan(
        incoming=still_there,
        heads=[make_head(gone)] + [make_head(d) for d in still_there],
    )

    assert result.report.expired == 0
    absent = next(h for h in result.heads if h.deal_key == RESOLVER.deal_key(gone))
    assert absent.status is DealLifecycleStatus.ACTIVE
    assert absent.missing_runs == 1


def test_expires_after_threshold_and_grace_are_both_met() -> None:
    gone = _absent_head(make_deal(deal_id="gone", url="https://hot.co.il/deal/gone"),
                        missing_runs=1, missing_days=2)
    present = [make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}") for i in range(5)]

    result = plan(incoming=present, heads=[gone] + [make_head(d) for d in present])

    assert result.report.expired == 1
    expired = next(h for h in result.heads if h.deal_key == gone.deal_key)
    assert expired.status is DealLifecycleStatus.EXPIRED
    assert expired.valid_to == NOW

    # Expiry is a version of its own, so the gap is queryable afterwards.
    assert (gone.deal_key, NOW) in result.closures
    version = next(v for v in result.versions if v.deal_key == gone.deal_key)
    assert version.version == gone.version + 1
    assert version.change_type is DealChangeType.EXPIRED
    assert version.is_current and version.valid_to is None


def test_expired_then_returned_leaves_a_queryable_gap() -> None:
    """as-of queries must answer "expired" for the days it was gone."""
    deal = make_deal(deal_id="d0", url="https://hot.co.il/deal/0")
    expired_head = make_head(
        deal,
        status=DealLifecycleStatus.EXPIRED,
        version=2,
        valid_from=NOW - timedelta(days=3),
        valid_to=NOW - timedelta(days=3),
    )

    result = plan(incoming=[deal], heads=[expired_head])

    version = result.versions[0]
    assert version.version == 3
    assert version.change_type is DealChangeType.REACTIVATED
    # The EXPIRED row (v2) is closed at "now", so v2 covers exactly the gap.
    assert result.closures == ((expired_head.deal_key, NOW),)


def test_grace_period_alone_is_not_enough() -> None:
    """Missing for a long time but only once (e.g. we were down) → keep it."""
    gone = _absent_head(make_deal(deal_id="gone", url="https://hot.co.il/deal/gone"),
                        missing_runs=0, missing_days=30)
    present = [make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}") for i in range(5)]

    result = plan(incoming=present, heads=[gone] + [make_head(d) for d in present])

    assert result.report.expired == 0


def test_failed_scrape_never_expires_anything() -> None:
    heads = [make_head(make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}"))
             for i in range(10)]

    result = plan(incoming=[], heads=heads, run_ok=False)

    assert result.report.expired == 0
    assert result.report.expiry_sweep_skipped == "scrape reported errors"


def test_partial_scrape_below_coverage_ratio_skips_the_sweep() -> None:
    """A source returning 1 of 10 deals is broken, not 90% expired."""
    heads = [
        _absent_head(make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}"),
                     missing_runs=5, missing_days=30)
        for i in range(10)
    ]
    survivor = make_deal(deal_id="d0", url="https://hot.co.il/deal/0")

    result = plan(incoming=[survivor], heads=heads)

    assert result.report.expired == 0
    assert result.report.expiry_sweep_skipped is not None
    assert "coverage" in result.report.expiry_sweep_skipped


def test_empty_run_against_a_populated_source_skips_the_sweep() -> None:
    heads = [make_head(make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}"))
             for i in range(10)]

    result = plan(incoming=[], heads=heads)

    assert result.report.expiry_sweep_skipped == "run returned zero deals"


def test_deduplicated_records_count_as_seen() -> None:
    """Unchanged deals filtered out upstream must not drift towards expiry."""
    deal = _absent_head(make_deal(deal_id="d0", url="https://hot.co.il/deal/0"),
                        missing_runs=5, missing_days=30)
    deal.raw_fingerprint = "fp-0"
    others = [make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}") for i in range(1, 6)]

    result = plan(
        incoming=others,
        heads=[deal] + [make_head(d) for d in others],
        seen_fingerprints={"fp-0"},
    )

    assert result.report.expired == 0
    head = next(h for h in result.heads if h.deal_key == deal.deal_key)
    assert head.missing_runs == 0


def test_steady_state_run_where_every_record_was_deduplicated_upstream() -> None:
    """The common production case: nothing changed, so the scrape stage passes
    on zero deals.  Every head must still be marked seen — treating this as
    "the source returned nothing" would expire the whole catalogue."""
    deals = [make_deal(deal_id=f"d{i}", url=f"https://hot.co.il/deal/{i}") for i in range(20)]
    heads = []
    for i, deal in enumerate(deals):
        head = make_head(deal, missing_runs=1, missing_since=NOW - timedelta(days=5))
        head.raw_fingerprint = f"fp-{i}"
        heads.append(head)

    result = plan(
        incoming=[],
        heads=heads,
        seen_fingerprints={f"fp-{i}" for i in range(20)},
    )

    assert result.report.unchanged == 20
    assert result.report.expired == 0
    assert result.report.expiry_sweep_skipped is None
    assert all(h.missing_runs == 0 and h.last_seen_at == NOW for h in result.heads)


def test_source_declared_end_date_expires_the_deal() -> None:
    ended = make_deal(discount_logic={"valid_until": "2026-01-01"})

    result = plan(incoming=[ended], heads=[])

    assert result.report.new == 1
    assert result.report.expired == 1
    assert result.heads[0].status is DealLifecycleStatus.EXPIRED


def test_expiry_sweep_can_be_disabled_entirely() -> None:
    gone = _absent_head(make_deal(deal_id="gone", url="https://hot.co.il/deal/gone"),
                        missing_runs=9, missing_days=99)

    result = plan(
        incoming=[],
        heads=[gone],
        config=IngestionConfig(enable_expiry_sweep=False),
    )

    assert result.report.expired == 0
    assert result.report.expiry_sweep_skipped == "disabled"


# ---------------------------------------------------------------------------
# Identity & hashing
# ---------------------------------------------------------------------------

def test_identity_survives_a_full_rewrite_when_the_source_has_a_real_id() -> None:
    resolver = DealIdentityResolver({"hot": lambda d: (d.discount_logic or {}).get("benefit_id")})
    before = make_deal(title="A", description="B", discount_logic={"benefit_id": 42})
    after = make_deal(title="Z", description="Y", discount_logic={"benefit_id": 42})

    assert resolver.deal_key(before) == resolver.deal_key(after)


def test_different_stores_are_different_deals() -> None:
    assert RESOLVER.deal_key(make_deal(store_id="s1")) != RESOLVER.deal_key(make_deal(store_id="s2"))


@pytest.mark.parametrize(
    "payload,expected_year",
    [
        ({"valid_until": "2026-03-01"}, 2026),
        ({"end_date": "01/03/2026"}, 2026),
        ({"limits": {"expiry_date": "2027-12-31T23:59:59"}}, 2027),
    ],
)
def test_source_expiry_parsing(payload: dict, expected_year: int) -> None:
    parsed = extract_source_expiry(make_deal(discount_logic=payload))
    assert parsed is not None and parsed.year == expected_year


def test_timestamps_do_not_affect_the_content_hash() -> None:
    first = make_deal()
    later = Deal(
        id="other",
        store_id=first.store_id,
        raw_id="other-raw",
        source_id=first.source_id,
        scraped_at=NOW + timedelta(days=3),
        resolved_at=NOW + timedelta(days=3),
        title=first.title,
        deal_description=first.deal_description,
        url=first.url,
        currency=first.currency,
    )
    assert compute_content_hash(first) == compute_content_hash(later)
