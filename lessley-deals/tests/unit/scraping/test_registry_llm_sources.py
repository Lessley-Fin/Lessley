from __future__ import annotations

import json
from pathlib import Path

from lessley_deals.scraping.registry import SourceRegistry


def test_register_llm_sites_from_file(tmp_path: Path) -> None:
    cfg = tmp_path / "llm_sources.json"
    cfg.write_text(
        json.dumps(
            [
                {
                    "site_id": "llm:demo",
                    "url": "https://demo.test/deals",
                    "instructions": "Extract every product and price.",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = SourceRegistry()
    registry.register_llm_sites(cfg)
    assert "llm:demo" in registry.list_all()


def test_register_llm_sites_missing_file_is_noop(tmp_path: Path) -> None:
    registry = SourceRegistry()
    registry.register_llm_sites(tmp_path / "nope.json")
    assert registry.list_all() == []
