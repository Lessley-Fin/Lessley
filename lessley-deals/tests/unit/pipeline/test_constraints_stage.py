from __future__ import annotations

from lessley_deals.enrichment.constaints_parser import DealConstraints, empty_constraints
from lessley_deals.pipeline.constraints_stage import ConstraintsStage
from tests.factories import make_raw_deal


def _fixed_parser(_terms: str, _source_id: str | None = None) -> DealConstraints:
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
    def _flaky(terms: str, _source_id: str | None = None) -> DealConstraints:
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


async def test_each_deals_source_id_reaches_the_parser() -> None:
    # The parser picks the source's terminology block off this argument, so a
    # dropped source_id would silently degrade every deal to the generic prompt.
    seen: list[tuple[str, str | None]] = []

    def _recording(terms: str, source_id: str | None = None) -> DealConstraints:
        seen.append((terms, source_id))
        return DealConstraints()

    deals = [
        make_raw_deal(id="b1", source_id="behatsdaa", raw_payload={"terms_and_conditions": "א"}),
        make_raw_deal(id="h1", source_id="hot", raw_payload={"terms_and_conditions": "ב"}),
    ]
    await ConstraintsStage(parser=_recording).run(deals)

    assert sorted(seen) == [("א", "behatsdaa"), ("ב", "hot")]
