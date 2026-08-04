"""Run journal — an auditable record of every scheduled scrape attempt.

Answers the questions you always end up asking at 2am: did this source run? how
long did it take? did it fail, and with what? how many deals changed? was it
retried?  Also the natural source for alerting ("hot hasn't succeeded in 24h").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

from lessley_deals.domain.enums import RunStatus
from lessley_deals.persistence.json_store import JsonStore

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """One attempt at running one source."""

    run_id: str
    source_id: str
    trigger: str                    # "schedule" | "startup" | "manual"
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    attempt: int = 1
    max_attempts: int = 1
    error: str | None = None
    # Pipeline / ingestion counters, flattened for easy dashboarding.
    scraped_records: int = 0
    deals_new: int = 0
    deals_updated: int = 0
    deals_unchanged: int = 0
    deals_expired: int = 0
    deals_reactivated: int = 0
    sent_to_review: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_id": self.source_id,
            "trigger": self.trigger,
            "status": str(self.status),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "error": self.error,
            "scraped_records": self.scraped_records,
            "deals_new": self.deals_new,
            "deals_updated": self.deals_updated,
            "deals_unchanged": self.deals_unchanged,
            "deals_expired": self.deals_expired,
            "deals_reactivated": self.deals_reactivated,
            "sent_to_review": self.sent_to_review,
            "metadata": self.metadata,
        }


class RunJournal(Protocol):
    def record(self, run: RunRecord) -> None: ...
    def recent(self, source_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]: ...
    def last_success(self, source_id: str) -> dict[str, Any] | None: ...


class JsonRunJournal:
    """File-backed journal for local development."""

    def __init__(self, path: Path, max_rows: int = 5000) -> None:
        self._store = JsonStore(path)
        self._max_rows = max_rows

    def record(self, run: RunRecord) -> None:
        rows = self._store.read()
        row = run.to_dict()
        for i, existing in enumerate(rows):
            if existing.get("run_id") == run.run_id and existing.get("attempt") == run.attempt:
                rows[i] = row
                break
        else:
            rows.append(row)
        # Keep the file bounded — this is a debugging aid, not the audit trail.
        self._store.write(rows[-self._max_rows :])

    def recent(self, source_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = [r for r in self._store.read() if source_id is None or r["source_id"] == source_id]
        return sorted(rows, key=lambda r: r["started_at"], reverse=True)[:limit]

    def last_success(self, source_id: str) -> dict[str, Any] | None:
        matches = [
            r
            for r in self._store.read()
            if r["source_id"] == source_id and r["status"] == str(RunStatus.SUCCESS)
        ]
        return max(matches, key=lambda r: r["started_at"], default=None)


class MongoRunJournal:
    """Production journal, in the ``scrape_runs`` collection.

    Rows are kept for ``retention_days`` via a TTL index — long enough to debug
    and chart, short enough that the collection never becomes a problem.
    """

    def __init__(self, db: Any, retention_days: int = 90) -> None:
        from pymongo import ASCENDING, DESCENDING

        self._col = db["scrape_runs"]
        self._col.create_index([("source_id", ASCENDING), ("started_at", DESCENDING)])
        self._col.create_index([("status", ASCENDING), ("started_at", DESCENDING)])
        self._col.create_index("run_id")
        self._col.create_index(
            "started_at_dt", expireAfterSeconds=retention_days * 24 * 3600, name="ttl_started_at"
        )

    def record(self, run: RunRecord) -> None:
        doc = run.to_dict()
        # A real BSON date alongside the ISO string: the TTL index needs it, and
        # aggregations are far nicer with a native type.
        doc["started_at_dt"] = run.started_at
        self._col.update_one(
            {"run_id": run.run_id, "attempt": run.attempt}, {"$set": doc}, upsert=True
        )

    def recent(self, source_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = {} if source_id is None else {"source_id": source_id}
        cursor = self._col.find(query, {"_id": 0}).sort("started_at", -1).limit(limit)
        return list(cursor)

    def last_success(self, source_id: str) -> dict[str, Any] | None:
        return self._col.find_one(  # type: ignore[no-any-return]
            {"source_id": source_id, "status": str(RunStatus.SUCCESS)},
            {"_id": 0},
            sort=[("started_at", -1)],
        )


class NullRunJournal:
    """No-op journal — used when journaling is disabled."""

    def record(self, run: RunRecord) -> None:
        logger.debug("Run %s/%s: %s", run.source_id, run.run_id, run.status)

    def recent(self, source_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def last_success(self, source_id: str) -> dict[str, Any] | None:
        return None


def stale_sources(
    journal: RunJournal,
    source_ids: Sequence[str],
    max_age_hours: float,
    now: datetime | None = None,
) -> list[str]:
    """Sources with no successful run within ``max_age_hours`` — feed to alerting."""
    now = now or datetime.now(timezone.utc)
    stale: list[str] = []
    for source_id in source_ids:
        last = journal.last_success(source_id)
        if last is None:
            stale.append(source_id)
            continue
        started = datetime.fromisoformat(str(last["started_at"]))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if (now - started).total_seconds() > max_age_hours * 3600:
            stale.append(source_id)
    return stale
