from __future__ import annotations

from lessley_deals.domain.enums import AliasSource
from lessley_deals.domain.models import CanonicalStore, StoreAlias


def _synthetic_alias(store: CanonicalStore) -> StoreAlias:
    """Create a synthetic alias entry from a canonical store's own name."""
    return StoreAlias(
        id=f"__store__{store.id}",
        store_id=store.id,
        alias=store.name,
        alias_forms=store.name_forms,
        source=AliasSource.SEED,
        created_at=store.created_at,
    )


class AliasIndex:
    """Pre-built lookup structure for matching store aliases."""

    def __init__(
        self,
        aliases: list[StoreAlias],
        stores: list[CanonicalStore],
    ) -> None:
        self._store_by_id: dict[str, CanonicalStore] = {s.id: s for s in stores}

        # Include each canonical store's own name as a synthetic alias so
        # the primary name participates in matching even without an explicit alias.
        all_aliases = list(aliases) + [_synthetic_alias(s) for s in stores]

        # exact_lookup: compact_form -> (store_id, alias_text)
        self._exact: dict[str, tuple[str, str]] = {}
        for alias in all_aliases:
            compact = alias.alias_forms.compact
            if compact not in self._exact:
                self._exact[compact] = (alias.store_id, alias.alias)

        # all_entries: list of (alias, store) for linear scans
        self._all_entries: list[tuple[StoreAlias, CanonicalStore]] = []
        for alias in all_aliases:
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
