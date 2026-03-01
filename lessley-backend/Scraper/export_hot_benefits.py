import asyncio
import json
import os
from pathlib import Path

from core.config import Settings
from Websites.HotScraper import HotScraper


async def export_hot_benefits() -> None:
    settings = Settings.from_env()
    scraper = HotScraper(settings)

    output_path = Path(os.getenv("HOT_BENEFITS_OUTPUT", "outputs/hot_getAllBenefits.json"))
    start_page = settings.page_start

    all_records: list[dict] = []
    page = start_page

    try:
        await scraper.initialize_session()

        while True:
            data = await scraper.fetch_benefits(page)
            if not data:
                break

            records = data.get("data", {}).get("records", [])
            if not records:
                print(f"[{scraper.club_name}] No more records after page {page}.")
                break

            all_records.extend(records)
            print(f"[{scraper.club_name}] Page {page}: fetched {len(records)} records.")

            page += 1
            await scraper.throttle()
    finally:
        await scraper.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    total_pages = page - start_page
    print(f"Export completed: {len(all_records)} records from {total_pages} pages.")
    print(f"Output file: {output_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(export_hot_benefits())
