from __future__ import annotations

from pathlib import Path

from lessley_deals.domain.models import Club
from lessley_deals.persistence.json_store import JsonStore
from lessley_deals.persistence.serialization import club_from_dict, to_dict


class ClubJsonRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)

    def save(self, club: Club) -> None:
        data = self._store.read()
        for i, d in enumerate(data):
            if d["id"] == club.id:
                data[i] = to_dict(club)
                self._store.write(data)
                return
        data.append(to_dict(club))
        self._store.write(data)

    def get_by_id(self, club_id: str) -> Club | None:
        for d in self._store.read():
            if d["id"] == club_id:
                return club_from_dict(d)
        return None

    def get_by_source(self, source_id: str) -> Club | None:
        for d in self._store.read():
            if d["source_id"] == source_id:
                return club_from_dict(d)
        return None

    def get_all(self) -> list[Club]:
        return [club_from_dict(d) for d in self._store.read()]
