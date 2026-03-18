# 📋 Structured Logging Quick Reference

## 🚀 Quick Start - Copy & Paste Templates

### Template 1: API Endpoint with Error Handling

```python
from config.structured_logging import log_api_request, log_api_response
import time
import logging

logger = logging.getLogger(__name__)

@router.get("/your-endpoint")
async def your_endpoint(request: Request, user_id: str):
    start_time = time.time()

    log_api_request(logger, "/your-endpoint", "GET", user_id=user_id)

    try:
        # Your business logic here
        result = await service.do_something(user_id)

        log_api_response(
            logger,
            "/your-endpoint",
            status_code=200,
            response_time_ms=(time.time() - start_time) * 1000,
            record_count=len(result)
        )
        return result
    except Exception as e:
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Operation failed: {str(e)}",
            reason="Endpoint execution error",
            extra_data={"user_id": user_id}
        )
        raise
```

### Template 2: Service Method with Logging

```python
from config.structured_logging import StructuredLogger, log_service_call, log_service_error
import logging

logger = logging.getLogger(__name__)

class YourService:
    async def your_method(self, user_id: str):
        log_service_call(
            logger,
            service_name="YourService",
            method_name="your_method",
            params={"user_id": user_id}
        )

        try:
            # Your business logic
            result = await self.fetch_data(user_id)

            StructuredLogger.log_with_context(
                logger,
                "info",
                "Data fetched successfully",
                reason="Business logic execution",
                extra_data={"user_id": user_id, "records": len(result)}
            )

            return result
        except Exception as e:
            log_service_error(
                logger,
                service_name="YourService",
                method_name="your_method",
                error=e,
                context={"user_id": user_id}
            )
            raise
```

### Template 3: Background Task / RabbitMQ Handler

```python
from config.structured_logging import StructuredLogger
import logging

logger = logging.getLogger(__name__)

async def process_message(message):
    user_id = message.data.get("user_id")

    StructuredLogger.log_with_context(
        logger,
        "info",
        "Processing message from queue",
        reason="RabbitMQ event received",
        extra_data={"user_id": user_id, "message_type": "calc_request"}
    )

    try:
        result = await handle_calculation(user_id)

        StructuredLogger.log_with_context(
            logger,
            "info",
            "Message processed successfully",
            reason="Queue handler completed",
            extra_data={"user_id": user_id}
        )
    except Exception as e:
        StructuredLogger.log_with_context(
            logger,
            "error",
            f"Queue processing failed: {str(e)}",
            reason="Background task error",
            extra_data={"user_id": user_id}
        )
        raise
```

---

## 🎯 Logging Checklist

- [ ] Add `import logging` and `from config.structured_logging import ...`
- [ ] Create logger: `logger = logging.getLogger(__name__)`
- [ ] Log API requests: `log_api_request(...)`
- [ ] Log API responses: `log_api_response(...)`
- [ ] Log service calls: `log_service_call(...)`
- [ ] Log errors with context: `StructuredLogger.log_with_context(...)`
- [ ] Include `reason` for every log
- [ ] Use `extra_data` for queryable fields
- [ ] Add timing information for performance analysis
- [ ] Test locally: `python main.py | jq .`

---

## 📊 Key Fields by Use Case

### API Request

```python
log_api_request(
    logger,
    endpoint="/insights/categories",
    method="GET",
    user_id="12345",
    params={"time_filter": True, "days": 30}
)
```

### API Response

```python
log_api_response(
    logger,
    endpoint="/insights/categories",
    status_code=200,
    response_time_ms=245.3,
    record_count=42
)
```

### Service Call

```python
log_service_call(
    logger,
    service_name="InsightsService",
    method_name="calculate_categories",
    params={"user_id": "12345"}
)
```

### Service Error

```python
log_service_error(
    logger,
    service_name="InsightsService",
    method_name="calculate_categories",
    error=e,
    context={"user_id": "12345", "attempt": 1}
)
```

### Custom Context

```python
StructuredLogger.log_with_context(
    logger,
    "info",
    "Processing complete",
    reason="All validation passed",
    extra_data={
        "user_id": "12345",
        "records_processed": 1000,
        "time_taken_ms": 150
    }
)
```

---

## ✅ Do's

✅ Log at appropriate levels

- `INFO`: User actions, successful operations, important state changes
- `WARNING`: Degraded conditions, retries, partial failures
- `ERROR`: Failures, exceptions, need for investigation

✅ Use `reason` to explain WHY the log occurred

```python
reason="User authentication succeeded"
reason="External API timeout, retrying..."
reason="Validation failed: missing required field"
reason="Service initialization error"
```

✅ Make logs queryable with extra_data

```python
extra_data={
    "user_id": "12345",           # Always include user context
    "response_time_ms": 245.3,    # Performance metrics
    "record_count": 42,           # Quantifiable results
    "api_endpoint": "transactions" # What was accessed
}
```

✅ Include timing for performance monitoring

```python
start_time = time.time()
# ... do work ...
elapsed_ms = (time.time() - start_time) * 1000
extra_data={"elapsed_ms": elapsed_ms}
```

---

## ❌ Don'ts

❌ DON'T include raw timestamps—it's automatic

```python
# ❌ Wrong
logger.info(f"Action at {datetime.now()}: {data}")

# ✅ Right
StructuredLogger.log_with_context(logger, "info", "Action", extra_data={"data": data})
```

❌ DON'T log the same data in message AND extra_data

```python
# ❌ Wrong
logger.info(f"User 12345 downloaded 50 items", extra={"extra_data": {"user_id": "12345", "count": 50}})

# ✅ Right (use extra_data for structured querying)
StructuredLogger.log_with_context(
    logger, "info", "Items downloaded",
    extra_data={"user_id": "12345", "count": 50}
)
```

❌ DON'T log sensitive data (passwords, tokens, PII)

```python
# ❌ Wrong
logger.info(f"Login successful for {password}")

# ✅ Right
StructuredLogger.log_with_context(
    logger, "info", "Login successful",
    extra_data={"username": "user@example.com"}  # Never log password
)
```

❌ DON'T create logs for routine operations

```python
# ❌ Wrong (too noisy)
for item in items:
    logger.debug(f"Processing item {item.id}")

# ✅ Right (one log with count)
StructuredLogger.log_with_context(
    logger, "info", "Batch processing complete",
    extra_data={"batch_size": len(items)}
)
```

❌ DON'T create logs without context

```python
# ❌ Wrong (why did this happen?)
logger.error("Operation failed")

# ✅ Right (includes reason and details)
StructuredLogger.log_with_context(
    logger, "error", "Database query failed",
    reason="Connection timeout to replica",
    extra_data={"query_type": "transactions", "retry_count": 3}
)
```

---

## 🔍 Loki Query Examples

### Find all errors for a specific user

```
{service="Personalization"} | json | username="user@example.com" | level="ERROR"
```

### Find slow endpoints (>1 second)

```
{service="Personalization"} | json | response_time_ms > 1000
```

### Find all requests with a trace ID

```
{service="Personalization"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

### Count API calls by endpoint

```
{service="Personalization"} | json | level="INFO" | reason="Request received" | stats count by endpoint
```

### Find rate limit violations

```
{service="Personalization"} | json | reason="Too many requests from client"
```

### Performance distribution

```
{service="Personalization"} | json | endpoint="/insights/categories" | stats p99(response_time_ms), p95(response_time_ms)
```

---

## 🧪 Testing Your Logs Locally

### 1. Install jq (pretty printer)

```bash
# macOS
brew install jq

# Linux
sudo apt-get install jq

# Windows (PowerShell)
choco install jq
```

### 2. Run service and pipe through jq

```bash
cd lessley-backend/Lessley.Personalization
python main.py | jq .
```

You'll see pretty-printed JSON:

```json
{
  "timestamp": "2026-03-18T10:30:45.123456Z",
  "service": "Personalization",
  "level": "INFO",
  "message": "Data fetched successfully",
  "class_name": "insights_service",
  "function": "calculate_categories",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "user@example.com",
  "reason": "Business logic execution",
  "extra_data": {
    "user_id": "12345",
    "records": 42
  }
}
```

### 3. Filter logs while running

```bash
# Show only errors
python main.py | jq 'select(.level == "ERROR")'

# Show only specific user
python main.py | jq 'select(.username == "user@example.com")'

# Show only a specific endpoint
python main.py | jq 'select(.extra_data.endpoint == "/insights/categories")'
```

---

## 📞 Request Context

Request context (request_id, username) is **automatically** available in all logs. No manual setup needed!

Set from request headers:

```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Username: user@example.com
```

Or via query parameter:

```
GET /api/data?user_id=12345
```

The middleware automatically sets the context for all logs in the request handling chain.

---

For more details, see [LOGGING.md](./LOGGING.md)
