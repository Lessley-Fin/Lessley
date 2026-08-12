# Lessley

A loyalty optimization platform: tracks spending, finds matching clubs, and sends
personalized deal notifications from Open Finance data.

**Running it:** [`lessley-cd/RUNNING.md`](lessley-cd/RUNNING.md) — three modes, first-time setup.
**Working on it:** [`instruction.md`](instruction.md) — architecture rules and conventions.

## Services

| Service | Language | Role |
|---|---|---|
| Caddy | — | The only public entry point: TLS, SPA, routing, edge authentication |
| Lessley.Gateway.Api | C# / .NET 8 | Auth authority, users, deals, notifications (SignalR) |
| Lessley.Personalization | Python / FastAPI | Spending insights and recommendations |
| Lessley.CategoriesEnricher | Python / FastAPI | LLM-powered transaction category enrichment |
| deal-optimizer | Python / FastAPI | Layered-DAG deal stacking engine — cheapest legal combination of deals for a cart |
| lessley-deals | Python | Scraper/normalizer worker that keeps the shared `deals`, `stores` and `clubs` collections fresh |

## How traffic flows

```
Client ──► Caddy ──┬──► Gateway          /api/v1/*  ·  /hubs/*  (SignalR)
                   ├──► Personalization  /api/v1/insights|open-finance/*
                   └──► deal-optimizer   /api/v1/optimizer/*

                        Gateway · Personalization · deal-optimizer
                                        └──► MongoDB (deals, stores, clubs, mccs)
```

Personalization and deal-optimizer are edge services, not things the Gateway proxies: Caddy
routes their prefixes straight to them. Both are `forward_auth`'d against the Gateway, which
is what lets them trust the injected identity.

## Shared collections

`deals`, `stores`, `clubs` and `mccs` are written by the scraping pipeline and read directly
by all three services — one shape, no projected copies. `deals_current` and `deal_versions`
hold the pipeline's own change history, not the read path.

Caddy authenticates every request once — validating the JWT cookie and CSRF token against
the Gateway — then injects the verified identity inward. Services never trust a
client-supplied identity, and the Gateway never calls Personalization over HTTP.

Recommendations (missed-savings, matching-clubs) are long-running, so they go over RabbitMQ
instead: Personalization publishes results back to the Gateway, which stores them as
notifications and pushes them to the client via SignalR.

## Secrets

Never commit `lessley-cd/.env` — use `.env.template` as the reference. If a secret is ever
committed, rotate it and purge it from history (`git filter-repo` / BFG). Production
secrets belong in your CI/CD secret store, not the repository.
