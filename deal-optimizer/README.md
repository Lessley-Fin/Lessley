# deal-optimizer

Independent module implementing the **layered-DAG deal stacking optimizer**.

Given a cart and a set of enriched deals, it finds the cheapest *legal*
combination of compatible deals — modeled as a directed acyclic flow graph:

```
START → deal → deal → ... → END
```

Each deal-vertex transforms a price (`price_in → price_out`) via its
`discount_logic`. Edges encode which deal may legally be applied after another,
derived from each deal's `combinability` plus a fixed global layer order:

```
store_sale → member_discount → coupon
```

An edge `A → B` exists only when **both** sides agree (A allows B's category AND
B allows A's), and B's layer is not earlier than A's. The optimal path is found
with a state-tracking DP that re-validates every (new, prior) pair as the chain
grows — so 3+ deal stacks can't sneak in a pairwise-illegal member.

**`giftcard_discount`, `payment_discount`, and `cashback` are not part of the
DAG chain.** Price-level deals (store_sale/member_discount/coupon) really do
apply to whatever's left, however you eventually pay, so chaining them is
exact. But gift-card loads, card-brand rebates, and cashback (earned on
whatever was charged to the card that earns it) each only discount the
specific slice of money paid through that instrument — you can't pay the same
400 ILS with two different cards. Chaining them the same way as price-level
deals would double-count. Instead, `tender.py` solves them as a bill-splitting
problem: for every DAG state, it finds the savings-maximizing way to route the
remaining bill across payment instruments (fixed-value vouchers are
all-or-nothing; percentage-off deals — capped via `max_discount_amount`, or
uncapped — are fractional-knapsack filled highest-rate-first). E.g. a 2000 ILS
bill against a 30%-off-up-to-1000 card, a 30%-off-up-to-500 card, and an
uncapped 20%-off card routes 1000 → the first card, 500 → the second, and the
remaining 500 → the third — never "30% off the whole 2000" from two different
cards at once.

`optimize()` doesn't just return the winner — it returns the top `top_n`
(default 5) distinct ranked outcomes, cheapest first, so you can see the
runner-up combinations too (e.g. "use only Hever" vs. "split Hever + Behatsdaa
+ Mastercard").

## Why a separate module

It is fully self-contained: depends only on `pydantic`, imports nothing from
`lessley_deals`, ships its own `Dockerfile`, and consumes already-enriched deal
JSON. The LLM constraints parser stays in the main project; this module is the
runtime engine.

## Schema

The engine consumes the lean target schema (`schema.py`): a top-level
`deal_type` + a `constraints` block (`combinability` / `limits` /
`redemption_channels` / `eligibility`). The `adapter.py` layer also accepts the
**legacy** enrichment shape (`discount_logic.constraints` with old field names,
structured `max_uses_per_period`, string `minimum_purchase`) and translates it
— so the engine runs on existing data today.

## Usage

```bash
pip install -e ".[dev]"

# CLI
python -m deal_optimizer.cli data/deals.json <store_id> 500 --quantity 1
python -m deal_optimizer.cli data/deals.json <store_id> 500 --strict     # unknown→no
python -m deal_optimizer.cli data/deals.json <store_id> 500 --top-n 3    # show fewer/more ranked options (default 5)

# Library
from deal_optimizer import optimize, UserContext
results = optimize(deals, cart_total=500, cart_quantity=1, top_n=5)
# → list of up to top_n dicts, cheapest first:
#   {"rank", "path": [...], "starting_price", "final_price", "total_savings", "per_step": [...]}
# per_step entries include "ils_covered": how much of the bill that specific
# deal paid for (tender deals only — None for price-level deals).
```

`unknown_as_yes=True` (default, optimistic) treats combinability `"unknown"` as
`"yes"`; `--strict` / `unknown_as_yes=False` treats it as `"no"`.

## Docker

```bash
docker build -t deal-optimizer .
docker build --target test -t deal-optimizer-test . && docker run --rm deal-optimizer-test
```

## Tests

```bash
pytest -q          # all Part 5 verification scenarios + adapter + eligibility
```

## Module layout

| File | Responsibility |
|------|----------------|
| `schema.py` | Lean Pydantic target schema (`DealType`, `Combinability`, `Limits`, …) |
| `adapter.py` | Normalize new + legacy deal dicts; deterministic `deal_type` inference |
| `graph.py` | `DealNode`, `LAYER_ORDER`, `ACCEPTS_KEY`, edges, vertex expansion (duplicates) |
| `transform.py` | `apply_deal` price transform (both plan bug fixes baked in) |
| `tender.py` | `allocate_tender` / `allocate_tender_top_k` — ranked bill-splitting across giftcard/payment/cashback deals |
| `engine.py` | `UserContext`, eligibility prune, 2-phase state-DP `find_top_paths` (chain → tender, ranked) + `find_best_path` convenience wrapper, `optimize`, `get_optimal_deal_path` |
| `cli.py` | Command-line entry point |
