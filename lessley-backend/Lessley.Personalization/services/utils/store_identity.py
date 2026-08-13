"""
One brand, however many times the catalogue happens to hold it.

The store list registers some brands twice — once in Hebrew and once in Latin — and the two
rows are separate documents with separate ids. That would be harmless except that **the deals
split across them**: `fox` carries six and `פוקס` three; `טרקלינ חשמל` carries nine and its
twin `טרקלין חשמל` none at all. Matching a purchase to the empty twin loses the coupon, which
is the one thing this feature exists to find.

So shops are folded into identities before anything is indexed, and an identity carries every
spelling, every category and every deal its members had.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set

from .store_text import is_hebrew, normalize

logger = logging.getLogger(__name__)


@dataclass
class StoreIdentity:
    """One shop, under all the names it goes by."""

    key: str
    store_ids: Set[str] = field(default_factory=set)
    names: List[str] = field(default_factory=list)      # display names, best first
    written_forms: List[str] = field(default_factory=list)  # names + aliases, for indexing
    categories: Set[str] = field(default_factory=set)
    deals: List[object] = field(default_factory=list)

    @property
    def name(self) -> str:
        """The name to show a user."""
        return self.names[0] if self.names else ""

    @property
    def store_id(self) -> str:
        """A stable id for the identity — the member id the rest of the system already knows."""
        return self.key

    @property
    def has_deal(self) -> bool:
        return bool(self.deals)


class _Union:
    """Union-find, just enough of it."""

    def __init__(self, keys: Iterable[str]):
        self._parent: Dict[str, str] = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self._parent
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self._parent[right_root] = left_root


def build_identities(
    stores: Sequence,
    aliases: Sequence = (),
    deals_by_store: Dict[str, List] | None = None,
) -> Dict[str, StoreIdentity]:
    """
    Fold the store list into one entry per real brand.

    Two rows are the same brand when their names match once spacing and letter forms are taken
    out, or when a name a human approved for one is the actual name of the other.

    An alias that points at more than one shop is *not* evidence of anything — it is a review
    mistake, and following it fuses unrelated brands ('Royal - רויאל' sits on both 'ROYAL CARE'
    and 'ROYAL LIGHT'). Those are left out of the merge and only used as extra spellings.
    """
    deals_by_store = deals_by_store or {}
    by_id = {store.store_id: store for store in stores if (store.name or "").strip()}

    aliases_by_store: Dict[str, List[str]] = {}
    stores_per_alias: Dict[str, Set[str]] = {}
    for alias in aliases:
        text = (getattr(alias, "alias", "") or "").strip()
        store_id = getattr(alias, "store_id", None)
        if not text or store_id not in by_id:
            continue
        aliases_by_store.setdefault(store_id, []).append(text)

        # Most aliases simply restate the shop's own name. They are not evidence about any
        # *other* shop, and counting them makes two shops that merely spell themselves the
        # same way look like an alias claiming both — which would then block the very merge
        # their identical names call for.
        compact = normalize(text).replace(" ", "")
        if compact != normalize(by_id[store_id].name).replace(" ", ""):
            stores_per_alias.setdefault(compact, set()).add(store_id)

    stores_by_compact: Dict[str, List[str]] = {}
    for store_id, store in by_id.items():
        compact = normalize(store.name).replace(" ", "")
        if compact:
            stores_by_compact.setdefault(compact, []).append(store_id)

    union = _Union(by_id)
    for same_name in stores_by_compact.values():
        for other in same_name[1:]:
            union.union(same_name[0], other)

    for store_id, texts in aliases_by_store.items():
        own_name = normalize(by_id[store_id].name).replace(" ", "")
        for text in texts:
            compact = normalize(text).replace(" ", "")
            if compact == own_name:
                continue  # says nothing the shop's own name did not already say
            if len(stores_per_alias.get(compact, ())) > 1:
                continue  # ambiguous: the same alias claims several shops
            for other in stores_by_compact.get(compact, ()):
                union.union(store_id, other)

    identities: Dict[str, StoreIdentity] = {}
    for store_id, store in by_id.items():
        root = union.find(store_id)
        identity = identities.get(root)
        if identity is None:
            identity = identities[root] = StoreIdentity(key=root)
        identity.store_ids.add(store_id)
        identity.names.append(store.name)
        identity.written_forms.append(store.name)

        official = getattr(getattr(store, "metadata", None), "official_name", None)
        if official and official.strip():
            identity.written_forms.append(official)
        identity.written_forms.extend(aliases_by_store.get(store_id, ()))

        identity.categories.update(getattr(getattr(store, "metadata", None), "mcc_codes", None) or ())
        identity.deals.extend(deals_by_store.get(store_id, ()))

    # Show a Hebrew name where there is one — the feed is Hebrew, and so is the reader.
    for identity in identities.values():
        identity.names.sort(key=lambda name: (not is_hebrew(name), -len(name)))

    merged = sum(1 for identity in identities.values() if len(identity.store_ids) > 1)
    logger.info(
        "Store identities built",
        extra={
            "reason": "Data preparation for merchant-name matching",
            "extra_data": {
                "stores": len(by_id),
                "identities": len(identities),
                "merged_identities": merged,
                "identities_with_deals": sum(1 for i in identities.values() if i.has_deal),
            },
        },
    )
    return identities
