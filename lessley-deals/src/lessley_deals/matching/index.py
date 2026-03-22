from __future__ import annotations

from lessley_deals.domain.models import CanonicalStore, StoreAlias


class AliasIndex:
    """Pre-built lookup structure for matching store aliases."""

    def __init__(
        self,
        aliases: list[StoreAlias],
        stores: list[CanonicalStore],
    ) -> None:
        self._store_by_id: dict[str, CanonicalStore] = {s.id: s for s in stores}

        # exact_lookup: compact_form -> (store_id, alias_text)
        self._exact: dict[str, tuple[str, str]] = {}
        for alias in aliases:
            compact = alias.alias_forms.compact
            if compact not in self._exact:
                self._exact[compact] = (alias.store_id, alias.alias)

        # all_entries: list of (alias, store) for linear scans
        self._all_entries: list[tuple[StoreAlias, CanonicalStore]] = []
        for alias in aliases:
            store = self._store_by_id.get(alias.store_id)
            if store is not None:
                self._all_entries.append((alias, store))

        # domain_to_store: domain -> store_id from store metadata
        self._domain_to_store: dict[str, str] = {}
        for store in stores:
            domain = store.metadata.get("domain")
            if domain:
                self._domain_to_store[domain] = store.id

    def exact_lookup(self, compact: str) -> tuple[str, str] | None:
        """O(1) lookup by compact form. Returns (store_id, alias_text) or None."""
        return self._exact.get(compact)

    def get_store(self, store_id: str) -> CanonicalStore | None:
        """Return the canonical store for a given id, or None."""
        return self._store_by_id.get(store_id)

    @property
    def all_entries(self) -> list[tuple[StoreAlias, CanonicalStore]]:
        return self._all_entries

    @property
    def domain_to_store(self) -> dict[str, str]:
        return self._domain_to_store
