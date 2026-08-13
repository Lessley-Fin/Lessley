# Open Questions

Running list. Questions are batched per chapter; anything marked **BLOCKING** stops that
chapter until answered. Resolved items stay in the file with their answer, struck through in
the index.

**Ground rule in force:** the code is the source of truth. Where a README and the code
disagree, nothing is silently chosen — it is recorded here.

---

## Raised during the outline stage

### ~~Q1~~ — Title-page details — **ANSWERED, partially**

Supplied by the user on 2026-08-13:

| Author | ID |
|---|---|
| Yoav Shalev | 207852401 |
| Ido Shmerling | 322876533 |
| Dor Habasov | 211678818 |
| Shahar Eldar | 324182476 |
| Roee Cohen | 322234238 |

- **Supervisor:** Ben Ephraim Ari → rendered on the title page as
  `Approved by the supervisor: Dr. Ari Ben Ephraim`. Note that example book A's title page
  spells the same name `Dr. Ari Ben-Efraim` (hyphenated, single *f*). Using the user's
  spelling; **confirm the college's preferred form before assembly.**
- **Faculty line / city:** `Submitted to the Computer Science Faculty of College of
  Management`, `Rishon LeZion` — standard across both example books.
- **Repository:** <https://github.com/Lessley-Fin/Lessley>. Cited in chapter 1.5
  (Methodology) and Appendix A, and matches the `Lessley-Fin` organisation already visible in
  the merge commits in `git log`.

Still outstanding on this item:

> ~~**Q1a**~~ — **ANSWERED:** submission date is **August 2026**.

> **Q1b** — **Acknowledgments** wording, or permission to write a conventional placeholder for
> you to edit. Example book B's is three sentences: thanks to the faculty, thanks to the
> supervisor by name.

---

### ~~Q2~~ — References for the Literature Review — **ANSWERED**

**Decision: I search the web for genuine sources** on each theme in the outline (microservice
edge authentication, open banking, fuzzy entity resolution, Hebrew NLP, LLM information
extraction, DAG/DP discount optimization, SCD Type 2) and build the numbered reference list
myself, with proper inline `[n]` citations.

Standing constraint that follows from this: every reference in chapter 6 must be a source I
actually retrieved and read. Anything I cannot verify does not go in the list, and the claim
it would have supported gets rewritten or dropped.

---

### Q3 — `lessley-deals/README.md` is stale in several places

`lessley-deals/CLAUDE.md` agrees with the code throughout; `lessley-deals/README.md` does
not. Four concrete contradictions:

> **Q3a** — `lessley-deals/README.md:73` says the store resolution is a **5-stage** matching
> pipeline (`ExactAlias`, `Compact`, `Normalized fuzzy`, `Domain`, `Token`), but
> `lessley-deals/src/lessley_deals/matching/stages/` implements **six** — `exact_alias.py`,
> `domain.py`, `compact.py`, `containment.py`, `normalized.py`, `token.py`. The README omits
> the containment stage and lists the remaining five in a different order from the pipeline.
> Which is correct?

> **Q3b** — `lessley-deals/README.md:142` labels `persistence/mongo_store.py` as
> "MongoDB backend (future)" and `:234` heads a section "Future: MongoDB migration", but
> `lessley-deals/src/lessley_deals/persistence/repositories/mongo/` is a fully populated
> package and `MONGO_URI`/`DEALS_STORAGE=mongo` are live settings the rest of the platform
> depends on. Is the MongoDB backend shipped?

> **Q3c** — `lessley-deals/README.md:104-149` documents the package as `src/deals/` with
> modules `scrapers/`, `resolution/`, `models/`, `persistence/json_store.py`, but the code is
> `src/lessley_deals/` with `scraping/`, `matching/`, `domain/`, `enrichment/`, `pipeline/`,
> `scheduling/`, `versioning/`. The README's project-structure block appears to predate a
> rename and a substantial restructure.

> **Q3d** — `lessley-deals/CLAUDE.md` lists the existing sources as `hot.py`, `mastercard.py`,
> `behatsdaa.py`, `isracard_topcash.py`, `hever.py` and `hever_teamim.py` — six. But
> `registry.py:203-214` registers **ten** adapter classes: `HotAdapter`, `MastercardAdapter`,
> `BehatsdaaAdapter`, `IsracardTopcashAdapter`, `SwishAdapter`, `HeverGiftCardAdapter`,
> `HeverTeamimAdapter`, `PaisPlusAdapter`, `PaisPlusFoodChainsAdapter` and
> `PaisPlusNetworksAdapter`, plus any number of config-driven LLM sites from
> `data/seed/llm_sources.json`. Chapter 1 states ten, from the registry. Are all ten current
> and scheduled, or are some registered but dormant?

My assumption unless you say otherwise: **the code wins, the README is stale**, and I
document what the code does without dwelling on the discrepancy in the book itself.

---

### Q4 — Hardware specification (**needed for 3.3 and 4.1**)

The spec asks chapter 3.3 to "specify the hardware specifications" and chapter 4.1 to
describe the machine experiments ran on. Both example books state this (example book B:
"a Windows 10 machine with 8GB of RAM").

> **[MISSING]** The development/measurement machine's specification — CPU, RAM, OS — and the
> deployment host's specification if it differs. Not derivable from the repository.

---

### Q5 — What chapter 4 should actually contain (**shapes chapter 4**)

The specification asks for experimental results, descriptive statistics ("means, standard
deviations, or confidence intervals") and a comparison against existing approaches. Lessley
is an engineering platform: there are no benchmark runs, no user study, no measured latencies
and no accuracy figures anywhere in the repository, and I will not invent any.

> **[MISSING]** Any recorded experiment, benchmark, accuracy measurement or user-study result
> for the system. Nothing of the kind exists in the repo.

Proposed honest substitution, per the outline:

1. Real test-suite results, produced by running `pytest` (deal-optimizer, Personalization,
   lessley-deals), `dotnet test` (Gateway) and `npm run test:run` (frontend), reported as
   measured output with the command and date.
2. Worked optimizer examples — the engine is deterministic, so real carts produce real,
   reportable stacks and savings.
3. Catalogue statistics computed from the actual data files or a live Mongo query.
4. A qualitative capability comparison table against manual comparison, per-club apps and
   cashback aggregators — like example book A's comparison table, not a performance benchmark.

**ANSWERED: substitution accepted, and I may run the suites and the optimizer locally to
generate the numbers.**

Standing constraints that follow:

- Every figure in chapter 4 is either measured output I produced by running a stated command,
  or a count computed from real data — each reported with the command and the date it was run.
- If a suite fails, chapter 4 reports the failure with its output. Failing tests are not
  quietly excluded.
- No means, standard deviations or confidence intervals are reported unless there is a real
  repeated measurement behind them. Single-run figures are labelled as single runs.
- The capability comparison in 4.4 is explicitly qualitative and will say so, so it is not
  mistaken for a performance benchmark.

---

### Q6 — College template for assembly

Do you have a college-supplied `.dotx`/`.docx` template? If so I will build on it and keep its
styles; otherwise I will generate the title page, automatic ToC, page numbers and numbered
heading styles myself, following the two example books' layout.

---

### ~~Q7~~ — `Lessley.CategoriesEnricher` is documented as a service but is not deployed — **ANSWERED**

**Decision: built, not yet deployed.** Chapter 3 describes it as an implemented service that
is deliberately not part of the running deployment, and says so plainly rather than implying
it is live. Its absence from `lessley-cd/docker-compose.yaml`,
`lessley-cd/docker-compose.prod.yaml` and `lessley-cd/Caddyfile` is accurate, not an
oversight, and the book will not present it as a component of the request path.

Consequences for the text: the architecture diagram in 3.1 shows five running services behind
Caddy, with the enricher drawn as a distinct not-yet-deployed component; the service table
carries a status column; and chapter 5 (Future Work) is the natural place to mention bringing
it into the deployment.

Still open, and pointing the same way:

> **Q7b** — `Lessley.CategoriesEnricher/README.md:12` and `:43` tell the reader to run it on
> port **8002**, which is the port `lessley-cd/RUNNING.md:37` assigns to Personalization. The
> two cannot both use 8002 in Mode 1.

> **Q7c** — `Lessley.CategoriesEnricher/README.md:36` documents `OpenAI_ApiKey` as a required
> variable and `config/settings.py:14` declares it `str | None = None` — optional. Meanwhile
> `lessley-deals` deliberately routes LLM calls to the faculty's self-hosted `gpt-oss-120b`
> by default rather than to OpenAI. Which provider does the enricher actually use?

Q7b and Q7c do not block chapter 3 now that the service's status is settled — both are
details of a component the book describes as not deployed. I will document the port collision
and the provider ambiguity as they stand in the code, and flag them again at review.

---

## Raised while writing chapter 1

### ~~Q8~~ — Market claims in §1.1 needing citations — **RESOLVED**

Two of the three claims now carry inline citations, inserted when chapter 6's reference list
was created:

1. Open Finance as regulated consent-based access → **[5]**, and §1.1 now names the Israeli
   instrument specifically (Financial Information Services Law, 2021; Israel Securities
   Authority) rather than describing the mechanism generically.
2. Hebrew orthographic variance as a matching obstacle → **[9]**.
3. The four-way categorization of benefit issuers needs no citation — it is the project's own
   framing of what the registered scrapers target, and §1.1 now says so explicitly rather
   than implying it is received taxonomy.

### Q9 — Deliberately excluded from chapter 1: unsourced market statistics

Example book A opens with market-share figures ("WooCommerce holding a 30% market share and
Magento 9%"). Chapter 1 contains no equivalent figures for the Israeli benefits market —
no market sizes, no membership counts, no average-savings claims — because none exist in the
repository and I will not invent them.

> If the college expects quantitative market framing in the Background section, say so and I
> will source real published figures during the chapter-2 research. Otherwise §1.1 stays
> qualitative.

### Q10 — Confirm the six-month project timeline

§1.5 states the project ran from 6 February 2026 to 12 August 2026 across 374 commits and 37
merged pull requests, all read from `git log` on the `main` branch. If work predates the
initial commit — a planning or design phase before the repository existed — tell me and I
will describe the timeline accordingly rather than equating it with repository history.

---

## Raised while writing chapter 2

### Q11 — Two references were verified bibliographically but not read in full

Chapter 2 cites thirteen sources. **Eleven were retrieved and read.** Two were not, and I want
this visible rather than buried:

- **[6] Fellegi & Sunter (1969)**, *JASA* 64(328):1183–1210 — the founding paper of
  probabilistic record linkage. Print-era, paywalled.
- **[7] Winkler (1990)**, ASA Survey Research Methods Section, pp. 354–359 — the origin of the
  Jaro–Winkler comparator. Proceedings paper; located via its ERIC record (ED325505).

For both, the bibliographic details and the substance attributed to them in §2.1.3 were
confirmed against multiple independent secondary sources, including the Binette & Steorts
survey [8] which I did read in full. Citing a foundational paper known through a survey is
ordinary scholarly practice, and §2.1.3 makes no claim about either that the secondary
literature does not support.

> **Q11** — Is that acceptable, or does the college expect every cited work to have been read
> in the original? If the latter, tell me and I will either obtain them through the college
> library or restrict §2.1.3 to citing [8] alone.

### Q12 — Two paywalled sources could not be retrieved, and are not cited

Both are directly relevant to §2.1.6 and would have strengthened it:

- A Springer/WISE 2017 chapter on efficient approximate entity matching using Jaro–Winkler
  distance (auth redirect).
- A 2025 *Expert Systems with Applications* article on conflicts and optimization of multiple
  promotion combinations for merchants (HTTP 403).

The second is the closest thing I found to prior work on the stacking-conflict problem, so its
absence is a genuine gap in the review rather than a formatting inconvenience. **If you have
college library access, these two are worth pulling** — I will fold them in and revise §2.1.6.
Neither is cited and no claim rests on them in the meantime.

### Q13 — Chapter 2's structure departs from the specification's literal shape

The spec gives chapter 2 a single sub-chapter, "2.1 Overview of Relevant Literature". A
single undifferentiated section covering seven distinct fields would be unreadable, so §2.1 is
divided into 2.1.1–2.1.8. Example book A does exactly this — themed sub-headings beneath one
numbered sub-chapter — and example book B goes further, numbering 2.1 through 2.8 at the
sub-chapter level.

I followed example book A, which stays closer to the spec's numbering. Flag it if your
supervisor wants the flatter literal form.

---

## Raised while writing chapter 3

### ~~Q14 / Q4~~ — Hardware specification — **RESOLVED by measurement**

The measurements in chapter 4 ran on this machine, so its specification was captured directly
rather than asked for: **Apple Mac16,10, Apple M4 (10 cores: 4 performance + 6 efficiency),
24 GB RAM, macOS 26.5.2 (build 25F84)**. Recorded in §4.1 and §3.3.7.

> Still worth confirming: is this the machine the project was **developed** on, and does the
> **deployment host** differ? §3.3.7 describes the development/measurement machine; if the
> college server has a different specification, give me one line and I will add it.

### ~~Q14 (original text)~~ — Hardware specification blocking two sections

§3.3.7 carries a `[MISSING]` block where the specification explicitly asks for hardware
details, and §4.1 will need the same information to describe the measurement environment.
This is the only `[MISSING]` marker in chapter 3.

Needed: **CPU, RAM and operating system** of the machine the system was developed and measured
on, plus the deployment host's specification if it differs. One line each is enough.

What the repository does establish, and what §3.3.7 says in the meantime: production targets a
single Docker Compose host on a college-administered DNS name, serving a pre-issued
certificate rather than using ACME, with only Caddy publishing ports; the worker defaults to
three sources scraped in parallel.

### Q15 — Confirm the two-phase optimizer split is fairly described as the core contribution

§3.3.3 and §2.1.8 both present the price-level / instrument-level distinction — chaining versus
bill-splitting — as the project's central technical contribution, on the grounds that the
promotion-optimization literature I reviewed models promotions as homogeneous.

That is my reading of the code and the literature, not a claim you made. **If you consider a
different part of the system the primary contribution** — the edge-authentication split, the
matching pipeline with its learning loop, or the guarded-expiry versioning — say so and I will
re-weight chapters 2, 3 and 5 accordingly. It is the kind of claim an examiner will probe, so
it should be the one you actually want to defend.

### Q16 — Eight mermaid diagrams need exporting before assembly

All eight are authored as ```` ```mermaid ```` blocks in chapter 3 and will need to be rendered
to images at the assembly stage. Full list in `00-outline.md`; figures 1–8 are all in this
chapter. Figures 6 and 7 (the DAG worked example and the two-phase flow) are the two that most
repay being drawn properly — they carry the argument that the prose in §1.2 sets up.

### Q17 — Chapter 3 has no code excerpt longer than about ten lines

Example book A embeds screenshots of code as figures. I have used short inline excerpts cited
to `path:line` instead, on the grounds that they are searchable, diffable and survive the
`.docx` conversion, whereas screenshots of code do not.

If your supervisor expects longer listings, the natural place is Appendix A rather than
chapter 3 — tell me and I will move fuller listings there.

---

## Raised while writing chapter 4

### Q20 — A probable product defect: `RawScrapedRecord.fingerprint` ignores `store_name`

**This is the most important item in this file.** Of the 13 test failures measured, 12 are
environmental or stale-test issues. This one is not.

> `tests/unit/domain/test_models.py::TestRawScrapedRecordFingerprint::test_differs_when_store_name_changes`
> builds two `RawScrapedRecord`s differing **only** in `store_name` (`"Store A"` vs
> `"Store B"`) and asserts their fingerprints differ. They are byte-identical:
> `7e05c99fb6919d71ff3287f21a03ea42f6f4164a844bf9c838d64dede8e5d943`.

A fingerprint invariant under a change of store name cannot distinguish records describing
different stores, and fingerprinting feeds record identity — so two distinct scraped records
could be treated as one.

I have **not** traced this to its cause. It is possible `store_name` is deliberately excluded
and the test encodes a stale expectation. But the test's name states the intended contract, so
the burden of proof runs the other way.

> **Q20** — Real defect, or stale test? §4.5 currently says it should be resolved before the
> system is described as production-ready. If it is a stale test I will soften that sentence;
> if it is a defect it belongs in chapter 5's limitations too.

Related, lower stakes: `test_brand_utils.py::test_unrecognised_substore_treated_as_specific`
expects `"UNKNOWN STORE"` but gets `"קבוצת גולף - תווים"` — the same kind of unresolved
test/implementation disagreement. Chapter 4 reports it as ambiguous rather than adjudicating.

### Q18 — Personalization's local `.env` blocks its own test suite

`config/settings.py:27` declares `SettingsConfigDict(env_file=".env", …)` with **no**
`extra="ignore"`, so pydantic-settings rejects unknown keys. The local
`Lessley.Personalization/.env` contains `GATEWAY_PROXY_TARGET` and
`PERSONALIZATION_PROXY_TARGET` (lines 4–5) — variables `lessley-cd/RUNNING.md:118-126` assigns
to the **frontend**. Collection failed with `extra_forbidden` across all 9 test files.

`.env` is git-ignored, so this is one checkout's local state, not committed code. I worked
around it (§4.1) and the suite then passed 64/64.

> **Q18** — Your call: remove the two frontend variables from that `.env`, or add
> `extra="ignore"` to the settings model so a shared `.env` cannot break the service. The
> second is more robust, the first more explicit.

### Q19 — Three frontend tests fail on an undefined `localStorage`

All three are in `src/routes/ProtectedRoute.test.tsx` at `localStorage.clear()`:
`TypeError: Cannot read properties of undefined (reading 'clear')`. `vite.config.ts:78-83`
sets `environment: 'jsdom'`, jsdom 29.1.1 is installed, and the other five test files pass.

My best reading is a Vitest 4.1.9 / jsdom global-exposure change rather than a defect in the
route guard — but I did not run it to ground, and chapter 4 says so rather than asserting it.

### Q21 — The Gateway suite could not be run, and it is chapter 4's biggest gap

No .NET SDK on this machine, so `Lessley.Gateway.Tests` did not execute. That suite carries
`AuthE2ETests`, `SecurityE2ETests`, `NotificationE2ETests` and `PipelineRealInfraE2ETests` —
precisely the tests that verify chapter 3's architectural and security claims.

§4.5 currently states those claims are "asserted by tests that exist rather than verified by
tests that ran". **Run `dotnet test` and paste me the summary line and I will fold the real
numbers in and delete that caveat.** It would materially strengthen the chapter.

### Q22 — Phase 1 operates on 4% of the real catalogue

Measured from `main/resources/deals.json` (10,137 deals): **95.5% are instrument-level**
(`payment_discount` 57.3%, `giftcard_discount` 35.3%, `cashback` 2.9%), 4.0% are `coupon`, and
there are **zero** `store_sale` and **zero** `member_discount` deals.

This cuts both ways, and chapter 4 reports both:

- It **strongly validates** the two-phase design — chaining all six types uniformly would
  compute the wrong answer for 95.5% of the catalogue. This is now the best available evidence
  for the contribution claim in **Q15**.
- It also means phase 1's layered DAG — the more elaborate half of the engine — currently runs
  on 4% of deals with two of its three layers empty.

§4.5 frames phase 1 as *anticipatory* rather than wasted. **Confirm that framing**, or tell me
that store-sale/member-discount sources are planned, in which case chapter 5 should say so.

---

## Noted, not blocking

- **`lessley-cd/docker-compose.yaml:215-247`** — the `deals-pipeline` and `deals-worker`
  services are commented out in the main stack; the scraper worker is deployed from
  `lessley-deals/docker-compose.worker.yml` instead. I will document it that way unless you
  tell me the main-stack entries are meant to be live.
- **Filename/type mismatch in the Gateway.** `Services/Classes/NotificationStore.cs` defines
  the class `NotificationRepository`, and `Services/Interfaces/INotificationStore.cs` defines
  `INotificationRepository`. The *type* names are used consistently everywhere
  (`Program.cs:65`, `NotificationService.cs`, `SendNotificationService.cs`); only the two
  filenames disagree. Chapter 3 refers to the types. Harmless, but renaming the files would
  remove a stumble for anyone reading the code alongside the book.
- **`lessley-deals/README.md:56`** shows a default `MONGO_URI` containing `guest:guest`
  credentials, and `lessley-cd/README.md:46` uses the same pair in its seeding commands. These
  are local development defaults, so I will reproduce the commands in Appendix A but will not
  present them as production configuration — and no real secret from `lessley-cd/.env` will
  appear anywhere in the book.
