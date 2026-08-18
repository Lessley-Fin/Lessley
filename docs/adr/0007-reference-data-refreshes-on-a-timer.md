# 0007 — Reference data refreshes on a timer with an atomic swap

**Status:** Accepted

## Context

`ReferenceDataRepository` holds clubs, stores and deals in memory because the insight
calculations look the same records up thousands of times per request and must never wait on
Mongo. It loaded once at startup and returned early forever afterwards.

Deals are scraped continuously. A cache loaded once means every deal added after boot is
invisible to missed-savings and club matching until the process restarts — a failure with no
symptom except quietly thinner results.

## Decision

Rebuild on a timer. `ReferenceData_RefreshSeconds` (default 900; zero restores load-once)
drives a background task that calls `load_async(force=True)`.

## The part that matters: how it rebuilds

The load used to assign `self._stores`, then `self._deals_by_id`, then `self._clubs` as each
query returned. Harmless at boot with nobody reading — unacceptable as a refresh, where a request
landing mid-rebuild would see new stores against old deals, and a rebuild that died half-way
would leave the cache permanently inconsistent.

Everything is now built into locals and published onto `self` in a single block at the end.
Readers take no lock, so a half-rebuilt cache must never be observable, and a rebuild that throws
must leave the previous snapshot serving.

`test_reference_data_refresh.py` pins exactly that: the store read succeeds, the deal read fails,
and the assertion is that `_stores` still holds the **old** row.

## The interval is wrong for the actual write pattern

`lessley-deals` upserts `stores`, `clubs`, `deals` and `store_aliases` in **one nightly batch**.
Polling every 15 minutes therefore performs roughly 95 pointless full rebuilds a day, and the one
rebuild that matters may land *during* the import and capture a half-written catalogue.

The timer was the right mechanism for the wrong cadence. The better arrangement is a completion
signal from the scraper — an event, or simply a much longer interval aligned to the batch window —
so Personalization refreshes once, after the import finishes.

Tracked in [`../production-readiness.md`](../production-readiness.md). Until then, raising
`ReferenceData_RefreshSeconds` and aligning it past the nightly batch is a one-line improvement.

## Consequences

- Deals are visible within one refresh interval rather than one deployment.
- A failed refresh is logged and the loop continues on the previous snapshot.
- A rebuild concurrent with the scraper's batch can snapshot a partially imported catalogue. The
  atomic swap guarantees *internal* consistency of the snapshot, not that the source was complete
  when it was read.
