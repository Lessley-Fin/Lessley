# Lessley Personalization Service

## Overview

AI-driven financial insights service for transaction analysis and categorization.

## Setup

1. Clone repository
2. Create .env from .env.override
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload --port 8001`

## Architecture

- **Controllers** (routers/): FastAPI route handlers
- **Services**: Business logic layer
- **Clients**: External API integrations
- **Utilities**: Data processing helpers

## API Endpoints

- GET /insights/categories
- GET /insights/top-accounts
- etc.

## Configuration

Required env vars:

- `Environment`: dev/staging/prod
- `OpenFinanceConfig_BaseUrl`: API URL
- ...
