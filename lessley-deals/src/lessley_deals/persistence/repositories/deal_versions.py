"""JSON-file implementations of the deal history repositories.

Intended for local development and tests — the whole file is rewritten on every
bulk write, which is fine for a few thousand rows and hopeless beyond that.  Use
the MongoDB implementations in production (see ``repositories/mongo/``).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from lessley_deals.domain.enums import DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, DealVersion
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import (
    current_deal_from_dict,
    deal_version_from_dict,
    to_dict,
)


class DealVersionJsonRepository:
    """Append-only SCD2 history stored as a JSON array."""

    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def append_many(self, versions: Sequence[DealVersion]) -> None:
        if not versions:
            return
        rows = self._store.read()
        existing = {(r["deal_key"], r["version"]) for r in rows}
        # Upsert semantics on (deal_key, version) make a replayed run a no-op.
        for version in versions:
            row: dict[str, Any] = to_dict(version)
            key = (version.deal_key, version.version)
            if key in existing:
                for i, current in enumerate(rows):
                    if (current["deal_key"], current["version"]) == key:
                        rows[i] = row
                        break
            else:
                rows.append(row)
                existing.add(key)
        self._store.write(rows)

    def close_current(self, closures: Sequence[tuple[str, datetime]]) -> None:
        if not closures:
            return
        by_key = dict(closures)
        rows = self._store.read()
        for row in rows:
            if not row.get("is_current") or row["deal_key"] not in by_key:
                continue
            # `status` is left as-is on purpose — see the protocol docstring.
            row["is_current"] = False
            row["valid_to"] = by_key[row["deal_key"]].isoformat()
        self._store.write(rows)

    def get_current(self, deal_key: str) -> DealVersion | None:
        for row in self._store.read():
            if row["deal_key"] == deal_key and row.get("is_current"):
                return deal_version_from_dict(row)
        return None

    def get_history(self, deal_key: str) -> list[DealVersion]:
        rows = [r for r in self._store.read() if r["deal_key"] == deal_key]
        rows.sort(key=lambda r: r["version"])
        return [deal_version_from_dict(r) for r in rows]

    def next_version(self, deal_key: str) -> int:
        versions = [r["version"] for r in self._store.read() if r["deal_key"] == deal_key]
        return (max(versions) + 1) if versions else 1


class CurrentDealJsonRepository:
    """Head table (one row per ``deal_key``) stored as a JSON array."""

    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def bulk_upsert(self, heads: Sequence[CurrentDeal]) -> None:
        if not heads:
            return
        rows = self._store.read()
        index = {r["deal_key"]: i for i, r in enumerate(rows)}
        for head in heads:
            row = to_dict(head)
            position = index.get(head.deal_key)
            if position is None:
                index[head.deal_key] = len(rows)
                rows.append(row)
            else:
                rows[position] = row
        self._store.write(rows)

    def get(self, deal_key: str) -> CurrentDeal | None:
        for row in self._store.read():
            if row["deal_key"] == deal_key:
                return current_deal_from_dict(row)
        return None

    def get_by_source(self, source_id: str) -> list[CurrentDeal]:
        return [
            current_deal_from_dict(r)
            for r in self._store.read()
            if r["source_id"] == source_id
        ]

    def get_active(self, store_id: str | None = None) -> list[CurrentDeal]:
        return [
            current_deal_from_dict(r)
            for r in self._store.read()
            if r["status"] == DealLifecycleStatus.ACTIVE
            and (store_id is None or r["store_id"] == store_id)
        ]

    def count_active(self, source_id: str) -> int:
        return sum(
            1
            for r in self._store.read()
            if r["source_id"] == source_id and r["status"] == DealLifecycleStatus.ACTIVE
        )
