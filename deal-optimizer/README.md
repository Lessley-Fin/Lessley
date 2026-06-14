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
store_sale → member_discount → coupon → giftcard_discount → payment_discount → cashback
```

An edge `A → B` exists only when **both** sides agree (A allows B's category AND
B allows A's), and B's layer is not earlier than A's. The optimal path is found
with a state-tracking DP that re-validates every (new, prior) pair as the chain
grows — so 3+ deal stacks can't sneak in a pairwise-illegal member.

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
python -m deal_optimizer.cli data/deals.json <store_id> 500 --strict   # unknown→no

# Library
from deal_optimizer import optimize, UserContext
result = optimize(deals, cart_total=500, cart_quantity=1)
# → {"path": [...], "starting_price", "final_price", "total_savings", "per_step": [...]}
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
| `engine.py` | `UserContext`, eligibility prune, state-DP `find_best_path`, `optimize`, `get_optimal_deal_path` |
| `cli.py` | Command-line entry point |
