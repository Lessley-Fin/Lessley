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

### Q8 — Three market claims in §1.1 need citations, not repository evidence

Chapter 1 carries no `[n]` markers yet because chapter 2's research has not run. Three
statements in §1.1 are general market observations rather than facts I can cite to a file,
and each will need a real reference once the list exists:

1. Open Finance characterized as a regulated, consent-based third-party access interface.
2. Hebrew orthographic variance (niqqud, final forms, presentation forms, legal suffixes) as
   a recognised entity-resolution obstacle.
3. The four-way categorization of Israeli benefit issuers (organizational clubs, card
   programmes, retailer programmes, voucher networks).

Everything else in the chapter is cited to `path:line`. This is tracked so the markers get
inserted when chapter 2 is written — not left to be noticed at proofreading.

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

## Noted, not blocking

- **`lessley-cd/docker-compose.yaml:215-247`** — the `deals-pipeline` and `deals-worker`
  services are commented out in the main stack; the scraper worker is deployed from
  `lessley-deals/docker-compose.worker.yml` instead. I will document it that way unless you
  tell me the main-stack entries are meant to be live.
- **`lessley-deals/README.md:56`** shows a default `MONGO_URI` containing `guest:guest`
  credentials, and `lessley-cd/README.md:46` uses the same pair in its seeding commands. These
  are local development defaults, so I will reproduce the commands in Appendix A but will not
  present them as production configuration — and no real secret from `lessley-cd/.env` will
  appear anywhere in the book.
