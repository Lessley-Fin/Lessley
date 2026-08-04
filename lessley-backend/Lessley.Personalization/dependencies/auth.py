import base64
import binascii
import json
import logging

from fastapi import HTTPException, Request

from middleware.edge_auth_middleware import dev_bypass_active

logger = logging.getLogger(__name__)

AUTH_EMAIL_HEADER = "X-Auth-Email"

# Same cookie the Gateway issues (Lessley.Gateway.Api/Configuration/AuthCookieNames.Access).
# It reaches this service unmodified whether Caddy fronts it or not, since a reverse proxy
# forwards the Cookie header either way.
ACCESS_TOKEN_COOKIE = "access_token"

# The Gateway writes claims under ClaimTypes.Email, and JwtSecurityTokenHandler serializes
# claims under their full ClaimTypes URI rather than shortening them.
JWT_EMAIL_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"


def email_from_access_token(request: Request) -> str | None:
    """
    Best-effort identity for dev bypass: decode (never verify) the access_token cookie and
    read its email claim.

    Only ever consulted while dev_bypass_active(). This service has no copy of the Gateway's
    signing key, so it cannot verify the token's signature — that's fine here because the
    bypass already means nothing in this request path is trusted for authorization, only
    used to know whose data to serve locally.
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        return None

    try:
        _, payload_b64, _ = token.split(".")
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        return None

    email = payload.get(JWT_EMAIL_CLAIM)
    return email.strip() if isinstance(email, str) and email.strip() else None


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
        dev_email = email_from_access_token(request)
        if dev_email:
            return dev_email
        # The bypass is on but has no identity to hand back. Say so explicitly — the
        # generic 401 below sends people hunting for an auth bug that isn't there.
        raise HTTPException(
            status_code=401,
            detail=(
                "Dev bypass is active but no access_token cookie with an email claim was "
                "found. Log in through the Gateway first so its cookie reaches this service."
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
