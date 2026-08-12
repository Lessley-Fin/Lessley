from __future__ import annotations

import json
from pathlib import Path

import pytest

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.swish import SwishAdapter


@pytest.fixture
def swish_db(tmp_path: Path) -> Path:
    records = [
        {
            "benefit_id": "101",
            "benefit_name": "Spa Package",
            "stores": ["Zeus Spa", "Hamei Gaash", "Zeus Spa"],  # duplicate intentional
            "scraped_at": "2026-01-01T00:00:00",
        },
        {
            "benefit_id": "202",
            "benefit_name": "Shopping Card",
            "stores": ["Renuar", "Zeus Spa"],  # Zeus already seen in 101
            "scraped_at": "2026-01-01T00:00:00",
        },
    ]
    path = tmp_path / "swish_database.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_swish_adapter_emits_raw_stores_not_deals(swish_db: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, deals = await adapter.scrape()

    assert deals == [], "SwishAdapter must never emit deals"
    assert len(stores) > 0


@pytest.mark.asyncio
async def test_swish_adapter_deduplicates_member_names(swish_db: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, _ = await adapter.scrape()

    store_names = [s.name for s in stores]
    assert store_names.count("Zeus Spa") == 1


@pytest.mark.asyncio
async def test_swish_adapter_emits_one_store_per_unique_member(swish_db: Path) -> None:
    adapter = SwishAdapter(SourceConfig(base_url="https://swish.co.il"), database_path=swish_db)
    stores, _ = await adapter.scrape()

    # Unique members: "Zeus Spa", "Hamei Gaash", "Renuar" = 3
    assert len(stores) == 3


@pytest.mark.asyncio
async def test_swish_adapter_returns_empty_when_db_missing(tmp_path: Path) -> None:
    adapter = SwishAdapter(
        SourceConfig(base_url="https://swish.co.il"),
        database_path=tmp_path / "no_file.json",
    )
    stores, deals = await adapter.scrape()
    assert stores == []
    assert deals == []
