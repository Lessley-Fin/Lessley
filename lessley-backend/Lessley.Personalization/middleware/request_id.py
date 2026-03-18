import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from config.structured_logging import StructuredLogger
import logging


logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Extract username from query params, headers, or user context
        username = None
        if "user_id" in request.query_params:
            username = request.query_params.get("user_id")
        elif "X-Username" in request.headers:
            username = request.headers.get("X-Username")
        elif hasattr(request.state, "user"):
            username = getattr(request.state.user, "username", None)

        # Store in request state for endpoint access
        request.state.request_id = request_id
        if username:
            request.state.username = username

        # Set context variables for structured logging
        StructuredLogger.set_request_context(request_id, username)

        try:
            response = await call_next(request)
        finally:
            # Clear context after request
            StructuredLogger.clear_request_context()

        response.headers["X-Request-ID"] = request_id
        return response
