from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from lessley_deals.domain.models import Deal
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import deal_from_dict, to_dict


class DealJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, deal: Deal) -> None:
        self._store.append(self._to_clean_dict(deal))

    def update(self, deal: Deal) -> bool:
        """Overwrite an existing deal (matched by id) in place.

        Returns True if a deal with that id existed and was replaced.
        """
        return self._store.update_by_id(deal.id, self._to_clean_dict(deal))

    def update_many(self, deals: Sequence[Deal]) -> int:
        """Overwrite existing deals in place, matched by ``id``.

        One read and one write for the whole batch — ``update()`` rewrites the
        entire file per deal, which is unusable across thousands of them.
        Deals whose id is not on file are ignored (never appended).
        """
        if not deals:
            return 0
        data = self._store.read()
        positions = {d["id"]: i for i, d in enumerate(data)}
        updated = 0
        for deal in deals:
            index = positions.get(deal.id)
            if index is None:
                continue
            data[index] = self._to_clean_dict(deal)
            updated += 1
        if updated:
            self._store.write(data)
        return updated

    def bulk_upsert(self, deals: Sequence[Deal]) -> int:
        """Insert-or-replace deals matched by ``id``, in one read and one write.

        The versioning counterpart to ``save``: a deal's id is stable across all
        its versions, so re-projecting an offer overwrites its row instead of
        appending a second copy of the same thing.
        """
        if not deals:
            return 0
        data = self._store.read()
        positions = {d["id"]: i for i, d in enumerate(data)}
        for deal in deals:
            record = self._to_clean_dict(deal)
            index = positions.get(deal.id)
            if index is None:
                positions[deal.id] = len(data)
                data.append(record)
            else:
                data[index] = record
        self._store.write(data)
        return len(deals)

    def delete_by_ids(self, deal_ids: Sequence[str]) -> int:
        if not deal_ids:
            return 0
        doomed = set(deal_ids)
        data = self._store.read()
        kept = [d for d in data if d.get("id") not in doomed]
        removed = len(data) - len(kept)
        if removed:
            self._store.write(kept)
        return removed

    def get_ids_by_source(self, source_id: str) -> set[str]:
        """Business keys of every row this source owns, expired ones included."""
        return {
            d["id"] for d in self._store.read()
            if d.get("source_id") == source_id and d.get("id")
        }

    @staticmethod
    def _to_clean_dict(deal: Deal) -> dict[str, Any]:
        d = to_dict(deal)
        if d.get("group_member_stores") is None:
            d.pop("group_member_stores", None)
        if d.get("group_member_store_ids") is None:
            d.pop("group_member_store_ids", None)
        if d.get("constraints") is None:
            d.pop("constraints", None)
        # ``status`` always stays — it is what consumers filter on, and an
        # absent field would read as "unknown" rather than "on offer".
        for lifecycle_field in ("deal_key", "first_seen_at", "last_seen_at", "expires_at", "expired_at"):
            if d.get(lifecycle_field) is None:
                d.pop(lifecycle_field, None)
        return d

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
