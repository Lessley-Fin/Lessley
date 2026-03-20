import logging
import json
from typing import Any, Optional, Dict
from datetime import datetime
from middleware.log_context_middleware import request_id_var, username_var



class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with production-ready fields.

    Includes:
    - timestamp: ISO format datetime
    - app_name: Application name (personalization)
    - service_name: The class where logging occurred
    - message: Main log message
    - request_id: Trace ID for request correlation
    - username: User identifier
    - exception: Exception details if logging an error
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "app_name": "personalization",
            "service_name": record.name,
            "username": username_var.get(),
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
            "exception": self.formatException(record.exc_info) if record.exc_info else None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

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
        request_id_var.set("N/A")
        username_var.set("anonymous")

    @staticmethod
    def log_with_context(
        logger: logging.Logger,
        level: str,
        message: str,
        reason: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Any = None,
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
            exc_info: Exception details for error logging
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

        logger.log(log_level, message, extra=extra, exc_info=exc_info)


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
        exc_info=error,
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
