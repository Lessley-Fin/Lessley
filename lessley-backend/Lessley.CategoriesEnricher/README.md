# Lessley Categories Enricher Service

## Overview

Transaction category enrichment service for automatic transaction categorization and enrichment.

## Setup

1. Clone repository
2. Create .env from .env.template
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload --port 8002`
5. Update dependencies: `pip freeze > requirements.txt`

## Architecture

- **Controllers** (routers/): FastAPI route handlers
- **Services**: Business logic layer
- **Clients**: External API integrations
- **Utilities**: Data processing helpers

## API Endpoints

- POST /categories/enrich
- GET /categories/health

## Configuration

Required env vars:

- `Environment`: dev/staging/prod
- `ConnectionStrings_Rabbit`: RabbitMQ connection string
- `RabbitMQ_Enabled`: Enable/disable RabbitMQ integration
- `Loki_Url`: Loki logging URL (optional)

## Development

### Running the service
```bash
uvicorn main:app --reload --port 8002
```

### Testing the API
```bash
# Health check
curl http://localhost:8002/categories/health

# Enrich categories
curl -X POST http://localhost:8002/categories/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"transaction_id": "1", "amount": 50, "description": "Whole Foods"},
      {"transaction_id": "2", "amount": 25, "description": "Netflix Subscription"}
    ],
    "user_id": "user123"
  }'
```
