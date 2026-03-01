import httpx
import asyncio
import Websites.BaseScraper as BaseScraper

class BehatzdahaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Behatzdaha", "https://back.behatsdaa.org.il")
        self.wallets_api = f"{self.base_url}/api/cards/GetCardGeneralInfo"
        self.chains_api = f"{self.base_url}/api/cards/GetWalletChain"

    def set_manual_session(self, cookie_string):
        self.client.headers.update({"cookie": cookie_string})

    async def fetch_wallets(self):
        try:
            response = await self.client.get(self.wallets_api)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("wallets", [])
        except Exception as e:
            print(f"[{self.club_name}] Failed to fetch wallets: {e}")
            return []

    async def fetch_chains_for_wallet(self, wallet_id):
        params = {"walletId": str(wallet_id)}
        try:
            response = await self.client.get(self.chains_api, params=params)
            response.raise_for_status()
            data = response.json()
            all_chains = []
            if data.get("status") and "data" in data:
                for tag in data["data"]:
                    all_chains.extend(tag.get("walletChainData", []))
            return all_chains
        except Exception as e:
            print(f"[{self.club_name}] Failed to fetch chains for wallet {wallet_id}: {e}")
            return []

    def normalize_wallet(self, wallet_data, chains):
        return {
            "club": self.club_name,
            "wallet_id": wallet_data.get("walletID"),
            "wallet_name": wallet_data.get("walletName"),
            "discount_rate": wallet_data.get("discountRate"), 
            "monthly_load_limit": wallet_data.get("maxDepositForMonth"), 
            "current_balance": wallet_data.get("walletBalance"),
            "supported_businesses": [
                {
                    "chain_id": c.get("chainID"),
                    "name": c.get("chainName"),
                    "website": c.get("webSite")
                } for c in chains
            ]
        }