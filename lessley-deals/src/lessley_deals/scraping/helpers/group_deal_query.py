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
    store_name_or_id: str,
    all_deals: list[RawScrapedRecord],
) -> list[RawScrapedRecord]:
    """Return all deals relevant to *store_name_or_id*.

    Merges two result sets without duplicates, preserving the original order
    of *all_deals*:

    1. **Direct deals** — ``deal.store_name`` matches *store_name_or_id*
       (case-insensitive).
    2. **Group-wide deals** — ``deal.raw_payload["group_member_stores"]``
       contains the target.  Each member entry is either:
         - a legacy ``str`` name (matched case-insensitively against the input), or
         - a structured ``{"name": ..., "store_id": ...}`` dict (the input
           matches *either* the ``name`` or the ``store_id``).

    Args:
        store_name_or_id: The target store name or canonical store id.
            Case-insensitive for name comparisons; exact for store_id.
        all_deals:  Full collection of :class:`RawScrapedRecord` instances.

    Returns:
        Filtered list in original order, no duplicates.

    Examples::

        relevant = get_deals_for_store("sabon", all_deals)          # by name
        relevant = get_deals_for_store("store_0123", all_deals)     # by id
    """
    raw_target = store_name_or_id.strip()
    target_lower = raw_target.lower()
    if not target_lower:
        return []

    seen_ids: set[str] = set()
    result: list[RawScrapedRecord] = []

    for deal in all_deals:
        if deal.id in seen_ids:
            continue

        matched = False

        # 1. Direct match on store_name
        if deal.store_name.strip().lower() == target_lower:
            matched = True

        # 2. Group-wide: check raw_payload["group_member_stores"]
        if not matched:
            group_members = deal.raw_payload.get("group_member_stores")
            if isinstance(group_members, list):
                for member in group_members:
                    if isinstance(member, str):
                        if member.strip().lower() == target_lower:
                            matched = True
                            break
                    elif isinstance(member, dict):
                        member_name = str(member.get("name") or "").strip().lower()
                        member_sid = str(member.get("store_id") or "").strip()
                        if member_name == target_lower or member_sid == raw_target:
                            matched = True
                            break

        if matched:
            seen_ids.add(deal.id)
            result.append(deal)

    logger.debug(
        "get_deals_for_store('%s'): %d/%d deals matched",
        store_name_or_id,
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
    """Return the list of member-store names covered by a group-wide gift card.

    Returns an empty list for non-group deals.  Both legacy ``str`` entries
    and structured ``{"name", "store_id"}`` dict entries are supported; only
    the ``name`` is returned.  See :func:`get_group_member_store_ids` for the
    resolved-id variant.

    Args:
        deal: Any :class:`RawScrapedRecord`.

    Returns:
        List of store-name strings, or ``[]`` if the deal is not group-wide.
    """
    members = deal.raw_payload.get("group_member_stores")
    if not isinstance(members, list):
        return []
    out: list[str] = []
    for m in members:
        if isinstance(m, str):
            out.append(m)
        elif isinstance(m, dict):
            name = m.get("name")
            if isinstance(name, str) and name:
                out.append(name)
    return out


def get_group_member_store_ids(deal: RawScrapedRecord) -> list[str]:
    """Return the list of resolved canonical ``store_id`` values for a group deal.

    Empty list for legacy deals where members are bare strings, or when no
    member has been resolved against the canonical stores table yet.
    """
    members = deal.raw_payload.get("group_member_stores")
    if not isinstance(members, list):
        return []
    out: list[str] = []
    for m in members:
        if isinstance(m, dict):
            sid = m.get("store_id")
            if isinstance(sid, str) and sid:
                out.append(sid)
    return out
