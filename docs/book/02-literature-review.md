# 2. Literature Review

## 2.1 Overview of Relevant Literature

Lessley sits at the meeting point of several established fields rather than inside any one of
them. Its architecture draws on the microservices literature and, specifically, on the
question of where authentication belongs in a distributed system. Its data source exists
because of a recent regulatory change in how consumer financial information may be accessed.
Its catalogue depends on entity resolution, a discipline older than the field of data
engineering itself, and on the particular difficulties of Hebrew orthography. Its enrichment
stage applies a technique — schema-constrained extraction with large language models — that
became practical only in the last few years. Its optimizer is a constrained combinatorial
problem of a kind studied under several names in the operations-research and e-commerce
literature. And its treatment of catalogue change over time follows a data-warehousing
pattern formalized three decades ago.

This chapter surveys each of these in turn, establishes what is already known, and identifies
where the existing work stops short of what this project required.

### 2.1.1 Microservice Architecture and Authentication at the Edge

The API Gateway pattern, described by Richardson, addresses the problem of how clients should
interact with a fleet of fine-grained services whose data a single client operation may
span [2]. Its solution is a component that serves as "the single entry point for all clients",
routing requests to the services that own them, translating between a public protocol and
whatever the services speak internally, and — relevant here — verifying client authorization
before anything reaches a service [2]. The stated drawbacks are the operational cost of
developing and running the gateway itself, and an additional network hop.

The companion Access Token pattern makes the identity mechanism explicit: the gateway
authenticates the request and then "passes an access token (e.g. JSON Web Token) that securely
identifies the requestor in each request to the services", so that identity is established
once and propagated inward rather than re-derived at every hop [3]. Barabanov and Makrushin's
survey of authentication and authorization patterns in microservice-based systems catalogues
this and competing arrangements, examining the advantages and disadvantages of each and the
environmental characteristics that make one appropriate over another [4].

The security motivation for centralizing this decision is documented most directly in the
OWASP API Security Top 10. Broken Object Level Authorization is ranked first in the 2023
edition, and it describes precisely the failure mode that arises when a service derives
identity from data the caller supplied: "Attackers can exploit API endpoints that are
vulnerable to broken object-level authorization by manipulating the ID of an object that is
sent within the request" [1]. The recommended mitigations include checking the user's access
permissions for every operation that uses a client-supplied identifier, and building
authorization tests before deploying changes [1]. The same vulnerability class is known in
older literature as Insecure Direct Object Reference.

**Where this project departs from the literature.** Richardson's gateway both authenticates
*and* proxies: services sit behind it, and the gateway is on the path of every call [2].
Lessley separates those two responsibilities. The edge authenticates every request, but it
does not proxy the services it protects — it routes each API prefix directly to the service
that owns it, having first verified the caller against a separate authentication authority
and injected the resulting identity. The consequence is that a service can be added at the
edge without any proxy code being written in the authentication authority, which is the usual
cost of the gateway pattern. The surveyed literature treats "gateway" and "authenticator" as
one component; the distinction between them, and what it buys, is developed in chapter 3.

### 2.1.2 Open Finance and Regulated Access to Consumer Financial Data

The European Union's second Payment Services Directive established the regulatory template
for third-party access to bank-held customer data, requiring banks to expose account
information through dedicated interfaces to licensed providers acting with the customer's
consent. Israel implemented a comparable but distinct regime through the Financial
Information Services Law, enacted in 2021 as part of the Economic Arrangements Law [5]. Three
features of the Israeli law bear directly on this project.

First, the supervising regulator is the Israel Securities Authority rather than the central
bank, and every provider must hold a valid licence from it, subject to background checks,
demonstrated financial stability, secure technology infrastructure and vetted
stakeholders [5]. Second, the data in scope covers bank account data, credit card information
and savings account details, retrieved "through a dedicated API interface from the banks, in a
unified, transparent, and secure manner" [5]. Third, and most important for how Lessley is
positioned: the law "deals solely with access to data" for analysis and management purposes,
and is distinguished from open banking proper, which permits third parties to initiate
transactions [5]. Access requires the customer's explicit permission and is limited to stated
purposes such as cash-flow analysis or budget management [5]. The technological standard
adapts the NextGenPSD2 framework to the Israeli financial system.

**Relevance.** Lessley is squarely a consumer of financial information services in this
sense: it reads, analyses and advises, and it initiates nothing. The regulatory boundary is
therefore also the boundary of the system's ambition, and it explains a design choice that
would otherwise look like an omission — the platform tells a user what the cheapest legal
combination is, but never executes it.

### 2.1.3 Entity Resolution and Approximate String Matching

The problem of deciding whether two records refer to the same real-world entity was
formalized statistically by Fellegi and Sunter in 1969 [6]. Their framework compares record
pairs across multiple quasi-identifiers, ranks candidate pairs by a likelihood ratio, and
partitions them by threshold into three outcomes rather than two: link, possibly link, and do
not link. The middle category is not a failure of the method but its central design
decision — the objective is to minimise the number of uncertain cases while controlling two
distinct error probabilities, the probability of linking records that do not match and the
probability of failing to link records that do.

Character-level comparison of the individual fields is a separate problem. Winkler extended
the Jaro string comparator with a metric that partially accounts for typographical variation
in names, together with decision rules that consume it, and demonstrated the improvement
empirically; the resulting comparators were used in production matching software for the Post
Enumeration Survey of the 1990 United States census [7]. The resulting Jaro–Winkler measure
remains a standard tool for name comparison. Binette and Steorts survey the field as it now
stands, tracing the lineage from the foundational work of the 1940s and 1950s through modern
probabilistic record linkage, and covering clustering approaches, semi-supervised and fully
supervised methods, and canonicalization [8]. They note the breadth of application across
human rights work, official statistics, medicine and citation networks [8].

**Relevance and departure.** Lessley's store-resolution pipeline is recognisably in the
Fellegi–Sunter tradition: it produces a three-way verdict against two thresholds rather than a
binary decision, and it routes the uncertain middle band to human adjudication rather than
guessing. Jaro–Winkler is one of the similarity measures it applies. Two differences are
worth noting. The pipeline is deterministic and staged rather than probabilistic — it applies
a sequence of increasingly permissive matchers and short-circuits on the first confident
answer, rather than computing a single likelihood ratio over all fields. And it closes the
loop: confirmed human decisions are written back as aliases, so the same comparison is
resolved without review on subsequent runs. The surveyed literature treats the review queue
as an output; here it is also an input.

### 2.1.4 Hebrew Text Normalization

Hebrew presents obstacles to string matching that Latin-script languages largely do not.
Niqqud — the system of diacritical marks representing vowels — is used in dictionaries, poetry
and children's books but is rarely present in ordinary modern text. Roth, Turetzky and Adi
observe that traditional Hebrew includes diacritics that "dictate the way individuals should
pronounce given words", but that "modern Hebrew rarely uses them", with the consequence that
"readers [are] expected to conclude the correct pronunciation and understand which phonemes to
use based on the context" [9]. Their work concerns speech synthesis, where the ambiguity is
phonetic; for text matching the same property has a different consequence, namely that the
*same* store name may appear with or without diacritics in two sources and compare as
unequal.

The wider Hebrew NLP literature treats diacritic removal as a standard normalization step,
applied specifically to reduce orthographic variability before comparison, alongside the
removal of matres lectionis. It also cautions that preprocessing decisions of this kind carry
consequences that are not always intended, and that stripping diacritics is not uniformly
beneficial for downstream models.

**Relevance.** Lessley's normalization stage performs exactly this class of transformation —
diacritic stripping, unification of final-form letters, resolution of Unicode presentation
forms, removal of legal suffixes and separation of branch descriptors from chain names — as a
deterministic preprocessing step whose output feeds the matcher. The literature justifies the
approach; the specific composition of steps for Israeli *retail* names, where the dominant
noise is commercial rather than literary, is the project's own contribution.

### 2.1.5 Information Extraction from Unstructured Text with Large Language Models

Converting free-text prose into structured records is a long-standing NLP task encompassing
named-entity recognition, relation extraction and event extraction. Xu et al. survey the
recent shift toward generative large language models for this purpose, which "aims to extract
structural knowledge from plain natural language texts" across the various information
extraction subtasks [10]. The attraction for practitioners is that a model can be directed by
prompt alone to emit a specified structure, without task-specific training data or a labelled
corpus — a substantial change from the supervised pipelines that preceded it.

**Relevance and limitation.** Lessley applies this technique to deal terms and conditions,
parsing free Hebrew prose into a fixed constraints schema. Two aspects of the project's use
are not addressed by the surveyed literature. The first is determinism: the parser is run at
temperature zero with a fixed seed, and identical inputs are deduplicated before parsing so
that shared boilerplate across thousands of deals costs a single model call — a
cost-engineering concern the extraction literature does not treat, because it evaluates
accuracy rather than throughput. The second is the failure mode. The literature evaluates
extraction quality on the assumption that the model answers; in a deployed pipeline, the more
consequential question is what happens when it cannot be reached. Lessley's answer — log and
skip, never fail the scrape — trades completeness for availability, and the resulting
silent degradation is a real operational risk discussed in chapter 4.

### 2.1.6 Discount Combination as Constrained Optimization

Selecting a set of promotions under constraints is studied in the e-commerce and operations
research literature, usually from the merchant's side. Albert and Goldenberg formalize the
Online Constrained Multiple-Choice Promotions Personalization Problem as an online
multiple-choice knapsack problem, choosing which promotion to present to each customer so as
to maximise purchase completions within a global promotional budget, and extending the
classical formulation to cases with negative weights and values [11]. The knapsack structure
underlying coupon allocation is NP-hard, which is why this literature is dominated by
approximation schemes, portfolio relaxations and heuristics rather than exact solutions.

A separate strand addresses the interaction between promotions rather than their selection:
when several promotions stack, the resulting combination can carry consequences the merchant
did not intend, motivating explicit modelling of combination rules and risk.

The algorithmic components Lessley uses are textbook material. Shortest paths in directed
acyclic graphs, dynamic programming over states, and the greedy solution to the fractional
knapsack problem — in which items are divisible and filling by highest value density first is
provably optimal — are all standard [12].

**Where this project differs, and why it matters.** The surveyed work optimizes from the
*merchant's* perspective: which promotion to offer, subject to a budget the merchant
controls. Lessley optimizes from the *consumer's*: which of the promotions already available
to this person may legally be combined, and how. That inversion changes the problem's
structure in three ways the literature does not cover.

First, legality is bilateral. An edge between two deals exists only if each accepts the
other's category, so the constraint is not a property of a deal but of a pair — and pairwise
legality is insufficient, since a longer chain may contain an illegal pair not adjacent in it.

Second, and most significantly, the deals are not homogeneous. Price-level promotions reduce
the bill and compose by chaining; instrument-level benefits — gift-card loads, card-brand
discounts, cashback — discount only the portion of the bill actually routed through that
instrument, and the same money cannot be routed twice. Treating the second kind as though it
were the first double-counts. This is not a knapsack over deals; it is a graph search over
one class of deal composed with a bill-splitting allocation over another, and the second
phase is where fractional knapsack applies [12]. The e-commerce promotion literature, which
models promotions as interchangeable budget-consuming offers, has no equivalent distinction.

Third, the objective is bounded by executability rather than by budget. An unbounded search
returns stacks no consumer would present at a checkout, so the useful formulation caps
combination length — a constraint with no analogue in the merchant-side budget formulations.

### 2.1.7 Preserving History: Slowly Changing Dimensions

A scraped catalogue changes continuously, and a system that overwrites records loses the
ability to explain what it recommended yesterday. The data-warehousing literature settled
this problem long ago. The Kimball Group's Type 2 slowly changing dimension technique handles
attribute change by adding "a new row in the dimension with the updated attribute values"
rather than updating in place, assigning a fresh surrogate key to each version and carrying
three metadata columns: a row effective date, a row expiration date, and a current row
indicator [13].

**Relevance and adaptation.** Lessley's deal history follows this pattern directly: an
append-only version collection paired with a current-head collection, with identity and
content distinguished by two separate hashes so that a reworded deal is recognised as the
same deal changed rather than as a new one. The adaptation the warehousing literature does
not address is the failure case peculiar to scraping. A warehouse load is authoritative; a
scrape may be partial, and treating an absent record as a deleted one would let a single
failed run mass-expire a live catalogue. Lessley therefore guards expiry behind coverage,
repetition and elapsed-time conditions — an asymmetry justified by the observation that
under-expiring is recoverable while mass false expiry is not.

### 2.1.8 Summary and Positioning

Each field surveyed above supplies a solved piece of this system. Edge authentication has an
established pattern and a well-documented vulnerability class that motivates it [1][2][3][4].
Regulated consumer financial data access has a legal framework that defines both the
opportunity and its limits [5]. Entity resolution has half a century of theory, a standard
three-way decision structure and mature string comparators [6][7][8]. Hebrew normalization
has a recognised inventory of transformations [9]. Structured extraction from prose has a
current and rapidly moving method [10]. Promotion optimization has a formal home in
constrained combinatorial optimization [11][12]. Historical preservation has a canonical
pattern [13].

What the literature does not supply is their composition, and the composition is where the
difficulty lies. No surveyed work joins a consumer's own regulated transaction history to a
multi-source, entity-resolved, LLM-enriched benefit catalogue in order to answer a
consumer-side optimization question. More narrowly, the central technical contribution of this
project — the recognition that price-level and instrument-level discounts are structurally
different problems that must be solved in two phases rather than chained uniformly — does not
appear in the promotion-optimization literature reviewed here, which models promotions as
homogeneous. Chapter 3 sets out how that composition was designed and built.

---

### Note on citation provenance

All thirteen sources listed in chapter 6 were located and checked during the writing of this
chapter. Eleven were retrieved and read directly. Two — Fellegi and Sunter (1969) [6] and
Winkler (1990) [7] — are pre-digital publications whose full text sits behind paywalls or in
print-only proceedings; their bibliographic details, and the substance attributed to them
above, were confirmed against multiple independent secondary sources including the Binette and
Steorts survey [8] and the ERIC record for the Winkler paper, but the original papers were
not read in full. This distinction is recorded rather than glossed over, and is tracked in
`OPEN-QUESTIONS.md` as **Q11**.

Two further sources relevant to §2.1.6 could not be retrieved at all — a Springer chapter on
efficient Jaro–Winkler entity matching and a 2025 journal article on conflicts between stacked
promotions — because both are behind publisher authentication. Neither is cited, and no claim
in this chapter rests on them.
