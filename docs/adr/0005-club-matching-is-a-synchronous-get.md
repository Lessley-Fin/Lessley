# 0005 — Club matching is a synchronous GET

**Status:** Accepted

## Context

Club matching used to be fire-and-forget: the client POSTed a trigger, the Gateway published
`Gateway.calculate_matching_clubs`, Personalization computed and published
`Personalize.matching_clubs_calculated`, the Gateway stored the result as a "calc" notification,
and the client polled `GET /User/recommendations` to collect it.

That is a great deal of machinery for an answer that takes no time to produce.

## Decision

`GET /insights/matching-clubs`, answered synchronously.

## Why it can be synchronous

`calculate_matching_clubs` reads the user's stored tags and scores them against clubs and stores
already held in memory by `ReferenceDataRepository` — loaded once at startup and refreshed on a
timer ([0007](0007-reference-data-refreshes-on-a-timer.md)). No Open Finance call, no transaction
fetch, no database scan. It is pure CPU over in-memory dictionaries.

## Why it lives under `/insights`

The edge forwards only `/api/v1/insights/*` and `/api/v1/open-finance/*` to Personalization, and
`lessley-cd/Caddyfile` warns against adding a route without `forward_auth`. A client-facing
endpoint anywhere else is simply unreachable, with nothing in this service's logs to explain why.

## Consequences

Deleted along with it: both recommendation commands and their contracts, the two result
consumers and their receive endpoints, `POST /User/recommendations/*`,
`GET /User/recommendations`, `CheckUserHasCategories`, and the entire `"calc"` notification type
(`SendCalcNotificationAsync`, `GetLatestCalcGroupedAsync`).

On the client, "recalculate" became a `refetch` rather than a POST followed by a hopeful cache
invalidation.
