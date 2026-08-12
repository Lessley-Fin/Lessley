"""Tests for the Swish group sync flow.

Covers:
- Auto-resolution of member stores via the matching pipeline.
- Unresolved members produce review-queue items with kind=group_member_match.
- Hand-maintained HOT entries are preserved on sync.
- Re-running sync removes stale Swish entries (full-refresh policy).
- Re-running sync does not duplicate review items already pending.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lessley_deals.domain.enums import AliasSource
from lessley_deals.domain.models import CanonicalStore, NameForms, StoreAlias
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.review.queue import ReviewQueue
from lessley_deals.scraping.helpers.swish_group_sync import (
    SWISH_GROUP_PREFIX,
    SWISH_MANAGED_BY,
    sync_swish_groups,
)


def _name_forms(name: str) -> NameForms:
    """Tiny helper for building seed stores in tests."""
    normalized = name.lower().strip()
    compact = "".join(ch for ch in normalized if ch.isalnum())
    tokens = tuple(sorted({w for w in normalized.split() if len(w) > 1}))
    return NameForms(normalized=normalized, compact=compact, tokens=tokens)


def _make_store(store_id: str, name: str) -> CanonicalStore:
    now = datetime.now(timezone.utc)
    return CanonicalStore(
        id=store_id,
        name=name,
        name_forms=_name_forms(name),
        created_at=now,
        updated_at=now,
    )


def _make_alias(store_id: str, alias: str) -> StoreAlias:
    return StoreAlias(
        id=f"alias_{alias}",
        store_id=store_id,
        alias=alias,
        alias_forms=_name_forms(alias),
        source=AliasSource.SEED,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture()
def alias_index() -> AliasIndex:
    """Two seed stores: 'sabon' and 'kitan'.  'mystery' has no canonical."""
    stores = [
        _make_store("store_sabon", "sabon"),
        _make_store("store_kitan", "kitan"),
    ]
    aliases = [
        _make_alias("store_sabon", "sabon"),
        _make_alias("store_kitan", "kitan"),
    ]
    return AliasIndex(aliases=aliases, stores=stores)


@pytest.fixture()
def review_queue(tmp_path: Path) -> ReviewQueue:
    repo = ReviewJsonRepository(tmp_path / "review.json")
    return ReviewQueue(repo)


@pytest.fixture()
def swish_db(tmp_path: Path) -> Path:
    """Two Swish benefits — first all-resolved, second one unknown member."""
    payload = [
        {
            "benefit_id": "100",
            "benefit_name": "All known stores",
            "stores": ["sabon", "kitan"],
        },
        {
            "benefit_id": "200",
            "benefit_name": "Mixed",
            "stores": ["sabon", "Mystery Store"],
        },
    ]
    path = tmp_path / "swish_database.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture()
def groups_path(tmp_path: Path) -> Path:
    """Pre-existing config with one hand-maintained HOT group."""
    path = tmp_path / "hot_store_groups.json"
    path.write_text(
        json.dumps(
            {
                "קבוצת גולף - תווים": {
                    "title_prefix": "תו קניה",
                    "stores": ["sabon", "kitan"],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _read_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestSyncSwishGroups:
    def test_resolves_all_known_members(
        self,
        swish_db: Path,
        groups_path: Path,
        alias_index: AliasIndex,
        review_queue: ReviewQueue,
    ) -> None:
        result = sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
            pipeline=MatchPipeline(MatchConfig()),
        )

        assert result.benefits_processed == 2
        assert result.groups_written == 2

        cfg = _read_config(groups_path)
        all_known = cfg[f"{SWISH_GROUP_PREFIX}100"]
        assert all_known["managed_by"] == "swish_scraper"
        store_ids = [m["store_id"] for m in all_known["stores"]]
        assert store_ids == ["store_sabon", "store_kitan"]

    def test_unresolved_member_pushed_to_review(
        self,
        swish_db: Path,
        groups_path: Path,
        alias_index: AliasIndex,
        review_queue: ReviewQueue,
    ) -> None:
        result = sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
        )

        # 'Mystery Store' has no canonical → review queue
        assert result.members_to_review >= 1
        assert result.review_items_created >= 1

        pending = review_queue.get_pending()
        # A pending item must reference the synthetic group_key::name raw_id
        mystery_items = [
            i for i in pending if "Mystery Store" in (i.raw_input_name or "")
        ]
        assert len(mystery_items) == 1
        item = mystery_items[0]
        assert item.raw_id.startswith(f"{SWISH_GROUP_PREFIX}200::")
        assert item.verdict.explanation.details.get("kind") == "group_member_match"

    def test_hand_maintained_entries_preserved(
        self,
        swish_db: Path,
        groups_path: Path,
        alias_index: AliasIndex,
        review_queue: ReviewQueue,
    ) -> None:
        sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
        )
        cfg = _read_config(groups_path)
        assert "קבוצת גולף - תווים" in cfg
        # The hand-maintained entry's stores stay as plain strings
        assert cfg["קבוצת גולף - תווים"]["stores"] == ["sabon", "kitan"]

    def test_full_refresh_removes_stale_swish_entries(
        self,
        swish_db: Path,
        groups_path: Path,
        alias_index: AliasIndex,
        review_queue: ReviewQueue,
    ) -> None:
        # Pre-seed a stale Swish-managed entry that will not be in the DB.
        cfg = _read_config(groups_path)
        cfg[f"{SWISH_GROUP_PREFIX}999"] = {
            "managed_by": "swish_scraper",
            "title_prefix": "תו קניה",
            "stores": [{"name": "ghost", "store_id": None, "confidence": None}],
        }
        groups_path.write_text(
            json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
        )

        result = sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
        )
        assert result.groups_removed == 1

        cfg2 = _read_config(groups_path)
        assert f"{SWISH_GROUP_PREFIX}999" not in cfg2

    def test_repeat_sync_does_not_duplicate_review_items(
        self,
        swish_db: Path,
        groups_path: Path,
        alias_index: AliasIndex,
        review_queue: ReviewQueue,
    ) -> None:
        first = sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
        )
        second = sync_swish_groups(
            swish_db_path=swish_db,
            alias_index=alias_index,
            review_queue=review_queue,
            groups_config_path=groups_path,
        )
        # First run created the review items; the second must reuse them.
        assert first.review_items_created >= 1
        assert second.review_items_created == 0
        assert second.pre_existing_review_skipped >= 1


def test_cross_benefit_dedup_creates_only_one_review_item(tmp_path: Path) -> None:
    """Same raw store name in two benefits → single review item."""
    db = [
        {"benefit_id": "101", "benefit_name": "A", "stores": ["רנואר"]},
        {"benefit_id": "202", "benefit_name": "B", "stores": ["רנואר"]},
    ]
    db_path = tmp_path / "swish_database.json"
    db_path.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")

    alias_index = AliasIndex(aliases=[], stores=[])
    queue = ReviewQueue(ReviewJsonRepository(tmp_path / "review.json"))

    result = sync_swish_groups(db_path, alias_index, queue)

    pending = queue.get_pending()
    review_names = [item.raw_input_name for item in pending]
    assert review_names.count("רנואר") == 1
    assert result.pre_existing_review_skipped == 1


def test_name_already_pending_from_other_source_prevents_push(tmp_path: Path) -> None:
    """Name already in queue from non-Swish source → not pushed again."""
    from datetime import datetime, timezone
    from lessley_deals.domain.enums import MatchDecision
    from lessley_deals.domain.models import Explanation, MatchVerdict, ReviewItem
    from lessley_deals.scraping.helpers.swish_group_sync import _build_name_forms

    review_repo = ReviewJsonRepository(tmp_path / "review.json")
    existing = ReviewItem(
        id="existing-id",
        raw_id="hot::רנואר",
        input_name="רנואר",
        input_name_forms=_build_name_forms("רנואר"),
        raw_input_name="רנואר",
        verdict=MatchVerdict(
            record_id="hot::רנואר",
            input_name="רנואר",
            decision=MatchDecision.NO_MATCH,
            candidates=(),
            explanation=Explanation(stages_run=(), reason="no match", stage_matched=None),
        ),
        created_at=datetime.now(timezone.utc),
    )
    review_repo.save(existing)

    db = [{"benefit_id": "101", "benefit_name": "A", "stores": ["רנואר"]}]
    db_path = tmp_path / "swish_database.json"
    db_path.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")

    queue = ReviewQueue(review_repo)
    alias_index = AliasIndex(aliases=[], stores=[])

    result = sync_swish_groups(db_path, alias_index, queue)

    assert result.review_items_created == 0
    assert result.pre_existing_review_skipped == 1
