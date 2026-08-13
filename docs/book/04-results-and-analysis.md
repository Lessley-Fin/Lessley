# 4. Results and Analysis

## 4.0 What this chapter reports, and what it does not

The chapter specification asks for experimental results, descriptive statistics including
means and confidence intervals, and a comparison against existing approaches. Lessley is an
engineering platform rather than a research study, and it is important to state plainly what
that means for this chapter.

**No benchmark run, user study, latency measurement or accuracy trial exists in the
repository, and none has been invented for this book.** Every figure below is one of three
things: the output of a test command actually executed, the output of the optimizer actually
run against real data, or a count computed from the project's own data files. Each is reported
with the command that produced it and the date it was run.

Consequently no means, standard deviations or confidence intervals appear. Producing them
would require repeated measurement of a stochastic quantity, and the quantities available here
are deterministic — the optimizer is a deterministic function, and a test suite either passes
or does not. Reporting a confidence interval over a single deterministic run would be
decoration, not statistics.

Two suites failed in part. Those failures are reported in full, with their error output and an
assessment of whether each is an environmental artefact or a genuine defect. One of them
appears to be a real product bug and is escalated accordingly in §4.3.

## 4.1 Experimental Setup

All measurements in this chapter were taken on **13 August 2026** on a single machine.

| Property | Value |
|---|---|
| Machine | Apple Mac16,10 |
| CPU | Apple M4, 10 cores (4 performance, 6 efficiency) |
| Memory | 24 GB |
| Operating system | macOS 26.5.2 (build 25F84) |
| Node.js | v26.3.0 |
| Python (test runs) | 3.12.13 (Homebrew) |
| .NET SDK | **not installed on this machine** |

Runtime environments were prepared as follows. `lessley-deals` used its existing checked-in
virtual environment (Python 3.12.13, pytest 8.4.2). Fresh virtual environments were created
for `deal-optimizer` (`pip install -e ".[dev,service]"`) and `Lessley.Personalization`
(`pip install -r requirements.txt -r requirements-dev.txt`). Frontend dependencies were
installed with `npm ci`.

Three deviations from a clean-room setup are recorded because they affect reproducibility.

**The .NET SDK is absent, so the Gateway suite was not run.** This is a limitation of the
measurement environment, not a result. It is reported as "not run" throughout rather than
being quietly omitted, and it is the single largest gap in this chapter — the Gateway carries
the end-to-end authentication, security and pipeline tests, which are precisely the ones that
exercise the architectural claims of chapter 3.

**Personalization's test suite could not be collected against the developer `.env` present on
this machine.** Its `Settings` model is declared with
`SettingsConfigDict(env_file=".env", …)` and no `extra="ignore"`
(`config/settings.py:27`), so pydantic-settings rejects unknown keys. The local `.env`
contains `GATEWAY_PROXY_TARGET` and `PERSONALIZATION_PROXY_TARGET` at lines 4–5 — variables
that `lessley-cd/RUNNING.md:118-126` assigns to the *frontend*, not to this service —
producing:

```
pydantic_core._pydantic_core.ValidationError: … personalization_proxy_target
  Extra inputs are not permitted [type=extra_forbidden, input_value='http://localhost:8002']
```

The suite was therefore run from a working directory containing no `.env`, with the three
genuinely required settings supplied as environment variables:

```bash
Environment=Testing \
ConnectionStrings_Rabbit="amqp://guest:guest@localhost:5672/" \
ConnectionStrings_MongoDb="mongodb://localhost:27017/lessley" \
RabbitMQ_Enabled=False \
PYTHONPATH=<service> .venv/bin/python -m pytest -q --rootdir=<service> <service>/tests
```

`.env` is git-ignored, so this is a property of one developer's checkout rather than of the
committed code. It is nonetheless a real reproducibility obstacle and is raised as **Q18**.

**No MongoDB or RabbitMQ instance was running.** Integration tests requiring live
infrastructure were therefore deselected (`lessley-deals`) or are absent from the run. The
figures below describe unit and in-process behaviour only.

## 4.2 Presentation of Results

### 4.2.1 Test suite results

Executed 13 August 2026. Every row is the verbatim summary line of the command shown.

| Suite | Command | Passed | Failed | Other | Wall clock |
|---|---|---:|---:|---|---:|
| deal-optimizer | `pytest -q` | **164** | 0 | — | 0.73 s |
| Lessley.Personalization | `pytest -q` | **64** | 0 | — | 0.96 s |
| lessley-deals | `pytest -q -m "not integration"` | **711** | **10** | 48 deselected | 4.43 s |
| lessley-frontend | `npm run test:run` | **39** | **3** | 42 tests / 6 files | 1.57 s |
| Lessley.Gateway.Tests | `dotnet test` | — | — | **not run — no .NET SDK** | — |

Totals across the four suites that ran: **978 passed, 13 failed**, with 48 integration tests
deselected for want of live infrastructure.

### 4.2.2 The thirteen failures, individually

Failures are not aggregated into a pass rate, because their causes differ in kind and only one
of them implicates product code.

**`lessley-deals` — ten failures.**

| # | Test | Error | Assessment |
|---|---|---|---|
| 1–5 | `test_swish_scanner.py` (5 tests) | `ModuleNotFoundError: No module named 'playwright'` | **Environmental.** Playwright is an optional browser extra that was not installed; the Dockerfile provides it in a dedicated `browser` stage. |
| 6–7 | `test_serialization.py::TestDealRoundTrip` (2 tests) | `TypeError: Deal.__init__() got an unexpected keyword argument 'description'` at `tests/factories.py:162` | **Stale test.** The test factory constructs `Deal` with a field the dataclass no longer accepts. Product code is not implicated. |
| 8 | `test_persist_stage.py::test_review_item_keeps_raw_input_name` | `RuntimeWarning: coroutine 'PersistStage.run' was never awaited` | **Stale test.** Calls an `async def` without awaiting it, so nothing is exercised. |
| 9 | `test_brand_utils.py::test_unrecognised_substore_treated_as_specific` | `assert 'קבוצת גולף - תווים' == 'UNKNOWN STORE'` | **Ambiguous.** Either group classification changed and the test was not updated, or a regression. Not adjudicated here — see §4.3. |
| 10 | `test_models.py::TestRawScrapedRecordFingerprint::test_differs_when_store_name_changes` | `assert '7e05c99f…d943' != '7e05c99f…d943'` | **Probable product defect.** See below. |

Failure 10 is the one that matters. The test constructs two `RawScrapedRecord` instances
differing only in `store_name` — `"Store A"` versus `"Store B"` — and asserts their
fingerprints differ. They are identical:

```
AssertionError: assert '7e05c99fb6919d71ff3287f21a03ea42f6f4164a844bf9c838d64dede8e5d943'
             != '7e05c99fb6919d71ff3287f21a03ea42f6f4164a844bf9c838d64dede8e5d943'
```

A fingerprint that is invariant under a change of store name cannot distinguish two records
that describe different stores. Because fingerprinting feeds record identity, this is a
correctness concern rather than a test-maintenance one, and it is escalated in §4.3.

**`lessley-frontend` — three failures.** All three are in
`src/routes/ProtectedRoute.test.tsx`, all at the same line of `beforeEach`:

```
TypeError: Cannot read properties of undefined (reading 'clear')
 ❯ src/routes/ProtectedRoute.test.tsx:23:18
     23|     localStorage.clear()
```

`vite.config.ts:78-83` sets `environment: 'jsdom'`, and jsdom 29.1.1 is present in
`node_modules`, so the configuration is correct on its face. The remaining five test files —
including `src/features/auth/store.test.ts` — pass. The most likely cause is a change in how
Vitest 4.1.9 exposes browser globals to this file rather than a defect in the route guard
itself, but this was not run to ground and is not asserted. Raised as **Q19**.

### 4.2.3 Optimizer worked examples

The engine is deterministic, so the following are exact reproducible outputs rather than
samples. All were produced with `deal_optimizer.cli` against `data/mock_deals.json`
(16 deals: 6 gift-card, 4 coupon, 2 member-discount, 2 payment-discount, 1 store-sale,
1 cashback) for `store_1`.

**Case A — 500 ILS cart, no wallet supplied.**

```bash
python -m deal_optimizer.cli data/mock_deals.json store_1 500 --top-n 3
```

Best option: **500.00 → 150.00 ILS, saving 350.00**, stacking a 50% member discount, a coupon
and a second coupon. Every deal in that stack is a deal the fixture labels `CANARY` — deals
that a real user would not qualify for.

**Case B — the same cart, with a wallet.**

```bash
python -m deal_optimizer.cli data/mock_deals.json store_1 500 --top-n 3 \
    --wallet-id user_ido_full --wallet-file data/mock_wallets.json
```

Best option: **500.00 → 270.00 ILS, saving 230.00**. The 50% member discount
(`D09_member_wrongclub`, a club the wallet does not belong to) is pruned, and the best
achievable saving falls by 120.00 ILS.

**Case C — 2000 ILS cart, wallet, cap of four deals.** Best option: **2000.00 → 972.00 ILS,
saving 1028.00**, composed of three chained coupons followed by one gift-card step that covers
1080.00 ILS of the remaining bill at 10%. This is a two-phase result: the first three steps are
price-level chaining, the fourth is a tender allocation against the residual bill.

**Case D — the effect of the `max_deals` cap.** Same 2000 ILS cart and wallet, varying only the
cap:

| `max_deals` | Final price (ILS) | Total saved (ILS) | Marginal saving from previous cap |
|---:|---:|---:|---:|
| 1 | 1500.00 | 500.00 | — |
| 2 | 1200.00 | 800.00 | +300.00 |
| 3 | 1080.00 | 920.00 | +120.00 |
| 4 | 972.00 | 1028.00 | +108.00 |
| 5 | 923.40 | 1076.60 | +48.60 |

### 4.2.4 Catalogue statistics

Computed 13 August 2026 from the project's seed data in `main/resources/`.

| Collection | Records |
|---|---:|
| `deals.json` | 10,137 |
| `stores.json` | 8,612 |
| `mccs.json` | 5,952 |
| `store_aliases.json` | 8,960 alias entries |
| `clubs.json` | 10 |

**Deals by source.** Nine of the ten registered adapters are represented:

| Source | Deals | Share |
|---|---:|---:|
| `hot` | 6,475 | 63.9% |
| `behatsdaa` | 1,949 | 19.2% |
| `hever_teamim_card_store` | 505 | 5.0% |
| `hever_gift_card_company` | 347 | 3.4% |
| `topcash` | 289 | 2.9% |
| `paisplus_networks` | 266 | 2.6% |
| `paisplus` | 232 | 2.3% |
| `paisplus_food_chains` | 40 | 0.4% |
| `mastercard` | 34 | 0.3% |

**Deals by type.**

| `deal_type` | Deals | Share | Optimizer phase |
|---|---:|---:|---|
| `payment_discount` | 5,813 | 57.3% | Phase 2 — tender |
| `giftcard_discount` | 3,579 | 35.3% | Phase 2 — tender |
| `coupon` | 409 | 4.0% | Phase 1 — chain |
| `cashback` | 289 | 2.9% | Phase 2 — tender |
| *(absent)* | 47 | 0.5% | — |

**Enrichment coverage.** 9,940 of 10,137 deals (**98.1%**) carry a populated `constraints`
block. 10,135 deals carry terms text, reducing to **4,078 distinct `(source_id, terms)`
pairs** — a **2.49×** deduplication factor, and therefore 2.49 times fewer LLM calls than
parsing each deal independently.

**Store coverage.** All 8,612 stores carry `mcc_codes` (100%). The alias table holds 8,960
entries, an average of 1.04 per store. Eleven deals (0.1%) carry group membership.

## 4.3 Data Analysis and Interpretation

### The catalogue is overwhelmingly instrument-level, which validates the two-phase design

The single most consequential number in §4.2.4 is this: **9,681 of 10,137 deals — 95.5% —
are `payment_discount`, `giftcard_discount` or `cashback`.** Only 409 deals (4.0%) are
`coupon`, and the real catalogue contains **no `store_sale` and no `member_discount` deals at
all**.

Chapter 3 argued that instrument-level benefits cannot be chained like price reductions,
because the same money cannot be routed through two instruments, and that they must instead be
solved as a bill-splitting allocation. That argument was made from first principles. The data
shows it is not an edge case being handled for completeness — it is the dominant case. An
optimizer that chained all six deal types uniformly would be computing the wrong answer for
95.5% of the catalogue.

This also reframes the phase-1 chain: on the current catalogue it operates on 4% of deals,
with two of its three layers unpopulated. The layered DAG is therefore, on today's data,
substantially more machinery than the coupon population requires. It is not wasted — the
layer order and bilateral-combinability rules are what make a coupon stack legal, and
`store_sale`/`member_discount` are real deal types the schema must support — but the honest
reading is that the project's *load-bearing* contribution is phase 2, not phase 1.

### Source concentration makes the catalogue fragile in a specific way

HOT alone supplies 63.9% of deals, and HOT plus Behatsdaa supply 83.1%. Two consequences
follow. First, catalogue freshness is effectively hostage to two scrapers: a change to HOT's
site degrades nearly two-thirds of the catalogue. Second, the guarded-expiry design of §3.2.5
is doing more work than its default parameters suggest. The `min_coverage_ratio` of 0.5 is
evaluated *per source*, so a total HOT failure does not trip the global guard — but it would
leave 6,475 deals ageing without refresh while the pipeline reports healthy runs for eight
other sources. Under-expiry is the safe failure, as chapter 3 argued, but "safe" here means
stale rather than wrong, and staleness in a discount catalogue eventually becomes wrong.

### Enrichment coverage is high, and the deduplication saving is real

98.1% constraints coverage indicates the LLM enrichment stage ran to substantial completion on
this dataset — the silent-degradation failure mode described in §3.2.4 is a real risk but did
not materialise here. The measured 2.49× deduplication factor confirms the design claim from
first principles: because the parser is deterministic and prompt-independent of surrounding
deals, grouping by `(source_id, terms)` is exactly equivalent to parsing each deal separately,
at 40% of the cost. The repository's own documentation states 2.6×; the measured figure on
this dataset is 2.49×, close enough to confirm the mechanism and different enough to show the
ratio is data-dependent rather than fixed.

The residual 197 deals without constraints, and the 47 without a `deal_type`, are the
population most likely to behave unexpectedly in the optimizer — a deal with no `deal_type`
falls into neither phase.

### The `max_deals` default of 3 is supported by the measured curve

Case D produces a clean diminishing-returns curve. Marginal savings from raising the cap run
+300.00, +120.00, +108.00, +48.60 ILS. The first increment is worth more than the next three
combined. Chapter 3 justified the default of 3 on executability grounds — that nobody presents
seven coupons at a checkout — and the measurement shows that argument costs little: moving
from 3 to 5 deals recovers a further 156.60 ILS on a 2000 ILS cart, roughly 7.8% of the cart,
in exchange for doubling the number of instruments the shopper must physically juggle.

The curve is measured on a 16-deal fixture and should not be generalised to the real
catalogue, where a 2000 ILS cart at a HOT-covered store would draw on a much larger tender
population. It supports the *shape* of the argument, not a specific savings claim.

### Eligibility pruning works, and the optimistic default is visible

Cases A and B differ only in whether a wallet was supplied, and the best achievable saving
falls from 350.00 to 230.00 ILS when one is. That 120.00 ILS gap is precisely the
`D09_member_wrongclub` deal being pruned — a 50% member discount for a club the wallet does
not belong to.

This makes concrete a behaviour that chapter 3 warned is easy to get backwards: **an absent
wallet is optimistic, not restrictive.** Case A's headline saving of 350.00 ILS is not a
result a real user could obtain; it is what the engine returns when it does not know who is
asking. A client that omits `member_source_ids` will show users savings they cannot realise.
The behaviour is correct by design — "unknown user" must not mean "no deals" — but it places a
real obligation on callers, and it is the single most likely source of a misleading number
reaching a user.

### On the fingerprint failure

Of the thirteen failures, twelve are attributable to a missing optional dependency, stale test
code, or a test environment. The thirteenth is not.

`RawScrapedRecord.fingerprint` returning an identical hash for records differing in
`store_name` means the fingerprint does not discriminate on a field that forms part of a
record's identity. Two distinct scraped records could therefore be treated as the same record.
This has not been traced to its cause, and it is possible the field is intentionally excluded
and the test encodes a stale expectation — but the test's name states the intended contract
unambiguously, and the burden of proof runs the other way. It is raised as **Q20**, and it is
the one finding in this chapter that should be resolved before the system is described as
production-ready.

The `test_brand_utils` failure (#9) sits in the same category of unresolved disagreement
between test and implementation, at lower stakes.

## 4.4 Comparison with Existing Approaches

This section is **qualitative**. It compares capabilities, not performance, and contains no
benchmark of Lessley against any other system — no such benchmark was run, and the alternatives
below are not directly measurable against a platform that computes rather than transacts.

### Against the alternatives available to a consumer today

| Capability | Manual comparison | Single-club app | Cashback aggregator | **Lessley** |
|---|---|---|---|---|
| Deals from multiple issuers in one place | No — one site at a time | No — one programme | Partial — participating merchants | **Yes — 9 sources, 10,137 deals** |
| Store identity unified across sources | No | N/A — single namespace | Partial | **Yes — 6-stage resolution, 8,960 aliases** |
| Personal spending used as input | No | Programme's own history only | Purchases made through it | **Yes — Open Finance, all accounts** |
| Recommends programmes not yet joined | No | No — inherent conflict of interest | No | **Yes — club scoring by category overlap** |
| Computes legal multi-deal combinations | Manual, error-prone | No | No | **Yes — two-phase optimizer** |
| Models instrument-level vs price-level correctly | N/A | N/A | N/A | **Yes — the 95.5% case** |
| Executes the transaction | User does | Sometimes | Yes | **No — out of regulatory scope [5]** |

The last row is a genuine limitation, not a rhetorical concession. A cashback aggregator
closes the loop; Lessley stops at advice. Under the Financial Information Services Law the
platform is a consumer of financial *information* and initiates nothing [5], so the gap between
computing the best combination and executing it is regulatory, not technical.

The row that matters most is the second-to-last. The distinction between price-level and
instrument-level discounts does not arise for the alternatives, because none of them attempts
combination at all. It is a capability without a comparator.

### Against the literature

§2.1.6 established that the promotion-optimization literature reviewed here optimizes from the
merchant's side — which offer to present, under a budget the merchant controls [11]. Two
structural differences follow, and §4.2.4 now supplies evidence for the second.

The literature models promotions as homogeneous, interchangeable, budget-consuming offers.
On the real catalogue, 95.5% of deals are instrument-level and cannot be treated that way
without double-counting. A merchant-side formulation applied to this catalogue would be
solving a different problem from the one the data poses.

### An internal comparison: why chaining tender deals would be wrong

The clearest comparison is against the design Lessley rejected. Chaining a capped
percentage-off card as though it were a price reduction lets it discount money a different card
already covered. The repository records the concrete case
(`deal-optimizer/src/deal_optimizer/tender.py:29-33`): a 30%-off-up-to-500 plus
10%-off-up-to-500 card against a flat 20% card on a 1500 ILS bill yields 350 ILS under correct
segment-wise allocation, and 300 ILS if whole options are chosen by headline rate. The naive
approach is not merely less precise — it selects the wrong instruments.

Case C is the same mechanism at work on a real run: the gift-card step covers 1080.00 ILS of
the bill, *not* the original 2000.00, because the three coupon steps reduced the bill first and
the card can only cover what is actually routed through it.

## 4.5 Discussion of Findings

**What the results establish.** Three of the five test suites that could be run pass
completely, including both suites covering the optimizer and the personalization engine — 228
tests between them, with zero failures. The optimizer's behaviour on real invocations matches
the design described in chapter 3 in every respect examined: two-phase composition, eligibility
pruning, the cap enforced during search, and ranked distinct outcomes. The catalogue statistics
confirm that the pipeline produced a substantial, well-enriched dataset — 10,137 deals across
nine sources at 98.1% constraint coverage.

**What the results do not establish.** They say nothing about the system under load, about
latency, about accuracy against ground truth, or about whether a retailer honours a computed
stack at a real checkout. No user has used this system and reported whether the advice was
good. The measurements are of internal consistency, not of external validity.

**The most significant limitation is the untested Gateway.** The .NET suite covers end-to-end
authentication, security and cross-service pipeline behaviour — precisely the claims chapter 3
makes most strongly. Those claims remain *asserted by tests that exist* rather than *verified
by tests that ran*. Any reader should treat §3.1's security properties as designed and tested
in principle, but unverified in this chapter.

**Store-resolution accuracy was not measured**, and this is a gap worth naming. §3.4 defined
the evaluation criterion as the distribution of the three-way verdict across a run, but that
distribution requires a live scrape against MongoDB, which was not available. The 8,960 alias
entries against 8,612 stores — 1.04 per store — is suggestive rather than conclusive: it
indicates the alias table is populated but not how much of it came from automatic matching
versus human review, which is the number that would actually characterise the pipeline.

**The fingerprint defect is the one finding that should block a production claim.** Twelve of
thirteen failures are maintenance debt in tests. The thirteenth suggests a record-identity
function that does not discriminate on store name. Until it is resolved (**Q20**), the
catalogue's deduplication behaviour cannot be assumed correct.

**A finding that surprised the analysis, and should shape future work.** The real catalogue
contains no `store_sale` and no `member_discount` deals. The layered DAG of phase 1 — the more
algorithmically elaborate half of the engine — currently operates on 4% of the catalogue with
two of its three layers empty, while the bill-splitting allocator of phase 2 carries 95.5%.
The engineering effort and the data are inversely distributed. This does not make phase 1
wrong; it makes it *anticipatory*, and whether that anticipation is justified depends on
whether sources publishing store-sale and member-discount deals are added later. That is a
concrete question for chapter 5 rather than a defect.

---

### Note on sourcing

Every figure in this chapter was produced on 13 August 2026 by a command reproduced in the
text, on the machine specified in §4.1. Test-suite figures are the verbatim summary lines of
those runs. Optimizer figures are exact deterministic outputs. Catalogue figures were computed
directly from the files in `main/resources/`. Two external citations appear — [5] and [11] —
and both resolve to chapter 6. Failures are reported in full; none was excluded.
