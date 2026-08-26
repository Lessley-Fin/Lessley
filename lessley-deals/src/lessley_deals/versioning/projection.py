"""Project the head table onto ``deals`` — the flat collection consumers read.

``ingestion.py`` already decides, correctly and conservatively, what happened to
every offer in a run: new, updated, unchanged, reactivated, expired.  But it
writes those decisions to ``deals_current`` / ``deal_versions`` only, and nothing
downstream reads those: ``deal-optimizer``'s ``deals_source``, the Gateway's deal
search and Personalization all read ``deals``.  Before this module, ``deals`` was
append-only — an offer taken down by its source kept being priced and shown
forever, because no code path ever removed or flagged the row.

This closes that gap.  After each run the projector walks the heads the
ingestion just wrote and mirrors them onto ``deals``:

===============  ===============================================================
ACTIVE head      upsert the row under its **stable** ``deal_id``, stamped with
                 ``status="active"`` and a fresh ``last_seen_at``
EXPIRED head     stamp ``status="expired"`` + ``expired_at`` — or delete the row
                 outright when ``delete_expired`` is on
===============  ===============================================================

Marking is the default rather than deleting.  An expired row still answers "why
is this deal no longer offered?" for a saved deal or a notification that
references it, and a source that goes quiet for a day and comes back
(REACTIVATED) then flips its own row back to active with its id — and therefore
every reference to it — intact.  Deleting is one env flag away for deployments
that would rather keep the collection small.

The upsert covers *every* active head, not just the ones that changed, so the
projection is idempotent and self-healing: a run that crashed halfway through
last time is fully repaired by the next one.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

from lessley_deals.domain.enums import DealLifecycleStatus
from lessley_deals.domain.models import CurrentDeal, Deal
from lessley_deals.persistence.serialization import deal_from_dict

logger = logging.getLogger(__name__)


class ProjectableDealRepository(Protocol):
    """The slice of the deals repository the projector needs."""

    def bulk_upsert(self, deals: Sequence[Deal]) -> int: ...
    def delete_by_ids(self, deal_ids: Sequence[str]) -> int: ...


@dataclass
class ProjectionReport:
    active: int = 0
    """Rows written back as on-offer."""

    expired: int = 0
    """Rows flagged as no longer on offer."""

    deleted: int = 0
    """Rows removed outright (only when ``delete_expired`` is on)."""

    skipped: int = 0
    """Heads whose snapshot could not be turned back into a deal."""

    def summary(self) -> str:
        parts = [f"active={self.active}", f"expired={self.expired}"]
        if self.deleted:
            parts.append(f"deleted={self.deleted}")
        if self.skipped:
            parts.append(f"skipped={self.skipped}")
        return "Projection: " + " ".join(parts)


class DealProjector:
    """Mirrors ``deals_current`` onto ``deals`` after every ingestion."""

    def __init__(
        self,
        deal_repo: ProjectableDealRepository,
        *,
        delete_expired: bool = False,
    ) -> None:
        self._deals = deal_repo
        self._delete_expired = delete_expired

    def apply(self, heads: Sequence[CurrentDeal]) -> ProjectionReport:
        report = ProjectionReport()
        upserts: list[Deal] = []
        deletions: list[str] = []

        for head in heads:
            deal = self._deal_from_head(head)
            if deal is None:
                report.skipped += 1
                continue

            if head.status == DealLifecycleStatus.EXPIRED:
                if self._delete_expired:
                    deletions.append(head.deal_id)
                    report.deleted += 1
                else:
                    upserts.append(deal)
                    report.expired += 1
            else:
                upserts.append(deal)
                report.active += 1

        if upserts:
            self._deals.bulk_upsert(upserts)
        if deletions:
            self._deals.delete_by_ids(deletions)

        logger.info(report.summary())
        return report

    @staticmethod
    def _deal_from_head(head: CurrentDeal) -> Deal | None:
        """Rebuild the flat deal a head describes, stamped with its lifecycle.

        The snapshot is the deal exactly as the source published it; everything
        about *when* it was seen and whether it is still on offer comes from the
        head, which is the only place that knows.
        """
        snapshot: dict[str, Any] = dict(head.snapshot or {})
        if not snapshot:
            return None

        # The head's own columns win over anything the snapshot happens to
        # carry: ``deal_id`` is the stable business key every consumer already
        # references, even if the snapshot predates it.
        snapshot["id"] = head.deal_id
        snapshot.setdefault("store_id", head.store_id)
        snapshot.setdefault("source_id", head.source_id)

        try:
            deal = deal_from_dict(snapshot)
        except (KeyError, TypeError, ValueError):
            # A malformed snapshot must never take a whole run down with it —
            # the head and version rows are still correct, and the next run
            # rebuilds this row from a fresh scrape.
            logger.warning("Skipping unprojectable head %s", head.deal_key, exc_info=True)
            return None

        expired = head.status == DealLifecycleStatus.EXPIRED
        return replace(
            deal,
            deal_key=head.deal_key,
            status=head.status,
            first_seen_at=head.first_seen_at,
            last_seen_at=head.last_seen_at,
            expires_at=head.source_expires_at,
            # ``valid_to`` is when the deal stopped being on offer; the sweep
            # sets it at the moment of expiry, so it is the honest timestamp.
            expired_at=(head.valid_to or head.last_seen_at) if expired else None,
        )


def stale_deal_ids(known_ids: set[str], heads: Sequence[CurrentDeal]) -> set[str]:
    """Ids in ``deals`` that no head accounts for — leftovers from before this.

    Every run before the projector existed appended a *fresh* random id for each
    deal it rebuilt, so a source that reworded a deal left the old row behind
    with nothing pointing at it.  Those rows are indistinguishable from live ones
    to a consumer, which is why ``deals reconcile-deals`` exists to sweep them.

    Deliberately not called during a run: an id missing from the heads is only
    evidence of a leftover if the heads for that source are complete, and only
    the reconcile command establishes that.
    """
    return known_ids - {head.deal_id for head in heads}
