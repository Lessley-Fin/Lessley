import logging

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.settings import settings

logger = logging.getLogger(__name__)

EDGE_KEY_HEADER = "X-Edge-Key"

_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def dev_bypass_active() -> bool:
    """
    True only when BOTH the environment is Development and the bypass is explicitly enabled.

    Two independent conditions, so neither a stray flag nor a mis-set environment opens
    production on its own. Shared with the identity dependency so the two cannot disagree.
    """
    return settings.Environment == "Development" and settings.Edge_AllowUnverified


class EdgeAuthMiddleware(BaseHTTPMiddleware):
    """Rejects requests that did not arrive through the edge (Caddy).

    The edge terminates TLS, authenticates the caller against the Gateway, and stamps
    X-Edge-Key on the way in. A caller reaching this service directly cannot produce it.

    This is defense in depth — the primary control is that only the edge publishes ports.
    It exists so a stray `ports:` entry or a network-policy regression cannot silently
    expose an unauthenticated service.
    """

    async def dispatch(self, request: Request, call_next):
        if dev_bypass_active() or not settings.Edge_ApiKey or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        if request.headers.get(EDGE_KEY_HEADER) != settings.Edge_ApiKey:
            logger.warning(
                "Rejected request that did not come through the edge",
                extra={
                    "reason": "Missing or invalid edge key",
                    "extra_data": {"path": request.url.path, "method": request.method},
                },
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: requests must arrive through the edge"},
            )

        return await call_next(request)
