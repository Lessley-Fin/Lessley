from __future__ import annotations

from datetime import datetime, timezone

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import NormalizedRecord
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.low_information import is_low_information_alias
from lessley_deals.matching.pipeline import MatchPipeline
from tests.factories import make_alias, make_name_forms, make_store


def _make_normalized(name: str) -> NormalizedRecord:
    return NormalizedRecord(
        raw_id="raw_001",
        source_id="test_source",
        store_name_forms=make_name_forms(name),
        deal_description="test deal",
        normalized_at=datetime.now(timezone.utc),
    )


class TestLowInformationAliases:
    def test_detects_generic_business_category_alias(self) -> None:
        assert is_low_information_alias(make_name_forms("מרפאת שיניים"))
        assert is_low_information_alias(make_name_forms("בית מרקחת"))
        assert not is_low_information_alias(make_name_forms('מרפאת שיניים ד"ר עלימי'))

    def test_exact_alias_ignores_generic_alias(self) -> None:
        store = make_store(name='מרפאת שיניים ד"ר עלימי')
        alias = make_alias(store.id, "מרפאת שיניים")
        index = AliasIndex(aliases=[alias], stores=[store])
        pipeline = MatchPipeline()

        verdict = pipeline.match(_make_normalized("מרפאת שיניים"), index)

        assert verdict.decision != MatchDecision.AUTO_MATCH
        assert verdict.best is None or verdict.best.stage != "exact_alias"

    def test_containment_does_not_promote_generic_alias_to_auto_match(self) -> None:
        store = make_store(name='מרפאת שיניים ד"ר עלימי')
        alias = make_alias(store.id, "מרפאת שיניים")
        index = AliasIndex(aliases=[alias], stores=[store])
        pipeline = MatchPipeline()

        verdict = pipeline.match(_make_normalized("מרפאת שיניים ultradent"), index)

        assert verdict.decision != MatchDecision.AUTO_MATCH
