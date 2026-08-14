# Lessley CD

Docker Compose environment: `manage.bat` shortcuts and database seeding.

> **To run the stack, see [RUNNING.md](RUNNING.md)** — three modes plus first-time config.

## Dev mirrors production

Dev and prod run the same topology and the **same Caddyfile**. In both, the browser talks
only to Caddy, which terminates TLS, serves the SPA, and routes `/api/v1` to whichever
service owns the prefix over a private network. Container ports are identical (gateway
`5001`, personalization `5002`, deal-optimizer `5003`), so the one Caddyfile works unchanged.

| | Dev | Prod |
|---|---|---|
| App URL | `https://localhost` (internal-CA cert) | `https://<DOMAIN>` (pre-issued cert, see `CUSTOM-CA-CERT.md`) |
| Swagger, FastAPI `/docs` | on | off |
| mongo-express | included | removed |
| HSTS | `max-age=0` | strong default |
| Host-published ports | services exposed for tooling | Caddy only |
| Auth emails | written to the gateway log | sent over SMTP (required) |

## Auth emails (verification / reset / sign-in codes)

Registration verifies the email address before the account is created, password reset is
code-based, and there is a passwordless "sign in with a code" path. All three need to deliver
a six-digit code.

**In dev nothing is configured by default** — the code is written to the gateway's log instead
of being sent:

```
docker compose logs -f gateway     # look for "EMAIL NOT SENT"
```

To exercise real delivery locally, set `SMTP_ENABLED=true` plus the `SMTP_*` vars in `.env`
(a Mailtrap inbox, or a MailHog container on port 1025 with no credentials).

**In prod SMTP is mandatory**: `docker-compose.prod.yaml` hardcodes `EmailConfig__Enabled=true`,
and the Gateway throws at startup if it is false in Production — the alternative is an app where
nobody can register or recover an account and nothing looks broken until users complain. See the
SMTP block in `.env.template` (Gmail needs an App Password, not the account password).

## `manage.bat`

Splits application from infrastructure, so `app down` leaves MongoDB and RabbitMQ running
(unlike `docker compose down`, which takes everything with it).

| Command | Description |
|---|---|
| `.\manage.bat help` | Show help menu |
| `.\manage.bat status` | Status of all containers |
| `.\manage.bat infra up\|down\|status` | Infra + Caddy edge (MongoDB, RabbitMQ, Loki, Grafana) |
| `.\manage.bat app up\|build\|down\|status` | Gateway + Personalization + deal-optimizer (`build` recompiles first) |

After editing the SPA, rebuild the edge image that carries it:
`docker compose up -d --build caddy`.

## Seeding MongoDB

Reference data lives in `main/resources/`. From this folder, for each collection:

#### clubs
```bash
docker cp ..\main\resources\clubs.json mongodb:/tmp/clubs.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection clubs --file /tmp/clubs.json --jsonArray --username guest --password guest --authenticationDatabase admin
```
#### deals
```bash
docker cp ..\main\resources\deals.json mongodb:/tmp/deals.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection deals --file /tmp/deals.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

#### mccs
```bash
docker cp ..\main\resources\mccs.json mongodb:/tmp/mccs.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection mccs --file /tmp/mccs.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

#### stores
```bash
docker cp ..\main\resources\stores.json mongodb:/tmp/stores.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection stores --file /tmp/stores.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

Those four collections — `clubs`, `deals`, `mccs`, `stores` — are the only ones this data
goes into. The scraping pipeline writes the same four, and the Gateway, Personalization and
deal-optimizer all read them directly; there is no projected copy in between.

> **Note on `_id`.** `mongoimport` gives every row a generated ObjectId `_id` and leaves the
> business key in `id`, whereas the pipeline writes the business key *as* `_id`. All three
> services read either shape, but the pipeline upserts on `_id`, so a scrape run against
> imported rows inserts duplicates rather than updating them.
