# Containerization and Environment Setup

## Overview

The deals system runs alongside the existing Lessley infrastructure -- MongoDB, RabbitMQ, and the Gateway service -- via Docker Compose profiles. This design is strictly additive: existing services and their configuration remain untouched. The deals containers only start when explicitly requested through profile flags, ensuring zero impact on the core platform during normal operation.

## Dockerfile (Multi-Stage Build)

The Dockerfile uses a multi-stage build with four targets, each serving a distinct purpose:

```dockerfile
# Stage 1: base -- HTTP scrapers only
FROM python:3.12-slim AS base
# Install production dependencies, copy source code
# Minimal image sufficient for running the pipeline with HTTP-based scrapers

# Stage 2: test -- adds pytest, mypy, ruff
FROM base AS test
# Install dev/test dependencies on top of base
# Used for linting, type checking, and running the test suite

# Stage 3: browser -- adds Playwright + Chromium
FROM base AS browser
# Install Playwright and a headless Chromium browser
# For scrapers that require JavaScript rendering

# Stage 4: api -- adds FastAPI + Uvicorn (future)
FROM base AS api
# For future REST API exposure of deals data
```

### Why Multi-Stage

- **Smaller images.** The `base` target contains only what is needed to run the HTTP pipeline. Dev tools (pytest, mypy, ruff) and heavy browser dependencies (Chromium) are excluded from production images.
- **Security.** No development tooling, test frameworks, or debugging utilities ship in the production image. The attack surface is limited to runtime dependencies.
- **Different targets for different use cases.** CI builds the `test` target to run linting and tests. The pipeline runs from `base`. Browser-dependent scrapers build from `browser`. Each target includes exactly what it needs and nothing more.

## Docker Compose Integration

The following services are added to the existing `docker-compose.yaml`. This is purely additive -- existing service definitions (rabbitmq, mongodb, mongo-express, gateway) are not modified.

```yaml
deals-pipeline:
  image: lessley/deals:dev
  build:
    context: ../lessley-deals
    target: base
  profiles: ["tools"]
  volumes:
    - deals_data:/app/data
  environment:
    - DEALS_LOG_LEVEL=INFO
    - DEALS_AUTO_MATCH_THRESHOLD=0.90
    - DEALS_REVIEW_THRESHOLD=0.50
  command: ["python", "-m", "lessley_deals.cli.main", "scrape", "--all"]

deals-review:
  image: lessley/deals:dev
  profiles: ["tools"]
  volumes:
    - deals_data:/app/data
  stdin_open: true
  tty: true
  command: ["python", "-m", "lessley_deals.cli.main", "review"]

deals-test:
  image: lessley/deals:test
  build:
    context: ../lessley-deals
    target: test
  profiles: ["test"]
  volumes:
    - deals_test_data:/app/test_data
```

Key points:

- `deals-pipeline` and `deals-review` share the same `lessley/deals:dev` image but run different commands.
- `deals-review` sets `stdin_open: true` and `tty: true` to support the interactive review TUI.
- `deals-test` builds from the `test` target, which includes pytest, mypy, and ruff.
- All deals services use profiles, so they never start with a bare `docker compose up`.

## Docker Compose Profiles

Profiles keep the deals system isolated from the default service set:

| Profile | Services | Purpose |
|---------|----------|---------|
| _(default, no profile)_ | rabbitmq, mongodb, mongo-express, gateway | Core platform -- unchanged |
| `tools` | deals-pipeline, deals-review | On-demand deals operations |
| `test` | deals-test | CI and local testing |

Usage:

```bash
# Start only core infrastructure (deals services do NOT start)
docker compose up

# Run the deals pipeline
docker compose --profile tools run deals-pipeline

# Run the interactive review session
docker compose --profile tools run --rm deals-review

# Run the test suite
docker compose --profile test run --rm deals-test
```

## Volume Strategy

| Volume | Contents | Lifecycle |
|--------|----------|-----------|
| `deals_data` | Persistent JSON files: stores, aliases, deals, reviews, raw scraped data | Persistent across runs |
| `deals_test_data` | Isolated test data | Ephemeral, safe to remove |
| `rabbitmq_data` | RabbitMQ state (existing) | Untouched |
| `mongodb_data` | MongoDB state (existing) | Untouched |

The `deals_data` volume is shared between `deals-pipeline` and `deals-review` so the review process can access the latest scraped data. Test data is kept in a separate volume to prevent test runs from corrupting production data.

## Environment Variables

The following variables are added to `.env.template`:

```
DEALS_LOG_LEVEL=INFO
DEALS_AUTO_MATCH_THRESHOLD=0.90
DEALS_REVIEW_THRESHOLD=0.50
# Source-specific credentials (as needed)
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DEALS_LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `DEALS_AUTO_MATCH_THRESHOLD` | `0.90` | Confidence threshold above which store matches are accepted automatically |
| `DEALS_REVIEW_THRESHOLD` | `0.50` | Confidence threshold below which matches are flagged for manual review |

Source-specific credentials (API keys, tokens) are added to `.env.template` as needed when new scrapers are introduced.

## Running Commands

Common operations:

```bash
# Run the full pipeline (scrape all sources)
docker compose --profile tools run --rm deals-pipeline

# Scrape a specific source
docker compose --profile tools run --rm deals-pipeline \
  python -m lessley_deals.cli.main scrape --source shufersal

# Interactive review session
docker compose --profile tools run --rm deals-review

# View review statistics
docker compose --profile tools run --rm deals-pipeline \
  python -m lessley_deals.cli.main review-stats

# List known stores
docker compose --profile tools run --rm deals-pipeline \
  python -m lessley_deals.cli.main list-stores

# Run the test suite
docker compose --profile test run --rm deals-test
```

The `--rm` flag removes the container after it exits, keeping the environment clean. For the interactive review session, the container attaches to stdin/stdout so the TUI works as expected.

## Dev vs Production

### Development

- Mount the source code directory as a volume for live reload during development.
- Set `DEALS_LOG_LEVEL=DEBUG` for verbose output.
- Use the `test` target to run linting and tests locally before pushing.

### Production

- Use a baked image with no source mounts. All code is copied into the image at build time.
- Set `DEALS_LOG_LEVEL=WARNING` to reduce log noise.
- Schedule pipeline runs via cron or an external scheduler rather than running containers manually.

### Future

- Separate Dockerfile targets with dedicated health checks for long-running services.
- Resource limits (CPU, memory) per container to prevent runaway scrapers from affecting the host.
- Dedicated production Compose file or overrides for production-specific configuration.

## When to Split Containers

### Current Approach

A single image serves all purposes. Different commands select different behavior (scrape, review, list-stores, review-stats). This keeps the setup simple while the system is small.

### Future Split Triggers

The single-image approach should be revisited when any of the following occur:

- **Browser scrapers need the heavy Chromium image.** HTTP scrapers should not pay the size cost of Playwright and Chromium. Split into `deals-http-pipeline` (from `base`) and `deals-browser-pipeline` (from `browser`).
- **The API service needs an always-on container.** A long-running FastAPI service has different lifecycle requirements (health checks, restart policies, resource limits) than a batch pipeline. Split into `deals-api` (from `api`).
- **The pipeline needs scheduled execution.** A dedicated `deals-worker` container with cron or a task queue decouples scheduling from the pipeline logic.

### Projected Container Split

| Container | Dockerfile Target | Purpose |
|-----------|-------------------|---------|
| `deals-http-pipeline` | `base` | HTTP-based scrapers, batch execution |
| `deals-browser-pipeline` | `browser` | JS-rendering scrapers with Chromium |
| `deals-api` | `api` | REST API for deals data (always-on) |
| `deals-worker` | `base` | Scheduled/queued pipeline execution |
