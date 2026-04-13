from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import contextvars
import uuid
import time
import logging

request_id_var = contextvars.ContextVar("request_id", default="N/A")
username_var = contextvars.ContextVar("username", default="anonymous")

class UnifiedContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        # 1. Extract or generate Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        status_code = 500

        # 2. Extract username
        username = "anonymous"
        if "user_id" in request.query_params:
            username = request.query_params.get("user_id")
        elif "X-Username" in request.headers:
            username = request.headers.get("X-Username")
        elif hasattr(request.state, "user"):
            username = getattr(request.state.user, "username", "anonymous")

        # 3. Store in request.state for downstream usage
        request.state.request_id = request_id
        request.state.username = username

        # 4. Set context variables for logs
        req_token = request_id_var.set(request_id)
        user_token = username_var.set(username)
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            # 5. Append Request ID to the response headers
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
           # 6. Log request summary before clearing context
            process_time_ms = (time.time() - start_time) * 1000
            req_logger = logging.getLogger("api.request")
            
            query = request.url.query
            full_path = f"{request.url.path}?{query}" if query else request.url.path
            
            req_logger.info(
                f"HTTP {request.method} {full_path} responded {status_code} in {process_time_ms:.2f} ms",
                extra={
                    "reason": "HTTP Request Summary",
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "query": query,
                        "status_code": status_code,
                        "process_time_ms": round(process_time_ms, 2)
                    }
                }
            )

            # 7. Safely reset context variables
            request_id_var.reset(req_token)
            username_var.reset(user_token)