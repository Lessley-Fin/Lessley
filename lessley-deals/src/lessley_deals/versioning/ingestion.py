"""SCD Type 2 ingestion — the single place that decides what happened to a deal.

Flow for one source, once per scrape run::

    heads = current_repo.get_by_source(source_id)     # what we knew before
    plan  = plan_ingestion(heads, incoming, ...)      # pure decision function
    apply(plan)                                       # bulk writes, no updates in place

Classification per incoming deal:

===============  =================================================================
NEW              no head for this ``deal_key``            → version 1, ACTIVE
UPDATED          head exists, ``content_hash`` differs    → close v(n), open v(n+1)
UNCHANGED        head exists, same ``content_hash``       → touch ``last_seen_at``
REACTIVATED      head exists but was EXPIRED, seen again  → new version, ACTIVE
EXPIRED          head not seen any more (see guards)      → close v(n), open v(n+1)
                                                            with status EXPIRED
===============  =================================================================

Expiry gets a version row of its own rather than a status flip on the live row.
Without that, a deal that expires and later returns leaves no trace of the gap,
and "what was the state on the 6th?" answers "active" for days it was not.

**The expiry guards are the important part.**  Naively expiring every deal
missing from a run would wipe the catalogue the first time a source rate-limits
us, returns an empty page or changes its HTML.  So a deal is only expired when:

1. the run itself succeeded (no scraper errors), **and**
2. the run returned a plausible number of deals — at least
   ``min_coverage_ratio`` of what we currently hold for that source, **and**
3. the deal has been missing for ``absence_threshold`` consecutive runs **and**
   for at least ``absence_grace`` wall-clock time.

Anything else logs a warning and skips the expiry sweep entirely — under-expiring
is recoverable, mass false expiry is not.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

from lessley_deals.domain.enums import DealChangeType, DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, Deal, DealVersion
from lessley_deals.domain.protocols import CurrentDealRepository, DealVersionRepository
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.versioning.hashing import (
    DealIdentityResolver,
    compute_content_hash,
    deal_snapshot,
    diff_snapshots,
    extract_source_expiry,
)
from lessley_deals.versioning.projection import DealProjector

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Configuration & reporting
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IngestionConfig:
    """Tuning knobs for the expiry heuristics.

    Defaults are deliberately conservative — a deal survives roughly a day of
    absence before being expired.
    """

    absence_threshold: int = 2
    """Consecutive runs a deal must be missing before it can expire."""

    absence_grace: timedelta = timedelta(hours=24)
    """Wall-clock time a deal must be missing before it can expire."""

    min_coverage_ratio: float = 0.5
    """Skip the expiry sweep if a run returns less than this fraction of the
    currently-active deals for the source (protects against partial scrapes)."""

    expire_on_source_date: bool = True
    """Expire deals whose source-declared end date has passed, even if the
    source still lists them."""

    enable_expiry_sweep: bool = True
    """Master switch — turn off for one-off backfills that only see a subset."""

    allow_reactivation: bool = True
    """Whether seeing an expired deal again brings it back.

    True for a scrape, which is a fresh observation of what a source offers
    right now.  **False for a rebuild from the raw archive** (``deals process``):
    that archive keeps every record ever scraped, so an expired deal's raw row is
    still sitting in it and would resurrect every offer the sources have retired.
    """


@dataclass
class IngestionReport:
    source_id: str
    run_id: str | None = None
    incoming: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    reactivated: int = 0
    expired: int = 0
    duplicates_dropped: int = 0
    expiry_sweep_skipped: str | None = None
    changed_keys: list[str] = field(default_factory=list)
    projected: int = 0
    """Rows written back to the flat ``deals`` collection (see projection.py)."""

    removed: int = 0
    """Expired rows deleted from ``deals`` rather than flagged."""

    reactivation_suppressed: int = 0
    """Expired deals left expired because this was a rebuild, not a scrape."""

    @property
    def total_written(self) -> int:
        return self.new + self.updated + self.reactivated + self.expired

    def summary(self) -> str:
        parts = [
            f"[{self.source_id}] incoming={self.incoming}",
            f"new={self.new}",
            f"updated={self.updated}",
            f"unchanged={self.unchanged}",
            f"reactivated={self.reactivated}",
            f"expired={self.expired}",
        ]
        if self.duplicates_dropped:
            parts.append(f"dupes={self.duplicates_dropped}")
        if self.projected:
            parts.append(f"projected={self.projected}")
        if self.removed:
            parts.append(f"removed={self.removed}")
        if self.reactivation_suppressed:
            parts.append(f"kept-expired={self.reactivation_suppressed}")
        if self.expiry_sweep_skipped:
            parts.append(f"expiry-sweep SKIPPED ({self.expiry_sweep_skipped})")
        return " ".join(parts)


@dataclass(frozen=True)
class IngestionPlan:
    """Everything the ingestion decided, before a single byte is written.

    Keeping the decision pure makes it trivially unit-testable and lets the
    write side be a dumb bulk executor.
    """

    versions: tuple[DealVersion, ...]
    closures: tuple[tuple[str, datetime], ...]
    heads: tuple[CurrentDeal, ...]
    report: IngestionReport


# ---------------------------------------------------------------------------
# Pure decision function
# ---------------------------------------------------------------------------

def plan_ingestion(
    *,
    source_id: str,
    incoming: Sequence[Deal],
    heads: Iterable[CurrentDeal],
    seen_fingerprints: Iterable[str] = (),
    raw_fingerprints: Mapping[str, str] | None = None,
    run_ok: bool = True,
    run_id: str | None = None,
    identity: DealIdentityResolver | None = None,
    config: IngestionConfig | None = None,
    now: datetime | None = None,
) -> IngestionPlan:
    """Decide what to write. Performs no I/O.

    Parameters
    ----------
    incoming
        Deals produced by this run for *this source*.
    heads
        Current head rows already stored for this source.
    seen_fingerprints
        Raw-record fingerprints observed during the run, including records the
        scrape stage deduplicated away because they were byte-identical to a
        previous run.  Without this, unchanged deals filtered out upstream would
        look "missing" and eventually expire.
    raw_fingerprints
        ``raw_id -> fingerprint`` for the incoming deals, so a head can remember
        which raw record produced it and be matched against
        ``seen_fingerprints`` on later runs.
    run_ok
        False when the scraper reported errors — disables the expiry sweep.
    """
    identity = identity or DealIdentityResolver()
    config = config or IngestionConfig()
    now = now or _utcnow()
    raw_fingerprints = raw_fingerprints or {}

    head_by_key: dict[str, CurrentDeal] = {h.deal_key: h for h in heads}
    fingerprints = set(seen_fingerprints)
    report = IngestionReport(source_id=source_id, run_id=run_id, incoming=len(incoming))

    versions: list[DealVersion] = []
    version_index: dict[str, int] = {}  # deal_key -> position in ``versions``
    closures: list[tuple[str, datetime]] = []
    updated_heads: dict[str, CurrentDeal] = {}

    # --- 1. Collapse duplicates inside the batch (last occurrence wins) -----
    by_key: dict[str, Deal] = {}
    for deal in incoming:
        key = identity.deal_key(deal)
        if key in by_key:
            report.duplicates_dropped += 1
        by_key[key] = deal

    # --- 2. Classify every incoming deal ------------------------------------
    for key, deal in by_key.items():
        head = head_by_key.get(key)
        content_hash = compute_content_hash(deal)
        snapshot = deal_snapshot(deal)
        expires_at = extract_source_expiry(deal)

        if head is None:
            change = DealChangeType.NEW
        elif head.status == DealLifecycleStatus.EXPIRED:
            if not config.allow_reactivation:
                # A rebuild re-reads records the source stopped publishing long
                # ago; that is not evidence the offer is back on.
                report.reactivation_suppressed += 1
                continue
            change = DealChangeType.REACTIVATED
        elif head.content_hash != content_hash:
            change = DealChangeType.UPDATED
        else:
            change = DealChangeType.UNCHANGED

        if change is DealChangeType.UNCHANGED and head is not None:
            # Nothing to version — just record that we saw it again.
            report.unchanged += 1
            updated_heads[key] = _touch_head(
                head, now, raw_fingerprint=raw_fingerprints.get(deal.raw_id)
            )
            continue

        # A version is being opened: keep the original deal id so downstream
        # references (notifications, saved deals) survive content changes.
        stable_id = head.deal_id if head else deal.id
        version_no = (head.version + 1) if head else 1
        changed_fields = diff_snapshots(head.snapshot, snapshot) if head else ()
        snapshot = {**snapshot, "id": stable_id}

        if head is not None:
            closures.append((key, now))

        version_index[key] = len(versions)
        versions.append(
            DealVersion(
                id=generate_id(),
                deal_key=key,
                version=version_no,
                store_id=deal.store_id,
                source_id=source_id,
                content_hash=content_hash,
                change_type=change,
                status=DealLifecycleStatus.ACTIVE,
                valid_from=now,
                valid_to=None,
                is_current=True,
                snapshot=snapshot,
                run_id=run_id,
                changed_fields=changed_fields,
                source_expires_at=expires_at,
            )
        )
        updated_heads[key] = CurrentDeal(
            deal_key=key,
            deal_id=stable_id,
            store_id=deal.store_id,
            source_id=source_id,
            version=version_no,
            content_hash=content_hash,
            status=DealLifecycleStatus.ACTIVE,
            first_seen_at=head.first_seen_at if head else now,
            last_seen_at=now,
            valid_from=now,
            valid_to=None,
            missing_runs=0,
            missing_since=None,
            source_expires_at=expires_at,
            raw_fingerprint=raw_fingerprints.get(deal.raw_id),
            snapshot=snapshot,
        )

        if change is DealChangeType.NEW:
            report.new += 1
        elif change is DealChangeType.UPDATED:
            report.updated += 1
        else:
            report.reactivated += 1
        report.changed_keys.append(key)

    # --- 3. Expire deals whose own end date has passed -----------------------
    # Covers heads we just wrote as well as ones we did not see this run: a deal
    # can arrive already past its end date, and one we stop seeing can pass it
    # while sitting in the database.
    if config.expire_on_source_date:
        for key in {*updated_heads, *head_by_key}:
            candidate = updated_heads.get(key) or head_by_key[key]
            if candidate.status != DealLifecycleStatus.ACTIVE:
                continue
            if candidate.source_expires_at and candidate.source_expires_at <= now:
                version_no = _expire(key, candidate, now, run_id, versions, version_index, closures)
                updated_heads[key] = _expire_head(candidate, now, version_no)
                report.expired += 1

    # --- 4. Heads confirmed alive by fingerprint alone -----------------------
    # The scrape stage drops records that are byte-identical to a previous run,
    # so on a steady-state run ``incoming`` is empty even though every deal was
    # seen.  Matching the raw fingerprints is positive evidence of presence, so
    # it happens *before* the guards below — otherwise a healthy quiet run looks
    # like a total scrape failure.
    still_alive: set[str] = set()
    for key, head in head_by_key.items():
        if key in by_key or head.status != DealLifecycleStatus.ACTIVE:
            continue
        if head.raw_fingerprint and head.raw_fingerprint in fingerprints:
            still_alive.add(key)
            report.unchanged += 1
            updated_heads[key] = _touch_head(head, now)

    # --- 5. Absence sweep, behind the safety guards --------------------------
    skip_reason = _expiry_sweep_block_reason(
        run_ok=run_ok,
        config=config,
        incoming_count=len(by_key) + len(still_alive),
        active_heads=sum(1 for h in head_by_key.values() if h.status == DealLifecycleStatus.ACTIVE),
    )
    if skip_reason:
        report.expiry_sweep_skipped = skip_reason
        return IngestionPlan(tuple(versions), tuple(closures), tuple(updated_heads.values()), report)

    for key, head in head_by_key.items():
        if key in by_key or key in still_alive or head.status != DealLifecycleStatus.ACTIVE:
            continue

        missing_runs = head.missing_runs + 1
        missing_since = head.missing_since or now
        long_enough = (now - missing_since) >= config.absence_grace
        often_enough = missing_runs >= config.absence_threshold

        if long_enough and often_enough:
            version_no = _expire(key, head, now, run_id, versions, version_index, closures)
            updated_heads[key] = _expire_head(head, now, version_no)
            report.expired += 1
        else:
            # Still on probation — record the miss, keep it ACTIVE.
            updated_heads[key] = replace(
                head, missing_runs=missing_runs, missing_since=missing_since
            )

    return IngestionPlan(tuple(versions), tuple(closures), tuple(updated_heads.values()), report)


def _expiry_sweep_block_reason(
    *,
    run_ok: bool,
    config: IngestionConfig,
    incoming_count: int,
    active_heads: int,
) -> str | None:
    """Return why the expiry sweep must not run, or None if it is safe."""
    if not config.enable_expiry_sweep:
        return "disabled"
    if not run_ok:
        return "scrape reported errors"
    if active_heads == 0:
        return None
    if incoming_count == 0:
        return "run returned zero deals"
    coverage = incoming_count / active_heads
    if coverage < config.min_coverage_ratio:
        return f"coverage {coverage:.0%} below {config.min_coverage_ratio:.0%}"
    return None


def _expire(
    deal_key: str,
    candidate: CurrentDeal,
    now: datetime,
    run_id: str | None,
    versions: list[DealVersion],
    version_index: dict[str, int],
    closures: list[tuple[str, datetime]],
) -> int:
    """Record that ``deal_key`` is no longer on offer. Returns its version number.

    Expiry is a state change like any other, so it gets **its own version row**
    rather than mutating the active one.  Without that, a deal that expires and
    later returns would leave no trace of the gap, and "what was the state on
    the 6th?" would answer "active" for a day when it was not.
    """
    position = version_index.get(deal_key)
    if position is not None:
        # Already writing a row for this key in this run (a deal that arrived
        # past its own end date) — mark that row expired instead of stacking a
        # second version on top of it.
        versions[position] = replace(
            versions[position], status=DealLifecycleStatus.EXPIRED, valid_to=None, is_current=True
        )
        return versions[position].version

    closures.append((deal_key, now))
    version_no = candidate.version + 1
    version_index[deal_key] = len(versions)
    versions.append(
        DealVersion(
            id=generate_id(),
            deal_key=deal_key,
            version=version_no,
            store_id=candidate.store_id,
            source_id=candidate.source_id,
            content_hash=candidate.content_hash,
            change_type=DealChangeType.EXPIRED,
            status=DealLifecycleStatus.EXPIRED,
            valid_from=now,
            valid_to=None,   # "expired" is the current state until something changes it
            is_current=True,
            snapshot=candidate.snapshot,
            run_id=run_id,
            source_expires_at=candidate.source_expires_at,
        )
    )
    return version_no


def _touch_head(
    head: CurrentDeal,
    now: datetime,
    raw_fingerprint: str | None = None,
) -> CurrentDeal:
    """Mark a head as seen again in this run, clearing any absence state."""
    return replace(
        head,
        last_seen_at=now,
        missing_runs=0,
        missing_since=None,
        raw_fingerprint=raw_fingerprint or head.raw_fingerprint,
    )


def _expire_head(head: CurrentDeal, now: datetime, version: int) -> CurrentDeal:
    """``valid_to`` records *when* the deal stopped being on offer."""
    return replace(
        head,
        status=DealLifecycleStatus.EXPIRED,
        version=version,
        valid_from=now,
        valid_to=now,
    )


# ---------------------------------------------------------------------------
# I/O side
# ---------------------------------------------------------------------------

class IngestionService:
    """Loads heads, plans, and applies the plan in bulk.

    Write order is deliberate and replay-safe:

    1. close superseded/expired version rows  (idempotent — already-closed rows
       are skipped by the repository)
    2. append the new version rows            (upsert on ``deal_key + version``)
    3. upsert the head rows                   (last, so a crash mid-way leaves
       the head pointing at the old version and the next run simply redoes the
       same work)

    Repositories are synchronous (pymongo / JSON files), so every call is
    off-loaded to a thread to keep the scraping event loop responsive.
    """

    def __init__(
        self,
        version_repo: DealVersionRepository,
        current_repo: CurrentDealRepository,
        identity: DealIdentityResolver | None = None,
        config: IngestionConfig | None = None,
        clock: Clock = _utcnow,
        projector: DealProjector | None = None,
    ) -> None:
        self._versions = version_repo
        self._current = current_repo
        self._identity = identity or DealIdentityResolver()
        self._config = config or IngestionConfig()
        self._clock = clock
        # Optional, but without it nothing downstream ever learns that a deal
        # expired — ``deals`` is the collection every consumer actually reads.
        self._projector = projector

    async def ingest(
        self,
        deals: Sequence[Deal],
        *,
        source_id: str,
        run_id: str | None = None,
        run_ok: bool = True,
        seen_fingerprints: Iterable[str] = (),
        raw_fingerprints: Mapping[str, str] | None = None,
    ) -> IngestionReport:
        heads = await asyncio.to_thread(self._current.get_by_source, source_id)

        plan = plan_ingestion(
            source_id=source_id,
            incoming=deals,
            heads=heads,
            seen_fingerprints=seen_fingerprints,
            raw_fingerprints=raw_fingerprints,
            run_ok=run_ok,
            run_id=run_id,
            identity=self._identity,
            config=self._config,
            now=self._clock(),
        )

        if plan.closures:
            await asyncio.to_thread(self._versions.close_current, plan.closures)
        if plan.versions:
            await asyncio.to_thread(self._versions.append_many, plan.versions)
        if plan.heads:
            await asyncio.to_thread(self._current.bulk_upsert, plan.heads)
            # Last, and only once the heads are durable: the read model may lag
            # the head table for a moment, but must never lead it.
            if self._projector is not None:
                projection = await asyncio.to_thread(self._projector.apply, plan.heads)
                plan.report.projected = projection.active + projection.expired
                plan.report.removed = projection.deleted

        if plan.report.expiry_sweep_skipped:
            logger.warning(
                "Expiry sweep skipped for %s: %s", source_id, plan.report.expiry_sweep_skipped
            )
        logger.info("Ingestion %s", plan.report.summary())
        return plan.report

    async def ingest_grouped(
        self,
        deals: Sequence[Deal],
        *,
        run_id: str | None = None,
        ok_sources: Iterable[str] | None = None,
        seen_fingerprints: Mapping[str, Iterable[str]] | None = None,
        raw_fingerprints: Mapping[str, str] | None = None,
    ) -> list[IngestionReport]:
        """Ingest a mixed batch, grouping by ``source_id``.

        Each source is ingested independently so one broken scraper can never
        cause deals from a healthy source to expire.
        """
        by_source: dict[str, list[Deal]] = {}
        for deal in deals:
            by_source.setdefault(deal.source_id, []).append(deal)

        ok = set(ok_sources) if ok_sources is not None else None
        fingerprints = seen_fingerprints or {}
        # Include sources that returned nothing this run — they still need their
        # heads touched (or, if the run was healthy, swept).
        for source_id in fingerprints:
            by_source.setdefault(source_id, [])

        reports: list[IngestionReport] = []
        for source_id, source_deals in by_source.items():
            reports.append(
                await self.ingest(
                    source_deals,
                    source_id=source_id,
                    run_id=run_id,
                    run_ok=(source_id in ok) if ok is not None else True,
                    seen_fingerprints=fingerprints.get(source_id, ()),
                    raw_fingerprints=raw_fingerprints,
                )
            )
        return reports
