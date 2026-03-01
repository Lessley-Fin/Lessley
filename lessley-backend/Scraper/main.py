import asyncio

from core.config import Settings
from core.container import ScraperContainer


async def main() -> None:
    settings = Settings.from_env()
    container = ScraperContainer(settings)
    pipeline = container.build_pipeline()
    result = await pipeline.run()

    print(
        f"Completed scraper '{settings.scraper_name}'. "
        f"offers={result['offers']} cards={result['cards']}"
    )


if __name__ == "__main__":
    asyncio.run(main())