from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import StoreAlias
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import alias_from_dict, to_dict


class AliasJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, alias: StoreAlias) -> None:
        self._store.append(to_dict(alias))

    def find_by_alias(self, alias: str) -> StoreAlias | None:
        normalized = alias.lower().strip()
        for d in self._store.read():
            if d["alias_forms"]["normalized"] == normalized:
                return alias_from_dict(d)
        return None

    def get_all(self) -> list[StoreAlias]:
        return [alias_from_dict(d) for d in self._store.read()]

    def search(self, query: str) -> list[StoreAlias]:
        q = query.lower().strip()
        return [
            alias_from_dict(d)
            for d in self._store.read()
            if q in d["alias"].lower() or q in d["alias_forms"]["normalized"]
        ]

    def get_by_store(self, store_id: str) -> list[StoreAlias]:
        return [
            alias_from_dict(d)
            for d in self._store.read()
            if d["store_id"] == store_id
        ]

    def delete(self, alias_id: str) -> None:
        data = self._store.read()
        data = [d for d in data if d["id"] != alias_id]
        self._store.write(data)
