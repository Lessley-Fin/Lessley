"""Query helpers for group-branded deals (e.g. HOT gift cards).

Some deals have a ``group_member_stores`` key in their ``raw_payload``
instead of a specific store name.  This happens when a gift card covers all
stores in a group (e.g. "קבוצת גולף - תווים" covers sabon, golf&co, kitan …).

Use :func:`get_deals_for_store` to retrieve **all** deals relevant to a given
store, including both:

- Direct deals whose ``store_name`` matches the store.
- Group-wide gift cards whose ``raw_payload["group_member_stores"]`` list
  contains the store name.

Example::

    from lessley_deals.scraping.helpers.group_deal_query import get_deals_for_store

    relevant = get_deals_for_store("sabon", all_deals)
    # Returns direct sabon deals + קבוצת גולף group-wide cards
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lessley_deals.domain.models import RawScrapedRecord

logger = logging.getLogger(__name__)


def get_deals_for_store(
    store_name: str,
    all_deals: list[RawScrapedRecord],
) -> list[RawScrapedRecord]:
    """Return all deals relevant to *store_name*.

    Merges two result sets without duplicates, preserving the original order
    of *all_deals*:

    1. **Direct deals** — ``deal.store_name`` matches *store_name*
       (case-insensitive).
    2. **Group-wide deals** — ``deal.raw_payload["group_member_stores"]``
       contains *store_name* (case-insensitive list membership).

    Args:
        store_name: The target store.  Case-insensitive.
        all_deals:  Full collection of :class:`RawScrapedRecord` instances.

    Returns:
        Filtered list in original order, no duplicates.

    Examples::

        relevant = get_deals_for_store("sabon", all_deals)
        # Includes direct sabon deals + any group-wide gift card that has
        # "sabon" in its raw_payload["group_member_stores"].
    """
    store_lower = store_name.strip().lower()
    if not store_lower:
        return []

    seen_ids: set[str] = set()
    result: list[RawScrapedRecord] = []

    for deal in all_deals:
        if deal.id in seen_ids:
            continue

        matched = False

        # 1. Direct match on store_name
        if deal.store_name.strip().lower() == store_lower:
            matched = True

        # 2. Group-wide: check raw_payload["group_member_stores"]
        if not matched:
            group_members = deal.raw_payload.get("group_member_stores")
            if isinstance(group_members, list):
                for member in group_members:
                    if isinstance(member, str) and member.strip().lower() == store_lower:
                        matched = True
                        break

        if matched:
            seen_ids.add(deal.id)
            result.append(deal)

    logger.debug(
        "get_deals_for_store('%s'): %d/%d deals matched",
        store_name,
        len(result),
        len(all_deals),
    )
    return result


def is_group_wide_deal(deal: RawScrapedRecord) -> bool:
    """Return ``True`` if *deal* is a group-wide gift card.

    A deal is considered group-wide when its ``raw_payload`` contains a
    non-empty ``group_member_stores`` list.

    Args:
        deal: Any :class:`RawScrapedRecord`.

    Returns:
        ``True`` for group-wide gift cards, ``False`` for specific-store deals.
    """
    members = deal.raw_payload.get("group_member_stores")
    return isinstance(members, list) and len(members) > 0


def get_group_member_stores(deal: RawScrapedRecord) -> list[str]:
    """Return the list of member stores covered by a group-wide gift card.

    Returns an empty list for non-group deals.

    Args:
        deal: Any :class:`RawScrapedRecord`.

    Returns:
        List of store name strings from ``raw_payload["group_member_stores"]``,
        or ``[]`` if the deal is not group-wide.
    """
    members = deal.raw_payload.get("group_member_stores")
    if isinstance(members, list):
        return [m for m in members if isinstance(m, str)]
    return []
