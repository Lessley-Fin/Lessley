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
import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import logging_loki
from services.di_container import DIContainer
from config.settings import settings
from config.structured_logging import StructuredFormatter, ContextInjectingFilter
from routers import open_finance_controller  # Import your new controller
from routers import mcc_controller  # Import your new controller
from routers import insights_controller  # Import your new controller
from routers import recommendation_controller  # Import recommendation controller
from routers import club_controller  # Import club controller
from database.db_client import init_db, close_db
from middleware.log_context_middleware import UnifiedContextMiddleware, request_id_var, username_var
from services.rabbitmq_publisher import RabbitMQPublisher
import uuid

# --- RabbitMQ Configuration ---
QUEUE_NAME = "personalize_calc_history_queue"
ROUTING_KEY = "Personalize.calc_history"

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


async def process_calc_history_message(message: aio_pika.abc.AbstractIncomingMessage):
    """
    This function is triggered every time a message hits the queue.
    """
    async with message.process():
        body = message.body.decode()
        data = json.loads(body)
        user_id = data.get("user_id")

        # Set context variables for background RabbitMQ task logs
        request_id_var.set(str(uuid.uuid4()))
        username_var.set(user_id or "anonymous")

        logger.info(
            "Calculation request received",
            extra={
                "reason": "RabbitMQ message processed",
                "extra_data": {"user_id": user_id, "message_type": "calc_history"},
            },
        )
        # TODO: 1. Fetch Open Finance Data for this user
        # TODO: 2. Run Gap Analysis & Logic Check via Optimizer
        # TODO: 3. Publish personalize.money_calc or personalize.suggestion


async def consume_rabbitmq():
    """
    Background task to maintain the RabbitMQ connection and listen for events.
    """
    try:
        connection = await aio_pika.connect_robust(settings.ConnectionStrings_Rabbit)
        channel = await connection.channel()

        # Declare the exchange and queue to ensure they exist
        exchange = await channel.declare_exchange("lessley_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        # Bind the queue to the specific event topic
        await queue.bind(exchange, routing_key=ROUTING_KEY)

        logger.info(f"[*] Waiting for messages on '{ROUTING_KEY}' in {settings.Environment} mode. To exit press CTRL+C")
        await queue.consume(process_calc_history_message)

        # Keep the connection open indefinitely
        await asyncio.Future()
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}")


# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and fetch setup data
    await init_db()
    await DIContainer.get_mcc_service().initialize()
    await DIContainer.get_recommendation_core_service().initialize()

    if settings.RabbitMQ_Enabled:
        # Start publisher so services can emit events to other Lessley services
        publisher = await RabbitMQPublisher.create(settings.ConnectionStrings_Rabbit)
        app.state.publisher = publisher

        # Start consumer as a background task
        task = asyncio.create_task(consume_rabbitmq())
        yield

        # Shutdown
        task.cancel()
        await publisher.close()
    else:
        app.state.publisher = None
        yield

    # Shutdown
    client = DIContainer.get_open_finance_client()
    await client.close_client()  # Ensure the HTTP client is properly closed on shutdown
    await close_db()
    listener.stop()  # Gracefully stop the logging queue listener


# --- Rate Limiter Configuration ---
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# --- Application Initialization ---
app = FastAPI(
    title="Lessley Personalization Engine",
    description="AI-driven financial gap analysis and recommendations",
    version="1.0.0",
    lifespan=lifespan,
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
app.add_middleware(UnifiedContextMiddleware)  # Inject Request ID and logging context
app.include_router(mcc_controller.router)
app.include_router(open_finance_controller.router)
app.include_router(insights_controller.router)
app.include_router(recommendation_controller.router)
app.include_router(club_controller.router)
