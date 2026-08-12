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

    def find(self, query):
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
        return _FakeCollection(self._contents.get(name, []))


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
