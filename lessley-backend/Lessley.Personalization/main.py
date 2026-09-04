from contextlib import asynccontextmanager
import asyncio
import json
from fastapi import FastAPI, status, Request
import aio_pika
import httpx
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
from config.constants import LIMITS
from config.settings import settings
from config.structured_logging import StructuredFormatter, ContextInjectingFilter
from routers import open_finance_controller
from routers import mcc_controller
from routers import insights_controller
from database.db_client import init_db, close_db
from middleware.log_context_middleware import UnifiedContextMiddleware, request_id_var, username_var
from middleware.edge_auth_middleware import EdgeAuthMiddleware, dev_bypass_active
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


def _field(data: dict, *names):
    """Read a field whichever casing the publisher used.

    The Gateway publishes these commands as raw JSON, so whether a property arrives as
    "UserId", "userId" or "user_id" depends on serializer configuration on the far side of
    the bus. Reading every spelling keeps a change over there from degrading into a silent
    fallback — which for a window size means calculating the wrong period and saying nothing.
    """
    for name in names:
        value = data.get(name)
        if value is not None:
            return value
    return None


async def _handle_gateway_command(routing_key: str, data: dict) -> None:
    """Dispatch an incoming Gateway command to the matching service method."""
    user_id = _field(data, "UserId", "userId", "user_id")

    if routing_key == "Gateway.calculate_user_categories":
        days = _field(data, "Days", "days") or LIMITS.DAYS
        service = DIContainer.get_insights_service()
        categories = await service.calculate_user_categories_async(user_id, time_filter=True, days=days)

        # The command path is the only thing that writes tags. The same calculation served
        # over HTTP publishes nothing, so a client reading its own insights can never move
        # the stored profile out from under the Gateway.
        tags = service.extract_mcc_tags(categories)

        if tags:
            await DIContainer.get_publisher_service().publish_user_tag_assigned(user_id, tags)
            return

        # An empty result is ambiguous and must not clear anything on its own. Open Finance
        # answers with [] both for a user who has no bank linked and for one whose data it
        # simply cannot produce right now — the two are indistinguishable from here. That was
        # tolerable while only a user's own actions triggered a recalculation; the weekly sweep
        # asks for every user at once, so one bad Monday would unsubscribe the entire user base
        # from every notification group, silently and with nothing in the logs looking wrong.
        #
        # Retaining a stale tag costs one irrelevant notification. Clearing wrongly costs all
        # of them. Genuinely disconnecting a bank should clear tags through an explicit unlink
        # signal, not through an absence we inferred.
        existing = await DIContainer.get_user_repository().get_user_tags(user_id)
        if existing:
            logger.warning(
                "Calculation returned no categories for a user who has tags — leaving them in place",
                extra={
                    "reason": "Ambiguous empty result",
                    "extra_data": {"user_id": user_id, "existing_tag_count": len(existing)},
                },
            )
        else:
            # A user who has never been tagged and produced nothing this time. Usually a new
            # account whose bank data has not landed yet: both the registration and the
            # bank-journey trigger fire before Open Finance can answer, so the first
            # calculations of a user's life legitimately come back empty.
            #
            # Logged because this path used to return in silence, which made a first-run
            # failure indistinguishable from one that never ran. Info, not warning — for a user
            # with no bank linked this is the correct and expected outcome, and the client asks
            # again once accounts appear.
            logger.warning(
                "Calculation returned no categories for a user who has none — nothing to store",
                extra={
                    "reason": "Empty result for an untagged user",
                    "extra_data": {"user_id": user_id},
                },
            )
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


async def refresh_reference_data() -> None:
    """Background task: rebuild the clubs/stores/deals cache so newly scraped deals appear.

    The cache is read thousands of times per calculation and must never wait on Mongo, so it
    is rebuilt on a timer rather than revalidated per request. A failed rebuild is logged and
    the loop continues — ``load_async`` only publishes a complete snapshot, so the previous
    one keeps serving rather than the service falling back to empty reference data.
    """
    repository = DIContainer.get_reference_data_repository()

    while True:
        await asyncio.sleep(settings.ReferenceData_RefreshSeconds)
        try:
            await repository.load_async(force=True)
        except Exception as e:
            logger.error(
                f"Reference data refresh failed, keeping the previous snapshot: {e}",
                exc_info=e,
                extra={"reason": "Scheduled refresh failure", "extra_data": {}},
            )


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
    await DIContainer.get_reference_data_repository().load_async()

    publisher_service = DIContainer.get_publisher_service()
    await publisher_service.initialize()

    consumer_task: asyncio.Task | None = None
    if settings.RabbitMQ_Enabled:
        consumer_task = asyncio.create_task(consume_gateway_commands())

    refresh_task: asyncio.Task | None = None
    if settings.ReferenceData_RefreshSeconds > 0:
        refresh_task = asyncio.create_task(refresh_reference_data())

    yield

    # Shutdown
    if consumer_task is not None:
        consumer_task.cancel()
    if refresh_task is not None:
        refresh_task.cancel()
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


@app.exception_handler(httpx.HTTPStatusError)
async def upstream_http_error_handler(request: Request, exc: httpx.HTTPStatusError):
    """An upstream API refusing a request is a bad gateway, not an internal fault of ours."""
    endpoint_logger = logging.getLogger(__name__)
    upstream_status = exc.response.status_code
    endpoint_logger.error(
        f"Upstream service returned {upstream_status} for {exc.request.url}",
        extra={
            "reason": "External API call failed",
            "extra_data": {
                "error_type": "HTTPStatusError",
                "upstream_status": upstream_status,
                "upstream_url": str(exc.request.url),
            },
        },
    )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        content={
            "detail": f"Upstream service error ({upstream_status})",
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
app.add_middleware(EdgeAuthMiddleware)        # Enforce edge-only access
app.add_middleware(UnifiedContextMiddleware)  # Inject Request ID and logging context

if dev_bypass_active():
    logging.getLogger(__name__).warning(
        "EDGE VERIFICATION BYPASSED — X-Edge-Key is not required and identity falls back to "
        "decoding the access_token cookie directly. Development only; never enable "
        "Edge_AllowUnverified outside local debugging."
    )
app.include_router(mcc_controller.router)
app.include_router(open_finance_controller.router)
app.include_router(insights_controller.router)
