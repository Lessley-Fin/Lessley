"""Repair ``club_id`` on deals written before ``PersistStage`` knew the clubs.

Every consumer reads ``deals`` directly — the Gateway's deal search, Personalization's
reference data and ``deal-optimizer`` — so the club a deal belongs to has to be correct in
the collection itself rather than recovered by whoever happens to read it.

The join is the same one the projection made: ``deals.source_id`` -> ``clubs.source_id``.
Only rows with no club are touched, so re-running changes nothing, and a deal whose source
has no club is left alone rather than guessed at.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pymongo import UpdateOne

logger = logging.getLogger(__name__)

# What counts as "no club": the field absent, null, or an empty string.
_MISSING_CLUB = {"$or": [{"club_id": {"$exists": False}}, {"club_id": None}, {"club_id": ""}]}


@dataclass
class BackfillResult:
    matched: int = 0
    """Deals given a club (or that would be, under --dry-run)."""

    by_source: dict[str, int] = field(default_factory=dict)
    """source_id -> number of deals updated."""

    unmatched_sources: dict[str, int] = field(default_factory=dict)
    """source_id -> deals left alone because no club claims that source."""

    club_by_source: dict[str, str] = field(default_factory=dict)
    """The join map this run used, for reporting."""


def build_club_by_source(db: Any) -> dict[str, str]:
    """``source_id`` -> ``club_id``, straight from the ``clubs`` collection."""
    mapping: dict[str, str] = {}
    for club in db["clubs"].find({}):
        source_id = club.get("source_id")
        club_id = club.get("_id") or club.get("id")
        if source_id and club_id:
            mapping[str(source_id)] = str(club_id)
    return mapping


def backfill_club_ids(db: Any, dry_run: bool = False) -> BackfillResult:
    """Set ``club_id`` on every ``deals`` row that lacks one and whose source has a club."""
    result = BackfillResult(club_by_source=build_club_by_source(db))
    if not result.club_by_source:
        logger.warning("No clubs in the database — nothing to join deals against")
        return result

    operations: list[UpdateOne] = []
    for deal in db["deals"].find(_MISSING_CLUB, {"_id": 1, "source_id": 1}):
        source_id = str(deal.get("source_id") or "")
        club_id = result.club_by_source.get(source_id)

        if club_id is None:
            # A source nothing claims — leave it null rather than invent a club.
            result.unmatched_sources[source_id] = result.unmatched_sources.get(source_id, 0) + 1
            continue

        result.by_source[source_id] = result.by_source.get(source_id, 0) + 1
        result.matched += 1
        operations.append(UpdateOne({"_id": deal["_id"]}, {"$set": {"club_id": club_id}}))

    if operations and not dry_run:
        db["deals"].bulk_write(operations, ordered=False)

    logger.info(
        "club_id backfill %s — %d deal(s) across %d source(s), %d left unmatched",
        "planned" if dry_run else "applied",
        result.matched,
        len(result.by_source),
        sum(result.unmatched_sources.values()),
    )
    return result
