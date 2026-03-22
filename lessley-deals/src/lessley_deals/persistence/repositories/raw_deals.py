from __future__ import annotations

from pathlib import Path
from typing import Sequence

from lessley_deals.domain.models import RawScrapedRecord
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import raw_deal_from_dict, to_dict


class RawDealJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, record: RawScrapedRecord) -> None:
        self._store.append(to_dict(record))

    def save_many(self, records: Sequence[RawScrapedRecord]) -> None:
        self._store.append_many([to_dict(r) for r in records])

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        return any(
            raw_deal_from_dict(d).fingerprint == fingerprint
            for d in self._store.read()
        )

    def get_by_id(self, record_id: str) -> RawScrapedRecord | None:
        for d in self._store.read():
            if d["id"] == record_id:
                return raw_deal_from_dict(d)
        return None

    def get_all(self) -> list[RawScrapedRecord]:
        return [raw_deal_from_dict(d) for d in self._store.read()]

    def get_by_source(self, source_id: str) -> list[RawScrapedRecord]:
        return [
            raw_deal_from_dict(d)
            for d in self._store.read()
            if d["source_id"] == source_id
        ]
