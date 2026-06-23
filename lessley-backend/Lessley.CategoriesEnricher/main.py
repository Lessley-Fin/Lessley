from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
import logging
from logging.handlers import QueueHandler, QueueListener
import queue
from config.structured_logging import StructuredFormatter, ContextInjectingFilter
from routers import categories_controller
from middleware.log_context_middleware import UnifiedContextMiddleware

# --- Logging Configuration ---
structured_formatter = StructuredFormatter()


class LocalQueueHandler(QueueHandler):
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


log_queue = queue.Queue(-1)
queue_handler = LocalQueueHandler(log_queue)
queue_handler.addFilter(ContextInjectingFilter())

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(structured_formatter)

listener = QueueListener(log_queue, stream_handler)
listener.start()

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(queue_handler)

for logger_name in ("uvicorn", "uvicorn.error"):
    log = logging.getLogger(logger_name)
    log.handlers = [queue_handler]
    log.propagate = False

logging.getLogger("uvicorn.access").disabled = True

logger = logging.getLogger(__name__)


# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    listener.stop()


# --- Rate Limiter Configuration ---
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# --- Application Initialization ---
app = FastAPI(
    title="Lessley Categories Enricher",
    description="Transaction category enrichment service",
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
app.add_middleware(UnifiedContextMiddleware)
app.include_router(categories_controller.router)
