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


def test_register_llm_sites_resolves_relative_file_path(tmp_path: Path) -> None:
    cfg = tmp_path / "llm_sources.json"
    cfg.write_text(
        json.dumps(
            [
                {
                    "site_id": "llm:hever-gift-card-company",
                    "url": "https://www.hvr.co.il/site/pg/gift_card_company",
                    "file_path": "data/hever_snapshots/giftcard.json",
                    "is_json": True,
                    "instructions": "Extract every store.",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = SourceRegistry()
    registry.register_llm_sites(cfg)
    adapter = registry.get("llm:hever-gift-card-company")

    # Relative file_path is resolved against the lessley-deals package root,
    # not left as a bare relative string (which would depend on cwd at run time).
    assert adapter._file_path.endswith(  # type: ignore[attr-defined]
        str(Path("data") / "hever_snapshots" / "giftcard.json")
    )
    assert Path(adapter._file_path).is_absolute()  # type: ignore[attr-defined]
    assert adapter._is_json is True  # type: ignore[attr-defined]


def test_register_llm_sites_absolute_file_path_untouched(tmp_path: Path) -> None:
    abs_path = tmp_path / "snapshot.html"
    cfg = tmp_path / "llm_sources.json"
    cfg.write_text(
        json.dumps(
            [
                {
                    "site_id": "llm:demo-file",
                    "url": "https://demo.test/deals",
                    "file_path": str(abs_path),
                    "instructions": "Extract every product.",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = SourceRegistry()
    registry.register_llm_sites(cfg)
    adapter = registry.get("llm:demo-file")
    assert adapter._file_path == str(abs_path)  # type: ignore[attr-defined]
