import argparse
import asyncio
import json
from pathlib import Path

from core.config import Settings
from hot.hot_scraper import HotScraper


async def export_benefit_details(benefit_id: str, is_commerce: str, output_path: Path) -> None:
    settings = Settings.from_env()
    scraper = HotScraper(settings)

    try:
        await scraper.initialize_session()
        details = await scraper.fetch_benefit_details(benefit_id=benefit_id, is_commerce=is_commerce)
    finally:
        await scraper.close()

    if not details:
        raise RuntimeError(f"Failed to fetch details for benefitId={benefit_id}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(f"Exported details for benefitId={benefit_id}")
    if "http_status" in details and details["http_status"] >= 400:
        print(f"Endpoint returned non-2xx status: {details['http_status']}")
    print(f"Output file: {output_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export HOT specific benefit details to JSON.")
    parser.add_argument("benefit_id", help="HOT benefit id (for example: 59373)")
    parser.add_argument("--is-commerce", default="0", help="isCommerce payload value (default: 0)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: hot/outputs/hot_benefit_<benefit_id>.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or f"hot/outputs/hot_benefit_{args.benefit_id}.json"
    asyncio.run(export_benefit_details(args.benefit_id, args.is_commerce, Path(output)))


if __name__ == "__main__":
    main()
