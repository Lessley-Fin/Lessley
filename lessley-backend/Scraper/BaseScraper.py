from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx

from core.config import Settings


class BaseScraper(ABC):
    def __init__(self, club_name: str, base_url: str, settings: Settings):
        self.club_name = club_name
        self.base_url = base_url
        self.settings = settings
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=30.0,
            follow_redirects=True,
            headers={
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/143.0.0.0 Safari/537.36"
                ),
                "accept": "application/json, text/plain, */*",
            },
        )

    @abstractmethod
    async def initialize_session(self) -> None:
        pass

    @abstractmethod
    async def iter_offers(self) -> AsyncIterator[dict[str, Any]]:
        pass

    @abstractmethod
    def normalize_offer(self, raw_offer: dict[str, Any]) -> dict[str, Any]:
        pass

    async def iter_cards(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}

    def normalize_card(self, raw_card: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_club": self.club_name,
            "external_id": raw_card.get("id"),
            "raw": raw_card,
            "scraped_at": self._utc_now_iso(),
        }

    async def throttle(self) -> None:
        await asyncio.sleep(self.settings.request_delay_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
