from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from lessley_deals.domain.models import Deal, RawScrapedRecord
from lessley_deals.enrichment.constaints_parser import empty_constraints
from lessley_deals.enrichment.propagate_constraints import propagate_constraints
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from tests.factories import make_raw_deal

_NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def make_deal(**overrides: Any) -> Deal:
    """Local Deal factory — tests.factories.make_deal still passes fields the
    model dropped (``description``/``price``) and raises on construction."""
    defaults: dict[str, Any] = dict(
        id="d1",
        store_id="s1",
        raw_id="r1",
        source_id="test_source",
        scraped_at=_NOW,
        resolved_at=_NOW,
        deal_description="Buy 2 get 1 free",
    )
    defaults.update(overrides)
    return Deal(**defaults)


class FakeRawRepo:
    def __init__(self, records: Sequence[RawScrapedRecord]) -> None:
        self._records = list(records)

    def get_all(self) -> list[RawScrapedRecord]:
        return list(self._records)


def _deals_file(tmp_path: Path, deals: Sequence[Deal]) -> Path:
    path = tmp_path / "deals.json"
    repo = DealJsonRepository(path)
    for deal in deals:
        repo.save(deal)
    return path


def test_copies_constraints_from_raw_to_deal(tmp_path: Path) -> None:
    raw = make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()})
    path = _deals_file(tmp_path, [make_deal(id="d1", raw_id="r1", constraints=None)])

    stats = propagate_constraints(FakeRawRepo([raw]), file=str(path))

    assert stats["updated"] == 1
    stored = DealJsonRepository(path).get_all()
    assert stored[0].constraints == empty_constraints()


def test_costs_no_llm_calls_and_leaves_other_fields_alone(tmp_path: Path) -> None:
    raw = make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()})
    deal = make_deal(id="d1", raw_id="r1", constraints=None, title="חצי מחיר")
    path = _deals_file(tmp_path, [deal])

    propagate_constraints(FakeRawRepo([raw]), file=str(path))

    stored = DealJsonRepository(path).get_all()[0]
    assert stored.title == "חצי מחיר"
    assert stored.store_id == deal.store_id


def test_skips_deals_that_already_have_constraints(tmp_path: Path) -> None:
    existing = {"combinability": {"stackable_with_coupons": False}}
    raw = make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()})
    path = _deals_file(tmp_path, [make_deal(id="d1", raw_id="r1", constraints=existing)])

    stats = propagate_constraints(FakeRawRepo([raw]), file=str(path))

    assert stats["updated"] == 0
    assert stats["skipped"] == 1
    assert DealJsonRepository(path).get_all()[0].constraints == existing


def test_force_overwrites_existing_constraints(tmp_path: Path) -> None:
    raw = make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()})
    path = _deals_file(
        tmp_path, [make_deal(id="d1", raw_id="r1", constraints={"stale": True})]
    )

    stats = propagate_constraints(FakeRawRepo([raw]), file=str(path), force=True)

    assert stats["updated"] == 1
    assert DealJsonRepository(path).get_all()[0].constraints == empty_constraints()


def test_deal_without_a_matching_raw_record_is_reported(tmp_path: Path) -> None:
    path = _deals_file(tmp_path, [make_deal(id="d1", raw_id="gone", constraints=None)])

    stats = propagate_constraints(FakeRawRepo([]), file=str(path))

    assert stats["updated"] == 0
    assert stats["no_raw_match"] == 1


def test_source_filter(tmp_path: Path) -> None:
    raws = [
        make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()}),
        make_raw_deal(id="r2", raw_payload={"constraints": empty_constraints()}),
    ]
    path = _deals_file(
        tmp_path,
        [
            make_deal(id="d1", raw_id="r1", source_id="hot", constraints=None),
            make_deal(id="d2", raw_id="r2", source_id="behatsdaa", constraints=None),
        ],
    )

    stats = propagate_constraints(FakeRawRepo(raws), file=str(path), source="hot")

    assert stats["updated"] == 1
    stored = {d.id: d for d in DealJsonRepository(path).get_all()}
    assert stored["d1"].constraints is not None
    assert stored["d2"].constraints is None


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    raw = make_raw_deal(id="r1", raw_payload={"constraints": empty_constraints()})
    path = _deals_file(tmp_path, [make_deal(id="d1", raw_id="r1", constraints=None)])
    before = path.read_bytes()

    stats = propagate_constraints(FakeRawRepo([raw]), file=str(path), dry_run=True)

    assert stats["updated"] == 1
    assert path.read_bytes() == before


def test_preserves_deal_order(tmp_path: Path) -> None:
    raws = [make_raw_deal(id=f"r{i}", raw_payload={"constraints": empty_constraints()})
            for i in range(4)]
    path = _deals_file(
        tmp_path, [make_deal(id=f"d{i}", raw_id=f"r{i}", constraints=None) for i in range(4)]
    )

    propagate_constraints(FakeRawRepo(raws), file=str(path))

    ids = [d["id"] for d in json.loads(path.read_text(encoding="utf-8"))]
    assert ids == ["d0", "d1", "d2", "d3"]
