# Lessley Personalization Service

## Overview

AI-driven financial insights and recommendations engine. Analyzes Open Finance transaction data to calculate spending categories, identify top accounts/stores, find missed savings opportunities, and match users with relevant loyalty clubs.

## Architecture

- **Insights** (HTTP-only, lightweight): Categories, top accounts, top stores — called synchronously by the Gateway.
- **Recommendations** (RabbitMQ, heavyweight): Missed savings, matching clubs — triggered via RabbitMQ commands from the Gateway. Results are published back to the Gateway as notification events.
- **Controllers** (`routers/`): FastAPI route handlers for insights and recommendations.
- **Services**: Business logic — `InsightsService`, `RecommendationService`, `PublisherService`.
- **Publishers** (`services/publishers/`): RabbitMQ publishers for user tags, deal broadcasts, and recommendation results.
- **Clients**: Open Finance API integration.

## API Endpoints

### Insights (HTTP — synchronous)
- `GET /insights/categories` — User spending categories
- `GET /insights/top-accounts` — Top spending accounts
- `GET /insights/top-stores` — Top spending stores

### Recommendations (HTTP trigger — results via RabbitMQ)
- `POST /recommendations/missed-savings` — Missed savings analysis
- `POST /recommendations/matching-clubs` — Club recommendations

### Open Finance
- `GET /open-finance/accounts` — User bank accounts
- `GET /open-finance/transactions` — User transactions

### Clubs
- `POST /clubs/categories` — Club category distribution

## Setup

1. Clone repository
2. Create `.env` from `.env.override`
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload --port 8001`
5. Update dependencies: `pip freeze > requirements.txt`

## Configuration

Required environment variables:

| Variable | Description |
|----------|-------------|
| `Environment` | dev / staging / prod |
| `ConnectionStrings_Rabbit` | RabbitMQ connection string |
| `ConnectionStrings_MongoDb` | MongoDB connection string |
| `RabbitMQ_Enabled` | Enable RabbitMQ consumer/publisher |
| `OpenFinanceConfig_BaseUrl` | Open Finance API URL |
| `OpenFinanceConfig_ClientId` | Open Finance client ID |
| `OpenFinanceConfig_ClientSecret` | Open Finance client secret |
| `Gateway_ApiKey` | Shared API key for Gateway authentication |
| `Loki_Url` | Grafana Loki URL (optional) |

## Parameters

Insights endpoints accept the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `email` | string | required | User email |
| `time_filter` | bool | `true` | Filter transactions by time window |
| `use_mock` | bool | `false` | Use mock data instead of Open Finance |
| `days` | int | 90 | Days to analyze (1–365) |

The Gateway hardcodes `time_filter=true` and `use_mock=false` — only `days` is configurable by the client.
