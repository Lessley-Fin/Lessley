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

    @staticmethod
    def _to_clean_dict(deal: Deal) -> dict[str, Any]:
        d = to_dict(deal)
        if d.get("group_member_stores") is None:
            d.pop("group_member_stores", None)
        if d.get("group_member_store_ids") is None:
            d.pop("group_member_store_ids", None)
        if d.get("constraints") is None:
            d.pop("constraints", None)
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
