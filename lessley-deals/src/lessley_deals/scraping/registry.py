from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Type

from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)


def _lessley_deals_root() -> Path:
    # registry.py is at src/lessley_deals/scraping/registry.py
    return Path(__file__).resolve().parents[3]


def _default_llm_sources_path() -> Path:
    return _lessley_deals_root() / "data" / "seed" / "llm_sources.json"


def load_llm_site_configs(path: Path | None = None) -> list[dict[str, str]]:
    """Load per-site LLM scraper configs. Returns [] if the file is absent."""
    cfg_path = path or _default_llm_sources_path()
    if not cfg_path.exists():
        return []
    with cfg_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        logger.error("llm_sources.json must be a list, got %s", type(data).__name__)
        return []
    return [c for c in data if {"site_id", "url", "instructions"} <= c.keys()]


def _coerce_float(value: object, default: float = 0.0) -> float:
    """Return a non-negative float, falling back to *default*."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        n = float(value)
    except ValueError:
        return default
    return n if n >= 0 else default


def _resolve_file_path(value: object) -> str | None:
    """Resolve a config ``file_path`` (relative paths are against the package root)."""
    if not value or not isinstance(value, str):
        return None
    path = Path(value)
    if not path.is_absolute():
        path = _lessley_deals_root() / path
    return str(path)


def _coerce_max_len(value: object, default: int = 6000) -> int:
    """Return a positive int chunk size, falling back to *default*."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return default
    try:
        n = int(value)
    except ValueError:
        return default
    return n if n > 0 else default


class SourceRegistry:
    """Central registry that maps *source_id* strings to adapter instances."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseSourceAdapter] = {}

    def register(
        self,
        adapter_class: Type[BaseSourceAdapter],
        config: SourceConfig,
    ) -> None:
        """Instantiate *adapter_class* with *config* and register it.

        The ``source_id`` is read from the newly created instance.

        Raises
        ------
        ValueError
            If a source with the same *source_id* is already registered.
        """
        instance = adapter_class(config)
        sid = instance.source_id
        if sid in self._adapters:
            raise ValueError(f"Source '{sid}' is already registered")
        self._adapters[sid] = instance
        logger.info("Registered source adapter: %s", sid)

    def get(self, source_id: str) -> BaseSourceAdapter:
        """Return the adapter for *source_id*.

        Raises
        ------
        KeyError
            If no adapter is registered under that id.
        """
        try:
            return self._adapters[source_id]
        except KeyError:
            raise KeyError(f"No adapter registered for source_id='{source_id}'") from None

    def list_all(self) -> list[str]:
        """Return a sorted list of all registered source ids."""
        return sorted(self._adapters)

    def register_llm_sites(self, path: Path | None = None) -> None:
        """Register an LlmScraperAdapter per entry in llm_sources.json."""
        from lessley_deals.scraping.sources.llm_scraper import LlmScraperAdapter

        for cfg in load_llm_site_configs(path):
            try:
                sample_raw = cfg.get("sample_limit")
                sample_limit = (
                    _coerce_max_len(sample_raw, default=0) or None
                    if sample_raw is not None
                    else None
                )
                instance = LlmScraperAdapter(
                    SourceConfig(base_url=cfg["url"]),
                    site_id=cfg["site_id"],
                    url=cfg["url"],
                    instructions=cfg["instructions"],
                    max_len=_coerce_max_len(cfg.get("max_len")),
                    crawl_details=bool(cfg.get("crawl_details", False)),
                    detail_instructions=str(cfg.get("detail_instructions", "")),
                    sample_limit=sample_limit,
                    detail_concurrency=_coerce_max_len(
                        cfg.get("detail_concurrency"), default=3
                    ),
                    render_wait_seconds=_coerce_float(cfg.get("render_wait_seconds")),
                    wait_selector=(
                        str(cfg["wait_selector"])
                        if cfg.get("wait_selector")
                        else None
                    ),
                    file_path=_resolve_file_path(cfg.get("file_path")),
                    is_json=bool(cfg.get("is_json", False)),
                )
                self._adapters[instance.source_id] = instance
                logger.info("Registered LLM source adapter: %s", instance.source_id)
            except ValueError:
                pass

    def register_defaults(self) -> None:
        """Register the built-in source adapters."""
        from lessley_deals.scraping.sources.behatsdaa import BehatsdaaAdapter
        from lessley_deals.scraping.sources.hever import HeverGiftCardAdapter
        from lessley_deals.scraping.sources.hot import HotAdapter
        from lessley_deals.scraping.sources.isracard_topcash import IsracardTopcashAdapter
        from lessley_deals.scraping.sources.mastercard import MastercardAdapter
        from lessley_deals.scraping.sources.swish import SwishAdapter

        defaults: list[tuple[type[BaseSourceAdapter], str]] = [
            (HotAdapter, "https://www.hot.co.il"),
            (MastercardAdapter, "https://www.mastercard.co.il"),
            (BehatsdaaAdapter, "https://back.behatsdaa.org.il"),
            (IsracardTopcashAdapter, "https://www.topcash.co.il/all-stores"),
            (SwishAdapter, "https://swish.co.il"),
            (HeverGiftCardAdapter, "https://www.hvr.co.il"),
        ]
        for cls, url in defaults:
            try:
                self.register(cls, SourceConfig(base_url=url))
            except ValueError:
                pass  # already registered

        self.register_llm_sites()
