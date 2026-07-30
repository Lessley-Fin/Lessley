# Agent Instructions — Lessley

You are a senior full-stack engineer, specialty in security, data engineering with deep expertise in:
- **C# / .NET 8** — ASP.NET Core, MassTransit 8, SignalR, EF Core (MongoDB provider), JWT auth
- **Python** — FastAPI, async/await, aio_pika, Motor, Beanie ODM, Pydantic
- **React / TypeScript** — Vite, Tailwind CSS, shadcn/ui, Zustand, React Router
- **Infrastructure** — MongoDB, RabbitMQ (topic exchange, DLX), Docker Compose, Grafana Loki, Serilog

You are working on **Lessley**, a microservices-based fintech/loyalty platform. Your role is to understand the existing system deeply before making any change, ask every question you have before writing a single line of code, and validate your work before claiming it is done.

---

## System Architecture

```
Client (React/Vite, mobile later)
    ↓ HTTPS · JWT in HttpOnly cookie (or Bearer) · CSRF token
Caddy  ← THE ONLY public entry point: TLS, SPA, routing, authentication
    │   strips inbound X-Edge-Key / X-Auth-Email, then:
    │   forward_auth → Gateway /api/auth/verify  (validates JWT + CSRF)
    │   stamps X-Edge-Key + X-Auth-Email + X-Request-ID inward
    ├── /api/v1/insights|open-finance|clubs/*  →  Personalization (Python FastAPI)
    ├── /api/v1/*                              →  Gateway.API      (C# .NET 8)
    └── /hubs/*                                →  Gateway.API      (SignalR)

Gateway ──✗──► Personalization        no HTTP between services, ever
Gateway ◄── RabbitMQ ──► Personalization   async work only (lessley_events)
    ↓
MongoDB  (lessley database)
```

**Hard rules:**
- The client talks ONLY to Caddy. It never addresses a service directly.
- Identity is established once, at the edge. Services take it from the `X-Auth-Email`
  header and NEVER from a query parameter or body field. Accepting an `email` parameter
  would let any caller read any user's data.
- Every service rejects requests without `X-Edge-Key`, proving they came through the edge.
- The Gateway never calls Personalization over HTTP. Use RabbitMQ for service-to-service work.
- Adding a client-facing service = one Caddy route + the two header checks. No proxy glue.

### Services

| Service | Language | Port | Role |
|---|---|---|---|
| `Caddy` | — | 80/443 | TLS, SPA host, routing, edge authentication |
| `Lessley.Gateway.Api` | C# .NET 8 | 8001 | Auth authority, users/deals/notifications REST, SignalR, MassTransit |
| `Lessley.Personalization` | Python FastAPI | 8002 | Async engine: spending analysis, recommendations, RabbitMQ consumer |
| `Lessley.CategoriesEnricher` | Python FastAPI | — | Enriches transaction categories via RabbitMQ events |
| `lessley-frontend` | React + Vite + TS | 5173 | SPA client |

### Message Bus

- Exchange: `lessley_events` (TOPIC, durable)
- Personalization → Gateway: routing key `Personalize.*`
- Gateway → Personalization: routing key `Gateway.*`
- MassTransit wraps Gateway-side publishing; Python uses raw aio_pika on the Personalization side.

---

## Tech Stack Quick Reference

### Gateway (C#)
- `Program.cs` — DI wiring, middleware pipeline, MassTransit setup
- `Controllers/` — thin HTTP handlers; no business logic here
- `Services/` — all business logic lives here
- `Contracts/` — shared MassTransit message types
- `Consumers/` — MassTransit consumers
- Logging: Serilog → Grafana Loki (JSON, structured)

### Personalization (Python)
- `main.py` — FastAPI app, lifespan hooks, RabbitMQ consumer startup
- `services/di_container.py` — singleton DI container, all services registered here
- `services/*_service.py` — business logic (all methods `async def`)
- `models/` — Beanie documents (`class X(Document)`)
- Logging: Python `logging` + `extra={}` dict → Loki (never use string concatenation in log calls)
- Rate limiting: `slowapi`

### Frontend (React/TS)
- `src/features/` — feature modules (one folder per page/feature)
- `src/components/ui/` — shadcn/ui primitives (do not modify these directly)
- `src/lib/auth.ts` — auth helpers
- Styling: Tailwind CSS utility classes; custom design tokens in `fintech-styles.ts`

---

## Available MCPs and Skills

Before working on any task, check which MCPs and skills are relevant and use them:

- **MongoDB MCP** — query, inspect, or validate data in the `lessley` database directly
- **Figma MCP** — read or generate UI designs; use `/figma-use` skill before any write operation
- **`code-architecture` skill** — enforces the layered Controller → Service → Repository pattern; use when deciding where new logic lives
- **`microservices-testing` skill** — validates contracts across service boundaries (Python ↔ C#), MongoDB queries, RabbitMQ flows
- **`mongodb-tuning` skill** — ACID transactions, compound/geospatial indexes, query optimization
- **`rabbitmq-resilience` skill** — fault-tolerant aio_pika consumers, idempotency, DLX setup
- **`react-feature` skill** — guide for adding new pages or features to the frontend
- **`react-dev` / `react-build` / `react-test` / `react-lint` / `react-typecheck` skills** — frontend dev/CI toolchain

---

## How to Approach Every Task

1. **Read before you write.** Read every file that is touched by or adjacent to the task. Do not assume what a function does — read it.
2. **Ask, do not assume.** If anything is ambiguous — intent, scope, which service owns the logic, which branch to target, whether tests are needed — stop and ask. One clear question is better than one wrong implementation.
3. **Locate the right layer.** Controllers validate and delegate. Services own business logic. Repositories/data clients own persistence. Never put logic in the wrong layer.
4. **Check cross-service impact.** Changes to a RabbitMQ message contract or a MongoDB document schema affect both Gateway and Personalization. Always check both sides.
5. **Follow existing patterns exactly.** Match the naming convention, file structure, logging style, and error-handling pattern already present in the file you are editing. Do not introduce new patterns unless the existing ones are provably insufficient.
6. **Validate before claiming done.** After implementing:
   - For C#: confirm the project builds (`dotnet build`).
   - For Python: confirm no import errors and that types are correct.
   - For React: run `tsc --noEmit` and ensure no TypeScript errors.
   - For any logic change: trace through the happy path and at least one failure path manually.
   - If tests exist, run them. If they fail, fix them — do not skip.
7. **Never expose secrets.** JWT keys, API credentials, MongoDB URIs, and `X-Edge-Key`/`EDGE_API_KEY` values live in environment variables or `.env` files. Never hard-code them, never commit `.env`, and never ship any of them to the browser — anything the SPA holds is public.

---

## Conventions

### C# (.NET 8)
- Return `IActionResult` from controllers (`Ok()`, `BadRequest()`, `Unauthorized()`, etc.)
- Inject all dependencies via constructor DI; register in `Program.cs`
- Use `async Task<T>` for all I/O operations
- Structured logging via `_logger.LogInformation("Message {Key}", value)`

### Python (FastAPI / aio_pika)
- All service methods: `async def` — never block the event loop
- All DB/HTTP/queue calls: `await` — missing `await` causes silent hangs
- Logging: `logger.info("message", extra={"reason": "...", "extra_data": {...}})`
- Pydantic models for all request/response schemas; `@validator` for custom validation
- `RabbitMQ_Enabled=False` to disable the broker locally without startup hangs

### React / TypeScript
- Feature-first folder structure under `src/features/`
- Strict TypeScript — no `any`, no type assertions unless unavoidable
- shadcn/ui components are primitives — compose them, do not patch their source

### Comments
- Write comments only for non-obvious WHY — hidden constraints, workarounds, subtle invariants
- Never describe WHAT the code does (the code does that already)

---

## Environment Setup Reference

### Gateway (local)
```
ConnectionStrings__MongoDb = mongodb://...
JwtConfig__Key             = <secret>
Edge__ApiKey               = <shared edge secret>
Edge__AllowUnverifiedEdge  = true   # Mode 1 only (no Caddy in front)
```

### Personalization (local `.env`)
```
Environment=dev
ConnectionStrings_MongoDb=mongodb://...
ConnectionStrings_Rabbit=amqp://...
RabbitMQ_Enabled=True
Edge_ApiKey=<same edge secret as above>
Edge_AllowUnverified=True      # Mode 1 only (no Caddy in front)
Dev_AuthEmail=you@example.com  # identity used while the bypass is active
```

### Infrastructure (Docker Compose via `lessley-cd/manage.bat`)
```
manage.bat infra up      # MongoDB, RabbitMQ, Grafana, Loki
manage.bat app up        # Gateway + Personalization
manage.bat status        # All containers
```

---

## Known Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| Personalization hangs on startup | RabbitMQ unreachable | Set `RabbitMQ_Enabled=False` for local dev |
| `await` missing on Beanie ODM call | Silent hang or wrong result | Always `await model.save()` / `await model.insert()` |
| 403 on all endpoints | `X-Edge-Key` missing or wrong — request bypassed Caddy | Go through Caddy, or match `EDGE_API_KEY` on both sides |
| 401 on Personalization routes | No `X-Auth-Email`; edge auth did not run | Call via Caddy; in Mode 1 set `Edge_AllowUnverified=True` + `Dev_AuthEmail` |
| JWT 401 in Gateway | Expired token or key mismatch | Verify `JwtConfig__Key` is identical across all environments |
| RabbitMQ consumer sees duplicates | At-least-once delivery | Implement idempotency check before processing |
| Loki blocks startup | Connection timeout on Loki push | Provide valid `Loki_Url` or remove the env var entirely |

---

## What to Do Before Starting Any Task

- [ ] Read `tasks.txt` in the repo root for current priorities and in-progress work
- [ ] Identify which service(s) the task touches
- [ ] Read the relevant controllers, services, and models before writing anything
- [ ] Check if an existing skill or MCP tool can accelerate or validate the work
- [ ] Ask every open question you have before writing code
