# Optimizer Engine: Layered DAG with Combinability Edges

## Context

The current optimizer evaluates each deal in isolation and ranks them by savings. This cannot answer the real question — **"which combination of compatible deals minimizes my final price?"** A 500₪ Rami Levi cart might benefit from a coupon AND a credit-card discount AND a cashback, if those three deals can legally stack together. Today we'd return whichever single deal saved the most, which can be strictly worse than the optimal stack.

**The new model treats the optimizer as a directed acyclic flow graph:**

- **Vertices** = `START`, every available deal, and `END`.
- **Each deal-vertex** transforms a price (`price_in → price_out`) via its `discount_logic`, conditional on its own validation rules (min_spend, exact_spend, min_quantity, etc.).
- **Edges** are directed, derived from each deal's `combinability` data plus a fixed global layer order. An edge `A → B` exists when applying B after A is legal — i.e. A's combinability allows B's category, and B's layer is >= A's layer.
- **`START`** has an edge to every deal (each deal can be the first applied).
- **Every deal** has an edge to `END` (each deal can be the last applied).
- **Goal**: find the path `START → ... → END` that yields the **lowest final price**.

The pathfinding itself is trivial (topological order + DP, since the graph is a DAG). **The real engineering challenge is building the graph correctly**, which means the constraints parser must emit metadata rich enough to determine each deal's category, its application math, and its directional edges.

---

## Part 1 — Deal Types (Graph Layers)

Six types, matching the field values in `data/final_format_of_deal.json`, in fixed global application order:

| # | `deal_type` value     | Hebrew              | Application behavior                                                  |
|---|-----------------------|---------------------|-----------------------------------------------------------------------|
| 1 | `store_sale`          | מבצע רשת             | Store sale applied to items in the cart. (Currently not scraped — store websites are out of scope, but kept in the layer list for future use.) |
| 2 | `member_discount`     | הנחת מועדון           | Club / loyalty discount (e.g. הוט יותר)                              |
| 3 | `coupon`              | קופון                | One-time code, % or fixed off                                         |
| 4 | `giftcard_discount`   | תו קניה / גיפט קארד    | Discount on a pre-purchased gift card / voucher (covers תוי קניה too) |
| 5 | `payment_discount`    | הנחה במעמד החיוב      | Credit-card-specific discount applied at billing                      |
| 6 | `cashback`            | קאשבק                | Post-purchase rebate (returned after settlement)                      |

**Global order is fixed**: `store_sale → member_discount → coupon → giftcard_discount → payment_discount → cashback`.

**Schema note**: `deal_type` is a **top-level** field on the deal object (sibling to `discount_logic`, `constraints`, `coupon_code`, `club_id`), per `data/final_format_of_deal.json`. It is NOT nested inside `constraints`.

**Intra-layer edges ARE allowed**: if Coupon A's combinability declares it stacks with other coupons AND Coupon B accepts coupons in return, there is an edge `A → B`. Same-layer edges are oriented deterministically by deal `id` so the underlying graph stays acyclic — i.e. for a same-layer pair `(A, B)` with `A.id < B.id`, only the direction `A → B` exists. Each vertex is visited at most once per path (see also "Duplicate vertices" below for the repeat-use exception).

**Bidirectional combinability is required for every edge.** An edge `A → B` exists only when *both* sides agree: A's combinability allows category(B), AND B's combinability allows category(A). A one-sided "yes" is not enough.

**Path-wide chain validity (not just pairwise on the edge)**: When a path already contains `[A, B]` and we consider extending to C, C must be pairwise compatible with both A and B — and both A and B must accept C. The edge-existence check alone is insufficient for paths of length ≥ 2; the path-builder must re-validate every (new, prior) pair as new deals are added. See Part 3 for the DP that tracks this state.

**Duplicate vertices for repeat-usable deals**: When a deal's `transaction_limits.max_uses_per_transaction = N` (with N ≥ 2), the graph contains N copies of that vertex (`{deal.id}#1`, `{deal.id}#2`, …, `{deal.id}#N`). Each instance is a distinct vertex with the same `discount_logic` and `constraints`. The duplicates are chained in id-order so the DP can apply them sequentially: `{id}#1 → {id}#2 → …`. Combinability with itself is implicit (`max_uses_per_transaction ≥ 2` is the user's explicit grant of self-stackability). Deals without a `max_uses_per_transaction` set, or with the value `1`, get exactly one vertex.

**Categorization rule** (the LLM parser sets `deal_type` at the same time it parses constraints):

| Hint                                                                          | `deal_type`           |
|-------------------------------------------------------------------------------|-----------------------|
| Terms describe buying a תו קניה / gift card / שובר with a face value           | `giftcard_discount`   |
| Terms describe קאשבק / cashback / money returned after purchase                | `cashback`            |
| Terms describe a discount **at billing** with a specific credit card (הנחה במעמד החיוב, כרטיס אשראי המשויך) and NO voucher purchase | `payment_discount`    |
| Deal carries a `coupon_code` or terms describe a קופון to apply at checkout    | `coupon`              |
| Terms describe an הנחת מועדון (club discount) tied to membership without a voucher | `member_discount`     |
| Store-side sale (מבצע רשת) not tied to club / card                             | `store_sale`          |

The Hebrew-first hints are used by the LLM; the optimizer also keeps a deterministic fallback based on the structural signature (e.g. `condition.type == "exact_spend"` strongly implies `giftcard_discount`) for deals where the LLM is uncertain.

---

## Part 2 — Constraints Parser: Emit the Target Schema

**File**: `lessley-deals/src/lessley_deals/enrichment/constaints_parser.py`

The parser's output must match `data/final_format_of_deal.json` exactly. That requires three things: (a) a new Pydantic schema, (b) writing `deal_type` at the top level (not inside constraints), and (c) a system-prompt rewrite to match the new field names.

### 2a. Replace the Pydantic schema

The current `DealConstraints` model is too rich (`details_for_display`, `original_hebrew_evidence`, dated eligibility, `phone_order`/`delivery` channels, structured `max_uses_per_period`). The new target shape is much leaner:

```python
class DealType(StrEnum):
    STORE_SALE        = "store_sale"
    MEMBER_DISCOUNT   = "member_discount"
    COUPON            = "coupon"
    GIFTCARD_DISCOUNT = "giftcard_discount"
    PAYMENT_DISCOUNT  = "payment_discount"
    CASHBACK          = "cashback"

class Combinability(BaseModel):
    stackable_with_store_sale:        Literal["yes", "no", "unknown"]
    stackable_with_member_discounts:  Literal["yes", "no", "unknown"]
    stackable_with_coupons:           Literal["yes", "no", "unknown"]
    stackable_with_payment_discounts: Literal["yes", "no", "unknown"]
    stackable_with_giftcards:         Literal["yes", "no", "unknown"]
    stackable_with_cashback:          Literal["yes", "no", "unknown"]

class Limits(BaseModel):
    max_uses_per_transaction: int | None
    max_uses_per_month:       int | None
    minimum_purchase:         float | None     # ₪ threshold the customer must spend

class RedemptionChannels(BaseModel):
    website:        Literal["yes", "no", "unknown"]
    mobile_app:     Literal["yes", "no", "unknown"]
    physical_store: Literal["yes", "no", "unknown"]

class Eligibility(BaseModel):
    membership_required:     Literal["yes", "no", "unknown"]
    payment_method_required: str | None         # e.g. "כרטיס אשראי המשויך למועדון הוט"

class DealConstraints(BaseModel):
    combinability:       Combinability
    limits:              Limits
    redemption_channels: RedemptionChannels
    eligibility:         Eligibility

class DealParseResult(BaseModel):
    """LLM returns both deal_type and constraints in one call."""
    deal_type:   DealType
    constraints: DealConstraints
```

### 2b. Fix the storage path and write both fields

Replace the existing in-place write (line 262):

```python
# BEFORE
deal.setdefault("discount_logic", {})["constraints"] = result.model_dump()

# AFTER
result: DealParseResult = parse_deal(deal.get("terms_and_conditions"))
deal["deal_type"]   = result.deal_type.value
deal["constraints"] = result.constraints.model_dump()
```

The `discount_logic.constraints` sub-key is dropped entirely (it is not present in `final_format_of_deal.json`). If a `max_discount_amount` limit ever needs to come back, it should be a new field under `constraints.limits` — not under `discount_logic`.

### 2c. Rewrite the system prompt

The existing prompt is heavily tuned for the old schema (date parsing, day-of-week parsing, `period_days`, Hebrew evidence quotes). The replacement prompt must:

1. Instruct the LLM to return a `DealParseResult` with both `deal_type` and `constraints`.
2. Use the new combinability field names (`stackable_with_store_sale`, `stackable_with_payment_discounts`, `stackable_with_giftcards`, `stackable_with_cashback`).
3. Drop date / day-of-week / evidence-quote parsing (the target schema doesn't have those fields).
4. Convert `max_uses_per_period: {period_days: 30, max_uses: N}` to a single `max_uses_per_month: N`. Periods other than 30 days are coerced (`period_days=7` → `max_uses_per_month = max_uses * 4`; `period_days=365` → `max_uses_per_month = max_uses / 12`, rounded). This loses fidelity for weekly/yearly limits but matches the target schema and is simple to read.
5. Provide the `deal_type` decision table from Part 1.

Hebrew phrase table for the new combinability fields:

| Hebrew phrase                                        | Effect                                      |
|------------------------------------------------------|---------------------------------------------|
| "כפל מבצעים" / "מבצעי הרשתות"                          | `stackable_with_store_sale`                 |
| "כפל קופונים"                                          | `stackable_with_coupons`                    |
| "הנחות מועדונים" / "הטבות מועדון"                       | `stackable_with_member_discounts`           |
| "כפל הנחות אמצעי תשלום" / "כרטיס אשראי + הנחה"           | `stackable_with_payment_discounts`          |
| "תו קניה" / "שובר" / "גיפט קארד"                       | `stackable_with_giftcards`                  |
| "קאשבק"                                               | `stackable_with_cashback`                   |

### 2d. Handling `"unknown"` at optimizer time

The existing tri-state values stay. The optimizer (Part 3) interprets `"unknown"` via a config flag:

- **Optimistic** (default `OPTIMIZER_UNKNOWN_AS_YES = True`): treat as `"yes"` — surface more candidate combinations.
- **Strict** (`False`): treat as `"no"` — only propose explicitly-allowed stacks.

This is purely an optimizer interpretation; the parser writes the raw `"unknown"` from the LLM.

---

## Part 3 — Optimizer Engine Rewrite

**File**: `lessley-deals/src/optimizer/optimizer_utils.py`

### 3a. Fix the existing two bugs (do these first; they're independent)

```python
# BUG 1 — percentage_off formula. Scrapers store values as ratios already.
# (discount_parser.py:143 → reward = {"value": float(pct.group(1)) / 100.0})

# BEFORE
calculated_savings = cond_val   * (reward_val / 100.0)
calculated_savings = cart_total * (reward_val / 100.0)
# AFTER
calculated_savings = cond_val   * reward_val
calculated_savings = cart_total * reward_val

# BUG 2 — min_quantity off-by-one
# BEFORE:  elif cond_type == "min_quantity" and cart_quantity <= cond_val:
# AFTER:   elif cond_type == "min_quantity" and cart_quantity <  cond_val:
```

### 3b. Vertex model

```python
@dataclass(frozen=True)
class DealNode:
    vertex_id: str                      # e.g. "019dc1b5...#1" — copy number for duplicates
    deal_id: str                        # the underlying deal's canonical id
    category: str                       # the deal_type value: store_sale | member_discount | coupon | giftcard_discount | payment_discount | cashback
    copy_index: int                     # 1..N for duplicates; 1 for single-use deals
    discount_logic: dict[str, Any]
    constraints: dict[str, Any]         # the full DealConstraints dict
    raw: dict[str, Any]                 # the original deal dict (for output)
```

Two sentinel nodes: `START` (no transform) and `END` (no transform). They have fixed ids `"__start__"` and `"__end__"`.

**Building vertices from deals (with duplicates):**

```python
def build_vertices(deals: list[dict]) -> list[DealNode]:
    vertices = []
    for d in deals:
        limits = d.get("constraints", {}).get("limits", {}) or {}
        max_per_tx = limits.get("max_uses_per_transaction") or 1
        for i in range(1, max_per_tx + 1):
            vertices.append(DealNode(
                vertex_id=f"{d['id']}#{i}",
                deal_id=d["id"],
                category=d["deal_type"],          # top-level field per target schema
                copy_index=i,
                discount_logic=d["discount_logic"],
                constraints=d["constraints"],
                raw=d,
            ))
    return vertices
```

### 3c. Edge construction (bidirectional + duplicates + layer order)

```python
LAYER_ORDER = {
    "store_sale":         0,
    "member_discount":    1,
    "coupon":             2,
    "giftcard_discount":  3,
    "payment_discount":   4,
    "cashback":           5,
}

# Combinability key on a deal that governs whether it ACCEPTS a partner of the given deal_type.
# Aligned with the final schema in data/final_format_of_deal.json — all six types are now mapped.
ACCEPTS_KEY = {
    "store_sale":         "stackable_with_store_sale",
    "member_discount":    "stackable_with_member_discounts",
    "coupon":             "stackable_with_coupons",
    "giftcard_discount":  "stackable_with_giftcards",
    "payment_discount":   "stackable_with_payment_discounts",
    "cashback":           "stackable_with_cashback",
}

def accepts(deal: DealNode, other_type: str, unknown_as_yes: bool) -> bool:
    """True if `deal` allows being stacked with a deal of `other_type`."""
    key = ACCEPTS_KEY[other_type]
    val = deal.constraints.get("combinability", {}).get(key, "unknown")
    if val == "yes": return True
    if val == "no":  return False
    return unknown_as_yes

def mutually_compatible(a: DealNode, b: DealNode, unknown_as_yes: bool) -> bool:
    """Both sides must accept the other's category."""
    return accepts(a, b.category, unknown_as_yes) and accepts(b, a.category, unknown_as_yes)
```

**Edge allowance** (used only for raw graph construction; the chain-validity check below is the binding correctness rule):

```python
def directed_edge_allowed(src: DealNode, dst: DealNode, unknown_as_yes: bool) -> bool:
    if src.vertex_id == dst.vertex_id:
        return False

    # Special case: duplicate vertices of the same deal chain in copy-index order.
    if src.deal_id == dst.deal_id:
        return dst.copy_index == src.copy_index + 1

    # Layer-order: never go to an earlier layer.
    if LAYER_ORDER[dst.category] < LAYER_ORDER[src.category]:
        return False

    # Same-layer pair must be oriented deterministically (by deal_id).
    if LAYER_ORDER[src.category] == LAYER_ORDER[dst.category]:
        if src.deal_id >= dst.deal_id:
            return False

    # Bidirectional pairwise combinability.
    return mutually_compatible(src, dst, unknown_as_yes)
```

START/END:
- START → every vertex (we always allow START → any deal as the first applied).
- Every vertex → END always.

### 3d. Vertex math (the transform applied at each deal)

```python
def apply_deal(price_in: float, quantity: int, deal: DealNode) -> float | None:
    """Returns price_out, or None if this deal cannot be applied to price_in."""
    dl   = deal.discount_logic
    cond = dl.get("condition", {})
    rew  = dl.get("reward", {})
    cval = cond.get("value", 0)
    rval = rew.get("value", 0)

    # Validate condition against the *incoming* price
    if cond.get("type") == "min_spend"   and price_in < cval:           return None
    if cond.get("type") == "min_quantity" and quantity  < cval:         return None
    if cond.get("type") in ("exact_spend", "voucher_value") and price_in < cval:
        return None

    # Compute savings (same as fixed savings calculator, see 3a)
    rt = rew.get("type")
    if   rt == "fixed_discount_amount": savings = rval
    elif rt == "fixed_total_amount":
        savings = cval - rval if cond.get("type") in ("exact_spend", "voucher_value") else 0
    elif rt == "percentage_off":
        base = cval if cond.get("type") in ("exact_spend", "voucher_value") else price_in
        savings = base * rval
    else:
        savings = 0

    return max(0.0, price_in - savings)
```

Note: `max_discount_amount` (the legacy field inside `discount_logic.constraints`) is not present in `final_format_of_deal.json` and is dropped from the optimizer. If a future deal needs a cap, add it to `constraints.limits.max_discount_amount` and re-introduce the clamp here reading from the new path.

This is the existing `calculate_discount_savings` logic refactored to return `price_out` instead of `savings`. Reuse it from both the legacy ranking path and the new graph engine.

### 3e. Pathfinding (state-tracking DP — chain-aware compatibility)

Because the validity of adding a deal depends on every deal already in the chain, the DP state cannot be just `current_vertex`. It must include the set of vertices already applied:

```
state = (current_vertex_id, frozenset_of_applied_vertex_ids)
```

When extending state `(v, S)` with candidate `w`, we require:
1. `w ∉ S` (no repeats; duplicates are separate vertices).
2. `directed_edge_allowed(v, w)` — basic layer + same-deal-chain rules.
3. For every `u ∈ S`: `mutually_compatible(u, w)` — w is compatible with every prior deal AND every prior deal accepts w.
4. `apply_deal(price_at(v, S), cart_quantity, w)` is not `None` — w's discount_logic condition (min_spend / exact_spend / min_quantity) is satisfied by the running price.

```python
def find_best_path(
    cart_total: float,
    cart_quantity: int,
    deal_dicts: list[dict],
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
) -> list[DealNode]:

    # 1. Eligibility prune
    if user_context is not None:
        deal_dicts = [d for d in deal_dicts if _deal_is_eligible(d, user_context)]

    # 2. Expand into vertices (duplicates honored)
    vertices = build_vertices(deal_dicts)
    vertices.sort(key=lambda v: (LAYER_ORDER[v.category], v.deal_id, v.copy_index))
    by_id = {v.vertex_id: v for v in vertices}

    # 3. State-DP. Keys: (current_vertex_id, frozenset_of_applied_vertex_ids).
    #    Value: (best_price, predecessor_state_or_None).
    INIT = ("__start__", frozenset())
    dp: dict[tuple[str, frozenset], tuple[float, tuple | None]] = {
        INIT: (cart_total, None)
    }

    # BFS-style expansion in topological vertex order.
    for v in vertices:
        new_dp: dict = {}
        for (cur_id, applied), (price, _prev) in dp.items():
            # 4. Try extending the current state with v.
            if v.vertex_id in applied:
                continue

            # Edge from cur_id → v.vertex_id must exist
            if cur_id != "__start__":
                cur = by_id[cur_id]
                if not directed_edge_allowed(cur, v, unknown_as_yes):
                    continue

            # Pairwise validity against ALL deals already in the chain
            ok = True
            for u_id in applied:
                if not mutually_compatible(by_id[u_id], v, unknown_as_yes):
                    ok = False
                    break
            if not ok:
                continue

            # Apply v's transformation; condition may reject (e.g. min_spend not met).
            p_out = apply_deal(price, cart_quantity, v)
            if p_out is None:
                continue

            new_state = (v.vertex_id, applied | {v.vertex_id})
            existing = dp.get(new_state)
            if existing is None or p_out < existing[0]:
                new_dp[new_state] = (p_out, (cur_id, applied))

        # Merge new states; we never overwrite states reached via earlier vertices
        # because applied sets are distinct (v.vertex_id is in the new state but not the old).
        for k, val in new_dp.items():
            existing = dp.get(k)
            if existing is None or val[0] < existing[0]:
                dp[k] = val

    # 5. Best terminal — END absorbs from every state, so we just pick the min price.
    best_state, (best_price_val, _) = min(dp.items(), key=lambda kv: kv[1][0])

    # 6. Reconstruct path
    path = []
    cur = best_state
    while cur is not None and cur != INIT:
        cur_id, _applied = cur
        if cur_id != "__start__":
            path.append(by_id[cur_id])
        cur = dp[cur][1]
    path.reverse()
    return path
```

**Complexity**: The state space is `O(V × 2^V)` in the worst case. For typical per-store deal counts (V ≤ ~15) this is fine. If V grows large in some store, prune by:
- Capping path length (a real shopping flow rarely stacks > 5 discounts).
- Pre-pruning vertices that can never appear together (incompatible with too many others).

These optimizations are not blocking for the initial implementation.

### 3f. UserContext (eligibility prune)

```python
@dataclass
class UserContext:
    member_club_ids:    list[str]      = field(default_factory=list)
    preferred_channels: list[str]      = field(default_factory=list)  # "website" | "mobile_app" | "physical_store"
    uses_this_month:    dict[str, int] = field(default_factory=dict)  # {deal_id: uses_in_current_month}
```

`_deal_is_eligible(deal, ctx)` filters out deals the user can't use:
- `eligibility.membership_required == "yes"` and `deal.club_id` not in `ctx.member_club_ids` → reject.
- `ctx.preferred_channels` provided and `redemption_channels[ch] == "no"` for every preferred channel → reject. ("unknown" treated optimistically.)
- `limits.max_uses_per_month` set and `ctx.uses_this_month[deal.id] >= limits.max_uses_per_month` → reject.

These rules use the new schema field names (`limits.max_uses_per_month`, three-channel `redemption_channels`, simplified `eligibility`). The graph is then built from only eligible deals.

### 3g. Public entry point

```python
def get_optimal_deal_path(
    file_path: str,
    target_store_id: str,
    cart_total: float,
    cart_quantity: int,
    user_context: UserContext | None = None,
    unknown_as_yes: bool = True,
) -> dict:
    """
    Returns {
      "path": [<deal-dict>, ...],      # ordered list of applied deals
      "starting_price": float,
      "final_price": float,
      "total_savings": float,
      "per_step": [{"deal_id": ..., "price_in": ..., "price_out": ...}, ...]
    }
    """
```

The legacy `get_best_deals_for_store` (single-deal ranking) stays as-is for backwards compatibility, plus the bug fixes from 3a.

---

## Part 4 — Files Modified

| File | Change |
|------|--------|
| `lessley-deals/src/lessley_deals/domain/enums.py` | Add `DealType` enum (six values matching `data/final_format_of_deal.json`) |
| `lessley-deals/src/lessley_deals/enrichment/constaints_parser.py` | Replace `DealConstraints` Pydantic schema (new lean shape); add `DealParseResult` wrapper; write `deal["deal_type"]` and `deal["constraints"]` at the top level; rewrite system prompt for new field names |
| `lessley-deals/src/optimizer/optimizer_utils.py` | Fix 2 bugs; add `DealNode`, `UserContext`, `LAYER_ORDER`, `ACCEPTS_KEY`, `accepts/mutually_compatible/directed_edge_allowed`, `apply_deal`, `find_best_path`, `get_optimal_deal_path`; keep legacy `get_best_deals_for_store` (with bug fixes) for backwards compat |
| `lessley-deals/src/lessley_deals/domain/models.py` | Add `deal_type: str | None` and `constraints: dict[str, Any] | None` fields to `Deal` (matches the final schema) |

**No edits to the sample enrichment JSON files.** The `0.13` in `lee_cooper_deal.json` is correctly stored as a ratio — the bug was in the optimizer formula.

**Sample enrichment files (`*_deal.json` / `*_deal_constraints.json`) will look different after re-running the parser** — the old `transaction_limits`, `details_for_display`, and `original_hebrew_evidence` sections will be gone, replaced by the new lean schema. This is expected; do not try to preserve the old fields.

---

## Part 5 — Verification

1. **Bug fixes (independent of graph engine):**
   - Lee Cooper, cart 500₪, quantity 1: should return `_calculated_savings = 65₪` (was 0.65). And quantity-1 should qualify (was rejected by `<=`).

2. **Single-deal sanity (graph with one node = legacy result):**
   - Build the graph for Rami Levi alone, cart 500₪. Optimal path = `[Rami Levi]`, final price = `472.5₪`.

3. **Stack scenario:**
   - Hand-craft two coupons: A (10% off, `stackable_with_coupons: "yes"`) and B (5% off, `stackable_with_coupons: "yes"`). Cart 1000₪.
   - Path `START → A → B → END` should beat either deal alone: `1000 → 900 (A 10%) → 855 (B 5%)`, final 855₪.
   - Path `START → B → A → END`: `1000 → 950 (B 5%) → 855 (A 10%)`, same final (commutative %).
   - Verify the engine picks one with the correct savings.

4. **Conflicting deals (one-sided refusal blocks the edge):**
   - Deal X (`deal_type: "coupon"`, `stackable_with_payment_discounts: "yes"`) and Deal Y (`deal_type: "payment_discount"`, `stackable_with_coupons: "no"`). The graph must NOT contain edge `X → Y` even though X says "yes" — Y refuses coupons. Optimal path picks max(X, Y) alone.

5. **Layer-order enforcement:**
   - Deal P (`deal_type: "store_sale"`) and Deal C (`deal_type: "cashback"`). Edge `P → C` exists; edge `C → P` does not. Verify by inspecting the edge list.

6. **Path-wide chain validity (3-deal stack with mid-chain refusal):**
   - Deals A (`coupon`, accepts everything), B (`giftcard_discount`, accepts everything), C (`payment_discount`, `stackable_with_coupons: "no"`). The pairs A↔B and B↔C are both valid, so the simple pairwise edges `A → B` and `B → C` exist. But A↔C is invalid (C refuses coupons). The optimal full path must NOT be `START → A → B → C → END` — the DP should reject extending `{A, B}` with C because C is not compatible with A. Verify the engine picks `START → B → C → END` or `START → A → B → END`, whichever is cheaper.

7. **Duplicate vertices for repeat-use:**
   - Terminal X deal (`constraints.limits.max_uses_per_transaction: 2`) on a 100₪ cart. The graph should contain two vertices `terminal_x#1` and `terminal_x#2` with a single edge between them. Optimal path `START → #1 → #2 → END` applies the deal twice. Final price reflects both applications.
   - Compare to Lee Cooper (`limits.max_uses_per_transaction: 2`): expect 2 vertices with edge `#1 → #2`. With cart 1000₪ and 13% off, applying once gives 870₪. The DP should consider applying twice if the conditions still hold.

8. **Parser output format:**
   - Run `constaints_parser.py` on `terminal_x_deal.json`. After: `deal["deal_type"]` is set to one of the six enum values (e.g. `"giftcard_discount"`); `deal["constraints"]` matches the `final_format_of_deal.json` shape; `deal["discount_logic"]` no longer carries a `constraints` sub-key.

9. **End-to-end:**
   - Use the four sample deals (Gifta, Terminal X, Lee Cooper, Rami Levi). Each is in a different store, so the per-store query returns one. Sanity-check that the optimal path for Lee Cooper at 500₪ correctly applies the 13% discount and reports `final_price = 435₪`.
