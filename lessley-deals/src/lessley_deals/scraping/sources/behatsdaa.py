"""Behatsdaa (בהצדעה) loyalty card scraper adapter.

Fetches wallet and chain data from the Behatsdaa API.  Unlike HOT and
Mastercard which provide *deals*, Behatsdaa provides *discount wallets*
— each wallet maps to a set of retail chains where the card is accepted.

Each chain becomes a :class:`RawStore`; each wallet + chain combination
becomes a :class:`RawScrapedRecord` representing the discount relationship.

Legacy lineage
--------------
- ``lessley-backend/Scraper/behatsdaa/behatsdaa_scraper.py`` — session, wallet/chain iteration
- ``lessley-backend/Scraper/import_businesses.py`` — brand cleaning, generic filtering

API details
-----------
- Base URL: ``https://back.behatsdaa.org.il``
- Auth: ``organizationid`` + ``native`` headers; optional ``AccessToken`` and cookie
- Wallets endpoint: ``/api/cards/GetCardGeneralInfo``
- Chains endpoint:  ``/api/cards/GetWalletChain?walletId=<id>``
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from lessley_deals.domain.models import RawScrapedRecord, RawStore
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig
from lessley_deals.scraping.helpers.brand_utils import (
    clean_brand,
    is_generic_behatsdaa_brand,
    normalize_website,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://back.behatsdaa.org.il"
_WALLETS_PATH = "/api/cards/GetCardGeneralInfo"
_CHAINS_PATH = "/api/cards/GetWalletChain"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/143.0.0.0 Safari/537.36"
)


class BehatsdaaAdapter(BaseSourceAdapter):
    """Scraper for the Behatsdaa loyalty card API.

    Fetches wallet information and associated retail chain data.
    Each chain is emitted as a :class:`RawStore` and each wallet ×
    chain combination as a :class:`RawScrapedRecord`.

    Parameters
    ----------
    config:
        Standard source config.
    access_token:
        ``AccessToken`` header value for authenticated endpoints.
    organization_id:
        ``organizationid`` header value (default ``"20"``).
    native:
        ``native`` header value (default ``"true"``).
    cookie_header:
        Optional ``cookie`` header for session persistence.
    origin:
        ``Origin`` header (default ``"https://www.behatsdaa.org.il"``).
    referer:
        ``Referer`` header (default ``"https://www.behatsdaa.org.il/"``).
    """

    def __init__(
        self,
        config: SourceConfig | None = None,
        *,
        access_token: str = "",
        organization_id: str = "20",
        native: str = "true",
        cookie_header: str = "",
        origin: str = "https://www.behatsdaa.org.il",
        referer: str = "https://www.behatsdaa.org.il/",
    ) -> None:
        super().__init__(
            config
            or SourceConfig(
                base_url=_BASE_URL,
                rate_limit_rps=1.0,
                timeout_seconds=30.0,
            )
        )
        self._access_token = access_token.strip()
        self._organization_id = (organization_id or "20").strip()
        self._native = (native or "true").strip()
        self._cookie_header = cookie_header.strip()
        self._origin = (origin or "https://www.behatsdaa.org.il").strip()
        self._referer = (referer or "https://www.behatsdaa.org.il/").strip()
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # BaseSourceAdapter interface
    # ------------------------------------------------------------------

    @property
    def source_id(self) -> str:
        return "behatsdaa"

    async def scrape(self) -> tuple[list[RawStore], list[RawScrapedRecord]]:
        """Fetch all wallets and chains, return stores and deal records."""
        logger.info("[%s] Starting scrape", self.source_id)
        try:
            await self._initialize_session()
            wallets = await self._fetch_wallets()
            logger.info("[%s] Found %d wallets", self.source_id, len(wallets))

            now = datetime.now(timezone.utc)
            seen_chains: dict[str, RawStore] = {}
            stores: list[RawStore] = []
            deals: list[RawScrapedRecord] = []

            for wallet in wallets:
                wallet_id = str(wallet.get("walletID") or "").strip()
                if not wallet_id:
                    continue

                chains = await self._fetch_chains(wallet_id)
                logger.debug(
                    "[%s] Wallet %s (%s) → %d chains",
                    self.source_id,
                    wallet_id,
                    wallet.get("walletName", "?"),
                    len(chains),
                )

                for chain in chains:
                    chain_name = clean_brand(chain.get("chainName") or "")
                    if not chain_name or is_generic_behatsdaa_brand(chain_name):
                        continue

                    # Store (one per unique chain name)
                    if chain_name not in seen_chains:
                        website = normalize_website(chain.get("webSite"))
                        store = RawStore(
                            id=generate_id(),
                            source_id=self.source_id,
                            name=chain_name,
                            scraped_at=now,
                            url=f"https://{website}" if website else None,
                            raw_payload={
                                "chainID": chain.get("chainID"),
                                "chainName": chain.get("chainName"),
                                "webSite": chain.get("webSite"),
                            },
                        )
                        seen_chains[chain_name] = store
                        stores.append(store)

                    # Deal record (wallet × chain = discount relationship)
                    wallet_name = wallet.get("walletName") or ""
                    discount_rate = wallet.get("discountRate")
                    rate_str = f"{float(discount_rate):g}%" if discount_rate else ""
                    description = (
                        f"הנחה {rate_str} ב{chain_name}"
                        if rate_str
                        else f"הנחה ב{chain_name} דרך {wallet_name}"
                    )

                    deals.append(
                        RawScrapedRecord(
                            id=generate_id(),
                            source_id=self.source_id,
                            store_name=chain_name,
                            deal_description=description,
                            price_text=rate_str,
                            scraped_at=now,
                            url=f"https://{website}" if (website := normalize_website(chain.get("webSite"))) else None,
                            raw_payload={
                                "walletID": wallet.get("walletID"),
                                "walletName": wallet_name,
                                "discountRate": discount_rate,
                                "maxDepositForMonth": wallet.get("maxDepositForMonth"),
                                "walletBalance": wallet.get("walletBalance"),
                                "chainID": chain.get("chainID"),
                                "chainName": chain.get("chainName"),
                                "webSite": chain.get("webSite"),
                            },
                        )
                    )

                await asyncio.sleep(self.config.rate_limit_rps)

            logger.info(
                "[%s] Scrape complete – %d stores, %d deals",
                self.source_id,
                len(stores),
                len(deals),
            )
            return stores, deals

        finally:
            await self._close()

    async def health_check(self) -> bool:
        """Quick connectivity check against the Behatsdaa API."""
        try:
            async with httpx.AsyncClient(
                timeout=10, headers=self._auth_headers()
            ) as client:
                resp = await client.get(f"{self.config.base_url}{_WALLETS_PATH}")
                return resp.status_code < 500
        except Exception:
            logger.debug("[%s] Health check failed", self.source_id, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Build the authentication / session headers."""
        headers: dict[str, str] = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "he,en;q=0.9,en-US;q=0.8",
            "Origin": self._origin,
            "Referer": self._referer,
            "organizationid": self._organization_id,
            "native": self._native,
        }
        if self._access_token:
            headers["AccessToken"] = self._access_token
        if self._cookie_header:
            headers["cookie"] = self._cookie_header
        return headers

    async def _initialize_session(self) -> None:
        """Create the HTTP client with auth headers."""
        self._client = httpx.AsyncClient(
            http2=True,
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers=self._auth_headers(),
        )

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    async def _fetch_wallets(self) -> list[dict[str, Any]]:
        """Fetch wallet info from the API."""
        if self._client is None:
            return []
        try:
            resp = await self._client.get(
                f"{self.config.base_url}{_WALLETS_PATH}"
            )
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict):
                wallets = payload.get("data", {}).get("wallets", [])
                if isinstance(wallets, list):
                    return [w for w in wallets if isinstance(w, dict)]
            return []
        except Exception:
            logger.exception("[%s] Failed to fetch wallets", self.source_id)
            return []

    async def _fetch_chains(self, wallet_id: str) -> list[dict[str, Any]]:
        """Fetch all chains for a given wallet ID."""
        if self._client is None:
            return []
        try:
            resp = await self._client.get(
                f"{self.config.base_url}{_CHAINS_PATH}",
                params={"walletId": wallet_id},
            )
            resp.raise_for_status()
            payload = resp.json()
            chains: list[dict[str, Any]] = []
            if isinstance(payload, dict) and payload.get("status"):
                data = payload.get("data", [])
                if isinstance(data, list):
                    for group in data:
                        if not isinstance(group, dict):
                            continue
                        chain_list = group.get("walletChainData")
                        if isinstance(chain_list, list):
                            chains.extend(
                                c for c in chain_list if isinstance(c, dict)
                            )
            return chains
        except Exception:
            logger.exception(
                "[%s] Failed to fetch chains for wallet %s",
                self.source_id,
                wallet_id,
            )
            return []

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _close(self) -> None:
        """Close the underlying HTTP client if open."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
