from contextlib import asynccontextmanager
import asyncio
import json
from fastapi import FastAPI, status, Request
import aio_pika
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import logging_loki
from services.di_container import DIContainer
from middleware.request_id import RequestIDMiddleware
from config.settings import settings
from routers import open_finance_controller  # Import your new controller
from routers import mcc_controller  # Import your new controller
from routers import insights_controller  # Import your new controller

# --- RabbitMQ Configuration ---
QUEUE_NAME = "personalize_calc_history_queue"
ROUTING_KEY = "Personalize.calc_history"

# --- Logging Configuration ---
loki_handler = logging_loki.LokiHandler(
    url=settings.Loki_Url,
    tags={"Application": "lessley-personalization", "environment": getattr(settings, "Environment", "dev")},
    version="1",
)

# Use QueueHandler to prevent Loki HTTP requests from blocking the async event loop
log_queue = queue.Queue(-1)
queue_handler = QueueHandler(log_queue)
listener = QueueListener(log_queue, logging.StreamHandler(), loki_handler)
listener.start()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[queue_handler]
)

# Route Uvicorn loggers to the queue handler so they are pushed to Loki
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    log = logging.getLogger(logger_name)
    log.handlers = [queue_handler]
    log.propagate = False
logger = logging.getLogger(__name__)

async def process_calc_history_message(message: aio_pika.abc.AbstractIncomingMessage):
    """
    This function is triggered every time a message hits the queue.
    """
    async with message.process():
        body = message.body.decode()
        data = json.loads(body)
        user_id = data.get("user_id")

        logger.info(f"[x] Received calculation request for User: {user_id}")
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
    if settings.RabbitMQ_Enabled:
        # Startup: Launch the RabbitMQ consumer as a background task
        task = asyncio.create_task(consume_rabbitmq())
        yield
        # Shutdown: Clean up tasks when the server stops
        task.cancel()
    else:
        yield

    client = DIContainer.get_open_finance_client()
    await client.close_client()  # Ensure the HTTP client is properly closed on shutdown
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
    request_id = getattr(request.state, "request_id", "unknown")
    logger = logging.getLogger(__name__)
    logger.warning(f"[{request_id}] Rate limit exceeded: {exc.detail}")
    return JSONResponse(
        status_code=429,
        headers={"X-Request-ID": request_id},
        content={"detail": "Rate limit exceeded", "request_id": request_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger = logging.getLogger(__name__)
    logger.warning(f"[{request_id}] Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        headers={"X-Request-ID": request_id},
        content={"detail": str(exc), "request_id": request_id},
    )


@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger = logging.getLogger(__name__)
    logger.error(f"[{request_id}] Connection error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"X-Request-ID": request_id},
        content={"detail": "External service unavailable", "request_id": request_id},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger = logging.getLogger(__name__)
    logger.error(f"[{request_id}] Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={"detail": "Internal server error", "request_id": request_id},
    )


app.state.limiter = limiter

# --- Middleware Registration (order matters) ---
app.add_middleware(RequestIDMiddleware)  # Add first so request_id is available to other middleware
app.include_router(mcc_controller.router)
app.include_router(open_finance_controller.router)
app.include_router(insights_controller.router)


@app.on_event("startup")
async def startup_event():
    """Validate dependencies on startup"""
    logger = logging.getLogger(__name__)

    # Check config
    if not settings.OpenFinanceConfig_BaseUrl:
        logger.error("Missing OpenFinanceConfig_BaseUrl")
        raise ValueError("Required config missing")

    # Check MCC service can load
    try:
        mcc_service = DIContainer.get_mcc_service()
        logger.info(f"MCC service initialized with {len(mcc_service.get_mcc())} codes")
    except Exception as e:
        logger.error(f"Failed to initialize MCC service: {e}")
        raise

    # Check external API connectivity
    try:
        await DIContainer.get_open_finance_client()._get_client()
        # Simple ping/health check
        logger.info("Open Finance API connectivity verified")
    except Exception as e:
        logger.warning(f"Open Finance API connectivity check failed: {e}")
        # Don't fail startup, but log warning


# --- REST Endpoints ---
@app.get("/health")
async def health_check():
    """Simple HTTP endpoint for the API Gateway to verify the service is alive."""
    # Returning data from our config to prove it works!
    return {
        "status": "healthy",
        "environment": settings.Environment,
        "rabbitmq_configured": bool(settings.ConnectionStrings_Rabbit),
    }
