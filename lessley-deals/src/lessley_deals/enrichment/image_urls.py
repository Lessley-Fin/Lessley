from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

#: Hosts the edge is willing to render an image from.
#:
#: This list is the twin of ``img-src`` in ``lessley-cd/Caddyfile``: a URL stored here
#: that is missing there renders as the category emoji instead of a picture, and a URL
#: allowed there but rejected here never reaches the browser at all. Change both, or
#: neither.
#:
#: Exact hosts rather than wildcard parent domains, deliberately. A new subdomain is a
#: rare event that degrades to the emoji fallback rather than a broken page, and the
#: edge reports the block to ``/api/v1/csp-report`` — so it surfaces in the log the
#: first time it happens instead of silently widening what a scraped page may point at.
ALLOWED_IMAGE_HOSTS: frozenset[str] = frozenset(
    {
        "cdn.hot.co.il",
        "pics.k4a.co.il",
        "www.topcash.co.il",
        "media.dolcemaster.co.il",
        "www.mastercard.com",
        "www.mastercard.co.il",
    }
)


def clean_image_url(url: str | None) -> str | None:
    """Return `url` if the browser will actually load it, else None.

    Image URLs arrive verbatim from whatever a scraped page put in `image_url`, and
    they end up as `<img src>` in every user's browser. Two things are rejected here:

    * anything not `https://<allowlisted host>` — a compromised or hostile source page
      would otherwise turn every deal card into a request to a host of its choosing;
    * root-relative paths like `/Image/<uuid>.png`, which the scraper has stored before.
      Those resolve against Lessley's own origin, hit the SPA history fallback, and come
      back as `index.html` — an "image" that can only ever fail to decode.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        logger.debug("Rejecting unparseable image_url: %r", url)
        return None

    # Plaintext images on an HTTPS page are blocked as mixed content anyway, so an
    # http:// URL is dead weight at best and a downgrade channel at worst.
    if parsed.scheme != "https":
        logger.debug("Rejecting non-https image_url: %r", url)
        return None

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_IMAGE_HOSTS:
        logger.info("Rejecting image_url from unlisted host %r: %r", host, url)
        return None

    return url
