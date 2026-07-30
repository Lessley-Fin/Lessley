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

    if dev_bypass_active():
        dev_email = (settings.Dev_AuthEmail or "").strip()
        if dev_email:
            return dev_email
        # The bypass is on but has no identity to hand back. Say so explicitly — the
        # generic 401 below sends people hunting for an auth bug that isn't there.
        raise HTTPException(
            status_code=401,
            detail=(
                "Dev bypass is active but Dev_AuthEmail is not set. Add "
                "Dev_AuthEmail=<your user's email> to Lessley.Personalization/.env"
            ),
        )

    logger.warning(
        "Request reached a user-scoped route without a verified identity",
        extra={
            "reason": f"Missing {AUTH_EMAIL_HEADER}",
            "extra_data": {"path": request.url.path},
        },
    )
    raise HTTPException(
        status_code=401,
        detail=(
            "Unauthenticated: no verified identity. Call through Caddy, or for local "
            "debugging set Environment=Development and Edge_AllowUnverified=True."
        ),
    )
