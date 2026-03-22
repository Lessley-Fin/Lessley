from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from lessley_deals.domain.enums import RecordFate
from lessley_deals.domain.models import PipelineRecord, RawScrapedRecord


@dataclass
class PipelineContext:
    """Tracks all records through the pipeline and collects stats."""

    records: list[PipelineRecord] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def add_raw(self, raw: RawScrapedRecord) -> PipelineRecord:
        rec = PipelineRecord(raw=raw)
        self.records.append(rec)
        return rec

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    def count_by_fate(self, fate: RecordFate) -> int:
        return sum(1 for r in self.records if r.fate == fate)

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def errors(self) -> list[PipelineRecord]:
        return [r for r in self.records if r.fate == RecordFate.ERROR]
