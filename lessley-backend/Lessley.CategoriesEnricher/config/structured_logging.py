import logging
import json
from typing import Optional
from datetime import datetime
from middleware.log_context_middleware import request_id_var, username_var


# Standard LogRecord attributes to ignore when extracting custom 'extra' fields
_STANDARD_LOG_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
    "color_message",
    "request_id",
    "username",  # Added to prevent duplication in extra
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
        logger.info(
            "User category enriched",
            extra={"reason": "Data enrichment", "extra_data": {"user_id": 123}}
        )
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base structured log payload
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "app_name": "categories_enricher",
            "service_name": record.name,
            "function_name": record.funcName,
            "filename": record.filename,
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
                "traceback": self.formatException(record.exc_info).split("\n"),
            }

        # Dynamically attach any custom fields provided via `logger.info(..., extra={...})`
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_ATTRS:
                log_obj[key] = value

        return json.dumps(log_obj, default=str)
