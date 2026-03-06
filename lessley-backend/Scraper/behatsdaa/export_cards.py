from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


async def export_behatsdaa_cards(output_path: Path) -> None:
    settings = Settings.from_env()
    request_delay = float(os.getenv("BEHATSDAA_API_REQUEST_DELAY", "1.0"))
    settings.request_delay_seconds = request_delay
    scraper = _build_scraper(settings)

    try:
        await scraper.initialize_session()
        card_general_info = await scraper.fetch_card_general_info()
        wallets = card_general_info.get("data", {}).get("wallets", [])
        if not isinstance(wallets, list):
            wallets = []

        wallets_detailed: list[dict[str, Any]] = []
        total_chains = 0
        for wallet in wallets:
            if not isinstance(wallet, dict):
                continue
            wallet_id = str(wallet.get("walletID") or "").strip()
            chains: list[dict[str, Any]] = []
            if wallet_id:
                chains = await scraper.fetch_chains_for_wallet(wallet_id)
                await scraper.throttle()
            total_chains += len(chains)
            wallets_detailed.append(
                {
                    "wallet": wallet,
                    "chains": chains,
                }
            )
    finally:
        await scraper.close()

    payload = {
        "source": "behatsdaa",
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "cardGeneralInfo": card_general_info,
        "walletsDetailed": wallets_detailed,
        "stats": {
            "walletsCount": len(wallets_detailed),
            "chainsCount": total_chains,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[Behatsdaa] Export completed: wallets={len(wallets_detailed)} chains={total_chains}")
    print(f"Output file: {output_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Behatsdaa card general info and wallet chains to JSON."
    )
    parser.add_argument(
        "--output",
        default=os.getenv("BEHATSDAA_CARDS_OUTPUT", "outputs/behatsdaa_cards.json"),
        help="Output JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    _load_behatsdaa_env()
    args = parse_args()
    asyncio.run(export_behatsdaa_cards(Path(args.output)))


if __name__ == "__main__":
    main()
