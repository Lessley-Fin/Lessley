import logging
import math
from collections import Counter, defaultdict
from typing import Dict, List, Set

from models.db.entities import Store

from .store_text import normalize, script_groups, strip_boilerplate, tokenize

logger = logging.getLogger(__name__)


class StoreIndex:
    """
    The store list, arranged for looking a shop up by name.

    Two things are precomputed here, both once at startup:

    * how *rare* each word is across all shop names. This is what lets matching tell a
      brand from a description — 'צומת' appears in one shop name, 'קפה' in a hundred, so
      they are worth wildly different amounts as evidence even though both are just words.
    * which shops contain each word, so a merchant name only has to be scored against the
      handful of shops that share a word with it rather than all several thousand.
    """

    def __init__(self, stores: List[Store]):
        self._stores_by_id: Dict[str, Store] = {}
        self._stores_by_exact_name: Dict[str, str] = {}     # squashed name -> store id
        self._token_groups: Dict[str, List[List[str]]] = {}  # store id -> its name(s), split by script
        self._stores_by_token: Dict[str, Set[str]] = defaultdict(set)
        self._document_frequency: Counter = Counter()

        for store in stores:
            self._add(store)

        # Rarity is scaled to 0..1 rather than left as a raw IDF, so the thresholds in
        # STORE_MATCH mean the same thing whatever size the store list happens to be.
        # A word in no shop name scores 1.0; one in every shop name scores 0.
        total = max(len(stores), 1)
        scale = math.log(total) or 1.0
        self._rarity: Dict[str, float] = {
            token: math.log(total / (1 + count)) / scale
            for token, count in self._document_frequency.items()
        }

        logger.info(
            "Store name index built",
            extra={
                "reason": "Data preparation for merchant-name matching",
                "extra_data": {
                    "store_count": len(self._stores_by_id),
                    "exact_name_count": len(self._stores_by_exact_name),
                    "vocabulary_size": len(self._document_frequency),
                },
            },
        )

    def _add(self, store: Store) -> None:
        self._stores_by_id[store.store_id] = store

        # A shop can be written more than one way. `official_name` carries the English
        # form for shops whose display name is Hebrew ('עיל"מ' / 'Herbology'), so a card
        # feed that reports either spelling can still find it.
        #
        # A `written_forms` list, when the caller has one, replaces that pair outright: an
        # identity folded together from several catalogue rows carries every spelling its
        # members had, plus the aliases a human approved, and all of them must be findable.
        written_forms = list(getattr(store, "written_forms", None) or ())
        if not written_forms:
            written_forms = [store.name]
            official_name = getattr(store.metadata, "official_name", None)
            if official_name and official_name.strip():
                written_forms.append(official_name)

        groups: List[List[str]] = []
        every_token: Set[str] = set()

        for written_form in written_forms:
            normalized = normalize(written_form)
            if not normalized:
                continue
            self._stores_by_exact_name.setdefault(normalized.replace(" ", ""), store.store_id)

            # Only feed boilerplate is dropped from a shop's own name. A town stays: a
            # branch's town is part of what identifies it, and 'יקבי בנימינה' must not be
            # allowed to answer for 'יקבי קיסריה'.
            tokens = strip_boilerplate(tokenize(normalized))
            if tokens:
                groups.extend(script_groups(tokens))
                every_token.update(tokens)

        if not groups:
            return

        self._token_groups[store.store_id] = groups
        for token in every_token:
            self._document_frequency[token] += 1
            self._stores_by_token[token].add(store.store_id)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_store(self, store_id: str) -> Store | None:
        return self._stores_by_id.get(store_id)

    def store_id_by_exact_name(self, squashed_name: str) -> str | None:
        """A shop whose name, with the spaces taken out, is exactly this."""
        return self._stores_by_exact_name.get(squashed_name)

    def token_groups(self, store_id: str) -> List[List[str]]:
        return self._token_groups.get(store_id, [])

    def document_frequency(self, token: str) -> int:
        """How many shop names contain this word."""
        return self._document_frequency.get(token, 0)

    def rarity(self, token: str) -> float:
        """
        How much this word narrows things down, from 0 (in every shop name) to 1 (in none).

        A word we have never seen scores highest, which is right as far as it goes — but
        callers must also check `is_known`, because a word that appears in no shop name at
        all cannot point at a shop, however rare it is.
        """
        return self._rarity.get(token, 1.0)

    def is_known(self, token: str) -> bool:
        return token in self._document_frequency

    def candidate_store_ids(self, tokens: Set[str], document_frequency_cap: int) -> Set[str]:
        """Every shop sharing at least one reasonably selective word with these."""
        candidates: Set[str] = set()
        for token in tokens:
            if 0 < self._document_frequency.get(token, 0) <= document_frequency_cap:
                candidates |= self._stores_by_token.get(token, set())
        return candidates

    def __len__(self) -> int:
        return len(self._stores_by_id)
