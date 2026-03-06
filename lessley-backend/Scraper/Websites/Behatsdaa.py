from __future__ import annotations

from typing import Any, AsyncIterator

from core.config import Settings
from Websites.BaseScraper import BaseScraper


class BehatsdaaScraper(BaseScraper):
    def __init__(
        self,
        settings: Settings,
        access_token: str = "",
        organization_id: str = "20",
        native: str = "true",
        cookie_header: str = "",
        origin: str = "https://www.behatsdaa.org.il",
        referer: str = "https://www.behatsdaa.org.il/",
    ):
        super().__init__("Behatsdaa", "https://back.behatsdaa.org.il", settings=settings)
        self.wallets_api = f"{self.base_url}/api/cards/GetCardGeneralInfo"
        self.chains_api = f"{self.base_url}/api/cards/GetWalletChain"
        self.access_token = access_token.strip()
        self.organization_id = str(organization_id).strip() or "20"
        self.native = str(native).strip() or "true"
        self.cookie_header = cookie_header.strip()
        self.origin = origin.strip() or "https://www.behatsdaa.org.il"
        self.referer = referer.strip() or "https://www.behatsdaa.org.il/"

    async def initialize_session(self) -> None:
        self.client.headers.update(
            {
                "origin": self.origin,
                "referer": self.referer,
                "organizationid": self.organization_id,
                "native": self.native,
                "accept-language": "he,en;q=0.9,en-US;q=0.8",
            }
        )
        if self.access_token:
            self.client.headers.update({"AccessToken": self.access_token})
        if self.cookie_header:
            self.client.headers.update({"cookie": self.cookie_header})

    async def fetch_wallets(self) -> list[dict[str, Any]]:
        payload = await self.fetch_card_general_info()
        wallets = payload.get("data", {}).get("wallets", [])
        if isinstance(wallets, list):
            return [item for item in wallets if isinstance(item, dict)]
        return []

    async def fetch_card_general_info(self) -> dict[str, Any]:
        try:
            response = await self.client.get(self.wallets_api)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        except Exception as exc:
            print(f"[{self.club_name}] Failed to fetch card general info: {exc}")
            return {}

    async def fetch_chains_for_wallet(self, wallet_id: str) -> list[dict[str, Any]]:
        try:
            response = await self.client.get(self.chains_api, params={"walletId": str(wallet_id)})
            response.raise_for_status()
            payload = response.json()
            all_chains: list[dict[str, Any]] = []
            if payload.get("status") and isinstance(payload.get("data"), list):
                for group in payload["data"]:
                    if not isinstance(group, dict):
                        continue
                    chain_list = group.get("walletChainData")
                    if isinstance(chain_list, list):
                        all_chains.extend(
                            item for item in chain_list if isinstance(item, dict)
                        )
            return all_chains
        except Exception as exc:
            print(f"[{self.club_name}] Failed to fetch chains for wallet {wallet_id}: {exc}")
            return []

    async def ping_keepalive(self, endpoint: str = "/api/category/GetCategoryHeader") -> int:
        url = endpoint if endpoint.startswith("http://") or endpoint.startswith("https://") else f"{self.base_url}{endpoint}"
        response = await self.client.get(url)
        return response.status_code

    async def iter_cards(self) -> AsyncIterator[dict[str, Any]]:
        wallets = await self.fetch_wallets()
        for wallet in wallets:
            wallet_id = str(wallet.get("walletID") or "").strip()
            if not wallet_id:
                continue
            chains = await self.fetch_chains_for_wallet(wallet_id)
            yield {
                "wallet": wallet,
                "chains": chains,
            }
            await self.throttle()

    async def iter_offers(self) -> AsyncIterator[dict[str, Any]]:
        async for card in self.iter_cards():
            yield card

    def normalize_card(self, raw_card: dict[str, Any]) -> dict[str, Any]:
        wallet = raw_card.get("wallet", {}) if isinstance(raw_card, dict) else {}
        chains = raw_card.get("chains", []) if isinstance(raw_card, dict) else []
        if not isinstance(wallet, dict):
            wallet = {}
        if not isinstance(chains, list):
            chains = []
        return {
            "club": self.club_name,
            "wallet_id": wallet.get("walletID"),
            "wallet_name": wallet.get("walletName"),
            "discount_rate": wallet.get("discountRate"),
            "monthly_load_limit": wallet.get("maxDepositForMonth"),
            "current_balance": wallet.get("walletBalance"),
            "supported_businesses": [
                {
                    "chain_id": chain.get("chainID"),
                    "name": chain.get("chainName"),
                    "website": chain.get("webSite"),
                }
                for chain in chains
                if isinstance(chain, dict)
            ],
        }

    def normalize_offer(self, raw_offer: dict[str, Any]) -> dict[str, Any]:
        return self.normalize_card(raw_offer)
