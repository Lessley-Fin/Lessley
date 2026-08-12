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

`max_deals` (default 3, `None` = no cap) is how long a combination the engine
searches for — the most deals any one returned option may stack, counting the
chain and tender phases together. Left unbounded the engine will happily stack
seven coupons for another few shekels, which nobody executes at a checkout. The
cap is enforced *during* the search, not by filtering results afterwards, so a
cap of 2 returns the best possible pair rather than a truncated 5-deal stack —
and it prunes the state space, so a lower cap is also a cheaper search.

`deal_eligibility` (used internally by `find_top_paths` before any DP runs, and
publicly by `wallet.py`) prunes deals a given `UserContext` doesn't qualify
for: membership (`eligibility.membership_required` vs. `ctx.member_source_ids`),
a required payment method (`eligibility.payment_method_required`, matched via
the deal's `source_id` against the same `member_source_ids`), preferred store
type, and monthly usage caps. Both membership and payment-method checks key on
`source_id` — which scraper/API a deal came from (`hot`, `mastercard`,
`hever_gift_card_company`, ...) — rather than `club_id`, since `source_id` is a
required field on every real `Deal` while `club_id` needs a separate
Club-registry lookup and is often unset; a deal with no `source_id` can't be
verified and is kept optimistically.

## Why a separate module

It is fully self-contained: depends only on `pydantic`, imports nothing from
`lessley_deals`, ships its own `Dockerfile`, and consumes already-enriched deal
JSON. The LLM constraints parser stays in the main project; this module is the
runtime engine.

## Schema

The engine consumes the lean target schema (`schema.py`): a top-level
`deal_type` + a `constraints` block (`combinability` / `limits` /
`store_coverage` / `eligibility`). The `adapter.py` layer also accepts the
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
python -m deal_optimizer.cli data/deals.json <store_id> 500 --max-deals 2  # at most 2 deals per option (default 3; 0 = no limit)

# Library
from deal_optimizer import optimize, UserContext
results = optimize(deals, cart_total=500, cart_quantity=1, top_n=5, max_deals=3)
# → list of up to top_n dicts, cheapest first:
#   {"rank", "path": [...], "starting_price", "final_price", "total_savings", "per_step": [...]}
```

Each `per_step` entry has two kinds of fields, deliberately named apart so
they can't be confused: **whole-cart running state** (`bill_before`/
`bill_after` — the running total across the *entire* cart, chained step to
step) vs. **this-step-only state** (`ils_covered`/`discount_rate`/`savings`/
`amount_paid_on_covered` — only the slice of the bill this specific deal
touched). A card capped at 1000 ILS on a 1200 ILS cart still shows
`bill_before: 1200` — that's the whole cart at that point, not what the card
itself covered (`ils_covered: 1000` says that).

| Field | Scope | Meaning |
|---|---|---|
| `deal_id`, `bill_before`, `bill_after` | whole cart | The running bill total before/after this step (`bill_after` of one step = `bill_before` of the next) |
| `ils_covered` | this step | For tender deals (giftcard/payment/cashback): how much of `bill_before` was routed through that instrument. `None` for price-level deals (store_sale/coupon/member), which discount whatever's left rather than a specific slice |
| `discount_rate` | this step | Fraction (0–1) saved on the ILS this step covered |
| `savings` | this step | ILS saved by this step alone |
| `amount_paid_on_covered` | this step | What you pay, after this step's discount, for the ILS it covered |
| `remaining_to_allocate` | whole cart | Bill ILS not yet routed to any payment instrument — `None` until the first tender step, then counts down to 0 |
| `cumulative_savings` / `cumulative_discount_rate` | whole cart | Running total ILS saved / fraction of the original cart price saved so far, through this step |
| `segments` | this step | For a tiered card (`reward.tiers`): how `ils_covered` split across its rungs, each `{tier_index, rate, ils_covered, savings}`. `None` for flat deals |

E.g. a 1200 ILS cart split Hever (30% off, up to 1000) then Behatsdaa (30% off,
remaining 200): step 1 has `bill_before: 1200`, covers 1000 of it at 30% (pay
700 on it, 200 left to allocate, 25% cumulative discount), `bill_after: 900`;
step 2 has `bill_before: 900`, covers the remaining 200 at 30% (pay 140,
nothing left, 30% cumulative discount), `bill_after: 840`.

### Tiered loadable cards

Some cards discount at a rate that steps down as you load more — PaisPlus
networks gives 25% on the first 600 ILS, then 15% up to a 1500 ILS ceiling.
These carry a `reward.tiers` ladder:

```json
"reward": {"type": "percentage_off", "value": 0.25, "max_discount_amount": 285,
           "tiers": [{"from_amount": 0,   "to_amount": 600,  "percentage_off": 0.25},
                     {"from_amount": 600, "to_amount": 1500, "percentage_off": 0.15}]}
```

Each rung is allocated separately, so a 10,000 ILS cart routes 1500 through the
card (600 at 25% + 900 at 15% = 285 saved) rather than claiming 25% of the
whole cart. The step reports the split in `segments`, and `discount_rate` is
the blended 19% across the ILS actually covered. `value` and
`max_discount_amount` stay populated as a bounded fallback for consumers that
don't walk the ladder.

Deals may also declare `discount_logic.exclusive_group`; two deals sharing that
string are never combined. It exists for sources that publish one deal per
membership tier of the *same* physical card (PaisPlus emits a regular and a vip
variant) — combinability can't express this, since it is keyed on `deal_type`
and both sides are `giftcard_discount`.

`unknown_as_yes=True` (default, optimistic) treats combinability `"unknown"` as
`"yes"`; `--strict` / `unknown_as_yes=False` treats it as `"no"`.

## Exporting results for an application

`--output/-o <path>` (both this CLI and `lessley-deals`' `deals optimize`)
writes the ranked results to a JSON file for an application to load, via
`build_export_payload()`:

```python
from deal_optimizer import build_export_payload
payload = build_export_payload(results, store_id=store_id, cart_total=cart_total,
                                cart_quantity=quantity, wallet_id=wallet_id)
```

```json
{
  "generated_at": "2026-07-31T09:31:19+00:00",
  "store_id": "...", "cart_total": 2000, "cart_quantity": 1, "wallet_id": "user_ido_full",
  "results": [
    {"rank": 1, "starting_price": 2000, "final_price": 1471.0, "total_savings": 529.0,
     "path": ["LC04_hever_giftcard_1000", "LC05_behatsdaa_giftcard_500", "..."],
     "per_step": [{"deal_id": "LC04_hever_giftcard_1000", "bill_before": 2000, "bill_after": 1700.0,
                   "ils_covered": 1000.0, "discount_rate": 0.3, "savings": 300.0,
                   "amount_paid_on_covered": 700.0, "remaining_to_allocate": 0.0,
                   "cumulative_savings": 300.0, "cumulative_discount_rate": 0.15,
                   "segments": null}, "..."]}
  ]
}
```

Unlike the in-memory `optimize()`/`get_optimal_deal_path()` return value (where
`path` holds the full original deal dict per step), the exported `path` is
reduced to bare `deal_id` strings — the application is expected to resolve
those against its own deals database rather than have full deal objects
duplicated into the export file.

## User wallets (demo)

A `UserWallet` (`wallet.py`) is a mock struct — generic user info plus the
loyalty programs joined and credit cards held — that resolves into a
`UserContext` so the optimizer only considers deals actually available to that
person. Each `WalletCard` links to the `source_id` a deal's `eligibility` block
checks against, so holding "a Mastercard" is enough to unlock deals gated by
`payment_method_required`, exactly the same way program membership unlocks
deals gated by `membership_required`.

```python
from deal_optimizer.wallet import load_wallets, get_eligible_deals, wallet_to_user_context
from deal_optimizer import optimize

wallets = load_wallets("data/mock_wallets.json")
wallet = wallets["user_ido_full"]

eligible = get_eligible_deals(deals, wallet)  # standalone pre-filter trace
results = optimize(deals, cart_total=500, cart_quantity=1,
                    user_context=wallet_to_user_context(wallet))
```

```bash
python -m deal_optimizer.cli data/mock_deals.json <store_id> 500 \
    --wallet-id user_ido_full --wallet-file data/mock_wallets.json
```

`--wallet-id`/`--wallet-file` provide a baseline context; `--sources`/
`--store-types`/`--monthly-uses` layer extra ad-hoc data on top without editing
the wallet file.

## HTTP service

`api.py` puts a thin FastAPI surface over the same engine, so the web UI can
price a cart without shelling out to the CLI. The engine itself stays a library —
the HTTP deps live behind the `service` extra, and nothing in `engine.py` knows
the API exists.

The service is exposed **by Caddy, not by the Gateway**: the edge routes
`/api/v1/optimizer/*` here, so the Gateway has no knowledge of this service at
all. Caddy strips `/api/v1` and every route below carries the `/optimizer`
prefix itself — the same split Personalization uses.

Ports follow the workspace convention: **5003 in the container (and in
production), published on 8003 in dev.**

```bash
pip install -e ".[service]"
uvicorn deal_optimizer.api:app --host 0.0.0.0 --port 5003
```

### Security

Two controls, both ported from Personalization — keep them in step:

- **`EdgeAuthMiddleware`** (`edge_auth.py`) rejects any request without
  `X-Edge-Key: $Edge_ApiKey`, which only Caddy can stamp. Defense in depth: the
  primary control is that production publishes no port for this service.
  `/optimizer/health` is exempt so Docker's healthcheck can reach it directly.
- **`authenticated_email`** (`auth.py`) requires `X-Auth-Email`, which Caddy sets
  from the Gateway's verified JWT claims via `forward_auth` and strips from
  anything a client sends. `/optimizer/optimize` refuses to run without it.
  Memberships still come from the request body — identity gates access to the
  endpoint, it does not select data.

| Variable | Meaning |
|---|---|
| `Edge_ApiKey` | Shared edge secret. Blank disables the check. |
| `Environment` | `Development` enables `/docs`; defaults to `Production`. |
| `Edge_AllowUnverified` | Mode 1 escape hatch — only honoured when `Environment=Development`. Drops the edge-key requirement and decodes identity out of the Gateway's `access_token` cookie. |

Running locally with no Caddy in front (Mode 1) means no `X-Edge-Key` and no
`X-Auth-Email`, so set **both** `Environment=Development` and
`Edge_AllowUnverified=True` or every call comes back 403/401.

`POST /optimizer/optimize` takes the cart and (optionally) what's in the user's wallet:

```jsonc
{
  "store_id": "store_1",
  "cart_total": 500,
  "cart_quantity": 1,
  "top_n": 5,
  "max_deals": 3,             // most deals one option may stack (1..10)
  "strict": false,            // combinability "unknown" → "no"
  "member_source_ids": ["hot", "mastercard"],
  "preferred_store_types": ["online"],
  "uses_this_month": {"D11": 1}
}
```

It returns `build_export_payload`'s envelope plus two fields the file export
doesn't need: a `deals` map (deal_id → title/type/source) so a client can render
a path without a round-trip per deal, and `deals_considered`.

Two behaviours worth knowing, both matching the CLI:

- **An absent wallet is optimistic, not restrictive.** Omitting
  `member_source_ids` means "unknown user" and prunes nothing; sending a wallet
  that lacks a deal's required `source_id` is what prunes it. So `[]` and a
  missing field both mean "don't filter" — send the user's actual programs to
  filter.
- **The trivial "apply nothing" path is dropped.** The DP always includes
  START → END (pay full price); it's a real path but not an option worth
  offering, so `results` comes back empty when nothing stacks. Callers render
  "no stack found" off an empty list rather than off a zero-savings result.

Deals are read from `lessley-deals`' MongoDB (`MONGO_URI` / `MONGO_DB`) — the shared
`deals` collection, alongside `stores` for display and `clubs`/`users` for eligibility.
The Gateway's deal search and Personalization read those same collections, so all three
services see one shape and there is no projected copy to keep in step.

`deals_current`/`deal_versions` are the pipeline's change history, not this read path:
they carry the deal under a `snapshot` sub-document and only cover the sources of
whichever run last populated them — reading them is what once hid every HOT deal from
this engine.

Store matching covers `store_id`, `group_member_store_ids` and `group_member_stores`, so
group-wide deals surface for any member store. `GET /optimizer/health` pings that database.

## Docker

```bash
docker build -t deal-optimizer .
docker build --target service -t deal-optimizer-api . && docker run --rm -p 8003:5003 deal-optimizer-api
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
| `engine.py` | `UserContext`, `deal_eligibility` prune (source/card/store-type/monthly-cap), 2-phase state-DP `find_top_paths` (chain → tender, ranked) + `find_best_path` convenience wrapper, `optimize`, `get_optimal_deal_path` |
| `wallet.py` | `UserWallet`/`WalletCard` mock demo model, `wallet_to_user_context` bridging, `get_eligible_deals()` standalone pre-filter, `load_wallets()` JSON loader |
| `cli.py` | Command-line entry point |
| `deals_source.py` | `deals`/`stores` → engine-dict loading (`load_store_deals`, `load_store`), plus the `summarize_deals` display lookup |
| `user_source.py` | The caller's clubs → `source_id`s, from the verified `X-Auth-Email` (`users`, `clubs`) |
| `api.py` | FastAPI surface — `POST /optimizer/optimize`, `GET /optimizer/health` |
