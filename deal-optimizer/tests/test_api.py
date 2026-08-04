"""The HTTP surface (api.py) and the Mongo → engine dict mapping it feeds on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from deal_optimizer import api
from deal_optimizer.deals_source import _to_engine_dict, load_store_deals, summarize_deals

from conftest import mk_deal


@pytest.fixture
def client():
    return TestClient(api.app)


@pytest.fixture
def stocked_store(monkeypatch):
    """Two stackable deals at store_1, and nothing anywhere else."""
    deals = [
        mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, store_id="store_1", title="10% coupon"),
        mk_deal("b", "giftcard_discount", reward_type="percentage_off", reward_value=0.20,
                accepts_all=True, store_id="store_1", title="20% gift card"),
    ]
    monkeypatch.setattr(
        api, "load_store_deals", lambda store_id: deals if store_id == "store_1" else []
    )
    return deals


def test_optimize_returns_ranked_results(client, stocked_store):
    response = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
    )

    assert response.status_code == 200
    body = response.json()

    assert body["store_id"] == "store_1"
    assert body["cart_total"] == 100
    assert body["deals_considered"] == 2
    assert len(body["results"]) >= 1

    best = body["results"][0]
    assert best["rank"] == 1
    assert best["final_price"] < body["cart_total"]
    # Ranked cheapest-first.
    assert [r["final_price"] for r in body["results"]] == sorted(r["final_price"] for r in body["results"])


def test_optimize_ships_a_deal_lookup_for_the_paths(client, stocked_store):
    body = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
    ).json()

    # build_export_payload reduces paths to bare ids; every one must be resolvable
    # from the sibling `deals` map so a client needs no extra round-trip.
    for result in body["results"]:
        for deal_id in result["path"]:
            assert deal_id in body["deals"]
    assert body["deals"]["a"]["title"] == "10% coupon"


def test_store_with_no_deals_is_an_empty_result_not_an_error(client, stocked_store):
    response = client.post(
        "/optimize", json={"store_id": "store_unknown", "cart_total": 100, "cart_quantity": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["deals_considered"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"store_id": "", "cart_total": 100},          # store_id must be non-empty
        {"store_id": "store_1", "cart_total": 0},      # cart_total must be > 0
        {"store_id": "store_1", "cart_total": -5},
        {"store_id": "store_1", "cart_total": 100, "cart_quantity": 0},
        {"store_id": "store_1", "cart_total": 100, "top_n": 0},
        {"cart_total": 100},                            # store_id is required
    ],
)
def test_invalid_requests_are_rejected(client, stocked_store, payload):
    assert client.post("/optimize", json=payload).status_code == 422


def test_strict_mode_is_passed_through(client, monkeypatch):
    # "unknown" combinability — optimistic by default, refused under strict.
    deals = [
        mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10, store_id="store_1"),
        mk_deal("b", "member_discount", reward_type="percentage_off", reward_value=0.20, store_id="store_1"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)

    optimistic = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "strict": False}
    ).json()
    strict = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "strict": True}
    ).json()

    # Optimistic can chain both; strict can only ever apply one at a time.
    assert max(len(r["per_step"]) for r in optimistic["results"]) == 2
    assert max(len(r["per_step"]) for r in strict["results"]) == 1


@pytest.fixture
def membership_gated(monkeypatch):
    """One open deal, one that needs membership in the 'hot' program."""
    deals = [
        mk_deal("open", "coupon", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, store_id="store_1"),
        mk_deal("gated", "member_discount", reward_type="percentage_off", reward_value=0.50,
                accepts_all=True, store_id="store_1", membership_required="yes", source_id="hot"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)
    return deals


def test_membership_deal_is_offered_to_a_member(client, membership_gated):
    body = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "member_source_ids": ["hot"]}
    ).json()

    assert any("gated" in r["path"] for r in body["results"])


def test_membership_deal_is_pruned_for_a_non_member(client, membership_gated):
    # A wallet that exists but doesn't include 'hot' — this is what prunes.
    body = client.post(
        "/optimize", json={"store_id": "store_1", "cart_total": 100, "member_source_ids": ["mastercard"]}
    ).json()

    assert body["results"]
    assert all("gated" not in r["path"] for r in body["results"])


def test_no_wallet_in_the_request_is_optimistic(client, membership_gated):
    # An absent wallet means "unknown user", not "user has nothing" — the engine
    # keeps gated deals rather than hiding savings the user may well be entitled to.
    body = client.post("/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert any("gated" in r["path"] for r in body["results"])


def test_current_deal_head_maps_onto_the_engine_dict():
    # A deals_current head: bookkeeping at the top level, the serialized Deal
    # under `snapshot` — that snapshot is what the engine reads.
    doc = {
        "_id": "key_abc",
        "deal_id": "deal_1",
        "store_id": "store_1",
        "source_id": "hot",
        "status": "active",
        "content_hash": "abc123",
        "version": 3,
        "snapshot": {"id": "deal_1", "store_id": "store_1", "title": "10% off", "deal_type": "coupon"},
    }

    deal = _to_engine_dict(doc)

    assert deal["id"] == "deal_1"
    assert deal["title"] == "10% off"
    assert deal["deal_type"] == "coupon"
    # Head-level bookkeeping must not leak into the engine's deal dict.
    assert "content_hash" not in deal
    assert "status" not in deal
    assert "_id" not in deal
    # The cursor's document is not ours to mutate.
    assert doc["snapshot"]["id"] == "deal_1"


def test_head_without_id_in_snapshot_falls_back_to_deal_id():
    doc = {
        "_id": "key_abc",
        "deal_id": "deal_1",
        "store_id": "store_1",
        "source_id": "hot",
        "snapshot": {"title": "10% off"},
    }

    deal = _to_engine_dict(doc)

    # The engine keys every path entry on id — it must never come back empty.
    assert deal["id"] == "deal_1"
    assert deal["store_id"] == "store_1"
    assert deal["source_id"] == "hot"


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.query = None

    def find(self, query):
        self.query = query
        return iter(self.docs)


class _FakeDb:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return self.collections[name]


def test_load_store_deals_reads_active_heads_from_deals_current():
    head = {
        "_id": "key_a",
        "deal_id": "a",
        "store_id": "store_1",
        "source_id": "hot",
        "status": "active",
        "snapshot": {"id": "a", "store_id": "store_1", "title": "10% off"},
    }
    collection = _FakeCollection([head])
    # The legacy append-only collection must not be touched — with versioning on
    # (the default) the pipeline no longer writes it.
    db = _FakeDb({"deals_current": collection})

    deals = load_store_deals("store_1", db=db)

    assert [d["id"] for d in deals] == ["a"]
    assert collection.query["status"] == "active"
    assert {"store_id": "store_1"} in collection.query["$or"]
    # Group-wide deals live under the snapshot, not at the head's top level.
    assert {"snapshot.group_member_store_ids": "store_1"} in collection.query["$or"]


def test_summarize_deals_keys_on_deal_id():
    deals = [
        {"id": "d1", "title": "First", "deal_type": "coupon", "source_id": "hot",
         "deal_description": "desc", "benefit_url": "http://x"},
        {"id": "d2", "title": "Second"},
    ]

    summary = summarize_deals(deals)

    assert set(summary) == {"d1", "d2"}
    assert summary["d1"] == {
        "deal_id": "d1",
        "title": "First",
        "description": "desc",
        "deal_type": "coupon",
        "source_id": "hot",
        "club_id": None,
        "url": "http://x",
    }
    assert summary["d2"]["title"] == "Second"
    assert summary["d2"]["url"] is None
