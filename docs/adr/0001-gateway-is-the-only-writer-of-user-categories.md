# 0001 — The Gateway is the only writer of user categories

**Status:** Accepted

## Context

Personalization calculates a user's spending categories. The result is stored on the user
document in Mongo as `ApplicationUser.Tags`, where the Gateway reads it to fan out
notifications and the client reads it to render settings.

The obvious arrangement is for the service that computes a value to store it. That was the
proposal: let Personalization write `Tags` directly and be the single source of truth.

## Decision

Personalization is the only **calculator**. The Gateway is the only **writer**. The computed
tags travel back over RabbitMQ as `Personalize.user_tag_assigned`, and the Gateway persists
them.

## Why not let Personalization write

`users` is an ASP.NET Identity aggregate persisted through EF Core with the MongoDB provider.
Identity's `UserStore.UpdateAsync` calls `Context.Update(user)`, which marks the **whole
entity** modified — so every Identity write replays `Tags` from the snapshot it read.

A concurrent `$set` from Python would be silently overwritten:

```
Gateway:  FindByEmailAsync ──────────────────────▶ UpdateAsync (writes Tags as read: OLD)
Python:          └── $set {Tags: NEW} ──┘
                                                    NEW is gone, no error anywhere
```

The concurrency stamp does not save it: a targeted `$set` from outside Identity does not
change `ConcurrencyStamp`, so the stale write passes validation. Every login, token refresh,
security-stamp update and settings save is a potential clobber.

The instinct behind the original proposal — one and only one writer — is right. The Gateway
already *is* that writer, and it cannot hand the role over while `MutedTags`, `Clubs`,
`MatchingScore` and the Identity fields live in the same document.

## Consequences

- `UserRepository` in Personalization is read-only by construction, and says so.
- The write is asynchronous relative to the calculation. A client that reads categories and
  immediately depends on them being stored can observe the gap; see [0002](0002-category-reads-have-no-side-effects.md).
- If this data ever needs to be owned by Personalization, the answer is a separate collection
  it owns outright — not a second writer on `users`.
