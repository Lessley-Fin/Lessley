from starlette.middleware.base import BaseHTTPMiddleware
import contextvars

request_id_var = contextvars.ContextVar("request_id", default="N/A")
username_var = contextvars.ContextVar("username", default="anonymous")

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        req_id = getattr(request.state, "request_id", "N/A")
        user_id = request.headers.get("X-User-ID", "anonymous")
        
        token1 = request_id_var.set(req_id)
        token2 = username_var.set(user_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            request_id_var.reset(token1)
            username_var.reset(token2)