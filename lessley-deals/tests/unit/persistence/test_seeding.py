"""Seeding canonical stores/aliases/clubs into MongoDB from the seed files."""

from __future__ import annotations

import json

from lessley_deals.persistence.seeding import (
    CLUBS,
    seed_candidate_dirs,
    seed_mcc_list,
    seed_mongo_if_empty,
    upsert_seed_file,
)


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = dict(docs or {})

    def count_documents(self, query, limit=None):
        return len(self.docs)

    def update_one(self, filter_, update, upsert=False):
        # Keyed on whatever the caller filtered by: most collections upsert on
        # `_id`, but `mcc_list` uses `mcc` because its `_id` has to stay an
        # ObjectId that Mongo assigns.
        ((_field, doc_id),) = filter_.items()
        existed = doc_id in self.docs
        if not existed and upsert:
            self.docs[doc_id] = dict(update["$setOnInsert"])
        # $setOnInsert never touches an existing document.
        return type("Result", (), {"upserted_id": None if existed else doc_id})()


class _FakeDb:
    def __init__(self, collections=None):
        self.collections = collections or {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, _FakeCollection())


def _write(dir_path, name, records):
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / name).write_text(json.dumps(records), encoding="utf-8")


def test_seeds_stores_aliases_and_clubs(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "stores.json", [{"id": "s1", "name": "Shop"}, {"id": "s2", "name": "Other"}])
    _write(seed, "store_aliases.json", [{"id": "a1", "store_id": "s1", "alias": "shp"}])
    db = _FakeDb()

    seed_mongo_if_empty(db, tmp_path)

    assert set(db["stores"].docs) == {"s1", "s2"}
    assert set(db["store_aliases"].docs) == {"a1"}
    assert set(db["clubs"].docs) == {c["_id"] for c in CLUBS}
    # `id` becomes `_id`, and is not left behind as a duplicate field.
    assert db["stores"].docs["s1"] == {"_id": "s1", "name": "Shop"}


def test_is_a_no_op_when_stores_already_exist(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "stores.json", [{"id": "s1", "name": "From seed"}])
    db = _FakeDb({"stores": _FakeCollection({"existing": {"_id": "existing", "name": "Live"}})})

    seed_mongo_if_empty(db, tmp_path)

    # The guard short-circuits before any file is read.
    assert set(db["stores"].docs) == {"existing"}


def test_rerunning_never_overwrites_an_edited_store(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "stores.json", [{"id": "s1", "name": "Original"}])
    db = _FakeDb()
    seed_mongo_if_empty(db, tmp_path)
    db["stores"].docs["s1"]["name"] = "Enriched by hand"

    # Bypass the emptiness guard to prove the writes themselves are $setOnInsert.
    assert upsert_seed_file(db, "stores", seed / "stores.json") == 0
    assert db["stores"].docs["s1"]["name"] == "Enriched by hand"


def test_missing_seed_files_still_seed_clubs_without_raising(tmp_path):
    db = _FakeDb()

    seed_mongo_if_empty(db, tmp_path / "nothing-here")

    assert db["stores"].docs == {}
    assert set(db["clubs"].docs) == {c["_id"] for c in CLUBS}


def test_data_dir_seed_subdir_is_preferred(tmp_path):
    candidates = seed_candidate_dirs(tmp_path)

    assert candidates[0] == tmp_path / "seed"


def test_seeds_the_mcc_catalogue(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "mcc_list.json", [
        {"mcc": "5411", "category": "GROCERIES"},
        {"mcc": "5812", "category": "RESTAURANT"},
    ])
    db = _FakeDb()

    inserted = seed_mcc_list(db, tmp_path)

    assert inserted == 2
    # Keyed on `mcc`, and `_id` is left for Mongo to assign — the Gateway's
    # MccRepository and Personalization's MccCode both bind it to an ObjectId.
    assert db["mcc_list"].docs["5411"] == {"mcc": "5411", "category": "GROCERIES"}
    assert "_id" not in db["mcc_list"].docs["5411"]


def test_mcc_catalogue_is_not_reseeded_when_present(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "mcc_list.json", [{"mcc": "5411", "category": "GROCERIES"}])
    db = _FakeDb({"mcc_list": _FakeCollection({"9999": {"mcc": "9999", "category": "OTHER"}})})

    assert seed_mcc_list(db, tmp_path) == 0
    assert set(db["mcc_list"].docs) == {"9999"}


def test_missing_mcc_file_is_not_fatal(tmp_path):
    assert seed_mcc_list(_FakeDb(), tmp_path) == 0


def test_boot_seeds_the_catalogue_but_never_deals(tmp_path):
    """Deals come from the scrapers; seeding them would ship stale benefits."""
    seed = tmp_path / "seed"
    _write(seed, "stores.json", [{"id": "s1", "name": "Shop"}])
    _write(seed, "store_aliases.json", [{"id": "a1", "store_id": "s1", "alias": "shp"}])
    _write(seed, "mcc_list.json", [{"mcc": "5411", "category": "GROCERIES"}])
    _write(seed, "deals.json", [{"id": "d1", "title": "should never be loaded"}])
    db = _FakeDb()

    seed_mongo_if_empty(db, tmp_path)

    assert set(db["mcc_list"].docs) == {"5411"}
    assert set(db["stores"].docs) == {"s1"}
    assert db["deals"].docs == {}


def test_mcc_is_seeded_even_when_stores_are_already_present(tmp_path):
    """The two guards are independent — a store-populated DB can still be
    missing the catalogue, which would leave the UI with no category filter."""
    seed = tmp_path / "seed"
    _write(seed, "mcc_list.json", [{"mcc": "5411", "category": "GROCERIES"}])
    db = _FakeDb({"stores": _FakeCollection({"existing": {"_id": "existing"}})})

    seed_mongo_if_empty(db, tmp_path)

    assert set(db["mcc_list"].docs) == {"5411"}
