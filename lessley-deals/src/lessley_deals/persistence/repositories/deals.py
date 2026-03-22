from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import Deal
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import deal_from_dict, to_dict


class DealJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, deal: Deal) -> None:
        self._store.append(to_dict(deal))

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return any(
            deal_from_dict(d).fingerprint == fingerprint
            for d in self._store.read()
        )

    def get_by_store(self, store_id: str) -> list[Deal]:
        return [
            deal_from_dict(d)
            for d in self._store.read()
            if d["store_id"] == store_id
        ]

    def get_all(self) -> list[Deal]:
        return [deal_from_dict(d) for d in self._store.read()]
