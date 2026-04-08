from config.structured_logging import StructuredFormatter
import logging
import sys

# Setup structured formatter for JSON logs
formatter = StructuredFormatter()

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear existing handlers
root_logger.handlers.clear()

# Add stream handler with structured formatter
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

# Suppress debug logs from external libraries
logging.getLogger("aio_pika").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("pika").setLevel(logging.WARNING)
