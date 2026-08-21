# 0004 — An empty calculation never clears tags

**Status:** Accepted — reverses an earlier decision

## Context

When the publish moved to the command handler, it was made unconditional: an empty result would
publish an empty tag list, clearing stale tags. The motivation was real — a user who disconnects
their bank should stop being tagged rather than keep receiving deal notifications for categories
they no longer spend in.

Two later facts made that dangerous.

1. Open Finance answers with `[]` both for a user with no bank linked **and** for one whose data
   it cannot produce right now. From Personalization the two are indistinguishable.
2. The weekly sweep ([0003](0003-weekly-sweep-instead-of-a-backfill.md)) asks for every user at
   once.

Together: one bad Monday clears the tags of the entire user base. Everyone silently drops out
of every notification group. Nothing errors, nothing looks broken, and the only symptom is an
app that quietly stops notifying anyone.

## Decision

Publish only when the calculation produced tags. When it produced none:

- if the user currently has tags, log a warning and **leave them in place**;
- if the user has none, do nothing.

A failed fetch raises before the publish, so exceptions were never the risk. The risk was a
successful-looking empty answer.

## Consequences

- Retaining a stale tag costs one irrelevant notification. Clearing wrongly costs all of them.
  The asymmetry decides it.
- A genuinely disconnected bank keeps its categories indefinitely. **Clearing should be driven
  by an explicit unlink signal, not by an absence we inferred** — that signal does not exist yet
  and is tracked in [`../production-readiness.md`](../production-readiness.md).
- The warning log is the detection surface. A spike in it means Open Finance is returning empty
  for users who should have data.
