from __future__ import annotations

from dataclasses import dataclass

from lessley_deals.domain.enums import RecordFate
from lessley_deals.pipeline.context import PipelineContext


@dataclass(frozen=True)
class PipelineReport:
    total_records: int
    auto_matched: int
    sent_to_review: int
    no_match: int
    duplicates: int
    errors: int
    duration_seconds: float

    @classmethod
    def from_context(cls, ctx: PipelineContext) -> PipelineReport:
        duration = 0.0
        if ctx.finished_at and ctx.started_at:
            duration = (ctx.finished_at - ctx.started_at).total_seconds()
        return cls(
            total_records=ctx.total,
            auto_matched=ctx.count_by_fate(RecordFate.AUTO_MATCHED),
            sent_to_review=ctx.count_by_fate(RecordFate.SENT_TO_REVIEW),
            no_match=ctx.count_by_fate(RecordFate.NO_MATCH),
            duplicates=ctx.count_by_fate(RecordFate.DUPLICATE),
            errors=ctx.count_by_fate(RecordFate.ERROR),
            duration_seconds=duration,
        )

    def summary(self) -> str:
        lines = [
            f"Pipeline complete in {self.duration_seconds:.1f}s",
            f"  Total:       {self.total_records}",
            f"  Auto-matched:{self.auto_matched}",
            f"  Review:      {self.sent_to_review}",
            f"  No match:    {self.no_match}",
            f"  Duplicates:  {self.duplicates}",
            f"  Errors:      {self.errors}",
        ]
        return "\n".join(lines)
