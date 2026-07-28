---
name: react-dev
description: 'Run and iterate on the Lessley React frontend. Use when: developing UI features, testing visual changes, debugging frontend behavior, or verifying that components render correctly.'
argument-hint: 'react-dev to work on the frontend'
user-invocable: true
---

# React Frontend Dev

**Dev mirrors production.** The integrated app is served by **Caddy at `https://localhost`**,
which serves the built SPA and reverse-proxies `/api` + `/hubs` to the gateway on one origin —
exactly like prod. The client talks **only** to Caddy; it never addresses the gateway or the
Personalization service directly.

## Primary flow — run the app like production

```bash
cd lessley-cd
.\manage.bat infra up     # brings up Caddy (+ SPA), Mongo, Rabbit, Loki, Grafana, mongo-express
.\manage.bat app build    # gateway + personalization
```

Open **https://localhost** (trust the local Caddy CA once — see `lessley-cd/README.md`).

The SPA is baked into the Caddy image, so after editing frontend code rebuild it:

```bash
cd lessley-cd && docker compose up -d --build caddy
```

## Fast UI-iteration shortcut (Vite HMR)

For tight visual/UX loops where rebuilding the image each time is too slow, run the Vite dev
server with hot-module reload. **This bypasses the Caddy edge** (plain http, separate origin),
so it's for UI work only — always confirm final behavior (auth cookies, CSRF, SignalR) on
`https://localhost` through Caddy.

```bash
cd lessley-frontend && npm run dev     # http://localhost:8000, HMR
```

Vite proxies `/api` + `/hubs` to `VITE_GATEWAY_PROXY_TARGET` (default `http://localhost:8001`,
the dev-published gateway), so login and API calls work same-origin during iteration.

## Ports (canonical scheme)

| Service | Dev (host) | Prod |
|---|---|---|
| App entry (Caddy) | `https://localhost` (443) | `https://<DOMAIN>` (443) |
| Gateway container | 5001 (published as **8001** for Swagger) | 5001 (internal only) |
| Personalization container | 5002 (published as **8002** for /docs) | 5002 (internal only) |
| Vite HMR shortcut | 8000 | n/a |

Container ports match dev/prod so the single `Caddyfile` (`reverse_proxy gateway:5001`) is
identical in both. The client never knows about Personalization.

## Prerequisites

- Run `npm install` in `lessley-frontend/` if `node_modules/` is missing.
- The Docker stack must be running (see `lessley-cd/README.md`).
