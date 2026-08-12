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

    def update_many(self, records: Sequence[RawScrapedRecord]) -> int:
        """Overwrite existing records in place, matched by ``id``.

        One read and one write for the whole batch — ``JsonStore.update_by_id``
        rewrites the entire file per record, which is unusable on a raw store
        holding tens of thousands of deals. Records whose id is not on file are
        ignored (never appended): this is an update, not an upsert.
        """
        if not records:
            return 0
        data = self._store.read()
        positions = {d["id"]: i for i, d in enumerate(data)}
        updated = 0
        for record in records:
            index = positions.get(record.id)
            if index is None:
                continue
            data[index] = to_dict(record)
            updated += 1
        if updated:
            self._store.write(data)
        return updated

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
