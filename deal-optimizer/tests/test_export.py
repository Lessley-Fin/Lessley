"""build_export_payload: the JSON envelope written by --output, with each
result's path reduced to bare deal_ids for an application to resolve against
its own database."""

from __future__ import annotations

from deal_optimizer.engine import build_export_payload, optimize

from conftest import mk_deal


def test_export_payload_reduces_path_to_deal_ids():
    deal_a = mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    deal_b = mk_deal("b", "giftcard_discount", reward_type="percentage_off", reward_value=0.20, accepts_all=True)
    results = optimize([deal_a, deal_b], cart_total=100, cart_quantity=1)

    payload = build_export_payload(results, store_id="store_1", cart_total=100, cart_quantity=1, wallet_id="u1")

    assert payload["store_id"] == "store_1"
    assert payload["cart_total"] == 100
    assert payload["cart_quantity"] == 1
    assert payload["wallet_id"] == "u1"
    assert "generated_at" in payload

    best = payload["results"][0]
    assert best["path"] == [step["deal_id"] for step in best["per_step"]]
    assert all(isinstance(deal_id, str) for deal_id in best["path"])


def test_export_payload_does_not_mutate_original_results():
    deal = mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    results = optimize([deal], cart_total=100, cart_quantity=1)

    build_export_payload(results, store_id="store_1", cart_total=100, cart_quantity=1)

    # Original in-memory results still carry full deal dicts, untouched —
    # console printing (CLI) relies on this shape.
    assert results[0]["path"][0]["id"] == "a"


def test_export_payload_wallet_id_defaults_to_none():
    deal = mk_deal("a", "coupon", reward_type="percentage_off", reward_value=0.10, accepts_all=True)
    results = optimize([deal], cart_total=100, cart_quantity=1)

    payload = build_export_payload(results, store_id="store_1", cart_total=100, cart_quantity=1)
    assert payload["wallet_id"] is None
