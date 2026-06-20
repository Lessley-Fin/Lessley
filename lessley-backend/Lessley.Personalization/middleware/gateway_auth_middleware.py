from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from config.settings import settings

_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Rejects requests that do not carry the expected X-Gateway-Key header.

    Only active when Gateway_ApiKey is configured in settings. This ensures
    the Personalization service is unreachable directly from the internet.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.Gateway_ApiKey or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        key = request.headers.get("X-Gateway-Key")
        if key != settings.Gateway_ApiKey:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: direct access to this service is not allowed"},
            )

        return await call_next(request)
