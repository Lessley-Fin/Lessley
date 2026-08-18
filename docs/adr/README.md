# Architecture Decision Records

Decisions that shaped the categories pipeline, why they were made, and what each one costs.

An ADR is written when a choice closes off alternatives — not for every change. If a future
reader would reasonably ask "why is it done this strange way?", the answer belongs here.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-gateway-is-the-only-writer-of-user-categories.md) | The Gateway is the only writer of user categories | Accepted |
| [0002](0002-category-reads-have-no-side-effects.md) | Category reads have no side effects; writes are command-triggered | Accepted |
| [0003](0003-weekly-sweep-instead-of-a-backfill.md) | A weekly sweep, not a one-off backfill | Accepted |
| [0004](0004-an-empty-calculation-never-clears-tags.md) | An empty calculation never clears tags | Accepted |
| [0005](0005-club-matching-is-a-synchronous-get.md) | Club matching is a synchronous GET | Accepted |
| [0006](0006-one-missed-savings-answer-gathered-by-shop.md) | One missed-savings answer, gathered by shop | Accepted |
| [0007](0007-reference-data-refreshes-on-a-timer.md) | Reference data refreshes on a timer with an atomic swap | Accepted |
| [0008](0008-the-bank-return-url-is-server-configured.md) | The bank-journey return URL is server-configured | Accepted |
| [0009](0009-single-gateway-instance.md) | A single Gateway instance is a design constraint | Accepted |

## The shape these decisions produce

```
Gateway  ──Gateway.calculate_user_categories──▶  Personalization
   ▲                                                    │
   │                                             compute (90 days)
   │                                                    │
   └──────Personalize.user_tag_assigned◀────────────────┘
   │
   ├─ writes Tags          ← the only write, anywhere
   ├─ syncs SignalR groups
   └─ pushes CategoriesUpdated to open tabs

Client ──GET /api/v1/insights/*──▶ Personalization   (reads only; writes nothing)
```

Three triggers ask for a recalculation — registration, starting a bank journey, and a
match-level change — plus a weekly sweep for everyone. Everything else is a read.

## Known failure points

These are live characteristics of the system, not bugs to be filed and forgotten. Anything
marked **unresolved** has a task in [`../production-readiness.md`](../production-readiness.md).

| Failure point | What happens | State |
|---|---|---|
| Open Finance quota is 1,000 req/min for the whole platform | Each insights endpoint refetches independently; a page load costs ~32 requests. ~31 page views/minute saturates the platform. | **unresolved — P0** |
| The Monday sweep is unpaced | 5,000 users × ~4 requests drains the global quota for ~20 minutes, failing live traffic throughout. | **unresolved — P0** |
| No health endpoint on either service | Both exempt `/health` from edge auth, but neither serves it. Orchestrators cannot tell a wedged container from a healthy one. | **unresolved — P1** |
| SignalR is single-instance | In-memory connection map, no backplane. A second replica silently delivers notifications to a subset of users. | accepted — see [0009](0009-single-gateway-instance.md) |
| The weekly sweep is single-instance | Two replicas each run it, doubling Open Finance load. | accepted — see [0009](0009-single-gateway-instance.md) |
| A recalculation lost to a broker outage is not retried | The trigger swallows publish failures so user-facing work never fails. The next trigger or the weekly sweep recovers it. | accepted — see [0002](0002-category-reads-have-no-side-effects.md) |
| Tags are never cleared automatically | A user who unlinks their bank keeps their categories, and keeps receiving notifications for them, until an explicit unlink signal exists. | accepted — see [0004](0004-an-empty-calculation-never-clears-tags.md) |
| Reference data is stale between refreshes | Deals scraped after a refresh are invisible for up to `ReferenceData_RefreshSeconds` (default 15 min). | accepted — see [0007](0007-reference-data-refreshes-on-a-timer.md) |
| `Edge_ApiKey` unset disables edge verification | Fails open rather than closed. Port publishing is the primary control; this is defence in depth that a config regression silently removes. | **unresolved — P2** |
| Identity writes race with tag writes | Concurrent saves are caught by Identity's concurrency stamp; the consumer throws and MassTransit retries. Not silent, but it depends on the retry ladder. | mitigated |
