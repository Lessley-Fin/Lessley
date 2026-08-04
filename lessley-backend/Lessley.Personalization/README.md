# Lessley Personalization

Analyzes Open Finance transaction data to produce spending categories, top accounts and
stores, missed-savings opportunities, and loyalty-club matches.

## Trust model — read before adding a route

This service performs **no user-level authorization of its own**. It acts on whatever
identity it is handed, so two rules are load-bearing:

- Identity comes from the **`X-Auth-Email` header**, injected by the edge (Caddy) after it
  validates the caller's JWT. Take it via `dependencies.auth.authenticated_email`.
- **Never accept an `email` parameter.** Doing so lets any caller read any user's bank data.

`EdgeAuthMiddleware` additionally rejects anything without `X-Edge-Key`, so requests that
bypassed the edge never reach a route. See [`../../instruction.md`](../../instruction.md).

## Endpoints

Reached by the client through Caddy at `/api/v1/...`; the prefix is stripped before it
arrives here.

| Route | Purpose |
|---|---|
| `GET /insights/categories\|top-accounts\|top-stores` | Spending analysis |
| `GET /open-finance/accounts\|transactions\|transactions/by-account` | Raw Open Finance data |
| `POST /clubs/categories` | Club MCC distribution |
| `POST /recommendations/missed-savings\|matching-clubs` | Not edge-exposed — driven by RabbitMQ |

Query parameters: `days` (1–365, default 90), `time_filter` (default true), `use_mock`
(default false).

## Run locally

```bash
copy .env.template .env          # then fill it in
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

Without Caddy in front, nothing injects an identity — set `Environment=Development` and
`Edge_AllowUnverified=True` in `.env`, or every user-scoped route returns 401. Identity
while the bypass is active is decoded straight from the Gateway's `access_token` cookie, so
log in through the Gateway first so that cookie reaches this service. Full setup:
[`../../lessley-cd/RUNNING.md`](../../lessley-cd/RUNNING.md).

Tests need the extra dev dependencies:
`pip install -r requirements-dev.txt && pytest`

> Regenerating `requirements.txt` in PowerShell: use
> `pip freeze | Out-File -Encoding utf8 requirements.txt`. A plain `>` redirect writes
> UTF-16, which breaks `pip install` in the Docker build.

## Configuration

| Variable | Description |
|---|---|
| `Environment` | `Development` enables `/docs` and permits the edge bypass |
| `ConnectionStrings_MongoDb` / `_Rabbit` | Infrastructure connection strings |
| `RabbitMQ_Enabled` | `False` to start without a broker |
| `OpenFinanceConfig_BaseUrl` / `_ClientId` / `_ClientSecret` | Open Finance credentials |
| `Edge_ApiKey` | Shared secret the edge presents as `X-Edge-Key` |
| `Edge_AllowUnverified` | Mode 1 bypass; identity comes from decoding `access_token`, Development only |
| `Cors_AllowOrigins`, `Loki_Url` | Optional |
