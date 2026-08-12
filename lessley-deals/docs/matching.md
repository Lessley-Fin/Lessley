# Entity Resolution / Matching Subsystem

## Overview

The matching subsystem resolves raw store names (as they appear in transaction
data) to canonical store identities. It is designed to be **conservative and
explainable**: the system prefers sending ambiguous cases to human review rather
than producing false positives.

The pipeline has **5 stages**, evaluated in order. Each stage applies a
different matching strategy with its own confidence characteristics. The
pipeline **short-circuits on a confident match** -- if an early stage produces
a score at or above the auto-match threshold, later stages are skipped.

Every verdict carries a full explanation of which stages ran, what they scored,
and why the final decision was made. This makes the review queue actionable and
the system auditable.

---

## Matching Pipeline Stages

The pipeline processes a raw store name through up to five stages. Each stage
produces zero or one candidate with an associated confidence score.

| Stage | Name             | Complexity | Max Confidence | Can Auto-Match? |
|-------|------------------|------------|----------------|-----------------|
| 1     | ExactAlias       | O(1)       | 1.00           | Yes             |
| 2     | Compact Form     | O(n)       | ~0.95          | Yes             |
| 3     | Normalized Fuzzy | O(n)       | ~1.00          | Yes             |
| 4     | Domain Match     | O(n)       | 0.80           | No              |
| 5     | Token Overlap    | O(n)       | 0.70           | No              |

### Stage 1: ExactAlias (O(1) lookup)

A pre-built dictionary maps each compact-form alias to its store ID:

```
compact_form -> store_id
```

If the input's compact form appears as a key, the match is immediate with
confidence **1.0** and decision **AUTO_MATCH**.

This is where the feedback loop pays off. When a human reviewer approves a
match, the approved alias is persisted as a `StoreAlias`. On the next pipeline
run that alias appears in the ExactAlias dictionary, so the same raw name will
never need review again.

### Stage 2: Compact Form (O(n) comparison)

Compares the input's compact form against every alias compact form using
Jaro-Winkler similarity, then applies a **0.95 discount factor**:

```
confidence = jaro_winkler(input_compact, alias_compact) * 0.95
```

The discount exists because compact forms strip punctuation, whitespace, and
some diacritics -- information that could distinguish genuinely different
stores. The best match above the review threshold becomes the candidate.

### Stage 3: Normalized Fuzzy (weighted scoring)

Operates on normalized forms (lowercased, trimmed, standardized) rather than
compact forms, preserving more of the original structure. Uses a weighted
combination of two algorithms:

```
score = 0.70 * jaro_winkler(input_norm, alias_norm)
      + 0.30 * token_jaccard(input_tokens, alias_tokens)
```

The Jaro-Winkler component rewards shared prefixes (common in store names).
The Token Jaccard component handles word reordering. The best combined score
above the review threshold becomes the candidate.

### Stage 4: Domain Match (URL-based)

If the input contains an extractable domain (e.g., from a URL embedded in the
transaction description) and a canonical store has the same domain on record,
this stage produces a candidate with a **fixed confidence of 0.80**.

Because 0.80 is below the auto-match threshold, domain matches always go to
review. A domain match is a useful supporting signal but is never treated as a
sole decider -- different stores can share infrastructure or parent domains.

### Stage 5: Token Overlap (last resort)

Uses Token Jaccard only, with confidence **capped at 0.70**:

```
confidence = min(token_jaccard(input_tokens, alias_tokens), 0.70)
```

This stage catches cases where word order differs completely or where
additional tokens (branch names, city suffixes) dilute prefix-based
similarity. Because the cap is below the auto-match threshold, token-only
matches **never** auto-match.

---

## Decision Thresholds

After all stages run (or after a short-circuit), the highest-confidence
candidate determines the verdict:

| Confidence Range       | Decision    | Effect                           |
|------------------------|-------------|----------------------------------|
| >= 0.90                | AUTO_MATCH  | Linked automatically, no review  |
| >= 0.50 and < 0.90    | REVIEW      | Sent to human review queue       |
| < 0.50                 | NO_MATCH    | No candidate, flagged as new     |

Exception: token-only matches (Stage 5) are capped at 0.70 and therefore can
never reach AUTO_MATCH regardless of token overlap.

---

## Scoring Algorithms

### Jaro-Winkler Similarity

Jaro-Winkler is a string similarity metric particularly effective for short
strings that share a common prefix. It works in two steps:

1. **Jaro similarity** counts the number of matching characters (characters
   that appear in both strings within a distance window of
   `floor(max(|s1|, |s2|) / 2) - 1`) and the number of transpositions (matched
   characters in different order). The Jaro score is:

   ```
   jaro = (matches/|s1| + matches/|s2| + (matches - transpositions/2)/matches) / 3
   ```

2. **Winkler adjustment** boosts the score for strings that share a common
   prefix (up to 4 characters):

   ```
   jaro_winkler = jaro + (prefix_length * 0.1 * (1 - jaro))
   ```

This is a better fit than Levenshtein for store-name matching because store
names frequently share a brand prefix. For example, comparing two Hebrew store
names that share the same brand but differ in a suffix will score high on
Jaro-Winkler due to the shared prefix, while Levenshtein would penalize
heavily for the differing tail.

### Token Jaccard Similarity

Token Jaccard treats each string as a **set of tokens** (words) and computes:

```
token_jaccard = |A intersection B| / |A union B|
```

This metric is order-independent, so reordered words score identically:

| Set A                  | Set B                  | Intersection | Union | Score |
|------------------------|------------------------|--------------|-------|-------|
| {"token1", "token2"}   | {"token2", "token1"}   | 2            | 2     | 1.00  |
| {"a", "b", "c"}        | {"a", "b"}             | 2            | 3     | 0.67  |
| {"a", "b"}             | {"c", "d"}             | 0            | 4     | 0.00  |

Token Jaccard complements Jaro-Winkler: it handles word reordering well but
ignores intra-word similarity. The weighted combination in Stage 3 balances
both strengths.

---

## AliasIndex (`index.py`)

The `AliasIndex` is a pre-built data structure created at pipeline start from
all known aliases (both manually curated and review-approved).

```python
class AliasIndex:
    exact_lookup: dict[str, str]   # compact_form -> store_id
    all_aliases: list[tuple[Alias, str]]  # (alias, store_id) for fuzzy stages
```

- **`exact_lookup`**: Powers Stage 1. A flat dictionary keyed by compact form,
  providing O(1) exact matching.
- **`all_aliases`**: Powers Stages 2-5. A list of all alias objects paired with
  their store IDs, iterated during fuzzy matching.

The index is **rebuilt when aliases change**, specifically after a review
approval creates a new `StoreAlias`. This ensures the feedback loop takes
effect on the next pipeline run without requiring a full system restart.

---

## MatchVerdict and Explanation

Every match attempt produces a `MatchVerdict` containing:

- **store_id**: The matched store (or `None` for NO_MATCH).
- **confidence**: The highest confidence score across all stages.
- **decision**: One of `AUTO_MATCH`, `REVIEW`, or `NO_MATCH`.
- **explanation**: A structured object describing the matching process.

The explanation includes:

- Which stages ran and in what order.
- Which stage produced the winning candidate.
- A `details` dict with per-stage scores (e.g., Jaro-Winkler score, Token
  Jaccard score, combined score, discount applied).
- Why certain stages were skipped (short-circuit on confident match).

Candidates are sorted by confidence descending, so the review queue presents
the most likely match first. This makes review decisions informed and
auditable -- a reviewer can see exactly why the system thinks "X" matches "Y"
and at what confidence.

---

## Confidence Caps and Safety

Several mechanisms prevent uncertain signals from triggering automatic matches:

| Mechanism              | Applied In   | Effect                                      |
|------------------------|--------------|---------------------------------------------|
| Token confidence cap   | Stage 5      | Caps score at 0.70, never auto-matches      |
| Compact form discount  | Stage 2      | Multiplies score by 0.95, penalizes info loss|
| Domain fixed confidence| Stage 4      | Fixed at 0.80, always goes to review        |
| Auto-match threshold   | All stages   | Only >= 0.90 bypasses review                |

The combination of these caps means that only Stage 1 (exact alias) and
high-scoring results from Stages 2-3 can auto-match. Every other signal is
routed through human review.

---

## Feedback Loop

The matching system improves over time through a human-in-the-loop cycle:

```
Raw name -> Pipeline -> REVIEW verdict
                            |
                      Human approves
                            |
                      StoreAlias created (source=REVIEW)
                            |
                      AliasIndex rebuilt
                            |
                      Next run: Stage 1 exact match (confidence 1.0)
```

1. A raw store name enters the pipeline and produces a REVIEW verdict.
2. A human reviewer approves (or rejects) the proposed match.
3. On approval, a `StoreAlias` is persisted with `source=REVIEW`.
4. On the next pipeline run, the `AliasIndex` is rebuilt including the new
   alias.
5. The same raw name now hits Stage 1's exact lookup and matches at confidence
   1.0 with AUTO_MATCH.

The system gets better over time without model training, redeployment, or
parameter tuning. Each review decision permanently teaches the system a new
mapping.

---

## MatchConfig

All matching parameters are centralized in a single configuration dataclass:

```python
@dataclass
class MatchConfig:
    auto_match_threshold: float = 0.90
    review_threshold: float = 0.50
    compact_discount: float = 0.95
    normalized_jw_weight: float = 0.70
    normalized_token_weight: float = 0.30
    domain_fixed_confidence: float = 0.80
    token_confidence_cap: float = 0.70
```

| Parameter                | Default | Purpose                                         |
|--------------------------|---------|-------------------------------------------------|
| `auto_match_threshold`   | 0.90    | Minimum confidence to skip human review          |
| `review_threshold`       | 0.50    | Minimum confidence to send to review queue       |
| `compact_discount`       | 0.95    | Multiplier applied to compact-form matches       |
| `normalized_jw_weight`   | 0.70    | Weight of Jaro-Winkler in Stage 3 combined score |
| `normalized_token_weight`| 0.30    | Weight of Token Jaccard in Stage 3 combined score|
| `domain_fixed_confidence`| 0.80    | Fixed confidence for domain-based matches        |
| `token_confidence_cap`   | 0.70    | Maximum confidence for token-only matches        |

---

## Example Walkthrough

Raw input from a transaction:

```
"שופרסל דיל - סניף תל אביב"
```

Assume the canonical store is "שופרסל דיל" (store_id: `shufersal-deal`) with
one existing alias whose compact form is `שופרסלדיל`.

### Preprocessing

| Form       | Value                        |
|------------|------------------------------|
| Raw        | `שופרסל דיל - סניף תל אביב`  |
| Normalized | `שופרסל דיל סניף תל אביב`    |
| Compact    | `שופרסלדילסניףתלאביב`         |
| Tokens     | `{שופרסל, דיל, סניף, תל, אביב}` |

### Stage 1: ExactAlias

Lookup compact form `שופרסלדילסניףתלאביב` in the exact dictionary.

The dictionary contains `שופרסלדיל` (the alias for "שופרסל דיל") but not the
full branch-qualified form. **No exact match. Proceed to Stage 2.**

### Stage 2: Compact Form

Compare `שופרסלדילסניףתלאביב` against `שופרסלדיל` using Jaro-Winkler.

The input is significantly longer due to the branch suffix. Jaro-Winkler
rewards the shared prefix (`שופרסלדיל`) but the extra characters reduce the
overall score. Suppose:

```
jaro_winkler("שופרסלדילסניףתלאביב", "שופרסלדיל") = 0.82
confidence = 0.82 * 0.95 = 0.779
```

Score 0.779 is above the review threshold (0.50) but below auto-match (0.90).
**Candidate recorded. Proceed to Stage 3 to look for a better match.**

### Stage 3: Normalized Fuzzy

Compare normalized forms and token sets:

```
jaro_winkler("שופרסל דיל סניף תל אביב", "שופרסל דיל") = 0.87
```

Token sets:
- Input:  {שופרסל, דיל, סניף, תל, אביב}
- Alias:  {שופרסל, דיל}
- Intersection: {שופרסל, דיל} -> size 2
- Union: {שופרסל, דיל, סניף, תל, אביב} -> size 5

```
token_jaccard = 2 / 5 = 0.40
```

Combined:
```
score = 0.70 * 0.87 + 0.30 * 0.40
      = 0.609 + 0.120
      = 0.729
```

Score 0.729 is below the compact-form candidate (0.779). **Stage 2 candidate
remains the best. Proceed to Stage 4.**

### Stage 4: Domain Match

No domain information in the input string. **Stage skipped.**

### Stage 5: Token Overlap

```
token_jaccard = 2 / 5 = 0.40
confidence = min(0.40, 0.70) = 0.40
```

Score 0.40 is below the review threshold. **No candidate from this stage.**

### Final Verdict

Best candidate across all stages: Stage 2, confidence **0.779**.

```
MatchVerdict:
  store_id:    shufersal-deal
  confidence:  0.779
  decision:    REVIEW
  explanation:
    stages_run: [ExactAlias, CompactForm, NormalizedFuzzy, DomainMatch, TokenOverlap]
    winning_stage: CompactForm
    details:
      compact_form:
        jaro_winkler_raw: 0.82
        discount: 0.95
        confidence: 0.779
      normalized_fuzzy:
        jaro_winkler: 0.87
        token_jaccard: 0.40
        combined: 0.729
      token_overlap:
        token_jaccard: 0.40
        capped_confidence: 0.40
```

The verdict is **REVIEW** because 0.779 falls between the review threshold
(0.50) and the auto-match threshold (0.90). A human reviewer will see the full
explanation and can approve or reject the match. If approved, the raw name
becomes a new alias and will exact-match on all future occurrences.
