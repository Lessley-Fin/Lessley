from __future__ import annotations

from pathlib import Path
from typing import Sequence

from lessley_deals.domain.models import RawStore
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import raw_store_from_dict, to_dict


class RawStoreJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, store: RawStore) -> None:
        self._store.append(to_dict(store))

    def save_many(self, stores: Sequence[RawStore]) -> None:
        self._store.append_many([to_dict(s) for s in stores])

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return any(
            raw_store_from_dict(d).fingerprint == fingerprint
            for d in self._store.read()
        )

    def get_all(self) -> list[RawStore]:
        return [raw_store_from_dict(d) for d in self._store.read()]

    def get_by_source(self, source_id: str) -> list[RawStore]:
        return [
            raw_store_from_dict(d)
            for d in self._store.read()
            if d["source_id"] == source_id
        ]
