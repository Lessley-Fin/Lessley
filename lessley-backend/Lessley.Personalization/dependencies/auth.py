import logging

from fastapi import HTTPException, Request

from config.settings import settings
from middleware.edge_auth_middleware import dev_bypass_active

logger = logging.getLogger(__name__)

AUTH_EMAIL_HEADER = "X-Auth-Email"


def authenticated_email(request: Request) -> str:
    """
    The caller's identity, as established by the edge.

    Caddy authenticates every request against the Gateway before forwarding it and injects
    X-Auth-Email from the verified JWT claims, stripping any value the client tried to send.
    Routes MUST take identity from here and never from a query parameter or body field —
    that is the whole reason this service can be exposed at the edge at all.
    """
    email = (request.headers.get(AUTH_EMAIL_HEADER) or "").strip()
    if email:
        return email

    if dev_bypass_active() and settings.Dev_AuthEmail:
        return settings.Dev_AuthEmail

    logger.warning(
        "Request reached a user-scoped route without a verified identity",
        extra={
            "reason": f"Missing {AUTH_EMAIL_HEADER}",
            "extra_data": {"path": request.url.path},
        },
    )
    raise HTTPException(status_code=401, detail="Unauthenticated: no verified identity")
