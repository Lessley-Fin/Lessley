"""The HTTP surface (api.py) and the Mongo → engine dict mapping it feeds on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from deal_optimizer import api
from deal_optimizer.deals_source import _to_engine_dict, load_store, load_store_deals, summarize_deals

from conftest import mk_deal


@pytest.fixture
def client():
    # X-Auth-Email is what Caddy's forward_auth copies onto every proxied request;
    # /optimizer/optimize refuses to run without it. Edge-key and identity enforcement
    # get their own coverage in test_edge_auth.py.
    return TestClient(api.app, headers={"X-Auth-Email": "user@example.com"})


@pytest.fixture(autouse=True)
def known_user(monkeypatch):
    """The caller exists and has joined nothing — the default for tests that don't care.

    Every request resolves eligibility from the users collection, so without this each
    test would 404 on a database that isn't there.
    """
    monkeypatch.setattr(api, "member_source_ids_for", lambda email: [])


@pytest.fixture
def member_of(monkeypatch):
    """Make the authenticated caller a member of these source_ids."""

    def _set(source_ids: list[str] | None) -> None:
        monkeypatch.setattr(api, "member_source_ids_for", lambda email: source_ids)

    return _set


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
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
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
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
    ).json()

    # build_export_payload reduces paths to bare ids; every one must be resolvable
    # from the sibling `deals` map so a client needs no extra round-trip.
    for result in body["results"]:
        for deal_id in result["path"]:
            assert deal_id in body["deals"]
    assert body["deals"]["a"]["title"] == "10% coupon"


def test_store_with_no_deals_is_an_empty_result_not_an_error(client, stocked_store):
    response = client.post(
        "/optimizer/optimize", json={"store_id": "store_unknown", "cart_total": 100, "cart_quantity": 1}
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
    assert client.post("/optimizer/optimize", json=payload).status_code == 422


def test_strict_mode_is_passed_through(client, monkeypatch):
    # "unknown" combinability — optimistic by default, refused under strict.
    deals = [
        mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10, store_id="store_1"),
        mk_deal("b", "member_discount", reward_type="percentage_off", reward_value=0.20, store_id="store_1"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)

    optimistic = client.post(
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "strict": False}
    ).json()
    strict = client.post(
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "strict": True}
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


def test_membership_deal_is_offered_to_a_member(client, membership_gated, member_of):
    member_of(["hot"])

    body = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert any("gated" in r["path"] for r in body["results"])


def test_membership_deal_is_pruned_for_a_non_member(client, membership_gated, member_of):
    # Clubs that exist but don't include 'hot' — this is what prunes.
    member_of(["mastercard"])

    body = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert body["results"]
    assert all("gated" not in r["path"] for r in body["results"])


def test_a_user_who_joined_nothing_is_pruned_not_treated_as_unknown(client, membership_gated, member_of):
    # The distinction that matters: [] is a *known* user with no memberships, so a
    # members-only deal must be pruned. Treating it as "unknown user" would offer every
    # gated deal to everybody — which is what happened while the client sent [] itself.
    member_of([])

    body = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert body["results"]
    assert all("gated" not in r["path"] for r in body["results"])


def test_memberships_in_the_request_body_are_ignored(client, membership_gated, member_of):
    # The whole point of resolving eligibility from the verified identity: a client
    # cannot hand itself a membership it does not have.
    member_of([])

    body = client.post(
        "/optimizer/optimize",
        json={"store_id": "store_1", "cart_total": 100, "member_source_ids": ["hot"]},
    ).json()

    assert all("gated" not in r["path"] for r in body["results"])


def test_deals_from_a_club_the_user_has_not_joined_are_not_offered(client, monkeypatch, member_of):
    # Neither deal declares membership_required — the state 911 of 10,137 real deals are
    # in, every Mastercard one among them. Only the caller's actual clubs decide.
    deals = [
        mk_deal("hot_deal", "coupon", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, store_id="store_1", source_id="hot"),
        mk_deal("mc_deal", "coupon", reward_type="percentage_off", reward_value=0.50,
                accepts_all=True, store_id="store_1", source_id="mastercard"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)
    member_of(["hot"])

    body = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert body["results"], "the joined club's deal should still be offered"
    assert all("mc_deal" not in r["path"] for r in body["results"])
    assert any("hot_deal" in r["path"] for r in body["results"])


def test_a_user_in_no_clubs_is_offered_nothing(client, monkeypatch, member_of):
    # Every real deal carries a source_id, so a user who has joined nothing can redeem
    # nothing. (A deal with no source_id at all is still kept — see test_eligibility.)
    deals = [
        mk_deal("hot_deal", "coupon", reward_type="percentage_off", reward_value=0.10,
                accepts_all=True, store_id="store_1", source_id="hot"),
        mk_deal("mc_deal", "coupon", reward_type="percentage_off", reward_value=0.50,
                accepts_all=True, store_id="store_1", source_id="mastercard"),
    ]
    monkeypatch.setattr(api, "load_store_deals", lambda store_id: deals)
    member_of([])

    body = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100}).json()

    assert body["results"] == []
    # The deals were considered and rejected, not missing.
    assert body["deals_considered"] == 2


def test_an_authenticated_caller_we_have_no_user_for_is_not_priced(client, membership_gated, member_of):
    # Edge-authenticated but absent from our users collection. Falling back to "unknown
    # user" here would price the cart with every members-only deal on offer.
    member_of(None)

    response = client.post("/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_a_deal_row_maps_onto_the_engine_dict():
    # A `deals` row: the deal itself, flat, with the business key as _id. This is what
    # DealMongoRepository.save writes and what every consumer reads.
    doc = {
        "_id": "deal_1",
        "store_id": "store_1",
        "source_id": "hot",
        "title": "10% off",
        "deal_type": "coupon",
        "fingerprint": "abc123",
    }

    deal = _to_engine_dict(doc)

    assert deal["id"] == "deal_1"
    assert deal["title"] == "10% off"
    assert deal["deal_type"] == "coupon"
    # Storage-level bookkeeping must not leak into the engine's deal dict.
    assert "fingerprint" not in deal
    assert "_id" not in deal


def test_an_imported_row_keeps_its_own_id():
    # mongoimport leaves the business key in `id` and generates an ObjectId `_id`; the
    # engine keys every path entry on id, so it must resolve either way.
    doc = {"_id": "68f0c0ffee00000000000001", "id": "deal_1", "store_id": "store_1"}

    deal = _to_engine_dict(doc)

    assert deal["id"] == "deal_1"
    assert deal["store_id"] == "store_1"


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


def test_load_store_deals_reads_the_shared_deals_collection():
    row = {"_id": "a", "store_id": "store_1", "source_id": "hot", "title": "10% off"}
    collection = _FakeCollection([row])
    # `deals` — the collection the Gateway and Personalization read too. deals_current is
    # the pipeline's change history and carries the deal under `snapshot`; reading it here
    # once hid every HOT deal from the optimizer.
    db = _FakeDb({"deals": collection})

    deals = load_store_deals("store_1", db=db)

    assert [d["id"] for d in deals] == ["a"]
    assert {"store_id": "store_1"} in collection.query["$or"]
    # Group-wide deals are matched in the query, in every shape the pipeline produces.
    assert {"group_member_store_ids": "store_1"} in collection.query["$or"]
    assert {"group_member_stores.store_id": "store_1"} in collection.query["$or"]


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
        "store_url": None,
        "terms_and_conditions": None,
        "minimum_purchase": None,
        "max_uses_per_transaction": None,
        "max_uses_per_month": None,
        "max_discount_amount": None,
        "membership_required": None,
    }
    assert summary["d2"]["title"] == "Second"
    assert summary["d2"]["url"] is None


def test_summarize_deals_lifts_terms_out_of_nested_documents():
    deal = {
        "id": "d1",
        "title": "Loadable card",
        "url": "http://store",
        "terms_and_conditions": "Up to 3,000 ILS per month.",
        "discount_logic": {"reward": {"type": "percentage_off", "value": 0.3, "max_discount_amount": 300}},
        "constraints": {
            "limits": {"minimum_purchase": 100, "max_uses_per_transaction": 1, "max_uses_per_month": 2},
            "eligibility": {"membership_required": True},
        },
    }

    summary = summarize_deals([deal])["d1"]

    assert summary["terms_and_conditions"] == "Up to 3,000 ILS per month."
    assert summary["minimum_purchase"] == 100
    assert summary["max_uses_per_transaction"] == 1
    assert summary["max_uses_per_month"] == 2
    assert summary["max_discount_amount"] == 300
    assert summary["membership_required"] is True
    # No benefit_url, so the claim link falls back to the merchant's own site,
    # which store_url reports separately.
    assert summary["url"] == "http://store"
    assert summary["store_url"] == "http://store"


def test_load_store_returns_display_fields(monkeypatch):
    class _Stores:
        def find_one(self, query):
            assert query == {"$or": [{"_id": "store_1"}, {"id": "store_1"}]}
            return {
                "_id": "store_1",
                "name": "KSP",
                "metadata": {
                    "store_url": "https://ksp.co.il",
                    "image_urls": ["https://cdn/1.png"],
                    "mcc_codes": ["ELECTRONICS"],
                },
            }

    store = load_store("store_1", db={"stores": _Stores()})

    assert store == {
        "store_id": "store_1",
        "name": "KSP",
        "store_url": "https://ksp.co.il",
        "image_urls": ["https://cdn/1.png"],
        "mcc_codes": ["ELECTRONICS"],
    }


def test_load_store_returns_none_when_the_store_is_unknown():
    class _Stores:
        def find_one(self, query):
            return None

    assert load_store("nope", db={"stores": _Stores()}) is None


def test_optimize_response_carries_the_store_for_display(client, stocked_store, monkeypatch):
    monkeypatch.setattr(
        api, "load_store", lambda store_id: {"store_id": store_id, "name": "KSP", "image_urls": ["u"]}
    )

    body = client.post(
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
    ).json()

    assert body["store"] == {"store_id": "store_1", "name": "KSP", "image_urls": ["u"]}


def test_a_broken_store_lookup_does_not_cost_the_caller_its_prices(client, stocked_store, monkeypatch):
    def _boom(store_id):
        raise PyMongoError("down")

    monkeypatch.setattr(api, "load_store", _boom)

    response = client.post(
        "/optimizer/optimize", json={"store_id": "store_1", "cart_total": 100, "cart_quantity": 1}
    )

    assert response.status_code == 200
    assert response.json()["store"] is None
    assert response.json()["results"]
