from __future__ import annotations

from core.config import Settings
from core.llm_normalizer import LLMNormalizer
from core.mongo_repository import MongoRepository
from core.pipeline import ScrapePipeline
from Websites.HotScraper import HotScraper


class ScraperContainer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _create_scraper(self):
        if self.settings.scraper_name == "hot":
            return HotScraper(self.settings)
        raise ValueError(f"Unsupported scraper: {self.settings.scraper_name}")

    def _create_repository(self) -> MongoRepository:
        return MongoRepository(self.settings.mongo_uri, self.settings.mongo_database)

    def _create_llm_normalizer(self) -> LLMNormalizer:
        return LLMNormalizer(self.settings)

    def build_pipeline(self) -> ScrapePipeline:
        scraper = self._create_scraper()
        repository = self._create_repository()
        llm_normalizer = self._create_llm_normalizer()
        return ScrapePipeline(self.settings, scraper, repository, llm_normalizer)