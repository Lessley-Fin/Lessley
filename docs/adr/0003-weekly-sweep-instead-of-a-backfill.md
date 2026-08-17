# 0003 — A weekly sweep, not a one-off backfill

**Status:** Accepted — **see the pacing warning below before deploying**

## Context

Once `GET /insights/categories` stopped writing ([0002](0002-category-reads-have-no-side-effects.md)),
existing users hit none of the three triggers: they had already registered, already started
their bank journey, and might never touch their match level again. Their tags would freeze at
whatever the last page view happened to store.

The obvious remedy was a one-off backfill script.

## Decision

A Quartz job (`RecalculateUserCategoriesJob`) publishes a recalculation command for every user,
every Monday at 00:00 UTC. Cron lives in configuration under `Scheduling:recalculate-user-categories`;
an empty value disables it.

## Why a schedule beats a script

All three event triggers fire when a user's *configuration* changes. None fires when their
*spending* changes, which it does continuously. A one-off backfill would have fixed the
historical population and left that hole open for everyone after it — a user who signs up,
links a bank and never revisits settings would keep their day-one categories forever.

The sweep makes stored tags a maintained projection rather than a snapshot, and it deploys with
the code instead of being a migration someone has to remember to run.

Triggers give immediacy; the sweep gives freshness. Both are needed.

## ⚠ The sweep is not yet safe to run at production scale

Open Finance permits **1,000 requests per minute across the entire platform**. One category
calculation costs roughly `1 + N` requests (accounts, then transactions per account) — about
4 for a typical user.

At 5,000 users the sweep issues ~20,000 requests. The consumer's `prefetch_count=10` bounds
*concurrency*, not *rate*, so the sweep drains as fast as Open Finance answers and will hold the
global quota at its ceiling for roughly twenty minutes — during which every live user request
is throttled.

**The sweep must be rate-budgeted before it runs against real volume.** Tracked as a P0 in
[`../production-readiness.md`](../production-readiness.md).

## Consequences

- `[DisallowConcurrentExecution]` prevents a slow run overlapping the next.
- `WithMisfireHandlingInstructionFireAndProceed` means a host that was down at 00:00 runs once
  on return rather than skipping the week.
- UTC is deliberate: the host time zone would make "Monday midnight" mean different instants on
  different machines and shift twice a year under DST.
- Two Gateway replicas would each run the sweep. See [0009](0009-single-gateway-instance.md).
