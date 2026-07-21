from __future__ import annotations

import logging
from pathlib import Path

from lessley_deals.enrichment.constaints_parser import parse_deal_constraints
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.deals import DealJsonRepository

logger = logging.getLogger(__name__)


def enrich_deal_constraints(
    data_dir: str = "data",
    source: str = "hot",
    limit: int = 0,
    dry_run: bool = False,
    force: bool = False,
    file: str | None = None,
) -> dict[str, int]:
    """Parse ``terms_and_conditions`` into structured ``constraints`` on deals.

    Additive and idempotent: deals that already carry a ``constraints`` object
    are skipped unless ``force=True``. Deals without terms are skipped. All
    other deal fields are preserved — only ``constraints`` is written.

    Args:
        data_dir: Data directory holding ``deals.json`` (used when ``file`` is None).
        source:   Only enrich deals from this ``source_id`` (``""`` = all).
        limit:    Enrich at most N deals (0 = no cap).
        dry_run:  Call the LLM but do not persist the result.
        force:    Re-parse deals that already have ``constraints``.
        file:     Explicit path to a deals JSON file. Overrides ``data_dir``.

    Returns:
        Counters: ``total``, ``processed``, ``skipped``, ``failed``.
    """
    deals_path = Path(file) if file else PersistenceConfig(base_dir=Path(data_dir)).deals_path
    repo = DealJsonRepository(deals_path)
    deals = repo.get_all()

    stats = {"total": len(deals), "processed": 0, "skipped": 0, "failed": 0}

    for deal in deals:
        if limit and stats["processed"] >= limit:
            break

        if source and deal.source_id != source:
            stats["skipped"] += 1
            continue

        if not force and deal.constraints is not None:
            stats["skipped"] += 1
            logger.debug("Skipping already-enriched deal: %s", deal.id)
            continue

        terms = deal.terms_and_conditions
        if not terms or not terms.strip():
            stats["skipped"] += 1
            logger.debug("Skipping deal with no terms: %s", deal.id)
            continue

        try:
            result = parse_deal_constraints(terms)
        except Exception as exc:
            stats["failed"] += 1
            logger.warning("Constraints parse failed for %s: %s", deal.id, exc)
            continue

        logger.info(
            "Enriched %s (%s) -> %s",
            deal.id,
            deal.title or deal.deal_description or "?",
            result.model_dump(),
        )

        if not dry_run:
            deal.constraints = result.model_dump()
            if not repo.update(deal):
                # Should not happen (we just read it from the same store) but
                # guard against a concurrent write racing the id away.
                stats["failed"] += 1
                logger.warning("Deal vanished before update: %s", deal.id)
                continue

        stats["processed"] += 1

    return stats
