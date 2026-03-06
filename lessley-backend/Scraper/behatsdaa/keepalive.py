from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import Settings
from Websites.Behatsdaa import BehatsdaaScraper


def _load_behatsdaa_env() -> None:
    local_env_path = Path(__file__).with_name(".env")
    if local_env_path.exists():
        load_dotenv(dotenv_path=local_env_path, override=True)


def _build_scraper(settings: Settings) -> BehatsdaaScraper:
    return BehatsdaaScraper(
        settings=settings,
        access_token=os.getenv("BEHATSDAA_ACCESS_TOKEN", ""),
        organization_id=os.getenv("BEHATSDAA_ORGANIZATION_ID", "20"),
        native=os.getenv("BEHATSDAA_NATIVE", "true"),
        cookie_header=os.getenv("BEHATSDAA_COOKIE", ""),
        origin=os.getenv("BEHATSDAA_ORIGIN", "https://www.behatsdaa.org.il"),
        referer=os.getenv("BEHATSDAA_REFERER", "https://www.behatsdaa.org.il/"),
    )


async def run_keepalive(interval_seconds: int, endpoint: str) -> None:
    settings = Settings.from_env()
    scraper = _build_scraper(settings)
    try:
        await scraper.initialize_session()
        while True:
            now = datetime.now(timezone.utc).isoformat()
            try:
                status_code = await scraper.ping_keepalive(endpoint=endpoint)
                print(f"[Behatsdaa][keepalive] {now} status={status_code} endpoint={endpoint}")
            except Exception as exc:
                print(f"[Behatsdaa][keepalive] {now} failed endpoint={endpoint} error={exc}")
            await asyncio.sleep(interval_seconds)
    finally:
        await scraper.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keep Behatsdaa session alive with periodic pings.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("BEHATSDAA_KEEPALIVE_SECONDS", "300")),
        help="Ping interval in seconds (default: 300).",
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("BEHATSDAA_KEEPALIVE_ENDPOINT", "/api/category/GetCategoryHeader"),
        help="Keepalive endpoint path or full URL.",
    )
    return parser.parse_args()


def main() -> None:
    _load_behatsdaa_env()
    args = parse_args()
    asyncio.run(run_keepalive(interval_seconds=max(5, args.interval_seconds), endpoint=args.endpoint))


if __name__ == "__main__":
    main()

