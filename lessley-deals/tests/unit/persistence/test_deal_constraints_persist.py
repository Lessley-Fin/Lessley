from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lessley_deals.domain.models import Deal
from lessley_deals.enrichment.constaints_parser import empty_constraints
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.serialization import deal_from_dict, to_dict


def _make_deal(deal_id: str = "deal_1", constraints: dict | None = None) -> Deal:
    now = datetime(2026, 7, 6, tzinfo=UTC)
    return Deal(
        id=deal_id,
        store_id="store_1",
        raw_id="raw_1",
        source_id="hot",
        scraped_at=now,
        resolved_at=now,
        title="תו קניה",
        terms_and_conditions="ניתן לממש עד 2 שוברים בעסקה.",
        constraints=constraints,
    )


def test_deal_constraints_round_trip() -> None:
    constraints = empty_constraints()
    constraints["limits"]["max_uses_per_transaction"] = 2
    constraints["store_coverage"]["is_include_physical_stores"] = True

    deal = _make_deal(constraints=constraints)
    restored = deal_from_dict(to_dict(deal))

    assert restored.constraints == constraints
    assert restored.constraints["limits"]["max_uses_per_transaction"] == 2
    assert restored.constraints["store_coverage"]["is_include_physical_stores"] is True


def test_save_omits_null_constraints(tmp_path: Path) -> None:
    repo = DealJsonRepository(tmp_path / "deals.json")
    repo.save(_make_deal(constraints=None))

    raw = repo._store.read()  # type: ignore[attr-defined]
    assert "constraints" not in raw[0]
    # And a re-hydrated deal reports None.
    assert repo.get_all()[0].constraints is None


def test_update_writes_constraints_in_place(tmp_path: Path) -> None:
    repo = DealJsonRepository(tmp_path / "deals.json")
    repo.save(_make_deal(constraints=None))

    deal = repo.get_all()[0]
    constraints = empty_constraints()
    constraints["combinability"]["stackable_with_coupons"] = False
    deal.constraints = constraints

    assert repo.update(deal) is True

    reloaded = repo.get_all()
    assert len(reloaded) == 1  # updated in place, not appended
    assert reloaded[0].constraints["combinability"]["stackable_with_coupons"] is False


def test_update_returns_false_for_unknown_id(tmp_path: Path) -> None:
    repo = DealJsonRepository(tmp_path / "deals.json")
    assert repo.update(_make_deal(deal_id="ghost")) is False
