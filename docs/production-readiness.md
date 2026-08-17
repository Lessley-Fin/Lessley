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

Needed: DLQs on both sides, a retry ladder on the Python consumer, and alerting on DLQ depth. A
message that cannot be processed should be inspectable, not gone.

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
4. **How often does the scraper add deals?** Sets `ReferenceData_RefreshSeconds` (P2-2).
5. **What is the expected notification broadcast frequency?** Sizes P1-5.
6. **Is there an account-deletion or data-erasure requirement?** Nothing currently removes a user's
   tags, notifications, refresh tokens or pending registrations as a unit.
7. **Do you need an audit trail for financial-data access?** Every insights call reads a user's
   bank transactions; nothing records that it happened in a queryable form.
8. **Does the average user have 1 account or 10?** The whole quota model scales on `N`. The
   arithmetic above assumes 3.
