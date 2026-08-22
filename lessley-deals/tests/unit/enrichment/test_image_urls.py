from __future__ import annotations

import pytest

from lessley_deals.enrichment.image_urls import ALLOWED_IMAGE_HOSTS, clean_image_url


@pytest.mark.parametrize("host", sorted(ALLOWED_IMAGE_HOSTS))
def test_allows_every_listed_host(host: str) -> None:
    url = f"https://{host}/Image/logo.png"
    assert clean_image_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        # A host nobody vouched for — the case the allowlist exists for.
        "https://evil.example/pixel.png",
        # Subdomains are not implied by a listed host.
        "https://other.hot.co.il/logo.png",
        # Parent domain of a listed host is itself not listed.
        "https://hot.co.il/logo.png",
        # Plaintext is blocked as mixed content by the browser regardless.
        "http://cdn.hot.co.il/logo.png",
        # Stored by the scraper before now; resolves to the SPA's index.html.
        "/Image/32457da72a9c4fbb8752633930edb4ff.png",
        "//cdn.hot.co.il/logo.png",
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
    ],
)
def test_rejects_unusable_urls(url: str) -> None:
    assert clean_image_url(url) is None


@pytest.mark.parametrize("value", [None, ""])
def test_rejects_empty(value: str | None) -> None:
    assert clean_image_url(value) is None


def test_host_match_is_case_insensitive() -> None:
    url = "https://CDN.HOT.CO.IL/logo.png"
    assert clean_image_url(url) == url


def test_preserves_query_and_path() -> None:
    url = "https://pics.k4a.co.il/img.png?v=2&size=large"
    assert clean_image_url(url) == url
