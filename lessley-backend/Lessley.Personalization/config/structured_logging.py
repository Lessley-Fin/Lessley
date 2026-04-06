import logging
import json
from typing import Any, Optional, Dict
from datetime import datetime
from middleware.log_context_middleware import request_id_var, username_var


# Standard LogRecord attributes to ignore when extracting custom 'extra' fields
_STANDARD_LOG_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    "color_message",
    "request_id", "username"  # Added to prevent duplication in extra
}


class ContextInjectingFilter(logging.Filter):
    """
    Injects ContextVars into the LogRecord in the calling thread.
    This is essential when using QueueHandler so that thread-local context isn't lost.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("N/A")
        record.username = username_var.get("anonymous")
        return True

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with production-ready fields.
    
    It automatically captures any custom context passed via the standard Python
    logging 'extra' parameter, promoting clean, native logging practices.
    
    Example:
        logger.info("User logged in", extra={"reason": "Auth API", "user_id": 123})
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base structured log payload
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "app_name": "personalization",
            "service_name": record.name,
            "username": getattr(record, "username", username_var.get("anonymous")),
            "request_id": getattr(record, "request_id", request_id_var.get("N/A")),
            "message": record.getMessage(),
        }

        # Inject exception trace if an error occurred
        if record.exc_info:
            exc_type, exc_val, _ = record.exc_info
            
            # Format exception into a readable structured dictionary with an array for the traceback
            log_obj["exception"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": str(exc_val),
                "traceback": self.formatException(record.exc_info).split("\n")
            }

        # Dynamically attach any custom fields provided via `logger.info(..., extra={...})`
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_ATTRS:
                log_obj[key] = value

        return json.dumps(log_obj, default=str)


class StructuredLogger:
    """
    Provides utilities for request context tracking and backwards-compatible logging methods.
    
    BEST PRACTICE:
        Instead of calling `StructuredLogger.log_with_context(...)`, simply use the standard 
        Python logging module:
        
        logger.info("Message", extra={"reason": "...", "extra_data": {...}})
    """

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a standard logger instance."""
        return logging.getLogger(name)

    @staticmethod
    def set_request_context(request_id: str, username: Optional[str] = None) -> None:
        """Set request context variables for all subsequent logs in this scope."""
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
        Backwards-compatible wrapper for legacy structured logging calls.
        
        RECOMMENDED: Use pure python standard logging:
        `logger.<level>(message, extra={'reason': ..., 'extra_data': ...})`
        """
        log_level = getattr(logging, level.upper(), logging.INFO)

        # Consolidate additional kwargs into extra_data for cleaner grouping
        combined_extra_data = {**(extra_data or {}), **kwargs}
        
        extra: Dict[str, Any] = {}
        if reason:
            extra["reason"] = reason
        if combined_extra_data:
            extra["extra_data"] = combined_extra_data

        logger.log(log_level, message, extra=extra, exc_info=exc_info)


# --- Common logging helper functions using standard logging best practices ---


def log_service_call(
    logger: logging.Logger, service_name: str, method_name: str, params: Optional[Dict] = None
) -> None:
    """Log when a service method is called."""
    data = {"service": service_name, "method": method_name}
    if params:
        data.update(params)

    logger.info(
        f"Service method called: {method_name}",
        extra={
            "reason": f"Method invocation in {service_name}",
            "extra_data": data
        }
    )


def log_service_error(
    logger: logging.Logger, service_name: str, method_name: str, error: Exception, context: Optional[Dict] = None
) -> None:
    """Log service errors with full context."""
    data = {"service": service_name, "method": method_name}
    if context:
        data.update(context)

    logger.error(
        f"Error in {service_name}.{method_name}: {str(error)}",
        exc_info=error,
        extra={
            "reason": "Service execution failure",
            "extra_data": data
        }
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

    logger.info(
        f"API request: {method} {endpoint}",
        extra={
            "reason": "Request received",
            "extra_data": data
        }
    )


def log_api_response(
    logger: logging.Logger, endpoint: str, status_code: int, response_time_ms: float, record_count: Optional[int] = None
) -> None:
    """Log API response."""
    data = {
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time_ms": response_time_ms
    }
    if record_count is not None:
        data["record_count"] = record_count

    logger.info(
        f"API response: {status_code}",
        extra={
            "reason": "Request completed",
            "extra_data": data
        }
    )
