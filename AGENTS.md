# Lessley Microservices - AI Agent Guide

This guide helps AI coding agents be immediately productive in the **Personalization service** and **Gateway.API** components.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Gateway.API (C# / .NET 8)                 │
│  - Entry point for client authentication (JWT)                 │
│  - Centralized auth + role-based access control                │
│  - Integrates with Open Finance API (external partner)         │
│  - Exposes REST endpoints (Auth, OpenFinance controllers)       │
│  - Logs to Grafana Loki (JSON structured)                       │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                       RabbitMQ Bus
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              Personalization Service (Python / FastAPI)         │
│  - Async engine: analyzes user transactions                     │
│  - Consumes: Transaction data from Open Finance API             │
│  - Produces: Insights, spending categories, recommendations     │
│  - Publishes results to RabbitMQ (personalize.* routing keys)   │
│  - Logs to Grafana Loki (JSON structured)                       │
│  - Uses async Motor + Beanie (MongoDB ODM)                      │
└─────────────────────────────────────────────────────────────────┘
```

Both services share:
- **Database**: MongoDB (`lessley` database)
- **Message Queue**: RabbitMQ (`lessley_events` exchange)
- **Logging**: Grafana Loki (JSON structured logs)

---

## ⚡ Quick Start: Build & Run

> **Full stack (dev == prod):** use `lessley-cd/` — `manage.bat infra up` then `manage.bat app build`.
> The app is reached **only through Caddy** at `https://localhost` (dev) / `https://<DOMAIN>` (prod),
> which serves the SPA and proxies `/api` + `/hubs` to the gateway (`gateway:5001`). The sections
> below run a single service standalone for focused backend work. Canonical ports: gateway container
> `5001` (dev host-publishes `8001` for Swagger), personalization container `5002` (dev host `8002`).

### **Gateway.API** (C#)

```bash
cd lessley-backend/Lessley.Gateway.Api

# Development
dotnet run

# With Docker
docker build -f Dockerfile -t lessley-gateway:latest .
docker run -p 8001:8001 \
  -e ASPNETCORE_HTTP_PORTS=8001 \
  -e ConnectionStrings__MongoDb=mongodb://... \
  -e JwtConfig__Key=your-secret-key \
  lessley-gateway:latest

# Access API (gateway: 8001 in dev, 5001 in prod)
# Local: http://localhost:8001/swagger
# Docker: http://localhost:8001/swagger
```

**Configuration**: Edit `appsettings.json` or pass environment variables:
- `ConnectionStrings__MongoDb` - MongoDB connection string
- `JwtConfig__Key` - Secret key for JWT signing
- `JwtConfig__Issuer` - JWT issuer (default: Lessley)
- `JwtConfig__Audience` - JWT audience (default: LessleyApi)

---

### **Personalization Service** (Python)

```bash
cd lessley-backend/Lessley.Personalization

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate on Windows

# Install dependencies
pip install -r requirements.txt

# Development
cp .env.template .env  # Edit with credentials
uvicorn main:app --reload --port 8002

# With Docker
docker build -t lessley-personalization . .
docker run -p 8002:8002 --env-file .env lessley-personalization

# Access API & docs
# http://localhost:8002/docs (Swagger)
# http://localhost:8002/redoc (ReDoc)
```

**Critical Environment Variables**:
```bash
Environment=dev                                    # dev|staging|prod
ConnectionStrings_MongoDb=mongodb://user:pass@... # Required
ConnectionStrings_Rabbit=amqp://user:pass@...     # Required
RabbitMQ_Enabled=True|False                       # Set False for local dev without broker
OpenFinanceConfig_ClientId=***
OpenFinanceConfig_ClientSecret=***
OpenFinanceConfig_BaseUrl=https://api.open-finance.ai
Loki_Url=http://localhost:3100/loki/api/v1/push  # Optional
```

---

## 🏛️ Architecture Patterns

### **Gateway.API** - Layered Architecture

```
Controllers (HTTP handlers)
    ↓ Validate requests
Services (Business logic)
    ↓ Orchestrate operations
Data Layer (MongoDB via EF Core)
```

**Key Classes**:
- `AuthController` - Register, Login, RefreshToken endpoints
- `OpenFinanceController` - External API proxy (GetAccounts, GetTransactions, GetConnections)
- `JwtService` - Token generation & validation (HS256, 12h access / 5h refresh)
- `OpenFinanceService` - Open Finance API client with error handling
- `ApplicationDbContext` - MongoDB context (auto-maps collections)

**Key Conventions**:
- Controllers return `IActionResult` (Ok, BadRequest, Unauthorized, etc.)
- Services are injected via DI container (Program.cs)
- JWT validation via middleware (BearerTokenUsageMiddleware)
- Roles: None, Viewer (default), Operator, Admin (RoleSeeder creates roles)

---

### **Personalization Service** - Dependency Injection + Async Everything

```
Routers (HTTP handlers - @app.get/@app.post)
    ↓ Validate via Pydantic
Services (Business logic - async def)
    ↓ All I/O operations are awaited
Clients (External APIs) + Database (MongoDB via Beanie)
```

**Key Pattern: Singleton DI Container**
```python
# In di_container.py
class DIContainer:
    @staticmethod
    def get_insights_service() -> InsightsService:
        # Lazy initialization on first call
        # Same instance returned on subsequent calls
```

**Key Classes**:
- `InsightsService` - Spending analysis, category detection
- `OpenFinanceClient` - Open Finance API calls with token caching (24h TTL)
- `RecommendationService` - Generates personalized recommendations
- Models use Beanie (Pydantic + MongoDB ODM):
  ```python
  class ClubList(Document):
      club_name: str
      class Settings:
          name = "club_list"  # Collection name
  ```

**Key Conventions**:
- All service methods: `async def`
- All DB/HTTP operations: `await` required
- Logging: Standard Python logging with `extra` dict for structured output
- File naming: `*_service.py`, `*_controller.py`, `*_client.py`
- Validation: Pydantic `BaseModel` + `@validator` decorators

---

## 📝 Logging: Structured JSON to Grafana Loki

Both services log as structured JSON automatically. **Zero duplication required** - the logger captures context automatically.

**Usage Pattern** (Python):
```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "Processing complete",
    extra={
        "reason": "Data aggregation succeeded",
        "extra_data": {"user_id": "user123", "count": 42}
    }
)
```

**Automatically captured** (no need to duplicate):
- `service_name` - From module path (e.g., `services.insights_service`)
- `username` - From request context
- `request_id` - From middleware (unique per request)

**Log Format Output** (Grafana Loki):
```json
{
  "timestamp": "2026-04-08T08:42:00.612626Z",
  "level": "INFO",
  "app_name": "personalization",
  "service_name": "services.open_finance_service",
  "username": "user@example.com",
  "request_id": "a0953090-9457-4ea5-bd95-9f3a78d533b2",
  "message": "Processing complete",
  "reason": "Data aggregation succeeded",
  "extra_data": {"user_id": "user123", "count": 42}
}
```

**See detailed guide** in [repository memory file](../.github/memories/logging-implementation.md) or ask about logging patterns.

---

## 🔌 Integration Points

### **Shared Database: MongoDB**

Both services use the `lessley` database:
- **Gateway.API**: Stores users, roles, refresh tokens (via EF Core)
- **Personalization**: Reads reference data (clubs, deals, MCC codes)

**MongoDB Connection**:
- Env var: `ConnectionStrings_MongoDb` or `ConnectionStrings__MongoDb`
- URL format: `mongodb://username:password@host:27017/`

---

### **Message Queue: RabbitMQ**

**Personalization Consumer** (runs in startup lifespan):
- Exchange: `lessley_events` (TOPIC, durable)
- Queue: `personalize_calc_history_queue`
- Routing Key: `Personalize.calc_history`
- Enable/disable: Set `RabbitMQ_Enabled=True|False`

**Warning**: If RabbitMQ is disabled but `RabbitMQ_Enabled=True`, the service hangs on startup. Set to `False` for local dev.

---

### **External: Open Finance API**

**Endpoint**: `https://api.open-finance.ai`

**Authenticated via**:
- OAuth 2.0 token exchange
- Client credentials: `OpenFinanceConfig_ClientId`, `OpenFinanceConfig_ClientSecret`
- Token caching: 24-hour TTL per user (use `client.invalidate_token(user_id)` to force refresh)

**Gateway.API** proxies this API:
- `POST /auth/connect-account` - Redirects to Open Finance
- `GET /open-finance/accounts` - Retrieves user accounts
- `GET /open-finance/transactions` - Retrieves transactions (paginated)
- `GET /open-finance/connections` - Lists active connections

**Personalization** consumes this data:
- Fetches transactions asynchronously
- Analyzes spending patterns
- Groups by category + merchant code (MCC)

**Mock Mode** (Personalization):
- Set `use_mock=True` in OpenFinanceClient to use local JSON for testing
- Data files in `data/` directory

---

## ⚠️ Common Pitfalls & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **Personalization hangs on startup** | RabbitMQ unreachable | Set `RabbitMQ_Enabled=False` for local dev |
| **"Beanie save failed" error** | Missing `await` on ODM operations | Always: `await model.insert()` or `await model.save()` |
| **Request context lost in RabbitMQ handler** | Middleware context only applies to HTTP | Manually call `StructuredLogger.set_request_context()` in handler |
| **Open Finance token cache stale** | 24-hour TTL not refreshed | Call `client.invalidate_token(user_id)` to force new token |
| **Logging blocks on startup** | Loki connection timeout | Set `Loki_Url` to valid endpoint or omit env var |
| **"401 Unauthorized" in Gateway.API** | JWT expired or invalid signature | Check token generation in JwtService, verify `JwtConfig__Key` matches |
| **MongoDB connection timeout** | Replica set unreachable | Verify connection string, test: `ping host:27017`, check firewall |

---

## 📚 Documentation & Further Reading

- [Gateway.API README](lessley-backend/Lessley.Gateway.Api/README.md) - Detailed API documentation
- [Personalization README](lessley-backend/Lessley.Personalization/README.md) - Service features & endpoints
- [Docker Compose Setup](lessley-cd/README.md) - Local dev environment (MongoDB, RabbitMQ, Grafana)
- **Logging Guide**: See repo memory `/memories/repo/logging-implementation.md` for structured logging patterns

---

## 🔑 Key Files for AI Agents

### **Gateway.API**
- `Program.cs` - Startup, DI configuration, middleware pipeline
- `Configuration/JwtConfig.cs` - JWT token settings
- `Services/JwtService.cs` - Token generation/validation logic
- `Controllers/AuthController.cs` - Registration, login, refresh endpoints
- `Controllers/OpenFinanceController.cs` - Proxy to external API
- `appsettings.json` - Configuration template

### **Personalization**
- `main.py` - FastAPI app, lifespan (startup/shutdown), RabbitMQ consumer
- `services/di_container.py` - Dependency injection (all services are singletons)
- `config/structured_logging.py` - JSON logging setup
- `services/open_finance_service.py` - Open Finance API client
- `services/open_finance_client.py` - Token caching, OAuth flow
- `requirements.txt` - All dependencies

---

## ✅ Productivity Checklist

When working in these services, always verify:

- [ ] Environment variables configured (`.env` for Personalization, `appsettings.json` for Gateway.API)
- [ ] MongoDB connection working (`mongosh` or Compass)
- [ ] For Personalization: RabbitMQ enabled/disabled appropriately
- [ ] Logs flowing to Grafana Loki (if configured)
- [ ] JWT secrets not exposed in source code (use env vars)
- [ ] All async operations have `await` (Python) or `await` (C#)
- [ ] Structured logging uses `extra` dict pattern, not string concatenation
