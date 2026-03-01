from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    scraper_name: str = "hot"
    mongo_uri: str = "mongodb://guest:guest@localhost:27017/lessley?authSource=admin"
    mongo_database: str = "lessley"
    offers_collection: str = "benefits"
    cards_collection: str = "cards"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    page_start: int = 1
    max_pages: int = 10
    request_delay_seconds: float = 0.7

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            scraper_name=os.getenv("SCRAPER_NAME", "hot").strip().lower(),
            mongo_uri=os.getenv(
                "MONGO_URI",
                "mongodb://guest:guest@localhost:27017/lessley?authSource=admin",
            ),
            mongo_database=os.getenv("MONGO_DATABASE", "lessley"),
            offers_collection=os.getenv("MONGO_OFFERS_COLLECTION", "benefits"),
            cards_collection=os.getenv("MONGO_CARDS_COLLECTION", "cards"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            page_start=int(os.getenv("SCRAPER_PAGE_START", "1")),
            max_pages=int(os.getenv("SCRAPER_MAX_PAGES", "10")),
            request_delay_seconds=float(os.getenv("SCRAPER_REQUEST_DELAY", "0.7")),
        )
