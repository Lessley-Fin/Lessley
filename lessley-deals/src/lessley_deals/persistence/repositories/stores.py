from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import CanonicalStore
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import canonical_store_from_dict, to_dict


class CanonicalStoreJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, store: CanonicalStore) -> None:
        data = self._store.read()
        # Update if exists, else append
        for i, d in enumerate(data):
            if d["id"] == store.id:
                data[i] = to_dict(store)
                self._store.write(data)
                return
        data.append(to_dict(store))
        self._store.write(data)

    def get_by_id(self, store_id: str) -> CanonicalStore | None:
        for d in self._store.read():
            if d["id"] == store_id:
                return canonical_store_from_dict(d)
        return None

    def get_all(self) -> list[CanonicalStore]:
        return [canonical_store_from_dict(d) for d in self._store.read()]

    def search(self, query: str) -> list[CanonicalStore]:
        q = query.lower()
        return [
            canonical_store_from_dict(d)
            for d in self._store.read()
            if q in d["name"].lower() or q in d["name_forms"]["normalized"]
        ]
