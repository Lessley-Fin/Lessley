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

## How traffic flows

```
Client ──► Caddy ──┬──► Gateway          /api/v1/*
                   ├──► Personalization  /api/v1/insights|open-finance|clubs/*
                   └──► Gateway          /hubs/*  (SignalR)
```

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
