"""Projecting the pipeline's collections into the Gateway's read model.

The Gateway binds these documents to C# types, so the shape is a contract:
ObjectId ``_id`` with the business key in ``id``, real BSON dates, and
``metadata.mcc_codes`` as strings.
"""

from __future__ import annotations

from datetime import datetime, timezone

from lessley_deals.persistence.gateway_view import (
    deal_list_document,
    store_list_document,
    sync_gateway_view,
)


def _head(**snapshot_overrides):
    snapshot = {
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
    snapshot.update(snapshot_overrides)
    return {"_id": "key_1", "deal_id": "deal_1", "store_id": "store_1",
            "status": "active", "snapshot": snapshot}


# --------------------------------------------------------------------------- #
# deal_list                                                                     #
# --------------------------------------------------------------------------- #

def test_timestamps_become_real_datetimes():
    # The snapshot stores ISO strings; the C# driver cannot bind a string to
    # DateTime, so leaving them as text breaks deal search at deserialization.
    doc = deal_list_document(_head())

    assert isinstance(doc["scraped_at"], datetime)
    assert isinstance(doc["resolved_at"], datetime)
    assert doc["scraped_at"] == datetime(2026, 8, 3, 19, 20, 13, 497214, tzinfo=timezone.utc)


def test_business_key_goes_to_id_not_mongo_id():
    doc = deal_list_document(_head())

    assert doc["id"] == "deal_1"
    # _id must stay unset so Mongo assigns an ObjectId, which is what [BsonId] binds.
    assert "_id" not in doc


def test_unparseable_or_missing_timestamps_become_null():
    assert deal_list_document(_head(scraped_at="not a date"))["scraped_at"] is None
    assert deal_list_document(_head(resolved_at=None))["resolved_at"] is None


def test_missing_title_and_club_become_empty_strings():
    # The C# properties are non-nullable strings defaulting to "".
    doc = deal_list_document(_head(title=None, club_id=None))

    assert doc["title"] == ""
    assert doc["club_id"] == ""


def test_head_without_a_deal_id_is_skipped():
    head = _head()
    head["snapshot"].pop("id")
    head.pop("deal_id")

    assert deal_list_document(head) is None


def test_redeem_channels_from_constraints():
    doc = deal_list_document(
        _head(constraints={"redemption_channels": {"website": "yes", "physical_store": "no"}})
    )

    assert doc["redeem_channels"] == ["website"]


def test_redeem_channels_default_to_empty_without_constraints():
    assert deal_list_document(_head())["redeem_channels"] == []


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


def test_sync_publishes_only_active_deals():
    db = _FakeDb()
    db["deals_current"] = _FakeCollection([
        _head(),
        {**_head(id="deal_2"), "status": "expired"},
    ])
    db["stores"] = _FakeCollection([{"_id": "store_1", "name": "Shop", "metadata": {}}])

    result = sync_gateway_view(db)

    assert result["deal_list"]["written"] == 1
    assert result["store_list"]["written"] == 1


def test_sync_prunes_rows_that_are_no_longer_produced():
    db = _FakeDb()
    db["deals_current"] = _FakeCollection([_head()])
    db["stores"] = _FakeCollection([])

    sync_gateway_view(db)

    # Anything whose id is not in this run's output is deleted, so an expired
    # deal disappears from search instead of lingering.
    assert db["deal_list"].deleted_query == {"id": {"$nin": ["deal_1"]}}
