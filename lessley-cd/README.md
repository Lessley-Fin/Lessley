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

Reference data lives in `../lessley-deals/data/seed/`, one `<collection>.json` array per
collection. Two scripts import it — `seed-db.sh` (Linux/macOS/Git Bash) and `seed-db.ps1`
(Windows PowerShell). They do the same thing and take the same options:

```bash
./seed-db.sh                                    # Linux
```
```powershell
.\seed-db.ps1                                   # Windows
```

With no arguments they seed `users`, `mccs`, `clubs`, `stores`, `store_aliases` and
`deals` into the `mongodb` container, reading the credentials and database name from `.env`
(`DB_USER` / `DB_PASS` / `DB_NAME`). Anything absent from the seed directory is
skipped with a note — `users.json` is not in the repo, so on a normal checkout the
`users` collection is left to the Gateway's own bootstrap seeder.

| Option (sh) | Option (ps1) | Default | Meaning |
|---|---|---|---|
| `-u`, `--username` | `-Username` | `DB_USER` from `.env`, else `guest` | Mongo user |
| `-p`, `--password` | `-Password` | `DB_PASS` from `.env`, else `guest` | Mongo password |
| `-d`, `--database` | `-Database` | `DB_NAME` from `.env`, else `lessley` | Target database |
| `-f`, `--path` | `-Path` | `../lessley-deals/data/seed` | Directory of `<collection>.json` |
| `-c`, `--container` | `-Container` | `mongodb` | Running Mongo container |
| `--collections` | `-Collections` | all six | Comma-separated subset |
| `--drop` | `-Drop` | off | Drop each collection first (destructive) |
| `--insert` | `-Insert` | off | Plain inserts instead of upserts |
| `--env-file` | `-EnvFile` | `./.env` | Where the defaults come from |
| `--dry-run` | `-DryRun` | off | Print the commands, change nothing |

```bash
./seed-db.sh -u admin -p s3cret -f /srv/lessley-dump          # other credentials + data
./seed-db.sh --collections stores,deals --drop                # re-import two, from scratch
```
```powershell
.\seed-db.ps1 -Username admin -Password s3cret -Path D:\dumps\lessley
.\seed-db.ps1 -Collections stores,deals -Drop
```

Re-running is safe: rows are upserted on their business key (`id`, or `_id` for `users`),
so an existing row is updated rather than duplicated.

Those collections — `users`, `clubs`, `deals`, `mccs`, `stores`, `store_aliases` — are the
only ones this data goes into. The scraping pipeline writes the same ones, and the Gateway,
Personalization and deal-optimizer all read them directly; there is no projected copy in
between. `store_aliases` is what the pipeline's match stage resolves a scraped name against,
so seeding `stores` without it leaves matching working off canonical names alone.

> **Note on `_id`.** `mongoimport` gives every row a generated ObjectId `_id` and leaves the
> business key in `id`, whereas the pipeline writes the business key *as* `_id`. All three
> services read either shape, but the pipeline upserts on `_id`, so a scrape run against
> imported rows inserts duplicates rather than updating them.
