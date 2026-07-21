from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from typing import Any

from lessley_deals.domain.models import RawScrapedRecord
from lessley_deals.enrichment.constaints_parser import DealConstraints, parse_deal_constraints

logger = logging.getLogger(__name__)


def _terms_of(deal: RawScrapedRecord) -> str | None:
    """Pull the terms & conditions text a scraper attached to the raw payload."""
    terms = deal.raw_payload.get("terms_and_conditions")
    if isinstance(terms, str) and terms.strip():
        return terms
    return None


class ConstraintsStage:
    """Parse every scraped deal's terms into a structured ``constraints`` block.

    Runs as part of the scrape pipeline (after scraping, before persist) so that
    constraints are produced for EVERY source uniformly — no scraper needs to
    know about the LLM. Deals without terms text are skipped; a parse failure
    (timeout, bad output, no LLM configured) is logged and skipped, never fatal.
    """

    def __init__(
        self,
        parser: Callable[[str], DealConstraints] = parse_deal_constraints,
        *,
        max_concurrency: int = 5,
    ) -> None:
        self._parser = parser
        self._max_concurrency = max(1, max_concurrency)

    async def run(self, deals: Sequence[RawScrapedRecord]) -> dict[str, dict[str, Any]]:
        """Return ``{raw_id: constraints_dict}`` for every deal we could parse."""
        targets = [(d.id, _terms_of(d)) for d in deals]
        parseable = [(rid, terms) for rid, terms in targets if terms is not None]

        skipped_no_terms = len(targets) - len(parseable)
        if not parseable:
            logger.info(
                "Constraints stage: 0/%d deals have terms — nothing to parse", len(targets)
            )
            return {}

        semaphore = asyncio.Semaphore(self._max_concurrency)
        loop = asyncio.get_event_loop()

        async def _one(raw_id: str, terms: str) -> tuple[str, dict[str, Any] | None]:
            async with semaphore:
                try:
                    result = await loop.run_in_executor(None, self._parser, terms)
                except Exception as exc:  # noqa: BLE001 — never let one deal kill the run
                    logger.warning("Constraints parse failed for %s: %s", raw_id, exc)
                    return raw_id, None
                return raw_id, result.model_dump()

        pairs = await asyncio.gather(*(_one(rid, terms) for rid, terms in parseable))
        constraints_map = {rid: c for rid, c in pairs if c is not None}

        logger.info(
            "Constraints stage: parsed %d/%d deals (%d without terms, %d failed)",
            len(constraints_map),
            len(targets),
            skipped_no_terms,
            len(parseable) - len(constraints_map),
        )
        return constraints_map
