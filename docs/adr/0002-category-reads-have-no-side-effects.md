# 0002 — Category reads have no side effects; writes are command-triggered

**Status:** Accepted

## Context

`GET /insights/categories` used to publish the derived tags as a side effect. Opening the
insights page therefore rewrote your stored profile. That was also, accidentally, the only
thing keeping anyone's tags current.

Two problems followed. A read that writes is a race: the HTTP response returned immediately
while the write travelled the bus behind it, so a client could act on categories the database
did not yet have. And the write only happened if a human happened to open a page.

## Decision

`calculate_user_categories_async` computes and returns. Nothing else.

The publish moved up into the RabbitMQ command handler (`main.py`), so the only caller that
turns a calculation into a write is the one that arrived over the bus. Writes are triggered
by `Gateway.calculate_user_categories`, published on:

- **registration** — Open Finance identifies people by email, so a new account may already
  have a linked bank and full history behind it;
- **starting a bank journey** — inside `OpenFinanceService.InitiateConnectionJourney`, so both
  controllers that call it are covered and a third cannot forget;
- **a match-level change** — and only that. `MatchingScore` is the single user field the
  calculation reads. Muted tags are applied at fanout and display time, and clubs only affect
  missed-savings; recalculating on those spends an Open Finance round trip to arrive at the
  same answer.

Plus the weekly sweep — see [0003](0003-weekly-sweep-instead-of-a-backfill.md).

## Trade-offs accepted

**The bank-journey trigger fires early.** It runs when the user *starts* the flow, not when
consent lands. For a user who already holds Open Finance consent this is exact; for a genuinely
new link the data arrives afterwards and the next trigger collects it. The alternative is a
provider callback the Gateway does not have.

**Publishing is best-effort.** `TriggerCalculateUserCategoriesAsync` swallows publish failures
and logs a warning. Every caller is finishing something a user is waiting on — a signup, a bank
journey, a settings save — and none should fail because the broker is unreachable. A dropped
recalculation is recoverable: stored categories stay valid, and the next trigger or the sweep
recomputes them.

**The client learns late.** After the write, the Gateway pushes `CategoriesUpdated` over
SignalR — no stored notification, no toast, because the user did not ask for the sweep and
should not be interrupted by it. Sending to zero connections is the normal case (the sweep runs
at midnight; the bank journey navigates the browser away), so the client also invalidates on
reconnect.
