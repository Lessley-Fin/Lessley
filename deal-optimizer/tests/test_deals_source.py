"""Which Mongo collections the engine reads.

``deals``/``stores`` — what ``lessley-deals``' Mongo repository writes, and what the
Gateway and Personalization read too. Reading the wrong collection fails silently: the
query returns plausible but stale deals rather than erroring. It cost real debugging time
once, when a tiered PaisPlus card quoted 25% of a 10,000 ILS cart because the collection
being read predated ``reward.tiers``.

So the names are pinned here rather than left as bare literals, and stay overridable for
pointing a debugging session at a copy.
"""

from __future__ import annotations

import importlib
from typing import Any

from deal_optimizer import deals_source


class _FakeCollection:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs
        self.last_query: dict[str, Any] | None = None

    def find(self, query):
        self.last_query = query
        return iter(self._docs)

    def find_one(self, query):
        return self._docs[0] if self._docs else None


class _FakeDb:
    """Records every collection name asked for."""

    def __init__(self, contents: dict[str, list[dict[str, Any]]]) -> None:
        self._contents = contents
        self.requested: list[str] = []

    def __getitem__(self, name: str) -> _FakeCollection:
        self.requested.append(name)
        self.last = _FakeCollection(self._contents.get(name, []))
        return self.last


def test_default_collections_are_the_long_standing_names():
    # Changing these changes behavior for every environment that has not opted
    # out, so the default is pinned deliberately rather than incidentally.
    assert deals_source.DEALS_COLLECTION == "deals"
    assert deals_source.STORES_COLLECTION == "stores"


def test_load_store_deals_queries_the_configured_collection():
    db = _FakeDb({"deals": [{"id": "d1", "store_id": "s1"}]})

    out = deals_source.load_store_deals("s1", db=db)

    assert db.requested == ["deals"]
    assert [d["id"] for d in out] == ["d1"]


def test_load_store_queries_the_configured_collection():
    db = _FakeDb({"stores": [{"id": "s1", "name": "fox"}]})

    deals_source.load_store("s1", db=db)

    assert db.requested == ["stores"]


def test_collections_can_be_overridden_by_environment(monkeypatch):
    # The escape hatch for pointing a debugging session at a restored copy — it must
    # work without editing code.
    monkeypatch.setenv("DEALS_COLLECTION", "deals_restored")
    monkeypatch.setenv("STORES_COLLECTION", "stores_restored")
    reloaded = importlib.reload(deals_source)
    try:
        assert reloaded.DEALS_COLLECTION == "deals_restored"
        assert reloaded.STORES_COLLECTION == "stores_restored"

        db = _FakeDb({"deals_restored": [{"id": "d1", "store_id": "s1"}]})
        reloaded.load_store_deals("s1", db=db)
        reloaded.load_store("s1", db=db)
        assert db.requested == ["deals_restored", "stores_restored"]
    finally:
        # Other tests import the module-level constants; restore the defaults.
        monkeypatch.delenv("DEALS_COLLECTION")
        monkeypatch.delenv("STORES_COLLECTION")
        importlib.reload(deals_source)


def test_expired_deals_are_filtered_out_of_the_query():
    """The pipeline stamps a lifecycle on every row; pricing must respect it.

    Without this the engine keeps quoting savings on offers the source took
    down — the collection used to have no lifecycle at all, so nothing stopped it.
    """
    db = _FakeDb({"deals": [{"id": "d1", "store_id": "s1"}]})

    deals_source.load_store_deals("s1", db=db)

    assert db.last.last_query["status"] == {"$ne": "expired"}


def test_the_filter_is_not_expired_rather_than_is_active():
    """Absent is not expired, and Mongo's ``$ne`` is what makes that true.

    ``{"status": {"$ne": "expired"}}`` matches documents with no ``status`` field
    at all; ``{"status": "active"}`` does not. Rows written before the pipeline
    stamped a lifecycle are live deals that simply predate the field, so the
    stricter filter would empty the optimizer on any database not yet fully
    re-scraped — a silent, total outage of every quote.
    """
    db = _FakeDb({"deals": []})

    deals_source.load_store_deals("s1", db=db)

    assert db.last.last_query["status"] == {"$ne": "expired"}, (
        "must stay an inequality — an equality on 'active' hides unstamped rows"
    )
