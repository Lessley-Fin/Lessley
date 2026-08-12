"""Edge-only access enforcement — the same control Personalization applies.

Ported from ``Lessley.Personalization/middleware/edge_auth_middleware.py``; keep the
two in step. The optimizer is exposed at the edge on ``/api/v1/optimizer/*``, so it
needs the identical guarantee: a request that did not come through Caddy is refused.
"""

from __future__ import annotations

import logging

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .settings import settings

logger = logging.getLogger(__name__)

EDGE_KEY_HEADER = "X-Edge-Key"

# /optimizer/health is the container healthcheck's target — Docker calls it directly,
# with no edge in between. The docs paths are only ever reachable on the dev-published
# port: Caddy routes /api/v1/optimizer/* and nothing else, so they cannot be hit
# through the edge at all.
_EXEMPT_PATHS = {"/optimizer/health", "/docs", "/openapi.json", "/redoc"}


def dev_bypass_active() -> bool:
    """
    True only when BOTH the environment is Development and the bypass is explicitly enabled.

    Two independent conditions, so neither a stray flag nor a mis-set environment opens
    production on its own. Shared with the identity dependency so the two cannot disagree.

    Case-insensitive to match the compose files, which use "Development" and "Production".
    """
    return settings.Environment.lower() == "development" and settings.Edge_AllowUnverified


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
                "Rejected request that did not come through the edge (path=%s method=%s)",
                request.url.path,
                request.method,
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: requests must arrive through the edge"},
            )

        return await call_next(request)
