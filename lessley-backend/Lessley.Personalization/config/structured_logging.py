import logging
import json
import contextvars
from typing import Any, Optional, Dict
from datetime import datetime

# Context variables for request-scoped data
request_id_var = contextvars.ContextVar("request_id", default=None)
username_var = contextvars.ContextVar("username", default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with production-ready fields.

    Includes:
    - timestamp: ISO format datetime
    - service: Application name (Personalization)
    - class_name: The class where logging occurred
    - level: Log level (INFO, ERROR, etc.)
    - message: Main log message
    - request_id: Trace ID for request correlation
    - username: User identifier
    - reason: Additional context about why this log occurred
    - exception: Exception details if logging an error
    - extra_data: Any additional structured data
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "Personalization",
            "level": record.levelname,
            "message": record.getMessage(),
            "class_name": record.name.split(".")[-1],
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request_id if available
        if request_id := request_id_var.get():
            log_obj["request_id"] = request_id

        # Add username if available
        if username := username_var.get():
            log_obj["username"] = username

        # Add reason if provided in extra
        if hasattr(record, "reason"):
            log_obj["reason"] = record.reason

        # Add exception details if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add any extra structured data
        if hasattr(record, "extra_data") and record.extra_data:
            log_obj["extra_data"] = record.extra_data

        return json.dumps(log_obj, default=str)


class StructuredLogger:
    """
    Wrapper around Python logger to provide structured logging with context propagation.

    Usage:
        logger = StructuredLogger.get_logger(__name__)
        logger.info("User login successful", username="john.doe", reason="API request")
    """

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance with structured formatting."""
        logger = logging.getLogger(name)
        return logger

    @staticmethod
    def set_request_context(request_id: str, username: Optional[str] = None) -> None:
        """
        Set request context variables for all subsequent logs in this context.

        Should be called from middleware for each request.
        """
        request_id_var.set(request_id)
        if username:
            username_var.set(username)

    @staticmethod
    def clear_request_context() -> None:
        """Clear request context variables."""
        request_id_var.set(None)
        username_var.set(None)

    @staticmethod
    def log_with_context(
        logger: logging.Logger,
        level: str,
        message: str,
        reason: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """
        Log with additional structured context.

        Args:
            logger: Logger instance
            level: Log level (info, error, warning, debug)
            message: Main log message
            reason: Context about why this occurred
            extra_data: Additional structured data as dictionary
            **kwargs: Additional fields to include
        """
        log_level = getattr(logging, level.upper(), logging.INFO)

        extra = {}
        if reason:
            extra["reason"] = reason
        if extra_data:
            extra["extra_data"] = extra_data

        # Add any other kwargs
        for key, value in kwargs.items():
            if key not in ["reason", "extra_data"]:
                if "extra_data" not in extra:
                    extra["extra_data"] = {}
                extra["extra_data"][key] = value

        logger.log(log_level, message, extra=extra)


# Helper functions for common logging scenarios


def log_service_call(
    logger: logging.Logger, service_name: str, method_name: str, params: Optional[Dict] = None
) -> None:
    """Log when a service method is called."""
    StructuredLogger.log_with_context(
        logger,
        "info",
        f"Service method called: {method_name}",
        reason=f"Method invocation in {service_name}",
        extra_data={"service": service_name, "method": method_name, **(params or {})},
    )


def log_service_error(
    logger: logging.Logger, service_name: str, method_name: str, error: Exception, context: Optional[Dict] = None
) -> None:
    """Log service errors with full context."""
    StructuredLogger.log_with_context(
        logger,
        "error",
        f"Error in {service_name}.{method_name}: {str(error)}",
        reason=f"Service execution failure",
        extra_data={"service": service_name, "method": method_name, **(context or {})},
    )


def log_api_request(
    logger: logging.Logger, endpoint: str, method: str, user_id: Optional[str] = None, params: Optional[Dict] = None
) -> None:
    """Log API request start."""
    data = {"endpoint": endpoint, "method": method}
    if user_id:
        data["user_id"] = user_id
    if params:
        data.update(params)

    StructuredLogger.log_with_context(
        logger, "info", f"API request: {method} {endpoint}", reason="Request received", extra_data=data
    )


def log_api_response(
    logger: logging.Logger, endpoint: str, status_code: int, response_time_ms: float, record_count: Optional[int] = None
) -> None:
    """Log API response."""
    data = {"endpoint": endpoint, "status_code": status_code, "response_time_ms": response_time_ms}
    if record_count is not None:
        data["record_count"] = record_count

    StructuredLogger.log_with_context(
        logger, "info", f"API response: {status_code}", reason="Request completed", extra_data=data
    )
