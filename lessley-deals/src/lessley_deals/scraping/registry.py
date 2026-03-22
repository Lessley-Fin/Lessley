from __future__ import annotations

import logging
from typing import Type

from lessley_deals.scraping.base import BaseSourceAdapter, SourceConfig

logger = logging.getLogger(__name__)


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

    def register_defaults(self) -> None:
        """Register the built-in source adapters."""
        from lessley_deals.scraping.sources.rami_levy import RamiLevyAdapter
        from lessley_deals.scraping.sources.shufersal import ShufersalAdapter

        for cls, url in [
            (ShufersalAdapter, "https://www.shufersal.co.il"),
            (RamiLevyAdapter, "https://www.rami-levy.co.il"),
        ]:
            try:
                self.register(cls, SourceConfig(base_url=url))
            except ValueError:
                pass  # already registered
