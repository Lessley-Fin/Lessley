from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from tests.factories import make_raw_deal


def _repo(tmp_path: Path) -> RawDealJsonRepository:
    return RawDealJsonRepository(tmp_path / "raw_source_deals.json")


def test_update_many_replaces_records_in_place(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    a = make_raw_deal(id="a", raw_payload={"terms_and_conditions": "תנאים"})
    b = make_raw_deal(id="b", raw_payload={"terms_and_conditions": "עוד תנאים"})
    repo.save_many([a, b])

    enriched = replace(a, raw_payload={**a.raw_payload, "constraints": {"limits": {}}})
    written = repo.update_many([enriched])

    assert written == 1
    stored = {r.id: r for r in repo.get_all()}
    assert len(stored) == 2  # updated in place, not appended
    assert stored["a"].raw_payload["constraints"] == {"limits": {}}
    assert stored["a"].raw_payload["terms_and_conditions"] == "תנאים"
    assert "constraints" not in stored["b"].raw_payload


def test_update_many_ignores_unknown_ids(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.save_many([make_raw_deal(id="a")])

    written = repo.update_many([make_raw_deal(id="ghost")])

    assert written == 0
    assert [r.id for r in repo.get_all()] == ["a"]


def test_update_many_preserves_record_order(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    records = [make_raw_deal(id=f"d{i}") for i in range(5)]
    repo.save_many(records)

    repo.update_many([replace(records[2], store_name="Renamed")])

    path = tmp_path / "raw_source_deals.json"
    ids = [d["id"] for d in json.loads(path.read_text(encoding="utf-8"))]
    assert ids == ["d0", "d1", "d2", "d3", "d4"]


def test_update_many_with_no_records_does_not_touch_the_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.save_many([make_raw_deal(id="a")])
    path = tmp_path / "raw_source_deals.json"
    before = path.read_bytes()

    assert repo.update_many([]) == 0
    assert path.read_bytes() == before
