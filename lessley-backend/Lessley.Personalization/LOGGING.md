# Production-Ready Logging Guide - Lessley Personalization Service

## Overview

This service now uses **structured JSON logging** for production readiness. All logs are output as JSON, making them compatible with Loki and other centralized logging systems, and enabling powerful log analysis and filtering.

## Log Format

Every log entry includes these fields:

```json
{
  "timestamp": "2026-03-18T10:30:45.123456Z",
  "service": "Personalization",
  "level": "INFO",
  "message": "User login successful",
  "class_name": "insights_service",
  "module": "insights_controller",
  "function": "calculate_user_categories",
  "line": 45,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "user@example.com",
  "reason": "User initiated API request",
  "exception": null,
  "extra_data": {
    "user_id": "12345",
    "response_time_ms": 245.3,
    "record_count": 42
  }
}
```

### Field Definitions

| Field        | Description                         | Example                              |
| ------------ | ----------------------------------- | ------------------------------------ |
| `timestamp`  | ISO 8601 UTC timestamp              | `2026-03-18T10:30:45.123456Z`        |
| `service`    | Application name                    | `Personalization`                    |
| `level`      | Log severity                        | `INFO`, `WARNING`, `ERROR`, `DEBUG`  |
| `message`    | Main log message                    | `"User login successful"`            |
| `class_name` | Source class/module name            | `insights_service`                   |
| `module`     | Python module name                  | `insights_controller`                |
| `function`   | Function name                       | `calculate_user_categories`          |
| `line`       | Line number in source file          | `45`                                 |
| `request_id` | Trace ID for request correlation    | UUID format                          |
| `username`   | User identifier (if available)      | Email or user ID                     |
| `reason`     | Context about why this log occurred | `"Service initialization failed"`    |
| `exception`  | Exception details (if error)        | Object with type, message, traceback |
| `extra_data` | Additional structured context       | Any custom fields                    |

## Usage Patterns

### 1. Basic Logging

```python
from config.structured_logging import StructuredLogger
import logging

logger = logging.getLogger(__name__)

# Simple info log - context (request_id, username) is automatic from middleware
logger.info("Processing user data")

# Output:
# {
#   "timestamp": "...",
#   "service": "Personalization",
#   "level": "INFO",
#   "message": "Processing user data",
#   "class_name": "your_module",
#   "request_id": "550e8400-e29b-41d4-a716-446655440000",
#   "username": "user@example.com"
# }
```

### 2. Logging with Reason and Extra Data

```python
from config.structured_logging import StructuredLogger
import logging

logger = logging.getLogger(__name__)

# Log with context
StructuredLogger.log_with_context(
    logger,
    "info",
    "User categories calculated successfully",
    reason="API request completed",
    extra_data={
        "user_id": "12345",
        "categories_count": 8,
        "response_time_ms": 245.3
    }
)

# Output includes extra_data fields for filtering
```

### 3. API Request/Response Logging

**In Controllers:**

```python
from config.structured_logging import log_api_request, log_api_response
import time

@router.get("/categories")
async def calculate_user_categories(request: Request, req: InsightsCalcRequests = Query()):
    start_time = time.time()

    # Log request received
    log_api_request(
        logger,
        endpoint="/insights/categories",
        method="GET",
        user_id=req.user_id,
        params={"time_filter": req.time_filter, "days": req.days}
    )

    try:
        # Your business logic here
        categories = await service.calculate_user_categories_async(...)

        response_time_ms = (time.time() - start_time) * 1000

        # Log successful response
        log_api_response(
            logger,
            endpoint="/insights/categories",
            status_code=200,
            response_time_ms=response_time_ms,
            record_count=len(categories)
        )

        return PaginatedResponse(status="success", data=categories, count=len(categories))

    except Exception as e:
        # Log error with full context
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Error calculating categories: {str(e)}",
            reason="Service call failed",
            extra_data={"user_id": req.user_id, "endpoint": "/insights/categories"}
        )
        raise
```

### 4. Service Logging

**In Services:**

```python
from config.structured_logging import StructuredLogger, log_service_call, log_service_error
import logging

logger = logging.getLogger(__name__)

class InsightsService:
    async def calculate_user_categories_async(self, user_id: str, time_filter: bool, days: int):
        # Log service method call
        log_service_call(
            logger,
            service_name="InsightsService",
            method_name="calculate_user_categories_async",
            params={"user_id": user_id, "time_filter": time_filter, "days": days}
        )

        try:
            # Get transactions from OpenFinance API
            transactions = await self.open_finance_service.get_user_transactions_async(
                user_id, time_filter, days
            )

            StructuredLogger.log_with_context(
                logger,
                "debug",
                "Transactions retrieved",
                reason="Data fetching stage",
                extra_data={
                    "user_id": user_id,
                    "transaction_count": len(transactions),
                    "source": "OpenFinance"
                }
            )

            # Process transactions
            categories = self.processing_core_service.get_top_spending_categories(transactions)

            StructuredLogger.log_with_context(
                logger,
                "info",
                "Categories calculated successfully",
                reason="Processing complete",
                extra_data={
                    "user_id": user_id,
                    "categories_count": len(categories)
                }
            )

            return categories

        except Exception as e:
            # Log service error
            log_service_error(
                logger,
                service_name="InsightsService",
                method_name="calculate_user_categories_async",
                error=e,
                context={"user_id": user_id}
            )
            raise
```

### 5. Error Logging with Exceptions

```python
from config.structured_logging import StructuredLogger
import logging

logger = logging.getLogger(__name__)

try:
    # Code that might fail
    result = await external_api.fetch_data()
except ConnectionError as e:
    # Log error with exception details
    StructuredLogger.log_with_context(
        logger,
        "error",
        f"Failed to fetch data: {str(e)}",
        reason="External API connection failed",
        extra_data={"api": "ExternalService", "retry_count": 3}
    )
    # Exception is automatically captured and included
    raise
```

## Request Context Propagation

Request context (request_id, username) is automatically propagated through middleware and available in all logs for the current request. This enables request tracing across logs.

### Setting Request Context in Middleware

The middleware automatically extracts context from:

1. **Request Headers**: `X-Request-ID`, `X-Username`
2. **Query Parameters**: `user_id` is used as username
3. **Request State**: `request.state.user` (if using authentication)

```python
# Middleware automatically sets context
StructuredLogger.set_request_context(request_id="550e8400-e29b-41d4-a716-446655440000",
                                      username="user@example.com")
```

## Log Levels

Use appropriate log levels:

- **DEBUG**: Detailed diagnostic information useful for developers (disabled by default in production)
- **INFO**: Significant events, API requests/responses, service state changes
- **WARNING**: Something unexpected happened but service continues (rate limits, degraded conditions)
- **ERROR**: Something failed and needs attention (exceptions, failed requests to external services)

```python
logger.debug("Processing transaction", extra={"extra_data": {"tx_id": "123"}})
logger.info("User request processed")
logger.warning("API response slower than expected")
logger.error("Database connection failed")
```

## Querying Logs in Loki

With structured JSON logging, you can create powerful queries in Loki/Grafana:

### Find all errors for a user

```
{service="Personalization"} | json | username="user@example.com" | level="ERROR"
```

### Find slow API requests

```
{service="Personalization"} | json | endpoint="/insights/categories" and response_time_ms > 1000
```

### Find all requests with a trace ID

```
{service="Personalization"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

### Find service errors

```
{service="Personalization"} | json | reason="Service execution failure"
```

## Best Practices

✅ **DO:**

- Include `reason` to explain why a log occurred
- Use `extra_data` for structured context (user_id, counts, timings)
- Log at appropriate levels (INFO for user actions, ERROR for failures)
- Include timing information for performance analysis
- Use request_id for correlating logs across services

❌ **DON'T:**

- Include sensitive data (passwords, tokens, PII) in logs
- Log the same information in both message and extra_data
- Use string concatenation for log messages (use extra_data instead)
- Create logs for routine operations (would cause log spam)

## Configuration

Logging is configured in two files:

1. **config/logging.py** - Basic logging configuration
2. **config/structured_logging.py** - Structured logging utilities

Both Loki and console output receive the same formatted JSON logs.

## Testing Logs Locally

When running locally, logs are output to stdout in JSON format:

```bash
cd lessley-backend/Lessley.Personalization
python main.py
```

You'll see JSON logs like:

```json
{
  "timestamp": "...",
  "service": "Personalization",
  "level": "INFO",
  "message": "..."
}
```

For better readability while developing, you can pipe through `jq`:

```bash
python main.py | jq .
```

This will pretty-print the JSON logs.

## Migration Guide

To add structured logging to existing code:

### Before

```python
logger.info(f"User {user_id} requested categories")
logger.error(f"Failed to fetch transactions for user {user_id}: {error}")
```

### After

```python
log_api_request(logger, endpoint="/insights/categories", user_id=user_id)

# or

StructuredLogger.log_with_context(
    logger,
    "error",
    "Failed to fetch transactions",
    reason="External API error",
    extra_data={"user_id": user_id, "error": str(error)}
)
```

## Troubleshooting

### Logs not appearing in Loki

1. Check Loki URL in settings: `settings.Loki_Url`
2. Verify network connectivity to Loki endpoint
3. Check the Queue Handler hasn't crashed: monitor `listener` in main.py

### Performance impact

- Structured logging has minimal overhead
- Loki ingestion is async (QueueListener non-blocking)
- Large `extra_data` dictionaries may slow logging - keep them reasonable

### Context variables not propagating

- Ensure RequestIDMiddleware is the first middleware added to the app
- Verify request context is set: `StructuredLogger.set_request_context(...)`
- Check async context variables are properly inherited in async tasks
