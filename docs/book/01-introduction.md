# 1. Introduction

Lessley is a loyalty-optimization platform that reads a consumer's real banking history
through a regulated Open Finance interface and converts it into two concrete, actionable
answers: *which loyalty programmes is this person losing money by not belonging to*, and
*given what they are about to buy, what is the cheapest legal way to pay for it*.

The two questions are deliberately paired. The first is retrospective and personal — it can
only be answered by joining a user's own spending history against a catalogue of the benefits
available in their market. The second is prospective and combinatorial — it requires knowing
not merely which discounts exist, but which of them may legally be applied together, in what
order, and against which portion of the bill. Neither question can be answered by a catalogue
alone, and neither can be answered by transaction data alone. Lessley exists at the
intersection: a scraping and normalization pipeline that builds the catalogue, an analytical
service that reads the user's spending, and an optimization engine that searches the space of
legal discount combinations.

The system is implemented as a set of independently deployable services behind a single
authenticating edge, written in C#, Python and TypeScript, and deployed with Docker Compose.
The complete source is available at <https://github.com/Lessley-Fin/Lessley>.

## 1.1 Background

Consumer discounts in the Israeli retail market are not published in one place, in one
format, or under one set of rules. They are fragmented across at least four distinct kinds of
issuer, each of which reaches the consumer through a different mechanism:

- **Employee and organizational clubs**, such as Behatsdaa and Hever, which negotiate
  benefits on behalf of a membership and publish them on member-facing portals.
- **Credit-card programmes**, such as Mastercard's benefit portal and Isracard's TopCash,
  where the discount is attached to the payment instrument rather than to the purchase.
- **Retailer and telecom loyalty programmes**, such as HOT's subscriber benefits, which are
  tied to an ongoing commercial relationship with a single company.
- **Loadable gift-card and voucher networks**, such as PaisPlus and Swish, where the consumer
  buys stored value at a discount and then spends it at face value.

The Lessley scraping pipeline registers a source adapter for each of these
(`lessley-deals/src/lessley_deals/scraping/registry.py:203-214` registers ten code-based
adapters — HOT, Mastercard, Behatsdaa, Isracard TopCash, Swish, two Hever datasets, and three
PaisPlus datasets — alongside any number of configuration-driven LLM-scraped sites). That
list is not an arbitrary sample; it is what a consumer in this market plausibly has access to
at one time, and it is precisely the fragmentation that makes the problem hard.

Three properties of this data make it resistant to naive aggregation.

**Store identity is not stable across sources.** The same physical chain appears under
different names in different catalogues. Israeli retail names carry Hebrew diacritics
(niqqud), final-form letters that vary with position, Unicode presentation forms, legal
suffixes such as *Ltd.*, and free-text branch descriptions appended to the chain name. Two
sources describing the same store frequently share no exact substring. Joining a user's
transaction at a store to a deal published for that store therefore requires entity
resolution, not string equality.

**Eligibility rules are published as free-text prose, not as data.** Each source states its
restrictions in its own Hebrew phrasing, and the numbers embedded in that prose are
systematically ambiguous: a shekel ceiling per transaction, a wallet-loading tier, a per-member
voucher cap, a calendar day of the month and a cashback waiting period all appear as "a
number followed by a unit", and only one of them is a usage limit. Turning these into
structured, machine-checkable constraints is an information-extraction problem.

**Discounts interact.** A deal is rarely usable in isolation. It may or may not stack with a
store sale, with a member discount, with a coupon, with a gift card, with a payment discount
or with cashback — and the deal on the other side of that pairing has its own opinion, which
may disagree.

Against this fragmented supply side, the demand side has recently become legible. Open
Finance — the regulated interface through which a licensed third party may, with the
consumer's consent, read their account and transaction data — makes an individual's actual
spending machine-readable for the first time. Lessley consumes it through a dedicated client
(`lessley-backend/Lessley.Personalization/services/clients/open_finance_client.py:11`), which
manages per-user access tokens, refreshes them ahead of expiry to avoid mid-request
rejection, and collapses concurrent refreshes behind a single lock. It is this data that
turns a generic catalogue into a personal recommendation: without it, the platform could only
say what discounts exist, not which ones would have mattered.

## 1.2 Problem Statement

The project addresses two distinct problems that share a data foundation.

**Problem 1 — a consumer cannot evaluate a loyalty programme they have not joined.**
Deciding whether a club membership is worth its cost requires knowing how much the member
would have saved on purchases they were already going to make. That is a counterfactual over
the consumer's own history, and it requires three things the consumer does not have: a
normalized catalogue of the club's benefits, a canonical mapping from the stores they shop at
to the stores the club covers, and a spending profile expressed in the same category
vocabulary as the catalogue. Each of the three is a non-trivial data problem, and no consumer
assembles them by hand.

**Problem 2 — stacking discounts correctly is a constrained combinatorial problem, and the
constraints are not uniform.** Even given a complete, structured catalogue, choosing the best
combination for a specific purchase is not a matter of picking the largest percentage. Three
difficulties compound:

*Legality is bilateral and order-dependent.* An edge from deal A to deal B exists only when A
accepts B's category **and** B accepts A's, and only when B's layer is not earlier than A's in
the fixed application order `store_sale → member_discount → coupon`
(`deal-optimizer/src/deal_optimizer/graph.py:21-38`, `:138-152`). Pairwise legality is also
not sufficient: a three-deal stack can contain a pair that is individually illegal, so
validity must be re-checked against every prior member as a chain grows, not just against its
immediate predecessor.

*Not all discounts are price reductions.* Store sales, member discounts and coupons reduce
the bill itself, so applying them in sequence against a shrinking total is exact. Gift-card
loads, card-brand payment discounts and cashback do not behave this way. Each discounts only
the specific slice of money routed through that instrument, and the same money cannot be
routed through two instruments at once — a consumer cannot pay the same 400 ILS with two
different cards. Chaining an instrument-level deal as though it were a price reduction
double-counts, letting a capped card appear to discount money that another card already
covered (`deal-optimizer/src/deal_optimizer/tender.py:1-42`). These deals are therefore not a
path-finding problem at all; they are a bill-splitting problem, and they must be solved as
one.

*More is not better.* Left unbounded, an optimizer will stack seven coupons to save a few
additional shekels — a combination no one executes at a real checkout. Usefulness imposes a
bound on stack length that pure cost minimization does not.

Together these mean the answer cannot be obtained by sorting deals by size, nor by a greedy
pass, nor by a single shortest-path search over a uniform graph.

## 1.3 Objectives

The project set out to build a working platform meeting the following objectives. Each is
stated so that its achievement can be checked against the delivered system.

1. **Aggregate a multi-source deal catalogue automatically.** Scrape every configured Israeli
   benefit source on an independent schedule, preserving raw records verbatim so that any
   downstream result can be traced back to what was actually published.

2. **Resolve store identity across sources.** Normalize Hebrew and English store names and
   map name variants to canonical store identities through a staged matching pipeline, with
   thresholds conservative enough that uncertain matches are escalated to human review rather
   than silently accepted.

3. **Extract structured constraints from free-text terms.** Convert each deal's
   terms-and-conditions prose into a machine-checkable constraints block covering
   combinability, limits, store coverage and eligibility.

4. **Track catalogue change over time without data loss.** Never overwrite a deal; record
   every change as an immutable version with a current head, and guard expiry so that a
   partial or failed scrape cannot mass-expire a live catalogue.

5. **Produce personal spending insights from Open Finance data.** Derive spending categories,
   top accounts and top stores from the user's real transactions.

6. **Recommend loyalty clubs from that spending profile.** Score each club by how well the
   stores it covers overlap the categories the user actually buys, and deliver the result
   asynchronously so a slow computation never blocks a request.

7. **Compute the cheapest legal deal combination for a cart.** Model price-level deals as a
   layered directed acyclic graph solved by a state-tracking dynamic program, solve
   instrument-level deals as a separate allocation problem, bound the stack length during the
   search rather than by filtering afterwards, and return a ranked list of distinct outcomes
   rather than a single winner.

8. **Establish identity once, at the edge.** Authenticate every request at a single public
   entry point and inject a verified identity inward, so that no service accepts a
   caller-supplied identity and no service trusts another service over HTTP.

9. **Deliver a single-origin client.** Serve the SPA and the API from one origin so that no
   CORS relaxation is required and strict same-site cookies work by default.

## 1.4 Scope and Limitations

### Scope

The delivered system comprises:

- **The edge.** A Caddy instance that terminates TLS, hosts the built React SPA, strips any
  client-supplied trust or identity headers, authenticates each request against the Gateway,
  and routes each API prefix to the service that owns it
  (`lessley-cd/Caddyfile:24-114`).
- **The Gateway** (C# / .NET 8) — the authentication authority, and the owner of users,
  clubs, deal search, MCC reference data and notifications, including the SignalR hub that
  pushes them.
- **Personalization** (Python / FastAPI) — Open Finance access, spending insights, and the
  club-matching and missed-savings recommendation engines.
- **deal-optimizer** (Python / FastAPI) — the deal-stacking engine, usable as a library, a
  CLI and an HTTP service.
- **lessley-deals** (Python) — the scraping, normalization, matching, enrichment and
  versioning pipeline, and the scheduled worker that runs it.
- **The frontend** (React / TypeScript / Vite) — a mobile-first SPA with Hebrew and English
  locales (`lessley-frontend/src/lib/i18n/locales/`).
- **The deployment** — Docker Compose definitions for a development stack and a production
  stack sharing one Caddyfile, with MongoDB, RabbitMQ, and Loki/Grafana for structured
  logging.

### Limitations

The following are genuine boundaries of the delivered system, not omissions from this
document.

**`Lessley.CategoriesEnricher` is implemented but not deployed.** The service exists in full,
with its own Dockerfile, and provides LLM-backed transaction, store and deal classification.
It appears in neither `lessley-cd/docker-compose.yaml` nor
`lessley-cd/docker-compose.prod.yaml`, and has no route in the Caddyfile. It is therefore not
part of the running request path in any mode, and this book does not describe it as one.
Bringing it into the deployment is discussed in chapter 5.

**Email is an immutable cross-service key.** Identity propagates between services as an email
address in the `X-Auth-Email` header, SignalR addresses connections by the email claim
(`lessley-backend/Lessley.Gateway.Api/Hubs/EmailUserIdProvider.cs:8-9`), and Open Finance
keys the user's bank data by the same value. Changing a user's email would orphan their
financial data, so email changes are unsupported by design
(`lessley-cd/RUNNING.md:186-187`).

**The user wallet is a mock structure.** The optimizer prunes deals a user cannot use by
matching the deal's required `source_id` against the programmes and cards the user holds. In
the delivered system that holding is represented by a mock `UserWallet` loaded from a JSON
file (`deal-optimizer/src/deal_optimizer/wallet.py:1-19`), not by a verified link to real
memberships or real cards. The eligibility logic is real; the evidence of eligibility is not.

**Constraint enrichment depends on a network-restricted model endpoint.** Terms parsing
defaults to the faculty's self-hosted model, reached over an internal address with a
self-signed certificate (`lessley-deals/src/lessley_deals/enrichment/llm_client.py:25-37`).
A deployment that cannot reach it scrapes successfully and silently leaves constraints empty,
because a failed parse is logged and skipped rather than treated as fatal. This is a
deliberate resilience choice with a real cost: catalogue completeness is
environment-dependent.

**Deployment targets a single Compose host.** There is no orchestration across nodes and no
horizontal scaling of the application services; the scraper worker's lease-locking is the one
component designed for multiple replicas.

**No mobile application.** The client is a mobile-first web SPA. A native application was out
of scope.

**Results were not validated against real checkout receipts.** The optimizer's output is
verified against its own test scenarios and is deterministic, but no purchase was executed to
confirm that a retailer honours a computed stack in practice.

## 1.5 Methodology

Development followed an incremental, branch-per-feature process against a fixed architectural
contract, over roughly six months: the repository's history runs from its initial commit on
6 February 2026 to 12 August 2026, comprising 374 commits and 37 merged pull requests
(numbered up to #46).

**A written architectural contract preceded the code.** `instruction.md` fixes a small number
of rules that every service obeys and that no feature is permitted to relax: the client talks
only to the edge; identity is established once and taken only from the injected header, never
from a query parameter or body field; every service rejects a request that cannot prove it
came through the edge; and the Gateway never calls Personalization over HTTP. These are not
style preferences. The identity rule in particular exists to eliminate a specific class of
insecure-direct-object-reference bug — accepting an `email` parameter would let any
authenticated caller read any other user's bank data — and the constraint is enforced at the
point where identity is read
(`lessley-backend/Lessley.Personalization/dependencies/auth.py:49`).
Fixing the contract first meant that adding a client-facing service later required one edge
route and two header checks rather than proxy code in the Gateway.

**A monorepo with feature branches and pull-request review.** Unlike the multi-repository
split used in comparable projects, all six components live in one repository, which keeps
cross-service contract changes — a RabbitMQ message type, a MongoDB document shape — visible
in a single diff. Work proceeded on prefixed branches (`feature/`, `improve/`, `hotfix/`,
`update/`) merged through pull requests.

**Environment parity between development and production.** The same Caddyfile and the same
container ports drive both the development and the production stack, so the topology a
developer tests against is the topology that is deployed; the two differ only in environment
values and in whether developer tooling is exposed. A third, lighter mode runs the services
directly on the developer's machine with a Vite proxy standing in for the edge, so that a
debugger can be attached without giving up the single-origin model
(`lessley-cd/RUNNING.md`).

**Per-language test suites at the boundaries that matter.** The Gateway is covered by xUnit
tests including end-to-end authentication, security and pipeline tests against real
infrastructure; Personalization and deal-optimizer by pytest; the frontend by Vitest. The
security properties asserted by the architectural contract are themselves tested, rather than
merely documented.

**Conventions encoded as executable guidance.** Recurring decisions — which layer new logic
belongs in, how to write a fault-tolerant RabbitMQ consumer, how to index a MongoDB query,
how to add a frontend feature — are captured as skill definitions under `.claude/skills/`, so
that convention is applied consistently rather than remembered inconsistently.

## 1.6 Organization of the Project Book

This book is organized into the following chapters:

- **Chapter 1: Introduction** — the market context that motivates the project, the two
  problems it addresses, its objectives, the boundaries and limitations of the delivered
  system, and the development methodology.

- **Chapter 2: Literature Review** — the existing research and practice the project builds
  on: microservice edge authentication, open banking as a data source, entity resolution and
  fuzzy matching, Hebrew text normalization, LLM-based information extraction, discount
  stacking as constrained combinatorial optimization, and slowly-changing-dimension history.

- **Chapter 3: System Design and Implementation** — the architecture and the code. The
  services and the request paths between them; the scraping pipeline that collects and
  preprocesses the catalogue; per-service implementation detail with code excerpts; the
  software and hardware specification; and the criteria by which each subsystem is judged
  correct.

- **Chapter 4: Results and Analysis** — measured results. Test-suite output, worked optimizer
  examples, catalogue statistics, their interpretation, a qualitative comparison against the
  alternatives available to a consumer today, and a discussion of what the results do and do
  not establish.

- **Chapter 5: Conclusion and Future Work** — what the project achieved, the challenges met
  along the way, the limitations that remain, and the directions worth pursuing next.

- **Chapter 6: References** — all sources cited in the text.

- **Chapter 7: Appendix A** — supporting reference material: the complete REST API surface,
  the environment-variable reference, the setup guide for each run mode, the deal constraints
  schema, and the optimizer's export payload format.

---

### Citations pending

Chapter 2's literature research has not yet been carried out, so no reference markers appear
above. Three statements in §1.1 are general market observations rather than repository facts
and will carry an inline `[n]` citation once the reference list exists: the characterization
of Open Finance as a regulated consented-access interface; the description of Hebrew
orthographic variance as an entity-resolution obstacle; and the framing of the four issuer
categories. Every other factual claim in this chapter is cited to a file and line in the
repository and can be verified there directly.
