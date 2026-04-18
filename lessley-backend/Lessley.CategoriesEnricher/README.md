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

- `POST /categories/enrich` - Enrich transactions with category information
- `POST /categories/store-mcc` - Classify a store and get its MCC code (LLM-powered)
- `POST /categories/deal-category` - Classify a deal/promotion (LLM-powered)
- `GET /categories/health` - Health check endpoint

## Configuration

Required env vars:

- `Environment`: dev/staging/prod
- `ConnectionStrings_Rabbit`: RabbitMQ connection string
- `RabbitMQ_Enabled`: Enable/disable RabbitMQ integration
- `OpenAI_ApiKey`: OpenAI API key for LLM-powered classification
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

# Enrich transactions
curl -X POST http://localhost:8002/categories/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"transaction_id": "1", "amount": 50, "description": "Whole Foods"},
      {"transaction_id": "2", "amount": 25, "description": "Netflix Subscription"}
    ],
    "user_id": "user123"
  }'

# Get store MCC (LLM-powered)
curl -X POST http://localhost:8002/categories/store-mcc \
  -H "Content-Type: application/json" \
  -d '{"store_name": "Teva Pharmacy"}'

# Get deal category (LLM-powered)
curl -X POST http://localhost:8002/categories/deal-category \
  -H "Content-Type: application/json" \
  -d '{
    "deal_name": "50% off electronics",
    "deal_description": "Big sale on all electronics including phones and laptops"
  }'
```
