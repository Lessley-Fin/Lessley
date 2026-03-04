from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import Settings
from hot.hot_scraper import HotScraper


DEFAULT_CLUBS = [
    {"club_id": 1, "name": "בהצדעה"},
    {"club_id": 2, "name": "הייטקזון"},
    {"club_id": 3, "name": "פיס"},
    {"club_id": 4, "name": "HOT"},
]


@dataclass(slots=True)
class BusinessRecord:
    brand: str
    slug: str
    website: str | None
    external_id: str
    tags: list[str]
    is_generic: bool


def normalize_brand(raw_brand: Any) -> str:
    brand = str(raw_brand or "").strip()
    if not brand:
        return ""
    brand = re.sub(r"_[0-9]+$", "", brand)
    brand = re.sub(r"\s+", " ", brand).strip(" -_")
    return brand


def to_slug(value: str) -> str:
    text = normalize_brand(value).lower()
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"[_\s]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def normalize_website(raw_website: Any) -> str | None:
    website = str(raw_website or "").strip().lower()
    if not website:
        return None
    website = website.replace(" ", "")
    if not re.match(r"^[a-z][a-z0-9+\-.]*://", website):
        website = f"https://{website}"
    try:
        parsed = urlparse(website)
    except Exception:
        return None
    host = parsed.netloc or parsed.path
    host = host.split("@")[-1].split(":")[0].strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


class BaseClubBusinessImporter(ABC):
    club_key: str
    club_id: int
    club_name: str
    generic_brand_patterns: tuple[str, ...]

    def is_generic_brand(self, brand: str) -> bool:
        if not brand:
            return True
        normalized = brand.strip().lower()
        for pattern in self.generic_brand_patterns:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return True
        return False

    def load_json_records(self, path: str) -> list[dict[str, Any]]:
        with open(path, "rb") as f:
            raw_bytes = f.read()

        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "cp1255"):
            try:
                data = json.loads(raw_bytes.decode(encoding))
                return self.extract_file_records(data)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
                last_error = err
        raise ValueError(f"Failed to decode JSON from '{path}': {last_error}")

    @abstractmethod
    def extract_file_records(self, payload: Any) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def normalize_record(self, record: dict[str, Any], tag_generic: bool) -> BusinessRecord | None:
        pass

    @abstractmethod
    async def iter_api_records(self, args: argparse.Namespace) -> AsyncIterator[dict[str, Any]]:
        pass


class HotBusinessImporter(BaseClubBusinessImporter):
    club_key = "hot"
    club_id = 4
    club_name = "HOT"
    generic_brand_patterns = (
        r"מועדון\s*הוט",
        r"הוט\s*מועדון\s*צרכנות",
        r"^\s*hot\s*(club)?\s*$",
    )

    def extract_file_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError("HOT input JSON must be an array of objects.")

    def normalize_record(self, record: dict[str, Any], tag_generic: bool) -> BusinessRecord | None:
        brand = normalize_brand(record.get("item_brand"))
        if not brand:
            return None

        slug = to_slug(brand)
        if not slug:
            return None

        is_generic = self.is_generic_brand(brand)
        if is_generic and not tag_generic:
            return None

        tags: set[str] = set()
        item_category = str(record.get("item_category") or "").strip()
        if item_category:
            tags.add(item_category)

        raw_tags = record.get("tags")
        if isinstance(raw_tags, list):
            for value in raw_tags:
                tag = str(value or "").strip()
                if tag:
                    tags.add(tag)

        if tag_generic and is_generic:
            tags.add("__generic_hot__")

        return BusinessRecord(
            brand=brand,
            slug=slug,
            website=normalize_website(record.get("supplierWebsite")),
            external_id=str(record.get("id") or "").strip(),
            tags=sorted(tags),
            is_generic=is_generic,
        )

    async def iter_api_records(self, args: argparse.Namespace) -> AsyncIterator[dict[str, Any]]:
        settings = Settings.from_env()
        if args.page_start is not None:
            settings.page_start = args.page_start
        if args.max_pages is not None:
            settings.max_pages = args.max_pages
        if args.request_delay is not None:
            settings.request_delay_seconds = args.request_delay

        scraper = HotScraper(settings)
        try:
            await scraper.initialize_session()
            async for record in scraper.iter_offers():
                yield record
        finally:
            await scraper.close()


IMPORTERS: dict[str, BaseClubBusinessImporter] = {
    HotBusinessImporter.club_key: HotBusinessImporter(),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import businesses for a club from file or club API into MongoDB."
    )
    parser.add_argument(
        "--club",
        default=os.getenv("SCRAPER_NAME", "hot"),
        help="Club key to import (for example: hot).",
    )
    parser.add_argument(
        "--input",
        default=os.getenv("HOT_OUTPUT_FILE", "hot/outputs/hot_getAllBenefits.json"),
        help="Path to club JSON file.",
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
        "--businesses-collection",
        default="businesses",
        help="Businesses collection name.",
    )
    parser.add_argument(
        "--clubs-collection",
        default="clubs",
        help="Clubs collection name.",
    )
    parser.add_argument(
        "--tag-generic",
        action="store_true",
        help="Tag generic club brands instead of skipping them.",
    )
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Fetch records directly from club API instead of reading --input JSON.",
    )
    parser.add_argument(
        "--page-start",
        type=int,
        default=None,
        help="Override scraper page start when using --from-api.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override max pages when using --from-api.",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="Override request delay seconds when using --from-api.",
    )
    return parser.parse_args()


async def ensure_indexes_and_clubs(
    db: Any,
    clubs_collection: str,
    businesses_collection: str,
    importer: BaseClubBusinessImporter,
) -> None:
    await db[clubs_collection].create_index([("club_id", ASCENDING)], unique=True)
    await db[businesses_collection].create_index([("slug", ASCENDING)], unique=True)
    await db[businesses_collection].create_index([("website", ASCENDING)], sparse=True)

    base_clubs = {club["club_id"]: club for club in DEFAULT_CLUBS}
    base_clubs[importer.club_id] = {"club_id": importer.club_id, "name": importer.club_name}
    for club in base_clubs.values():
        await db[clubs_collection].update_one(
            {"club_id": club["club_id"]},
            {"$set": club},
            upsert=True,
        )


async def upsert_business(
    db: Any,
    businesses_collection: str,
    importer: BaseClubBusinessImporter,
    business: BusinessRecord,
) -> str:
    mappings_entry = {
        "club_id": importer.club_id,
        "original_name": business.brand,
        "external_id": business.external_id,
    }
    now = datetime.now(timezone.utc)

    if business.website:
        query: dict[str, Any] = {"$or": [{"slug": business.slug}, {"website": business.website}]}
    else:
        query = {"slug": business.slug}

    existing = await db[businesses_collection].find_one(query)
    if existing:
        existing_tags = set(existing.get("tags", []))
        merged_tags = sorted(existing_tags.union(business.tags))

        await db[businesses_collection].update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "canonical_name": existing.get("canonical_name") or business.brand,
                    "website": existing.get("website") or business.website,
                    "tags": merged_tags,
                    "last_updated": now,
                },
                "$unset": {
                    "categories": "",
                    "catagories": "",
                },
            },
        )
        await db[businesses_collection].update_one(
            {"_id": existing["_id"]},
            {"$pull": {"mappings": {"club_id": importer.club_id}}},
        )
        await db[businesses_collection].update_one(
            {"_id": existing["_id"]},
            {"$addToSet": {"mappings": mappings_entry}},
        )
        return "updated"

    document = {
        "canonical_name": business.brand,
        "slug": business.slug,
        "website": business.website,
        "tags": business.tags,
        "mappings": [mappings_entry],
        "last_updated": now,
    }
    await db[businesses_collection].update_one(
        {"slug": business.slug}, {"$setOnInsert": document}, upsert=True
    )
    return "inserted"


async def run() -> None:
    args = parse_args()
    club_key = str(args.club or "").strip().lower()
    importer = IMPORTERS.get(club_key)
    if not importer:
        available = ", ".join(sorted(IMPORTERS.keys()))
        raise ValueError(f"Unsupported club '{club_key}'. Available clubs: {available}")

    client = AsyncIOMotorClient(args.mongo_uri)
    db = client[args.db]

    counters = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "skipped_generic": 0,
        "skipped_invalid": 0,
    }

    try:
        await ensure_indexes_and_clubs(
            db,
            clubs_collection=args.clubs_collection,
            businesses_collection=args.businesses_collection,
            importer=importer,
        )

        if args.from_api:
            async for item in importer.iter_api_records(args):
                counters["processed"] += 1
                business = importer.normalize_record(item, tag_generic=args.tag_generic)
                if business is None:
                    brand = normalize_brand(item.get("item_brand"))
                    if importer.is_generic_brand(brand):
                        counters["skipped_generic"] += 1
                    else:
                        counters["skipped_invalid"] += 1
                    continue
                status = await upsert_business(
                    db,
                    businesses_collection=args.businesses_collection,
                    importer=importer,
                    business=business,
                )
                counters[status] += 1
        else:
            for item in importer.load_json_records(args.input):
                counters["processed"] += 1
                business = importer.normalize_record(item, tag_generic=args.tag_generic)
                if business is None:
                    brand = normalize_brand(item.get("item_brand"))
                    if importer.is_generic_brand(brand):
                        counters["skipped_generic"] += 1
                    else:
                        counters["skipped_invalid"] += 1
                    continue
                status = await upsert_business(
                    db,
                    businesses_collection=args.businesses_collection,
                    importer=importer,
                    business=business,
                )
                counters[status] += 1
    finally:
        client.close()

    print(
        f"[{importer.club_key}] Import completed: "
        f"processed={counters['processed']} "
        f"inserted={counters['inserted']} "
        f"updated={counters['updated']} "
        f"skipped_generic={counters['skipped_generic']} "
        f"skipped_invalid={counters['skipped_invalid']}"
    )


if __name__ == "__main__":
    asyncio.run(run())
