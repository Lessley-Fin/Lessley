from __future__ import annotations

from dataclasses import dataclass

from lessley_deals.domain.enums import RecordFate
from lessley_deals.pipeline.context import PipelineContext
from lessley_deals.pipeline.ingest_stage import IngestSummary
from lessley_deals.pipeline.scrape_stage import ScrapeOutcome


@dataclass(frozen=True)
class PipelineReport:
    total_records: int
    auto_matched: int
    sent_to_review: int
    no_match: int
    duplicates: int
    errors: int
    duration_seconds: float
    scraped_records: int = 0
    failed_sources: tuple[str, ...] = ()
    ok_sources: tuple[str, ...] = ()
    deals_new: int = 0
    deals_updated: int = 0
    deals_unchanged: int = 0
    deals_expired: int = 0
    deals_reactivated: int = 0

    @classmethod
    def from_context(
        cls,
        ctx: PipelineContext,
        scrape: ScrapeOutcome | None = None,
        ingest: IngestSummary | None = None,
    ) -> PipelineReport:
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
            scraped_records=scrape.total_scraped if scrape else 0,
            failed_sources=tuple(sorted(scrape.failed_sources)) if scrape else (),
            ok_sources=tuple(sorted(scrape.ok_sources)) if scrape else (),
            deals_new=ingest.new if ingest else 0,
            deals_updated=ingest.updated if ingest else 0,
            deals_unchanged=ingest.unchanged if ingest else 0,
            deals_expired=ingest.expired if ingest else 0,
            deals_reactivated=ingest.reactivated if ingest else 0,
        )

    def summary(self) -> str:
        lines = [
            f"Pipeline complete in {self.duration_seconds:.1f}s",
            f"  Scraped:     {self.scraped_records}",
            f"  Total:       {self.total_records}",
            f"  Auto-matched:{self.auto_matched}",
            f"  Review:      {self.sent_to_review}",
            f"  No match:    {self.no_match}",
            f"  Duplicates:  {self.duplicates}",
            f"  Errors:      {self.errors}",
        ]
        if any((self.deals_new, self.deals_updated, self.deals_unchanged,
                self.deals_expired, self.deals_reactivated)):
            lines += [
                "  ── history ──",
                f"  New:         {self.deals_new}",
                f"  Updated:     {self.deals_updated}",
                f"  Unchanged:   {self.deals_unchanged}",
                f"  Reactivated: {self.deals_reactivated}",
                f"  Expired:     {self.deals_expired}",
            ]
        if self.failed_sources:
            lines.append(f"  Failed sources: {', '.join(self.failed_sources)}")
        return "\n".join(lines)
