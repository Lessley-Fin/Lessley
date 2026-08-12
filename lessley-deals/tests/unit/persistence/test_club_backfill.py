"""The club_id backfill — putting each deal's club into the collection every reader uses."""

from __future__ import annotations

import pytest

from lessley_deals.persistence.club_backfill import backfill_club_ids, build_club_by_source


class FakeCollection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        self.written: list[tuple[dict, dict]] = []

    def find(self, query: dict | None = None, projection: dict | None = None):
        return iter([dict(d) for d in self._matching(query or {})])

    def bulk_write(self, operations, ordered=True):  # noqa: ANN001, ARG002
        for op in operations:
            self.written.append((op._filter, op._doc))
        return None

    def _matching(self, query: dict) -> list[dict]:
        if "$or" not in query:
            return self.docs
        return [d for d in self.docs if self._missing_club(d)]

    @staticmethod
    def _missing_club(doc: dict) -> bool:
        return "club_id" not in doc or doc["club_id"] in (None, "")


class FakeDb:
    def __init__(self, clubs: list[dict], deals: list[dict]) -> None:
        self.collections = {"clubs": FakeCollection(clubs), "deals": FakeCollection(deals)}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


CLUBS = [
    {"_id": "club_hot", "source_id": "hot", "name": "HOT"},
    {"_id": "club_mastercard", "source_id": "mastercard", "name": "Mastercard"},
]


def test_build_club_by_source_keys_on_the_source():
    db = FakeDb(CLUBS, [])

    assert build_club_by_source(db) == {"hot": "club_hot", "mastercard": "club_mastercard"}


def test_deals_without_a_club_get_one_from_their_source():
    deals = [
        {"_id": "d1", "source_id": "hot"},                 # field absent
        {"_id": "d2", "source_id": "mastercard", "club_id": None},   # explicit null
        {"_id": "d3", "source_id": "hot", "club_id": ""},  # empty string
    ]
    db = FakeDb(CLUBS, deals)

    result = backfill_club_ids(db)

    assert result.matched == 3
    assert result.by_source == {"hot": 2, "mastercard": 1}
    written = dict((f["_id"], d["$set"]["club_id"]) for f, d in db["deals"].written)
    assert written == {"d1": "club_hot", "d2": "club_mastercard", "d3": "club_hot"}


def test_deals_that_already_have_a_club_are_untouched():
    db = FakeDb(CLUBS, [{"_id": "d1", "source_id": "hot", "club_id": "club_hot"}])

    result = backfill_club_ids(db)

    assert result.matched == 0
    assert db["deals"].written == []


def test_a_source_with_no_club_is_left_alone_not_guessed():
    db = FakeDb(CLUBS, [{"_id": "d1", "source_id": "behatsdaa"}])

    result = backfill_club_ids(db)

    assert result.matched == 0
    assert result.unmatched_sources == {"behatsdaa": 1}
    assert db["deals"].written == []


def test_dry_run_reports_without_writing():
    db = FakeDb(CLUBS, [{"_id": "d1", "source_id": "hot"}])

    result = backfill_club_ids(db, dry_run=True)

    assert result.matched == 1
    assert db["deals"].written == []


def test_no_clubs_means_no_join_and_no_writes():
    # Guard against wiping club_id off every deal when the clubs collection is empty.
    db = FakeDb([], [{"_id": "d1", "source_id": "hot"}])

    result = backfill_club_ids(db)

    assert result.club_by_source == {}
    assert result.matched == 0
    assert db["deals"].written == []


@pytest.mark.parametrize("club_key", ["_id", "id"])
def test_club_business_key_is_read_from_either_field(club_key):
    # `clubs` keys on _id; rows imported by hand can carry `id` instead.
    db = FakeDb([{club_key: "club_hot", "source_id": "hot"}], [{"_id": "d1", "source_id": "hot"}])

    result = backfill_club_ids(db)

    assert result.matched == 1
    assert db["deals"].written[0][1]["$set"]["club_id"] == "club_hot"
