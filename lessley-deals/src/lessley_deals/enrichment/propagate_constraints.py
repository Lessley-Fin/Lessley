from __future__ import annotations

import logging
from pathlib import Path

from lessley_deals.domain.protocols import RawDealRepository
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.deals import DealJsonRepository

logger = logging.getLogger(__name__)


def propagate_constraints(
    raw_repo: RawDealRepository,
    *,
    data_dir: str = "data",
    file: str | None = None,
    source: str = "",
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Copy constraints already parsed onto raw records across to built deals.

    ``PersistStage`` reads ``raw_payload["constraints"]`` when it builds a Deal,
    so deals built *before* the raw records were enriched carry none. Rather
    than re-parsing their terms — the answer is already on disk — this matches
    each deal to its raw record by ``raw_id`` and copies the block over.

    Costs zero LLM calls and runs in seconds. Idempotent: deals that already
    have constraints are left alone unless *force*.

    Args:
        raw_repo: Raw deal repository holding the enriched records.
        data_dir: Data directory holding ``deals.json`` (used when *file* is None).
        file:     Explicit path to a deals JSON file. Overrides *data_dir*.
        source:   Only touch deals from this ``source_id`` (``""`` = all).
        force:    Overwrite deals that already carry constraints.
        dry_run:  Report what would change without writing.

    Returns:
        Counters: ``total``, ``updated``, ``skipped``, ``no_raw_match``,
        ``raw_without_constraints``.
    """
    deals_path = Path(file) if file else PersistenceConfig(base_dir=Path(data_dir)).deals_path
    deal_repo = DealJsonRepository(deals_path)
    deals = deal_repo.get_all()

    constraints_by_raw_id = {
        record.id: record.raw_payload["constraints"]
        for record in raw_repo.get_all()
        if record.raw_payload.get("constraints")
    }
    logger.info(
        "Loaded %d deals and %d enriched raw records", len(deals), len(constraints_by_raw_id)
    )

    stats = {
        "total": len(deals),
        "updated": 0,
        "skipped": 0,
        "no_raw_match": 0,
        "raw_without_constraints": 0,
    }
    updated = []

    for deal in deals:
        if source and deal.source_id != source:
            stats["skipped"] += 1
            continue
        if deal.constraints is not None and not force:
            stats["skipped"] += 1
            continue

        constraints = constraints_by_raw_id.get(deal.raw_id)
        if constraints is None:
            # Either the raw record is gone, or it was never enriched — most
            # often because it has no terms text to parse in the first place.
            if deal.raw_id in constraints_by_raw_id:
                stats["raw_without_constraints"] += 1
            else:
                stats["no_raw_match"] += 1
            continue

        deal.constraints = constraints
        updated.append(deal)
        stats["updated"] += 1

    if updated and not dry_run:
        written = deal_repo.update_many(updated)
        if written != len(updated):
            logger.warning(
                "Wrote %d/%d deals — %d ids vanished", written, len(updated), len(updated) - written
            )
            stats["updated"] = written

    logger.info(
        "Propagated constraints to %d/%d deals (%d skipped, %d without a raw match)",
        stats["updated"],
        stats["total"],
        stats["skipped"],
        stats["no_raw_match"],
    )
    return stats
