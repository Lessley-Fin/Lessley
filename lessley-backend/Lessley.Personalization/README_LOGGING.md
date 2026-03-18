# 📋 Logging Documentation Index

## Quick Navigation

**Start Here** 👇

### For Developers

1. **[LOGGING_QUICK_REFERENCE.md](./LOGGING_QUICK_REFERENCE.md)** ⚡
   - Copy-paste templates
   - Common patterns
   - Do's and don'ts
   - 10-minute read

2. **Example Implementations**
   - [services/open_finance_service.py](./services/open_finance_service.py) - Service logging pattern
   - [routers/insights_controller.py](./routers/insights_controller.py) - API endpoint pattern

### For DevOps/SRE

1. **[LOGGING.md](./LOGGING.md)** 📚
   - Complete reference
   - Loki query examples
   - Troubleshooting
   - Configuration details

2. **[LOGGING_IMPLEMENTATION.md](./LOGGING_IMPLEMENTATION.md)** ✅
   - What was implemented
   - Migration timeline
   - Benefits overview

### For Setup/Validation

- **[validate_logging.py](./validate_logging.py)** - Run to validate imports and setup

---

## 📁 Implementation Files

### Core Framework

- `config/structured_logging.py` - Main logging utilities
- `config/logging.py` - Logger initialization
- `middleware/request_id.py` - Request context propagation

### Updated Application Code

- `main.py` - App initialization and exception handlers
- `services/open_finance_service.py` - Service logging example
- `routers/insights_controller.py` - API endpoint logging example

---

## 🎯 What Each File Does

### Developers Should Read

| File                             | Time     | Purpose                             |
| -------------------------------- | -------- | ----------------------------------- |
| LOGGING_QUICK_REFERENCE.md       | 5-10 min | Copy-paste templates, quick answers |
| services/open_finance_service.py | 10 min   | See service logging in action       |
| routers/insights_controller.py   | 10 min   | See API logging in action           |

### DevOps/SRE Should Read

| File                      | Time      | Purpose                                   |
| ------------------------- | --------- | ----------------------------------------- |
| LOGGING.md                | 20-30 min | Full guide, Loki queries, troubleshooting |
| LOGGING_IMPLEMENTATION.md | 10 min    | Overview of what was implemented          |

### Everyone Should Know

| File                      | Time  | Purpose                         |
| ------------------------- | ----- | ------------------------------- |
| LOGGING_IMPLEMENTATION.md | 5 min | High-level overview of benefits |

---

## 🚀 Getting Started (2 Steps)

### Step 1: Understand the Pattern (5 min)

Read the relevant section in [LOGGING_QUICK_REFERENCE.md](./LOGGING_QUICK_REFERENCE.md):

- **API Endpoint?** → Template 1
- **Service Method?** → Template 2
- **Background Task?** → Template 3

### Step 2: Add Logging (5 min per function)

Copy the template and adapt to your code.

Example:

```python
from config.structured_logging import StructuredLogger, log_api_request
import logging

logger = logging.getLogger(__name__)

@router.get("/my-endpoint")
async def my_endpoint(request: Request):
    log_api_request(logger, "/my-endpoint", "GET", user_id=request.query_params.get("user_id"))

    try:
        result = await service.do_work()
        return result
    except Exception as e:
        StructuredLogger.log_with_context(
            logger, "error", str(e),
            reason="Endpoint failed",
            extra_data={"error_type": type(e).__name__}
        )
        raise
```

---

## 📊 Log Format (What You Get)

```json
{
  "timestamp": "2026-03-18T10:30:45.123456Z",
  "service": "Personalization",
  "level": "INFO",
  "message": "User categories calculated",
  "class_name": "insights_service",
  "module": "insights_controller",
  "function": "calculate_user_categories",
  "line": 45,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "user@example.com",
  "reason": "API request completed",
  "extra_data": {
    "user_id": "12345",
    "categories_count": 8,
    "response_time_ms": 245.3
  }
}
```

---

## ✨ Key Features

✅ **Structured JSON** - Easy to parse and query  
✅ **Request Tracing** - Track requests across services with request_id  
✅ **Automatic Context** - request_id and username automatic from middleware  
✅ **Performance Tracking** - Response times recorded automatically  
✅ **Error Context** - Full exception details captured  
✅ **Loki Ready** - Logs go directly to Loki for centralized management  
✅ **Well Documented** - Copy-paste templates and examples provided

---

## 🔍 Querying Logs with Loki

```bash
# Find all errors for a user
{service="Personalization"} | json | username="user@example.com" | level="ERROR"

# Find slow requests
{service="Personalization"} | json | response_time_ms > 1000

# Trace a specific request
{service="Personalization"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

More examples in [LOGGING.md](./LOGGING.md#querying-logs-in-loki)

---

## ✅ Implementation Status

- [x] Core logging framework
- [x] Request context propagation
- [x] Exception handlers updated
- [x] Example services updated
- [x] Example controllers updated
- [x] Comprehensive documentation
- [x] Quick reference guide
- [x] Validation script
- [ ] Remaining controllers (recommended next step)
- [ ] Remaining services (recommended next step)
- [ ] Loki dashboards (optional)

---

## 🧪 Testing Locally

```bash
# Run the service
python main.py | jq .

# Or filter by level
python main.py | jq 'select(.level == "ERROR")'

# Or by username
python main.py | jq 'select(.username == "user@example.com")'
```

---

## 💡 Common Questions

**Q: Do I need to manually set request_id and username?**  
A: No! The middleware does this automatically from headers and query params.

**Q: What if I don't have a user in the request?**  
A: That's fine - username field will just be null in logs.

**Q: How much overhead does structured logging add?**  
A: Minimal - JSON encoding is fast and Loki sending is async (non-blocking).

**Q: Can I add custom fields to logs?**  
A: Yes! Use the `extra_data` parameter in `StructuredLogger.log_with_context()`.

More Q&A in [LOGGING.md](./LOGGING.md#troubleshooting)

---

## 🚦 Recommended Reading Order

### For Just Adding Logging (15 min total)

1. [LOGGING_QUICK_REFERENCE.md](./LOGGING_QUICK_REFERENCE.md) - Templates
2. [services/open_finance_service.py](./services/open_finance_service.py) - See example
3. Copy template to your code

### For Understanding Everything (45 min total)

1. [LOGGING_QUICK_REFERENCE.md](./LOGGING_QUICK_REFERENCE.md) - Overview
2. [LOGGING_IMPLEMENTATION.md](./LOGGING_IMPLEMENTATION.md) - What was built
3. [LOGGING.md](./LOGGING.md) - Deep dive

### For Operations/Monitoring (20 min total)

1. [LOGGING_IMPLEMENTATION.md](./LOGGING_IMPLEMENTATION.md) - Overview
2. [LOGGING.md](./LOGGING.md) - Loki queries section

---

## 📞 Support

- **Quick questions?** → Check [LOGGING_QUICK_REFERENCE.md](./LOGGING_QUICK_REFERENCE.md#-dos--donts)
- **Need examples?** → See [services/open_finance_service.py](./services/open_finance_service.py)
- **Setup issues?** → Run `python validate_logging.py`
- **Detailed guide?** → Read [LOGGING.md](./LOGGING.md)

---

**Status:** ✅ Production Ready  
**Last Updated:** March 18, 2026  
**Version:** 1.0.0
