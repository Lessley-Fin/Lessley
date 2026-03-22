# Scraping Subsystem

## Overview

The scraping subsystem is a generic framework for extracting raw deal and store
data from external sources. Each source is implemented as a self-contained
adapter that knows how to reach a single data provider, paginate through its
results, and return raw records.

**Scrapers extract raw data only.** They perform no normalization, matching, or
deduplication. Every piece of text coming from the source is stored verbatim so
that downstream pipeline stages can work with the original data and the raw
payload is available for audit at any time.

The subsystem lives under `src/lessley_deals/scraping/` with the following
layout:

```
src/lessley_deals/scraping/
    __init__.py
    orchestrator.py
    registry.py
    base.py                    # BaseSourceAdapter + SourceConfig
    clients/
        __init__.py
        http.py                # Rate-limited async httpx client
        browser.py             # Playwright browser client
        auth.py                # Authentication strategies
    pagination/
        __init__.py
        strategies.py          # Pagination strategy implementations
    sources/
        __init__.py
        shufersal.py           # Example: Shufersal HTML scraper
        ...
```

---

## Base Source Adapter

Every scraper implements `BaseSourceAdapter`, an abstract base class defined in
`base.py`.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

class BaseSourceAdapter(ABC):
    source_id: str
    config: SourceConfig

    @abstractmethod
    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Fetch all available data from the source.

        Returns a tuple of (stores, deals). The adapter is free to return
        an empty list for either side when the source only provides one
        kind of entity.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the source is reachable and responding normally."""
        ...
```

### SourceConfig

`SourceConfig` carries every setting a scraper needs to talk to its source.

```python
@dataclass
class SourceConfig:
    base_url: str
    rate_limit_rps: float          # max requests per second
    timeout_seconds: int
    retry_config: RetryConfig
    auth_config: AuthConfig
    pagination_config: PaginationConfig
```

| Field               | Purpose                                          |
|---------------------|--------------------------------------------------|
| `base_url`          | Root URL for the source (API or website).         |
| `rate_limit_rps`    | Maximum requests per second for this source.      |
| `timeout_seconds`   | Per-request timeout.                              |
| `retry_config`      | Backoff and retry parameters (see HTTP Client).   |
| `auth_config`       | Authentication strategy and credentials.          |
| `pagination_config` | Which pagination strategy to use and its params.  |

---

## Source Types

Sources fall into two categories based on how they deliver content.

### HTTP / API Scrapers

Used when the data is available as plain HTML or a JSON API response.

- HTTP requests are made with **httpx** (async).
- HTML parsing uses **selectolax** for fast CSS-selector-based extraction.
- JSON API responses are consumed directly.

### Browser Scrapers

Used when the page requires JavaScript execution to render its content.

- Built on **Playwright** with headless Chromium.
- Suitable for SPAs, pages with lazy-loaded content, or sources that rely
  on client-side rendering.

### Authentication Variations

Each source declares which auth strategy it needs through `auth_config`:

| Strategy          | Description                                       |
|-------------------|---------------------------------------------------|
| `NoAuth`          | No credentials required. Pass-through.            |
| `ApiKeyAuth`      | API key sent as a header or query parameter.      |
| `CookieAuth`      | Performs a login flow, then reuses session cookie. |
| `BearerTokenAuth` | OAuth2 client-credentials flow or stored token.   |

---

## HTTP Client

**Location:** `clients/http.py`

A rate-limited async httpx client shared by all HTTP/API scrapers.

### Features

- **Rate limiting** -- configurable requests-per-second ceiling per source.
  Implemented with a token-bucket or semaphore that sleeps when the limit is
  reached.
- **Retry with exponential backoff** -- on transient failures (5xx, timeouts,
  connection errors) the client retries with exponential backoff:
  - Base delay: 2 seconds
  - Maximum delay: 60 seconds
  - Maximum retries: 3
- **Custom headers and cookies** -- callers can inject arbitrary headers and
  cookies into every request.
- **Response validation** -- the client raises on non-2xx status codes after
  retries are exhausted and provides structured error information.

### Usage

```python
from lessley_deals.scraping.clients.http import HttpClient

client = HttpClient(
    base_url="https://example.com",
    rate_limit_rps=2.0,
    timeout_seconds=30,
    retry_config=RetryConfig(base_delay=2, max_delay=60, max_retries=3),
    headers={"Accept-Language": "he-IL"},
)

response = await client.get("/api/deals", params={"page": 1})
```

---

## Browser Client

**Location:** `clients/browser.py`

A Playwright-based client for scraping JavaScript-rendered pages.

### Features

- **Headless Chromium** -- runs without a visible browser window in
  production; headed mode available for local debugging.
- **Page pool for concurrency** -- maintains a pool of browser pages so
  multiple URLs can be fetched concurrently without opening a new browser
  instance for each one.
- **Screenshot on failure** -- when a page load or element lookup fails, the
  client captures a screenshot and attaches it to the error report. This
  makes debugging selector changes or site redesigns straightforward.

### Usage

```python
from lessley_deals.scraping.clients.browser import BrowserClient

async with BrowserClient(pool_size=4) as browser:
    page = await browser.get_page("https://example.com/deals")
    await page.wait_for_selector(".deal-card")
    html = await page.content()
```

---

## Pagination Strategies

**Location:** `pagination/strategies.py`

Pagination is pluggable. Each strategy knows how to compute the next page
request given the current response.

### SinglePage

No pagination. The scraper makes one request and returns.

### PageNumber

Classic page-number pagination. Increments a query parameter.

```
?page=1  ->  ?page=2  ->  ?page=3  ->  ...
```

Stops when the response contains no results or the page count is reached.

### CursorBased

The response includes a `next_cursor` value that is passed back as a query
parameter to fetch the next batch.

```
?cursor=<token>  ->  ?cursor=<next_token>  ->  ...
```

Stops when `next_cursor` is `null` or absent.

### OffsetLimit

Advances by a fixed `limit` on each request.

```
?offset=0&limit=50  ->  ?offset=50&limit=50  ->  ?offset=100&limit=50  ->  ...
```

Stops when fewer than `limit` results are returned.

---

## Authentication

**Location:** `clients/auth.py`

Authentication strategies are injected into the HTTP or browser client. Each
strategy implements a common interface that prepares a request (or browser
context) with the necessary credentials.

### NoAuth

Pass-through. No modification to the request.

### ApiKeyAuth

Adds an API key as either:

- A request header (e.g., `X-Api-Key: <key>`), or
- A query parameter (e.g., `?api_key=<key>`).

Configured via `auth_config`.

### CookieAuth

Performs a login flow (POST to a login endpoint with username/password) and
extracts the session cookie from the response. The cookie is attached to all
subsequent requests. Re-authenticates automatically when the session expires.

### BearerTokenAuth

Obtains an access token via OAuth2 client-credentials grant or reads a stored
token from configuration. Adds an `Authorization: Bearer <token>` header.
Refreshes the token automatically before expiry when a refresh token or
client-credentials flow is available.

---

## Orchestrator

**Location:** `orchestrator.py`

The `ScraperOrchestrator` is the entry point for running a scrape cycle.

### Behavior

1. Loads all registered source adapters from the registry.
2. Executes every adapter's `scrape()` method in parallel using
   `asyncio.gather`. Each adapter still respects its own per-source rate
   limit, so parallelism does not violate individual rate ceilings.
3. Collects results and errors into a `ScrapeRun` metadata object.

### ScrapeRun

Top-level metadata for a complete scrape cycle.

```python
@dataclass
class ScrapeRun:
    run_id: str
    started_at: datetime
    finished_at: datetime
    source_results: list[SourceRunResult]
```

### SourceRunResult

Per-source outcome within a run.

```python
@dataclass
class SourceRunResult:
    source_id: str
    stores_count: int
    deals_count: int
    errors: list[str]
    duration: timedelta
```

### Usage

```python
from lessley_deals.scraping.orchestrator import ScraperOrchestrator
from lessley_deals.scraping.registry import registry

orchestrator = ScraperOrchestrator(registry)
scrape_run = await orchestrator.run()

for result in scrape_run.source_results:
    print(f"{result.source_id}: {result.deals_count} deals, "
          f"{result.stores_count} stores, "
          f"{len(result.errors)} errors, "
          f"{result.duration.total_seconds():.1f}s")
```

---

## Registry

**Location:** `registry.py`

The `SourceRegistry` is a central catalog of all available source adapters.

### API

```python
class SourceRegistry:
    def register(self, adapter_class: type[BaseSourceAdapter]) -> None:
        """Register an adapter class by its source_id."""
        ...

    def get(self, source_id: str) -> type[BaseSourceAdapter]:
        """Return the adapter class for a given source_id. Raises KeyError
        if not found."""
        ...

    def list_all(self) -> list[type[BaseSourceAdapter]]:
        """Return all registered adapter classes."""
        ...
```

### Discovery

The registry discovers sources automatically by importing every module in the
`sources/` directory at startup. Each source module registers itself by calling
`registry.register(MyAdapter)` at module level, or by using a decorator:

```python
from lessley_deals.scraping.registry import registry

@registry.register
class ShufersalAdapter(BaseSourceAdapter):
    source_id = "shufersal"
    ...
```

---

## How to Add a New Scraper

Follow these steps to add a scraper for a new data source.

### 1. Create the source file

```
src/lessley_deals/scraping/sources/my_source.py
```

### 2. Subclass BaseSourceAdapter

```python
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.registry import registry
```

### 3. Set source_id and config

Define the source identifier (must be unique across all scrapers) and configure
connection parameters.

### 4. Implement scrape()

Fetch pages from the source, parse the content, and return `(stores, deals)`.

### 5. Register in the registry

Use the `@registry.register` decorator on the class, or call
`registry.register(MyAdapter)` at module level.

### 6. Add environment variables

If the source requires credentials, add them to `.env` and reference them in
`auth_config`. Document the required variables in the source file docstring.

### 7. Add test fixtures

Place representative response fixtures (HTML pages, JSON payloads) in
`tests/fixtures/my_source/` so that unit tests can run without network access.

### Complete Example: Shufersal HTML Scraper

The following example shows a simplified scraper for Shufersal, an Israeli
supermarket chain. It fetches paginated HTML deal pages, parses them with
selectolax, and returns raw stores and deals.

```python
"""Shufersal deal scraper.

Env vars:
    (none -- public pages, no auth required)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from selectolax.parser import HTMLParser

from lessley_deals.scraping.base import (
    BaseSourceAdapter,
    PaginationConfig,
    RetryConfig,
    SourceConfig,
)
from lessley_deals.scraping.clients.auth import NoAuth
from lessley_deals.scraping.clients.http import HttpClient
from lessley_deals.scraping.pagination.strategies import PageNumber
from lessley_deals.scraping.registry import registry
from lessley_deals.scraping.models import RawScrapedRecord, RawStore


@registry.register
class ShufersalAdapter(BaseSourceAdapter):
    source_id = "shufersal"

    config = SourceConfig(
        base_url="https://www.shufersal.co.il",
        rate_limit_rps=2.0,
        timeout_seconds=30,
        retry_config=RetryConfig(base_delay=2, max_delay=60, max_retries=3),
        auth_config=NoAuth(),
        pagination_config=PaginationConfig(
            strategy=PageNumber(param_name="page", start=1),
            max_pages=50,
        ),
    )

    def __init__(self) -> None:
        self.client = HttpClient(
            base_url=self.config.base_url,
            rate_limit_rps=self.config.rate_limit_rps,
            timeout_seconds=self.config.timeout_seconds,
            retry_config=self.config.retry_config,
        )

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        paginator = self.config.pagination_config.strategy
        page_params = paginator.first_page_params()

        while page_params is not None:
            response = await self.client.get(
                "/online/he/deals", params=page_params
            )
            html = response.text
            page_stores, page_deals = self._parse_page(html)

            stores.extend(page_stores)
            deals.extend(page_deals)

            # Determine if there is a next page.
            page_params = paginator.next_page_params(
                current_params=page_params,
                response_body=html,
                result_count=len(page_deals),
            )

        return stores, deals

    async def health_check(self) -> bool:
        try:
            response = await self.client.get("/online/he/deals")
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_page(
        self, html: str
    ) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        tree = HTMLParser(html)
        stores: list[RawStore] = []
        deals: list[RawScrapedRecord] = []

        for node in tree.css(".deal-item"):
            deal = self._parse_deal_node(node, raw_html=html)
            if deal is not None:
                deals.append(deal)

            store = self._parse_store_node(node)
            if store is not None:
                stores.append(store)

        return stores, deals

    def _parse_deal_node(
        self, node, raw_html: str
    ) -> RawScrapedRecord | None:
        title_el = node.css_first(".deal-title")
        price_el = node.css_first(".deal-price")
        if title_el is None:
            return None

        # Collect every piece of text exactly as it appears on the page.
        raw_payload = {
            "title": title_el.text(deep=True),
            "price": price_el.text(deep=True) if price_el else None,
            "description": (
                node.css_first(".deal-description").text(deep=True)
                if node.css_first(".deal-description")
                else None
            ),
            "image_url": (
                node.css_first("img").attributes.get("src")
                if node.css_first("img")
                else None
            ),
            "raw_html_snippet": node.html,
        }

        fingerprint = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True).encode()
        ).hexdigest()

        return RawScrapedRecord(
            source_id=self.source_id,
            scraped_at=datetime.now(timezone.utc),
            raw_payload=raw_payload,
            fingerprint=fingerprint,
            source_url=f"{self.config.base_url}/online/he/deals",
        )

    def _parse_store_node(self, node) -> RawStore | None:
        store_el = node.css_first(".store-name")
        if store_el is None:
            return None

        raw_payload = {
            "name": store_el.text(deep=True),
            "address": (
                node.css_first(".store-address").text(deep=True)
                if node.css_first(".store-address")
                else None
            ),
        }

        fingerprint = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True).encode()
        ).hexdigest()

        return RawStore(
            source_id=self.source_id,
            scraped_at=datetime.now(timezone.utc),
            raw_payload=raw_payload,
            fingerprint=fingerprint,
        )
```

Key points illustrated by the example:

- **Fetching pages**: the adapter uses `HttpClient.get()` inside a pagination
  loop. The paginator decides when to stop.
- **Parsing HTML**: `selectolax.HTMLParser` and CSS selectors extract data from
  the DOM.
- **Constructing raw records**: `RawScrapedRecord` and `RawStore` carry the
  verbatim `raw_payload` dict plus a SHA-256 `fingerprint`.
- **Pagination**: the `PageNumber` strategy increments the `page` query
  parameter automatically. The loop ends when `next_page_params` returns
  `None`.

---

## Raw Entity Rules

Scrapers produce `RawScrapedRecord` and `RawStore` objects. These objects must
preserve the source data exactly as it was received.

1. **Store ALL original text verbatim in `raw_payload`.** Do not clean, trim,
   strip whitespace, fix encoding, or normalize any value. If the source
   returns `"  Milk 1L  \n"`, that exact string goes into `raw_payload`.

2. **Do not normalize anything.** No lowercasing, no unit conversion, no date
   parsing, no currency formatting. Downstream stages handle all of that.

3. **Include the full response data for audit.** When practical, store the
   complete relevant portion of the response (e.g., the HTML snippet for the
   deal node, or the full JSON object for an API record). This allows later
   re-parsing if extraction logic changes.

4. **Compute a `fingerprint` for each record.** The fingerprint is a SHA-256
   hash of the canonicalized `raw_payload` (JSON-serialized with sorted keys).
   Scrapers themselves do not perform deduplication -- the persistence layer
   uses the fingerprint to detect and skip duplicates on insert.
