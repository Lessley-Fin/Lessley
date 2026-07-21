from __future__ import annotations

from lessley_deals.enrichment.constaints_parser import DealConstraints, empty_constraints
from lessley_deals.pipeline.constraints_stage import ConstraintsStage
from tests.factories import make_raw_deal


def _fixed_parser(_terms: str) -> DealConstraints:
    return DealConstraints()


async def test_parses_deals_with_terms() -> None:
    deals = [
        make_raw_deal(id="d1", raw_payload={"terms_and_conditions": "כולל כפל מבצעים"}),
        make_raw_deal(id="d2", raw_payload={"terms_and_conditions": "ללא כפל קופונים"}),
    ]
    stage = ConstraintsStage(parser=_fixed_parser)

    result = await stage.run(deals)

    assert set(result) == {"d1", "d2"}
    assert result["d1"] == empty_constraints()


async def test_skips_deals_without_terms() -> None:
    deals = [
        make_raw_deal(id="d1", raw_payload={"terms_and_conditions": "יש תנאים"}),
        make_raw_deal(id="d2", raw_payload={}),  # no terms
        make_raw_deal(id="d3", raw_payload={"terms_and_conditions": "   "}),  # blank
    ]
    stage = ConstraintsStage(parser=_fixed_parser)

    result = await stage.run(deals)

    assert set(result) == {"d1"}


async def test_parser_failure_is_skipped_not_fatal() -> None:
    def _flaky(terms: str) -> DealConstraints:
        if "boom" in terms:
            raise RuntimeError("Request timed out.")
        return DealConstraints()

    deals = [
        make_raw_deal(id="ok", raw_payload={"terms_and_conditions": "fine terms"}),
        make_raw_deal(id="bad", raw_payload={"terms_and_conditions": "boom terms"}),
    ]
    stage = ConstraintsStage(parser=_flaky)

    result = await stage.run(deals)

    # The failing deal is dropped; the healthy one still lands.
    assert set(result) == {"ok"}


async def test_empty_input_returns_empty_map() -> None:
    stage = ConstraintsStage(parser=_fixed_parser)
    assert await stage.run([]) == {}
