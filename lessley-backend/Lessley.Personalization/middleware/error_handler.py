from functools import wraps
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def handle_service_errors(logger_name: str = "service"):
    """Decorator to handle common service errors"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger_instance = logging.getLogger(logger_name)
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                logger_instance.warning(f"Validation error: {e}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            except ConnectionError as e:
                logger_instance.error(f"Connection error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External service unavailable"
                )
            except Exception as e:
                logger_instance.error(f"Unexpected error: {e}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        return wrapper

    return decorator
