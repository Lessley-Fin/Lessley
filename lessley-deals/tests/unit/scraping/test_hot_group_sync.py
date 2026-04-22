from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    ReviewItem,
)
from lessley_deals.scraping.helpers.hot_group_sync import (
    HotGroupSyncSummary,
    _build_name_forms,
    _existing_pending_names,
    _make_review_verdict,
    _resolve_member,
    _resolve_member_list,
    _to_normalized_record,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

HOT_SOURCE_ID = "hot_groups"


def _make_verdict(decision: MatchDecision, store_id: str | None = None, conf: float = 0.95) -> MatchVerdict:
    best = None
    if store_id:
        best = MatchCandidate(store_id=store_id, store_name="dummy", confidence=conf, stage="exact_alias")
    return MatchVerdict(
        record_id="test::name",
        input_name="name",
        decision=decision,
        candidates=(best,) if best else (),
        explanation=Explanation(stages_run=("exact_alias",), reason="test", stage_matched=None, details={}),
        best=best,
    )


def _make_pipeline(verdict: MatchVerdict) -> MagicMock:
    pipeline = MagicMock()
    pipeline.match.return_value = verdict
    return pipeline


def _make_queue(pending: list[str] | None = None) -> MagicMock:
    queue = MagicMock()
    items = []
    if pending:
        for name in pending:
            item = MagicMock()
            item.raw_input_name = name
            items.append(item)
    queue.get_pending.return_value = items
    queue.add = MagicMock()
    return queue


# ── Helper tests ──────────────────────────────────────────────────────────────

def test_build_name_forms_returns_name_forms():
    forms = _build_name_forms("Fox Home")
    assert isinstance(forms, NameForms)
    assert forms.normalized == "fox home"
    assert forms.compact == "foxhome"
    assert "fox" in forms.tokens
    assert "home" in forms.tokens


def test_to_normalized_record_uses_hot_source_id():
    record = _to_normalized_record("Super-Pharm", "my_group")
    assert record.source_id == HOT_SOURCE_ID
    assert record.raw_id == "my_group::Super-Pharm"
    assert isinstance(record.store_name_forms, NameForms)


def test_make_review_verdict_adds_source_and_kind():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    stamped = _make_review_verdict("קבוצת פוקס", "fox", verdict)
    assert stamped.explanation.details["kind"] == "group_member_match"
    assert stamped.explanation.details["source"] == "hot_groups"
    assert stamped.explanation.details["group_key"] == "קבוצת פוקס"
    assert stamped.record_id == "קבוצת פוקס::fox"


def test_resolve_member_auto_match_returns_store_id():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123", conf=0.97)
    pipeline = _make_pipeline(verdict)
    index = MagicMock()

    member, returned_verdict = _resolve_member("fox", "group_key", pipeline, index)

    assert member == {"name": "fox", "store_id": "abc_123", "confidence": 0.97}
    assert returned_verdict is None


def test_resolve_member_no_match_returns_null_store_id():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    index = MagicMock()

    member, returned_verdict = _resolve_member("unknown store", "group_key", pipeline, index)

    assert member == {"name": "unknown store", "store_id": None, "confidence": None}
    assert returned_verdict is verdict


def test_existing_pending_names_returns_raw_input_names():
    queue = _make_queue(pending=["fox", "mango"])
    names = _existing_pending_names(queue)
    assert names == {"fox", "mango"}


# ── _resolve_member_list tests ────────────────────────────────────────────────

def test_plain_string_auto_match_upgrades_to_dict():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123", conf=0.97)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()

    result = _resolve_member_list(
        members=["fox"],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    assert result == [{"name": "fox", "store_id": "abc_123", "confidence": 0.97}]
    assert summary.members_resolved == 1
    assert summary.members_pending == 0
    queue.add.assert_not_called()


def test_plain_string_no_match_pushed_to_review():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()

    result = _resolve_member_list(
        members=["unknown store"],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    assert result == [{"name": "unknown store", "store_id": None, "confidence": None}]
    assert summary.members_pending == 1
    assert summary.review_items_created == 1
    queue.add.assert_called_once()
    added_item = queue.add.call_args[0][0]
    assert isinstance(added_item, ReviewItem)
    assert added_item.raw_input_name == "unknown store"
    assert added_item.verdict.explanation.details["kind"] == "group_member_match"
    assert added_item.verdict.explanation.details["source"] == "hot_groups"


def test_dict_with_store_id_skipped():
    pipeline = _make_pipeline(_make_verdict(MatchDecision.AUTO_MATCH, store_id="abc_123"))
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    already_resolved = {"name": "fox", "store_id": "abc_123", "confidence": 1.0}

    result = _resolve_member_list(
        members=[already_resolved],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    assert result == [already_resolved]
    pipeline.match.assert_not_called()
    assert summary.members_resolved == 0
    assert summary.members_pending == 0


def test_dict_with_null_store_id_reprocessed():
    verdict = _make_verdict(MatchDecision.AUTO_MATCH, store_id="new_id", conf=0.92)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    unresolved = {"name": "fox", "store_id": None, "confidence": None}

    result = _resolve_member_list(
        members=[unresolved],
        group_key="קבוצת פוקס",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    assert result[0]["store_id"] == "new_id"
    assert summary.members_resolved == 1
    pipeline.match.assert_called_once()


def test_dedup_already_pending_not_pushed_twice():
    verdict = _make_verdict(MatchDecision.NO_MATCH)
    pipeline = _make_pipeline(verdict)
    queue = _make_queue()
    summary = HotGroupSyncSummary()
    pending = {"unknown store"}  # already in queue

    _resolve_member_list(
        members=["unknown store"],
        group_key="קבוצת פוקס",
        pending_names=pending,
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    queue.add.assert_not_called()
    assert summary.pre_existing_review_skipped == 1
    assert summary.review_items_created == 0


def test_empty_string_members_skipped():
    pipeline = MagicMock()
    queue = _make_queue()
    summary = HotGroupSyncSummary()

    result = _resolve_member_list(
        members=["", "  "],
        group_key="some_group",
        pending_names=set(),
        pipeline=pipeline,
        index=MagicMock(),
        review_queue=queue,
        summary=summary,
        now=datetime.now(UTC),
    )

    assert result == []
    pipeline.match.assert_not_called()
    assert summary.members_resolved == 0
    assert summary.members_pending == 0
