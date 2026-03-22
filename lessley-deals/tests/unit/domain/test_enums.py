from __future__ import annotations

from lessley_deals.domain.enums import (
    AliasSource,
    MatchDecision,
    RecordFate,
    ReviewAction,
    ReviewStatus,
)


class TestAllEnumsAreStrings:
    """Every StrEnum member must be an instance of str."""

    def test_match_decision_values_are_strings(self) -> None:
        for member in MatchDecision:
            assert isinstance(member, str)
            assert isinstance(member.value, str)

    def test_review_status_values_are_strings(self) -> None:
        for member in ReviewStatus:
            assert isinstance(member, str)

    def test_review_action_values_are_strings(self) -> None:
        for member in ReviewAction:
            assert isinstance(member, str)

    def test_alias_source_values_are_strings(self) -> None:
        for member in AliasSource:
            assert isinstance(member, str)

    def test_record_fate_values_are_strings(self) -> None:
        for member in RecordFate:
            assert isinstance(member, str)


class TestMatchDecision:
    def test_auto_match(self) -> None:
        assert MatchDecision.AUTO_MATCH == "auto_match"

    def test_review(self) -> None:
        assert MatchDecision.REVIEW == "review"

    def test_no_match(self) -> None:
        assert MatchDecision.NO_MATCH == "no_match"


class TestReviewStatus:
    def test_pending(self) -> None:
        assert ReviewStatus.PENDING == "pending"

    def test_approved(self) -> None:
        assert ReviewStatus.APPROVED == "approved"

    def test_created(self) -> None:
        assert ReviewStatus.CREATED == "created"

    def test_discarded(self) -> None:
        assert ReviewStatus.DISCARDED == "discarded"

    def test_skipped(self) -> None:
        assert ReviewStatus.SKIPPED == "skipped"


class TestReviewAction:
    def test_approve(self) -> None:
        assert ReviewAction.APPROVE == "approve"

    def test_create_new(self) -> None:
        assert ReviewAction.CREATE_NEW == "create_new"

    def test_discard(self) -> None:
        assert ReviewAction.DISCARD == "discard"

    def test_skip(self) -> None:
        assert ReviewAction.SKIP == "skip"


class TestAliasSource:
    def test_seed(self) -> None:
        assert AliasSource.SEED == "seed"

    def test_scraper(self) -> None:
        assert AliasSource.SCRAPER == "scraper"

    def test_review(self) -> None:
        assert AliasSource.REVIEW == "review"

    def test_manual(self) -> None:
        assert AliasSource.MANUAL == "manual"
