# Production readiness

Work required to run Lessley for thousands of active users. Written against the codebase as of
the categories rewrite (see [`adr/`](adr/)).

Ordered by what breaks first, not by effort. **P0 items will fail in production as written** —
they are not polish.

Assumptions this is sized against, confirmed with the team:

- Open Finance permits **1,000 requests per minute across the whole platform**.
- Transaction data **may not be stored at rest**. Regulatory, not a preference.
- Target scale **1,000–5,000 active users**.
- **One Gateway instance.** See [ADR-0009](adr/0009-single-gateway-instance.md).

---

## The binding constraint: Open Finance

Everything else is secondary. Do this arithmetic before designing anything that touches
transactions.

One call to `get_user_transactions_async` costs:

```
1 request   GET accounts
N requests  GET transactions, one per account, fired simultaneously via asyncio.gather
────────────
1 + N       ≈ 4 for a user with 3 accounts
```

**Per insights page load.** `InsightsRecommendationsPage` mounts roughly eight queries —
`useTransactions` twice (two day-ranges), `useSpendingSaved`, `useTopAccounts` twice,
`useCategoryInsights`, `useTopStores`, `useSpendingPeriodComparison`. Each is a separate HTTP
request that independently calls `_transactions_for`. Nothing is shared between them.

```
8 endpoints × ~4 requests = ~32 Open Finance requests per page view
1000 / 32   ≈ 31 page views per minute, platform-wide, before throttling
```

At 5,000 users, **31 page views per minute is roughly 0.6% of the user base**. This is the first
thing that will break, and it will break as an outage rather than a slowdown.

**Per weekly sweep.** 5,000 users × ~4 requests ≈ **20,000 requests**. `prefetch_count=10` bounds
concurrency, not rate, so the sweep issues them as fast as Open Finance answers — holding the
global quota at its ceiling for roughly twenty minutes while every live user request fails.

### P0-1 — Collapse the insights page onto one fetch

The single highest-value change available, and it needs no caching, so the data-at-rest
constraint does not apply.

Add `GET /insights/overview?days=90` returning categories, top accounts, top stores,
spending-by-day, spending-saved and the period comparison from **one** `_transactions_for` call.
The calculations are already pure functions over a transaction list — `top_spending_categories`,
`top_spending_accounts`, `top_spending_stores`, `spending_by_day_of_week`, `spending_saved`,
`spending_difference_between_two_periods` all take `list[Transaction]`. The orchestration is the
only thing that duplicates work.

`8 × 4 → 1 × 4`. Page views per minute go from ~31 to ~250.

Keep the individual endpoints for anything that genuinely needs one figure; make the page use the
aggregate.

### P0-2 — Rate-budget every Open Finance caller

A token bucket in front of `OpenFinanceClient`, sized below the global ceiling and **split by
purpose**: interactive traffic must never queue behind the sweep.

Suggested split: 800/min for user-facing requests, 200/min for the sweep. At 200/min the sweep
processes ~50 users per minute; 5,000 users takes ~100 minutes starting at 00:00 Monday, which is
acceptable and leaves live traffic untouched.

This must live in Personalization, not the Gateway — the Gateway does not know the cost of a
command.

### P0-3 — Handle 429

`open_finance_client` retries once on 401/403 (stale token) and handles nothing else. A 429 today
propagates as a 502 to the caller, and inside the sweep it nacks the message — which, with
`requeue=False` and no retry policy on the Python consumer, **drops that user's recalculation
silently**.

Needed: respect `Retry-After`, exponential backoff with jitter, and a bounded retry. Pair with
P1-4 (dead-letter queues) so exhausted retries are visible rather than lost.

### P0-4 — Cap per-account concurrency

`asyncio.gather` fires every account's transaction request simultaneously. A user with 15
accounts issues 15 concurrent requests from one page view. Bound it with a semaphore (4–6).

### P0-5 — Health endpoints

Neither service serves `/health`, though **both exempt it from edge auth** — the exemption was
written for a probe that does not exist (`EdgeVerificationMiddleware.ExemptPrefixes`,
`edge_auth_middleware._EXEMPT_PATHS`).

Compose has healthchecks for infrastructure but none for the application containers. A wedged
Gateway — event loop blocked, Mongo pool exhausted, reference data failed to load — looks
identical to a healthy one.

Needed: liveness (process responds) and readiness (Mongo reachable, RabbitMQ connected,
reference data loaded) on both services, wired into both compose files.

---

## Second audit — race conditions and silent failures

Found after the first pass, looking specifically for things that can happen at once.

### P0-6 — SignalR dies permanently and silently

`useSignalR` configures `withAutomaticReconnect([0, 2000, 5000, 10000, 30000])` — five attempts
over roughly 47 seconds — and then `connection.onclose(() => {})`, which does nothing.

Access tokens live **30 minutes**. Once the access cookie has expired, negotiate returns 401, the
five reconnects all fail, and the connection is closed for good. The app keeps working — the next
HTTP call silently refreshes the cookie — but real-time notifications never come back until a full
page reload, with nothing on screen to say so.

Any tab left open longer than 30 minutes is one network blip away from this: a backgrounded mobile
tab, a laptop sleeping, a wifi handover.

**Fix:** on close, attempt a cookie refresh and rebuild the connection with backoff, rather than
leaving a dead object. Surface connection state in the UI so silent loss becomes visible.

### P0-7 — Out-of-order tag writes

Two recalculation commands for the same user can be in flight simultaneously — the weekly sweep
overlapping a match-level change, or two rapid triggers. `prefetch_count=10` runs handlers
concurrently, so completion order is not arrival order, and `UserTagAssignedEvent(UserId, Tags)`
carries no timestamp or version.

An older calculation can therefore overwrite a newer one, and the user keeps stale categories until
something recalculates again.

**Decision taken: add a version guard.** Stamp the calculation time on the event, store it on
`ApplicationUser`, and have `AssignTagsAsync` reject a write whose stamp is older than the one it
holds. Note this adds a field to `users`, which three services read — see
[ADR-0001](adr/0001-gateway-is-the-only-writer-of-user-categories.md).

### P1-7 — The `CategoriesUpdated` refetch amplifies the sweep

Every tag write pushes `CategoriesUpdated`, and the client responds by invalidating
`queryKeys.insights.all`. On the insights page that refetches ~8 queries — roughly **32 more Open
Finance requests per open tab**, against the quota the sweep is already straining. Multiple tabs
multiply it.

React Query only refetches *active* queries, so the blast radius is users currently viewing
insights. At 00:00 Monday that is few; after a settings change during the day it is the user who
just acted, which is correct behaviour.

**Fix:** have the push carry the tags (it already does) and let the client update the cached
profile directly instead of invalidating the whole insights tree. Reserve full invalidation for
reconnect.

### P1-8 — Notification listing is unbounded

`GetByUserAsync` is `.Where(UserId).OrderByDescending(SentAt).ToListAsync()` — no `.Take()`, no
paging. `MarkAllAsReadAsync` similarly loads every unread row into memory and updates them one by
one.

At the expected volume — **hundreds to thousands per user** — every notification page load pulls
the lot into memory and serialises it.

**Fix:** paginate the endpoint, batch the mark-all update, and batch the fanout write in
`SendToGroupAsync` (which currently writes one document per matching user in a single
`SaveManyAsync`).

### P1-9 — Scraper and reference cache have no handshake

`lessley-deals` writes the catalogue in **one nightly batch**; Personalization polls every 15
minutes. That is ~95 pointless rebuilds a day, and the one that matters may run mid-import and
snapshot a half-written catalogue.

**Fix:** a completion signal from the scraper, or an interval aligned past the batch window. See
[ADR-0007](adr/0007-reference-data-refreshes-on-a-timer.md).

### P1-10 — Deploys collide with the sweep

Single instance means every deploy is downtime, and a deploy during the Monday sweep loses the run
with no record of progress; misfire handling will not re-run it until the following week.

**Decision taken: scheduled maintenance windows, kept away from Monday 00:00 UTC.** Document the
collision in the deploy checklist. This lowers the urgency of sweep resumability (P1-2) without
removing the need for it.

### P1-11 — Account deletion has no single path

Not yet a legal obligation but expected. A user's data currently lives in: `users` (tags, muted
tags, clubs, matching score), `notifications`, `refresh_tokens`, `pending_registrations`,
`verification_codes`, and the Open Finance connection held by the provider.

Nothing removes them as a unit, and nothing revokes the bank connection. Scope the inventory now,
while it is six collections rather than twelve.

---

## P1 — before scale

### P1-1 — Transaction caching within the regulatory boundary

Storage at rest is prohibited, which rules out the obvious fix. What remains:

- **In-process TTL cache** keyed by `(user_id, days)`, 30–120s, memory only, never serialised to
  disk. This is what makes repeat page views and the remaining endpoint duplication cheap.
- **Confirm the boundary explicitly.** "At rest" usually means persisted storage; an ephemeral
  in-memory cache is normally outside it, but that needs a written answer from whoever owns the
  regulatory position, not an assumption from engineering. **Blocking question — see below.**
- If even in-memory caching is disallowed, P0-1 becomes the *only* lever and the aggregate
  endpoint must cover every screen.

### P1-2 — Sweep progress and resumability

`RecalculateUserCategoriesJob` loads every email into memory and publishes in a loop. If the
Gateway restarts mid-sweep, the run is lost with no record of how far it got, and
`WithMisfireHandlingInstructionFireAndProceed` will not re-run it until next Monday.

Needed: persisted progress (last processed user), resume on restart, and a completion record so
"did Monday's sweep finish?" is answerable.

### P1-3 — Explicit unlink signal

[ADR-0004](adr/0004-an-empty-calculation-never-clears-tags.md) means tags are never cleared
automatically. A user who disconnects their bank keeps their categories and keeps receiving
notifications for them, indefinitely.

Needed: a real disconnect path — Open Finance revocation webhook, or an in-app "disconnect bank"
action — that clears tags deliberately. Until it exists, the warning log
`"Calculation returned no categories for a user who has tags"` is the only signal, and nobody is
watching it.

### P1-4 — Dead-letter queues and consumer retry

The Gateway has `UseMessageRetry` on `gateway.user_tag_assigned` only. Personalization's consumer
has none: `message.process()` with `requeue=False` means any exception drops the message.

This is how a throttled sweep loses data. Open Finance returns 429, `_transactions_for` raises,
the message is nacked and gone — potentially for thousands of users in one run, with no record
beyond a log line.

**Decision taken: retry with backoff, then dead-letter.** Respect `Retry-After`, bound the
retries, and route exhausted messages to a DLQ that is monitored. Pair with the rate budget
(P0-2), which is what should prevent the situation arising at all.

### P1-5 — Notification volume

`SendToGroupAsync` writes one `Notification` per matching user per broadcast. A group notification
to a popular category at 5,000 users writes 5,000 documents in one `SaveManyAsync`.

Needed: batching, and a check of what the 90-day TTL implies for collection size at expected
broadcast frequency. Also confirm `GetUserNotificationsAsync` is paginated — the client renders a
list with no visible limit.

### P1-6 — Idempotency on tag assignment

`UserTagAssignedEventConsumer` has no deduplication. Redelivery re-applies the same tags, which is
harmless today, but the retry ladder added in the categories work makes redelivery routine rather
than exceptional. If any future consumer side-effect stops being idempotent, this becomes a real
bug.

---

## P2 — hardening

### P2-1 — `Edge_ApiKey` fails open

`EdgeAuthMiddleware` skips verification entirely when the key is unset, rather than rejecting.
Deliberate — port publishing is the primary control — but a config regression removes
defence-in-depth silently. Fail closed in non-Development environments.

### P2-2 — Reference-data refresh interval

`ReferenceData_RefreshSeconds` defaults to 900s, chosen without knowing the scraper's cadence.
Match it to how often deals actually change. A full rebuild at every interval also re-reads all
stores, deals, clubs and aliases — at large catalogue sizes, consider an incremental path.

### P2-3 — Mongo indexes for the query patterns that remain

`idx_tags` supports the group fanout. Confirm coverage for `GetUserNotificationsAsync`
(`UserId + SentAt`, exists), and drop indexes that only served the deleted calc-notification
queries.

### P2-4 — Naming debt

`extract_mcc_tags` returns category *names* (`"GROCERIES"`), not MCC codes.
`get_mcc_codes_by_tag` still carries a legacy numeric branch. The mismatch cost real
investigation time during the categories work and will cost it again.

### P2-5 — Structured error responses

Personalization raises and lets FastAPI shape the response; the Gateway returns anonymous objects.
Clients see inconsistent error bodies. Settle on one shape.

### P2-6 — Frontend lint debt

`src/routes/index.tsx` has 12 `react-refresh/only-export-components` errors. Pre-existing, but it
means `npm run lint` cannot be used as a gate.

---

## Message flow — where RabbitMQ is now

After the categories rewrite the topology is deliberately small. Exchange `lessley_events`,
topic, durable.

| Direction | Routing key | Queue | Purpose |
|---|---|---|---|
| Gateway → Personalization | `Gateway.calculate_user_categories` | `personalization.gateway_commands` (binds `Gateway.*`) | The only command |
| Personalization → Gateway | `Personalize.user_tag_assigned` | `gateway.user_tag_assigned` | The only result |
| Gateway → (tests) | `Gateway.notification_dispatched` | — | E2E observation only |

Everything else was removed: both recommendation commands, both result events, three deal
notification consumers whose publishers had no callers, and two consumer classes that were never
registered with MassTransit at all.

**Gaps to close:** no DLQs (P1-4); no consumer retry on the Python side (P1-4); no queue-depth
monitoring; `Gateway.*` binds wholesale, so an unrecognised key is logged and dropped — correct,
but it means a typo'd routing key fails silently rather than loudly.

---

## Validation gaps

- **`days` is validated (1–365) but the stored tags are always the 90-day answer.** A user who
  changes the range picker sees a 30-day view while notifications are driven by 90-day tags.
  Cosmetic today; a trap for whoever wires the picker into a write path.
- **No validation that a user's `Tags` are known MCC categories.** `PUT /admin/users/{email}/tags`
  accepts arbitrary strings, which then become SignalR group names.
- **`merchantName` and `merchantAddress` are used for matching without normalisation limits.** The
  matcher handles this, but there is no guard against pathological input from the feed.
- **No schema validation on inbound RabbitMQ payloads.** `_handle_gateway_command` reads fields
  defensively across casings; a malformed payload produces `None` and fails downstream rather
  than being rejected at the edge of the consumer.

---

## Open questions

These change the shape of the work above. I have written the tasks against my best assumption and
flagged where the assumption is load-bearing.

1. **Does "no storage at rest" permit an in-memory TTL cache?** Blocking for P1-1. If not, the
   aggregate endpoint is the only lever and must cover every screen.
2. **Is the 1,000/min quota per-client or per-endpoint?** If per-endpoint, the budget splits
   differently and the sweep is cheaper than modelled.
3. **What does Open Finance return when the quota is exhausted — 429, 503, or an empty `[]`?** If
   it can return `[]`, [ADR-0004](adr/0004-an-empty-calculation-never-clears-tags.md)'s guard is
   doing even more work than assumed, and the warning log needs an alert on it.
4. **What is the expected notification broadcast frequency?** Sizes P1-5 and P1-8 together.
5. **Do you need an audit trail for financial-data access?** Every insights call reads a user's
   bank transactions; nothing records that it happened in a queryable form.
6. **Does the average user have 1 account or 10?** The whole quota model scales on `N`. The
   arithmetic above assumes 3 — at 10 the page-view ceiling drops from ~31/min to ~9/min.
7. **How long may a stale category last before it matters?** Decides whether the weekly sweep is
   the right cadence or whether it should be daily — which the quota may not permit.
8. **Is `Auth:IsRotateRefresh` enabled in production?** Rotation with reuse detection is
   implemented and is the safer setting; it is configurable, so it can be off without anyone
   noticing.

### Answered

- **Scraper cadence:** one nightly batch. Drives P1-9.
- **`users` as a cross-service read contract:** intentional. Documented in
  [ADR-0001](adr/0001-gateway-is-the-only-writer-of-user-categories.md).
- **Account deletion:** not yet required, expected. P1-11.
- **Deploys:** scheduled maintenance windows, kept clear of Monday 00:00 UTC. P1-10.
- **Write ordering:** version guard, not last-write-wins. P0-7.
- **Sweep failures:** retry with backoff, then dead-letter. P1-4.
- **Notification volume:** hundreds to thousands per user. P1-8.
