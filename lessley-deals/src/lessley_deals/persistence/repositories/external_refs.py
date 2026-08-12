from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import ExternalReference
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import external_ref_from_dict, to_dict


class ExternalRefJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, ref: ExternalReference) -> None:
        self._store.append(to_dict(ref))

    def get_by_store(self, store_id: str) -> list[ExternalReference]:
        return [
            external_ref_from_dict(d)
            for d in self._store.read()
            if d["store_id"] == store_id
        ]

    def get_by_system(self, system: str) -> list[ExternalReference]:
        return [
            external_ref_from_dict(d)
            for d in self._store.read()
            if d["system"] == system
        ]

    def delete(self, ref_id: str) -> None:
        data = self._store.read()
        data = [d for d in data if d["id"] != ref_id]
        self._store.write(data)
