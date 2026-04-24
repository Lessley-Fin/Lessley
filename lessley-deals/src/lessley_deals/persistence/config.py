from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PersistenceConfig:
    base_dir: Path = field(default_factory=lambda: Path("data"))

    @property
    def raw_stores_path(self) -> Path:
        return self.base_dir / "raw_source_stores.json"

    @property
    def raw_deals_path(self) -> Path:
        return self.base_dir / "raw_source_deals.json"

    @property
    def stores_path(self) -> Path:
        return self.base_dir / "stores.json"

    @property
    def aliases_path(self) -> Path:
        return self.base_dir / "store_aliases.json"

    @property
    def external_refs_path(self) -> Path:
        return self.base_dir / "store_external_references.json"

    @property
    def reviews_path(self) -> Path:
        return self.base_dir / "store_match_review.json"

    @property
    def deals_path(self) -> Path:
        return self.base_dir / "deals.json"

    @property
    def clubs_path(self) -> Path:
        return self.base_dir / "clubs.json"
