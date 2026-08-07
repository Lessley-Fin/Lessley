"""Projecting the pipeline's collections into the Gateway's read model.

The Gateway binds these documents to C# types, so the shape is a contract:
ObjectId ``_id`` with the business key in ``id``, real BSON dates, and
``metadata.mcc_codes`` as strings.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from lessley_deals.persistence.gateway_view import (
    deal_list_document,
    store_list_document,
    sync_gateway_view,
)


def _deal(**overrides):
    """A ``deals`` row, in the flat shape ``data/deals.json`` uses."""
    deal = {
        "_id": ObjectId("6a73988c1a1610b82f7b1bfa"),
        "id": "deal_1",
        "store_id": "store_1",
        "title": "10% off",
        "deal_description": "ten percent",
        "club_id": "club_hot",
        "scraped_at": "2026-08-03T19:20:13.497214+00:00",
        "resolved_at": "2026-08-03T19:20:42.028685+00:00",
        "benefit_url": "https://example.com/b",
        "url": "https://example.com",
    }
    deal.update(overrides)
    return deal


# --------------------------------------------------------------------------- #
# deal_list                                                                     #
# --------------------------------------------------------------------------- #

def test_timestamps_become_real_datetimes():
    # deals stores ISO strings; the C# driver cannot bind a string to DateTime,
    # so leaving them as text breaks deal search at deserialization.
    doc = deal_list_document(_deal())

    assert isinstance(doc["scraped_at"], datetime)
    assert isinstance(doc["resolved_at"], datetime)
    assert doc["scraped_at"] == datetime(2026, 8, 3, 19, 20, 13, 497214, tzinfo=timezone.utc)


def test_business_key_goes_to_id_not_mongo_id():
    doc = deal_list_document(_deal())

    # The source row's ObjectId must not leak through as the business key.
    assert doc["id"] == "deal_1"
    # _id must stay unset so Mongo assigns an ObjectId, which is what [BsonId] binds.
    assert "_id" not in doc


def test_rows_written_by_the_repo_carry_the_business_key_in_mongo_id():
    # DealMongoRepository.save() moves the business id into _id and writes no
    # ``id`` field, unlike the rows imported from data/deals.json.
    doc = deal_list_document({"_id": "deal_9", "store_id": "store_1", "title": "x"})

    assert doc["id"] == "deal_9"


def test_unparseable_or_missing_timestamps_become_null():
    assert deal_list_document(_deal(scraped_at="not a date"))["scraped_at"] is None
    assert deal_list_document(_deal(resolved_at=None))["resolved_at"] is None


def test_missing_title_and_club_become_empty_strings():
    # The C# properties are non-nullable strings defaulting to "".
    doc = deal_list_document(_deal(title=None, club_id=None))

    assert doc["title"] == ""
    assert doc["club_id"] == ""


def test_row_without_an_id_or_store_is_skipped():
    assert deal_list_document({"store_id": "store_1"}) is None
    assert deal_list_document({"id": "deal_1"}) is None


def test_redeem_channels_from_constraints():
    doc = deal_list_document(
        _deal(constraints={"redemption_channels": {"website": "yes", "physical_store": "no"}})
    )

    assert doc["redeem_channels"] == ["website"]


def test_redeem_channels_default_to_empty_without_constraints():
    assert deal_list_document(_deal())["redeem_channels"] == []


# --------------------------------------------------------------------------- #
# store_list                                                                    #
# --------------------------------------------------------------------------- #

def test_mcc_codes_are_stringified():
    # stores holds them as numbers, but the Gateway filters with List<string> —
    # AnyIn against ints silently matches nothing.
    doc = store_list_document(
        {"_id": "store_1", "name": "Shop", "metadata": {"mcc_codes": [7832, 5912]}}
    )

    assert doc["metadata"]["mcc_codes"] == ["7832", "5912"]


def test_store_metadata_defaults_are_present():
    doc = store_list_document({"_id": "store_1", "name": "Shop"})

    assert doc["metadata"] == {"mcc_codes": [], "store_url": None, "image_urls": []}


# --------------------------------------------------------------------------- #
# sync                                                                          #
# --------------------------------------------------------------------------- #

class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.written: list = []

    def find(self, query=None):
        query = query or {}
        return iter([d for d in self.docs if all(d.get(k) == v for k, v in query.items())])

    def bulk_write(self, operations, ordered=True):
        self.written.extend(operations)

    def delete_many(self, query):
        self.deleted_query = query
        return type("R", (), {"deleted_count": 0})()


class _FakeDb(dict):
    def __getitem__(self, name):
        return self.setdefault(name, _FakeCollection())


def test_sync_publishes_every_deals_row():
    db = _FakeDb()
    db["deals"] = _FakeCollection([_deal(), _deal(id="deal_2")])
    db["stores"] = _FakeCollection([{"_id": "store_1", "name": "Shop", "metadata": {}}])

    result = sync_gateway_view(db)

    # deals has no ``status``, so there is nothing to filter on — every row is
    # published, and a deal leaves search only by being deleted from deals.
    assert result["deal_list"]["written"] == 2
    assert result["store_list"]["written"] == 1


def test_sync_reads_deals_not_deals_current():
    # deals_current only covers whichever sources the last versioned run
    # touched; reading it is what previously hid every HOT deal.
    db = _FakeDb()
    db["deals"] = _FakeCollection([_deal()])
    db["deals_current"] = _FakeCollection([_deal(id="ignored")])
    db["stores"] = _FakeCollection([])

    sync_gateway_view(db)

    assert db["deal_list"].deleted_query == {"id": {"$nin": ["deal_1"]}}


def test_sync_prunes_rows_that_are_no_longer_produced():
    db = _FakeDb()
    db["deals"] = _FakeCollection([_deal()])
    db["stores"] = _FakeCollection([])

    sync_gateway_view(db)

    # Anything whose id is not in this run's output is deleted, so a deal
    # removed from deals disappears from search instead of lingering.
    assert db["deal_list"].deleted_query == {"id": {"$nin": ["deal_1"]}}
