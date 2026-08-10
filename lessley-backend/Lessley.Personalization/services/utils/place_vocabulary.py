import logging
from collections import Counter
from typing import Iterable, Set

from .store_text import normalize, tokenize

logger = logging.getLogger(__name__)


class PlaceVocabulary:
    """
    The words that say *where* a branch is rather than *what* it is — malls, retail parks,
    streets, shopping-centre names: 'קניון ערים', 'עזריאלי', 'רננים', 'הנשיאים'.

    This is the one thing name matching cannot work out for itself. Nothing in the store
    list separates a mall from a brand: 'עזריאלי' appears in two shop names and 'קסטרו' in
    two, and both look equally like somebody's trading name. Yet the difference decides
    every verdict — an unexplained brand word means "different shop", an unexplained mall
    word means "same shop, other branch".

    Rather than keep a hand-written list, these are learned: a place word turns up
    attached to *many unrelated* merchants, while a brand turns up attached to one. Feed
    enough merchant names through `learn_from_merchant_names` and the place words separate
    themselves out.

    Until that has seen enough traffic the vocabulary is simply empty, and matching falls
    back to being cautious about unexplained words. The transaction's own `townName`
    covers actual towns from day one and does not depend on this at all.
    """

    def __init__(self, words: Iterable[str] | None = None):
        self._words: Set[str] = {word for word in (words or []) if word}

    def __contains__(self, word: str) -> bool:
        return word in self._words

    def __len__(self) -> int:
        return len(self._words)

    def strip(self, tokens: Iterable[str]) -> list[str]:
        """Drop place words, unless that would leave nothing at all."""
        tokens = list(tokens)
        if not self._words:
            return tokens
        kept = [token for token in tokens if token not in self._words]
        return kept or tokens

    @classmethod
    def learn_from_merchant_names(
        cls,
        merchant_names: Iterable[str],
        store_index,
        min_merchants: int = 3,
        max_store_share: float = 0.002,
    ) -> "PlaceVocabulary":
        """
        Work out which words are places by how they behave across merchant names.

        A word earns its place in the vocabulary when it shows up against many *different*
        merchants while being rare in the store list itself. 'קניון' attaches to a dozen
        unrelated shops; 'קסטרו' attaches only to Castro, however often Castro is visited.

        `merchant_names` should be distinct names — the same shop visited fifty times is
        one piece of evidence, not fifty. Counting raw transactions would promote whichever
        shops a user happens to frequent into "places" and quietly break their matching.
        """
        appearances: Counter = Counter()
        seen: Set[str] = set()

        for merchant_name in merchant_names:
            normalized = normalize(merchant_name)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            for token in set(tokenize(normalized)):
                appearances[token] += 1

        store_count = max(len(store_index), 1)
        words = {
            token
            for token, count in appearances.items()
            if count >= min_merchants
            and store_index.document_frequency(token) / store_count <= max_store_share
        }

        logger.info(
            "Place vocabulary learned from merchant names",
            extra={
                "reason": "Data preparation for merchant-name matching",
                "extra_data": {
                    "distinct_merchant_names": len(seen),
                    "vocabulary_size": len(words),
                    "min_merchants": min_merchants,
                },
            },
        )
        return cls(words)


EMPTY = PlaceVocabulary()
