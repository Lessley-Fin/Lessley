# 0006 — One missed-savings answer, gathered by shop

**Status:** Accepted

## Context

Two implementations answered the same question. `missed_savings` returned one row per
transaction with the alternative shops attached; `missed_savings_by_store` returned one row per
shop with the purchases it could have covered.

The per-transaction shape produces the same suggestion repeatedly: a user who bought coffee four
times is told about קפה קפה four separate times.

## Decision

Keep `missed_savings_by_store`. Delete the per-transaction path entirely.

## Consequences

Removed: `missed_savings`, `_missed_savings_for`, `_describe_missed_stores`,
`calculate_missed_savings_async`, `TransactionInsightSchema`, `MissedStoreDiscountSchema`,
`MissedStoreSchema`, the `POST /recommendations/missed-savings` route, the Gateway command,
consumer, contracts and receive endpoint, and the frontend's `MissedSavingsSlide.tsx` — which was
already orphaned, nothing imported it.

`_shops_for` stayed: it is the shared matching both paths used.

Tests that covered behaviour still present — club filtering, skipping purchases without an id,
falling back to the original amount — were retargeted at `missed_savings_by_store` rather than
deleted with the method they happened to exercise.

## What callers should read

`match_band` before wording anything on screen. `EXACT` and `STRONG` mean the user shopped at
that shop. `SIMILAR` means only a line-of-business word matched (`קפה`), so it is somewhere
*like* theirs and must be worded that way.
