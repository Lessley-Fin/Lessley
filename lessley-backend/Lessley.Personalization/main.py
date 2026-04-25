from contextlib import asynccontextmanager
import asyncio
import json
from fastapi import FastAPI, status, Request
import aio_pika
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import logging_loki
from services.di_container import DIContainer
from config.settings import settings
from config.structured_logging import StructuredFormatter, ContextInjectingFilter
from routers import open_finance_controller
from routers import mcc_controller
from routers import insights_controller
from routers import recommendation_controller
from routers import club_controller
from database.db_client import init_db, close_db
from middleware.log_context_middleware import UnifiedContextMiddleware, request_id_var, username_var
from middleware.gateway_auth_middleware import GatewayAuthMiddleware
import uuid

# --- RabbitMQ Configuration ---
GATEWAY_COMMANDS_QUEUE  = "personalization.gateway_commands"
GATEWAY_COMMANDS_PATTERN = "Gateway.*"

# --- Logging Configuration ---
# Create a structured formatter
structured_formatter = StructuredFormatter()

# Create Loki handler only if URL is configured
loki_handler = None
if settings.Loki_Url:
    loki_handler = logging_loki.LokiHandler(
        url=settings.Loki_Url,
        tags={"app_name": "personalization", "environment": getattr(settings, "Environment", "dev")},
        version="1",
    )
    loki_handler.setFormatter(structured_formatter)


class LocalQueueHandler(QueueHandler):
    """
    Custom QueueHandler that preserves exc_info.
    The default QueueHandler flattens the exception into the message and strips exc_info
    to make records picklable for multiprocessing. Since we use threads, we bypass this.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


# Use QueueHandler to prevent Loki HTTP requests from blocking the async event loop
log_queue = queue.Queue(-1)
queue_handler = LocalQueueHandler(log_queue)

# Attach ContextInjectingFilter to capture request_id before handing off to the background thread
queue_handler.addFilter(ContextInjectingFilter())

# Stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(structured_formatter)

# Only add loki_handler if it was successfully created
listener_handlers = [stream_handler]
if loki_handler is not None:
    listener_handlers.append(loki_handler)

listener = QueueListener(log_queue, *listener_handlers)
listener.start()

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(queue_handler)

# Route Uvicorn loggers to the queue handler so they are pushed to Loki
for logger_name in ("uvicorn", "uvicorn.error"):
    log = logging.getLogger(logger_name)
    log.handlers = [queue_handler]
    log.propagate = False

# Silence uvicorn.access entirely since we will log requests manually inside FastAPI with context
logging.getLogger("uvicorn.access").disabled = True

logger = logging.getLogger(__name__)


async def _handle_gateway_command(routing_key: str, data: dict) -> None:
    """Dispatch an incoming Gateway command to the matching service method."""
    user_id = data.get("UserId") or data.get("userId") or data.get("user_id")
    club_id = data.get("ClubId") or data.get("clubId") or data.get("club_id")

    if routing_key == "Gateway.calculate_missed_savings":
        service = DIContainer.get_insights_service()
        await service.calculate_missed_savings_async(
            user_id,
            time_filter=True,
            days=90,
            use_mock=False,
        )
    elif routing_key == "Gateway.calculate_matching_clubs":
        service = DIContainer.get_recommendation_service()
        await service.calculate_matching_clubs(user_id)
    else:
        logger.warning("Unhandled Gateway command routing key: %s", routing_key)


async def process_gateway_command(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    """Process a single Gateway→Personalization command message."""
    async with message.process():
        routing_key = message.routing_key or ""
        body = message.body.decode()
        data = json.loads(body)

        # Unwrap MassTransit envelope if present
        if "message" in data and isinstance(data["message"], dict):
            data = data["message"]

        user_id = data.get("UserId") or data.get("userId") or data.get("user_id") or "unknown"
        request_id_var.set(str(uuid.uuid4()))
        username_var.set(user_id)

        logger.info(
            "Gateway command received",
            extra={
                "reason": "RabbitMQ command consumed",
                "extra_data": {"routing_key": routing_key, "user_id": user_id},
            },
        )

        try:
            await _handle_gateway_command(routing_key, data)
        except Exception as e:
            logger.error(
                f"Error processing Gateway command '{routing_key}': {e}",
                exc_info=e,
                extra={"reason": "Command handler failure", "extra_data": {"routing_key": routing_key}},
            )
            raise


async def consume_gateway_commands() -> None:
    """Background task: consume Gateway recommendation commands from RabbitMQ."""
    try:
        connection = await aio_pika.connect_robust(settings.ConnectionStrings_Rabbit)
        channel    = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange("lessley_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue    = await channel.declare_queue(GATEWAY_COMMANDS_QUEUE, durable=True)
        await queue.bind(exchange, routing_key=GATEWAY_COMMANDS_PATTERN)

        logger.info(
            "Listening for Gateway commands on '%s'",
            GATEWAY_COMMANDS_PATTERN,
            extra={"reason": "Consumer started", "extra_data": {"queue": GATEWAY_COMMANDS_QUEUE}},
        )
        await queue.consume(process_gateway_command)
        await asyncio.Future()
    except Exception as e:
        logger.error(f"Gateway command consumer failed: {e}")


# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and load static data
    await init_db()
    await DIContainer.get_mcc_service().initialize()
    await DIContainer.get_recommendation_core_service().initialize()

    publisher_service = DIContainer.get_publisher_service()
    await publisher_service.initialize()

    consumer_task: asyncio.Task | None = None
    if settings.RabbitMQ_Enabled:
        consumer_task = asyncio.create_task(consume_gateway_commands())

    yield

    # Shutdown
    if consumer_task is not None:
        consumer_task.cancel()
    if publisher_service is not None:
        await publisher_service.close()

    gateway_client = DIContainer.get_open_finance_client()
    await gateway_client.close_client()
    await close_db()
    listener.stop()


# --- Rate Limiter Configuration ---
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# --- Application Initialization ---
_is_dev = settings.Environment.lower() == "development"
app = FastAPI(
    title="Lessley Personalization Engine",
    description="AI-driven financial gap analysis and recommendations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs"        if _is_dev else None,
    redoc_url="/redoc"      if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)

# --- CORS Configuration ---
allowed_origins = [
    origin.strip()
    for origin in settings.Cors_AllowOrigins.split(",")
    if origin and origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global Exception Handlers ---
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    endpoint_logger = logging.getLogger(__name__)
    endpoint_logger.warning(
        "Rate limit exceeded",
        exc_info=exc,
        extra={
            "reason": "Too many requests from client",
            "extra_data": {"detail": exc.detail},
        },
    )
    return JSONResponse(
        status_code=429,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={"detail": "Rate limit exceeded", "request_id": getattr(request.state, "request_id", "unknown")},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    endpoint_logger = logging.getLogger(__name__)
    level = "warning" if exc.status_code < 500 else "error"
    log_level_method = getattr(endpoint_logger, level)
    log_level_method(
        f"HTTP Exception {exc.status_code}: {exc.detail}",
        exc_info=exc,
        extra={
            "reason": "HTTP Error",
            "extra_data": {"error_type": "HTTPException", "status_code": exc.status_code},
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={"detail": exc.detail, "request_id": getattr(request.state, "request_id", "unknown")},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    endpoint_logger = logging.getLogger(__name__)
    endpoint_logger.warning(
        f"Validation error: {str(exc)}",
        exc_info=exc,
        extra={
            "reason": "Invalid request payload or parameters",
            "extra_data": {"error_type": "ValueError"},
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={"detail": str(exc), "request_id": getattr(request.state, "request_id", "unknown")},
    )


@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    endpoint_logger = logging.getLogger(__name__)
    endpoint_logger.error(
        f"Connection error: {str(exc)}",
        exc_info=exc,
        extra={
            "reason": "Failed to connect to external service",
            "extra_data": {"error_type": "ConnectionError"},
        },
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={
            "detail": "External service unavailable",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    endpoint_logger = logging.getLogger(__name__)
    endpoint_logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=exc,
        extra={
            "reason": "Unhandled exception during request processing",
            "extra_data": {"error_type": type(exc).__name__},
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", "unknown")},
    )


app.state.limiter = limiter

# --- Middleware Registration (order matters) ---
app.add_middleware(GatewayAuthMiddleware)     # Enforce gateway-only access
app.add_middleware(UnifiedContextMiddleware)  # Inject Request ID and logging context
app.include_router(mcc_controller.router)
app.include_router(open_finance_controller.router)
app.include_router(insights_controller.router)
app.include_router(recommendation_controller.router)
app.include_router(club_controller.router)
