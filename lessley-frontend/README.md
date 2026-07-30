# Lessley Frontend

Mobile-first React SPA — Vite, TypeScript, Tailwind, shadcn/ui, Zustand, React Query.

## Run

```bash
npm install
copy .env.example .env
npm run dev          # http://localhost:8000
```

For the full local setup (the gateway and personalization services this talks to), see
[`../lessley-cd/RUNNING.md`](../lessley-cd/RUNNING.md) — Mode 1.

| Script | Purpose |
|---|---|
| `npm run dev` | Dev server on 8000, proxying `/api/v1` and `/hubs` |
| `npm run build` | Production bundle (baked into the Caddy image) |
| `npm run test` / `test:run` | Vitest, watch / single-run |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm run lint` | ESLint |

## Structure

`src/features/` is the unit of organisation — one folder per feature (`auth`, `insights`,
`deal-finder`, `notifications`, `admin`, `settings`, …), each with its own `api.ts`.
Shared primitives live in `src/components/ui/` (shadcn — compose these, don't edit them)
and helpers in `src/lib/`.

## API calls

Every request is **relative** (`/api/v1/...`), because the SPA is always served from the
same origin as the API — by Caddy in production, by the Vite proxy in dev. There is no
gateway URL to configure, and no CORS. `src/lib/api-client.ts` adds the CSRF header and
retries once through a cookie refresh on 401.
