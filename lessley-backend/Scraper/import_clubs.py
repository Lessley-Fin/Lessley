from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import supported consumer clubs JSON into MongoDB."
    )
    parser.add_argument(
        "--input",
        default=os.getenv("CLUBS_INPUT_FILE", "clubs_supported.json"),
        help="Path to clubs JSON file.",
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv(
            "MONGO_URI",
            "mongodb://guest:guest@localhost:27017/lessley?authSource=admin",
        ),
        help="MongoDB connection URI.",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("MONGO_DATABASE", "lessley"),
        help="MongoDB database name.",
    )
    parser.add_argument(
        "--collection",
        default="clubs",
        help="MongoDB collection name for clubs.",
    )
    return parser.parse_args()


def load_records(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input JSON must be an array of club objects.")
    return [row for row in data if isinstance(row, dict)]


async def run() -> None:
    args = parse_args()
    clubs = load_records(args.input)

    client = AsyncIOMotorClient(args.mongo_uri)
    db = client[args.db]

    inserted_or_updated = 0
    skipped_invalid = 0

    try:
        collection = db[args.collection]
        await collection.create_index([("club_id", ASCENDING)], unique=True)

        for club in clubs:
            club_id = club.get("club_id")
            name = str(club.get("name") or "").strip()
            website = str(club.get("website") or "").strip()
            logo_url = str(club.get("logo_url") or "").strip()

            if club_id is None or not name:
                skipped_invalid += 1
                continue

            await collection.update_one(
                {"club_id": club_id},
                {
                    "$set": {
                        "club_id": club_id,
                        "name": name,
                        "website": website,
                        "logo_url": logo_url,
                    }
                },
                upsert=True,
            )
            inserted_or_updated += 1
    finally:
        client.close()

    print(
        f"Clubs import completed: processed={len(clubs)} "
        f"upserted={inserted_or_updated} skipped_invalid={skipped_invalid}"
    )


if __name__ == "__main__":
    asyncio.run(run())
