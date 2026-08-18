# 0009 — A single Gateway instance is a design constraint

**Status:** Accepted — deliberate, and load-bearing

## Context

Three pieces of the Gateway assume exactly one process is running.

## The assumptions

**SignalR has no backplane.** `Program.cs` calls `AddSignalR()` with no Redis or Azure backplane,
and `ConnectionManager` is an in-process `ConcurrentDictionary`. With two replicas,
`GetConnections(email)` on instance A returns nothing for a user connected to instance B, and
`Clients.Group(tag)` does not cross the process boundary. Every notification path silently
delivers to a subset.

**The weekly sweep is not clustered.** Quartz runs in-memory, so each replica fires
`RecalculateUserCategoriesJob` independently — doubling Open Finance load against a quota that is
already the platform's tightest constraint ([0003](0003-weekly-sweep-instead-of-a-backfill.md)).

**Notification fanout reads live connections.** `SendToUserAsync` and the `CategoriesUpdated`
push both enumerate `_connectionManager`, which only knows about this process.

## Decision

Run one Gateway instance. Document the constraint rather than build for a scale that is not
planned.

At the target of 1,000–5,000 users this is comfortable: the constraint is Open Finance's global
quota, not Gateway CPU.

## What to do when this changes

In order of urgency, none of which is large:

1. A SignalR backplane (Redis) — restores group sends and per-user sends across replicas.
2. Replace `ConnectionManager` with the backplane's own presence tracking, or accept that it
   only answers "is this user connected *here*".
3. Quartz clustering (it supports a database job store), or move the sweep to a single dedicated
   worker.

**The failure mode is silence, not an error.** Nothing crashes when a second replica appears;
notifications simply reach fewer people and the sweep runs twice. That is why this is written
down.
