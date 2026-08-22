# Running Lessley — the three modes

There are three ways to run the stack. Modes 2 and 3 are **identical topology** (browser →
Caddy → gateway); Mode 1 is the local debug loop. Pick one:

| Mode | When | How the browser reaches the app |
|---|---|---|
| **1. Local debug** | Step through code / fast HMR | `http://localhost:8000` (Vite proxy stands in for Caddy) |
| **2. Dev docker-compose** | Run dev exactly like prod | `https://localhost` → Caddy → `gateway:5001` |
| **3. Production** | Real deployment | `https://<DOMAIN>` → Caddy → `gateway:5001` |

**Prereqs:** Docker Desktop, .NET 8 SDK, Node 20, Python 3.11+. Do the **First-time config**
(bottom of this file) once before anything else.

---

## Mode 1 — Local debug (services run on your machine)

Infra runs in Docker; the gateway, personalization, deal-optimizer and frontend run locally so
you can attach a debugger and get hot-reload. (Caddy is **not** used here — you hit Vite
directly.)

1. **Start infra only (no edge, no app containers):**
   ```bash
   cd lessley-cd
   docker compose up -d mongodb rabbitmq loki grafana mongo-express
   ```
2. **Gateway** — debug the `http` profile in VS/Rider, or:
   ```bash
   cd lessley-backend/Lessley.Gateway.Api && dotnet run
   ```
   Serves `http://localhost:8001` (Swagger at `/swagger`). Needs local secrets — see First-time config.
3. **Personalization**:
   ```bash
   cd lessley-backend/Lessley.Personalization
   .venv\Scripts\activate            # (create with: python -m venv .venv && pip install -r requirements.txt)
   uvicorn main:app --reload --port 8002
   ```
4. **deal-optimizer**:
   ```bash
   cd deal-optimizer
   .venv\Scripts\activate            # (create with: python -m venv .venv && pip install -e ".[service]")
   uvicorn deal_optimizer.api:app --reload --port 8003
   ```
5. **Frontend**:
   ```bash
   cd lessley-frontend && npm run dev
   ```
6. Open **http://localhost:8000**. The Vite proxy stands in for Caddy: it routes each
   edge-owned prefix to its own service (`/api/v1/insights` and `/api/v1/open-finance` to
   Personalization, `/api/v1/optimizer` to deal-optimizer) and everything else to the
   Gateway, so the browser sees one origin — no CORS. Cookies are non-Secure over http
   (normal for debug).

✅ *Works when:* login succeeds at `localhost:8000`, `localhost:8001/swagger`,
`localhost:8002/docs` and `localhost:8003/docs` all load.

---

## Mode 2 — Dev via docker-compose (same as production)

Everything runs in containers behind Caddy over HTTPS — byte-for-byte the prod topology, just
on `localhost` with Swagger/mongo-express enabled.

```bash
cd lessley-cd
.\manage.bat infra up      # mongo, rabbit, loki, grafana, mongo-express, CADDY
.\manage.bat app build     # gateway + personalization + deal-optimizer
```

1. **Trust the local cert once** (see First-time config), then open **https://localhost**.
2. After editing frontend code, rebuild the SPA (it's baked into the Caddy image):
   ```bash
   docker compose up -d --build caddy
   ```

Dev-only tooling: Swagger `http://localhost:8001/swagger`, FastAPI docs
`http://localhost:8002/docs` (personalization) and `http://localhost:8003/docs`
(deal-optimizer), mongo-express `http://localhost:8081`,
RabbitMQ UI `http://localhost:15672`, Grafana `http://localhost:3000`.

✅ *Works when:* `https://localhost` loads over HTTPS with no cert warning (CA trusted), login
sets `Secure; HttpOnly; SameSite=Strict` cookies, and notifications arrive (SignalR).

---

## Mode 3 — Production

Same as Mode 2 but with the prod compose and a real domain; **no** Swagger, **no** mongo-express.

1. On the prod host: `copy .env.template .env` and set **all** secrets, plus `DOMAIN`,
   `EDGE_API_KEY` and `CADDY_TLS_DIRECTIVE` (the pre-issued cert — see `CUSTOM-CA-CERT.md`).
   `ACME_EMAIL` is required by Caddy's global block but never used. Point DNS for `DOMAIN`
   at this host (ports 80/443 open).
2. Deploy:
   ```bash
   docker compose -f docker-compose.prod.yaml up -d --build
   ```
   Caddy serves the cert named by `CADDY_TLS_DIRECTIVE` — there is no ACME in this setup,
   in either environment. Open **https://<DOMAIN>**.

✅ *Works when:* `curl -skI https://<DOMAIN>/` shows a valid cert + HSTS; `GET /swagger` and
`/docs` return 404; Mongo/RabbitMQ are unreachable from the host (only Caddy publishes ports).

No public domain yet, deployed on a private/institution-only DNS name, or want Caddy to use a
CA or certificate you already have instead of Let's Encrypt? See
[`CUSTOM-CA-CERT.md`](./CUSTOM-CA-CERT.md).

---

## First-time config (what's missing out of the box)

1. **`lessley-cd/.env`** — `copy .env.template .env`, then fill `DB_*`, `RABBIT_*`, `JWT_KEY`
   (≥32 chars), `OpenFinanceConfig_*`, `BOOTSTRAP_*`, `GRAFANA_*`. For **dev** you can leave
   `DOMAIN`/`ACME_EMAIL` unset (defaults to `localhost`). For **prod** set `DOMAIN`, `ACME_EMAIL`,
   and `EDGE_API_KEY`.
2. **`lessley-backend/Lessley.Personalization/.env`** — `copy .env.template .env`; for debug use
   `localhost` connections and set `RabbitMQ_Enabled=True` (rabbit is up) or `False` (no broker).
3. **`lessley-frontend/.env`** — already present. These are read by `vite.config.ts` in
   Node to point the dev proxy, and are deliberately **not** `VITE_`-prefixed, so none of
   them reach the browser bundle (the SPA's own API calls are always relative):
   ```
   GATEWAY_PROXY_TARGET=http://localhost:8001
   PERSONALIZATION_PROXY_TARGET=http://localhost:8002
   OPTIMIZER_PROXY_TARGET=http://localhost:8003
   ```
4. **Mode 1 edge bypass.** Caddy is what authenticates callers and injects identity, so with
   no Caddy in front the services would reject every request. Enable the bypass — it needs
   *two* conditions each, so production cannot be opened by one stray flag:
   ```
   # Gateway
   ASPNETCORE_ENVIRONMENT=Development   Edge__AllowUnverifiedEdge=true
   # Personalization .env
   Environment=Development   Edge_AllowUnverified=True
   # deal-optimizer (same variable names as Personalization)
   Environment=Development   Edge_AllowUnverified=True
   ```
   Each logs a loud warning at startup while the bypass is active. If you see that warning
   anywhere but your own machine, something is badly misconfigured.

   Personalization and deal-optimizer still need to know who you are — they decode the email
   claim straight out of the Gateway's `access_token` cookie (the same cookie your browser
   already sends, Caddy or not). Log in through the Gateway first; nothing else to configure.
   deal-optimizer then reads that user's saved clubs to decide which deals you are eligible
   for, so a user with no clubs is correctly offered nothing.

5. **Local gateway secrets (Mode 1 only).** The committed `appsettings.json` ships these **blank**,
   so provide them via environment variables or `dotnet user-secrets` (values must match your
   `lessley-cd/.env`):
   ```
   ConnectionStrings__MongoDb=mongodb://<DB_USER>:<DB_PASS>@localhost:27017/<DB_NAME>?authSource=admin
   ConnectionStrings__RabbitMq=amqp://<RABBIT_USER>:<RABBIT_PASS>@localhost:5672/
   JwtConfig__Key=<32+ chars>   JwtConfig__Issuer=lessley-app   JwtConfig__Audience=lessley-users
   Bootstrap__Key=<key>   Bootstrap__Username / Password / Email
   OpenFinanceConfig__ClientId / ClientSecret
   ```
   (Modes 2 & 3 inject these from `.env` automatically — no per-service config needed.)
6. **Trust the dev HTTPS cert (Mode 2).** Caddy serves `https://localhost` with its own CA:
   ```powershell
   cd lessley-cd
   docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt .\caddy-local-ca.crt
   # double-click → Install Certificate → Local Machine → Trusted Root Certification Authorities
   ```
7. **Seed MongoDB reference data** into `mccs`/`stores`/`store_aliases`/`deals`/`clubs` — run
   `.\seed-db.ps1` (Windows) or `./seed-db.sh` (Linux) from `lessley-cd`.
   Options and the data layout: `README.md` → *Seeding MongoDB*.
8. **Create the first admin** — call the bootstrap endpoint with `Bootstrap__Key` once the gateway is up.

## Adding a client-facing service

The edge is the only public entry point, and it authenticates every request once. A new
service therefore needs no proxy code anywhere:

1. Add a `handle /api/v1/<prefix>/*` block to `lessley-cd/Caddyfile` with `forward_auth`
   to `gateway:5001 /api/auth/verify`, `copy_headers X-Auth-Email`, and
   `header_up X-Edge-Key {$EDGE_API_KEY}`. Put it **above** the general `/api/v1/*` block.
2. In the service, reject any request without `X-Edge-Key`, and read identity **only** from
   `X-Auth-Email`. Never accept an `email` parameter — that is the IDOR this design removes.
3. Add the service to `depends_on` for `caddy` in both compose files.

Two constraints worth knowing before you design around them:

- **Shared database.** Gateway, Personalization and deal-optimizer share the `lessley`
  database, reading the same `deals`, `stores`, `clubs` and `mccs` the scraping pipeline
  writes — one shape, no projected copies. Personalization and deal-optimizer read `users`
  **read-only**; every write goes through the Gateway or RabbitMQ. Keep that discipline.
- **Email is the cross-service key.** It is also what Open Finance keys accounts by, so
  changing a user's email would orphan their bank data. Email changes are unsupported.

> Deeper reference (architecture, per-service details, DB seeding commands): see `README.md`.
