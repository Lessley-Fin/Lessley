from __future__ import annotations

from core.config import Settings
from core.llm_normalizer import LLMNormalizer
from core.mongo_repository import MongoRepository
from Websites.BaseScraper import BaseScraper


class ScrapePipeline:
    def __init__(
        self,
        settings: Settings,
        scraper: BaseScraper,
        mongo_repository: MongoRepository,
        llm_normalizer: LLMNormalizer,
    ):
        self.settings = settings
        self.scraper = scraper
        self.mongo_repository = mongo_repository
        self.llm_normalizer = llm_normalizer

    async def run(self) -> dict[str, int]:
        offers_count = 0
        cards_count = 0

        try:
            await self.scraper.initialize_session()

            async for raw_offer in self.scraper.iter_offers():
                normalized_offer = self.scraper.normalize_offer(raw_offer)
                # enriched_offer = await self.llm_normalizer.normalize_offer(normalized_offer)
                print(normalized_offer)
                # await self.mongo_repository.upsert_offer(self.settings.offers_collection, enriched_offer)
                offers_count += 1

            # async for raw_card in self.scraper.iter_cards():
            #     normalized_card = self.scraper.normalize_card(raw_card)
            #     enriched_card = await self.llm_normalizer.normalize_card(normalized_card)
            #     await self.mongo_repository.upsert_card(self.settings.cards_collection, enriched_card)
            #     cards_count += 1
        finally:
            await self.scraper.close()
            await self.mongo_repository.close()

        return {"offers": offers_count, "cards": cards_count}