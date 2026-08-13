"""
Which shops running a deal could this purchase have been made at?

A different question from ``store_name_matcher``, and answered differently. That one asks "is
this definitely the same shop" and says nothing when unsure, because naming the wrong shop is
worse than naming none. Here the answer feeds "you could have had a coupon", where a near miss
still lands on a shop selling the same thing — 'קפה ברלין' against 'קפה קפה' is two cafés, and
telling the user about a café deal is useful even when it is not *their* café.

So the shop's name still has to be accounted for, but the merchant's leftover words no longer
have to be. Every answer carries a band saying how much weight it will bear, because the
difference between "you missed a coupon here" and "somewhere similar has one" is the
difference between a useful product and a lying one.

Only shops that actually run a deal are searched. A match to a shop with nothing on offer
cannot produce a missed coupon, so leaving them out costs nothing and removes a whole class
of possible mistakes.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Sequence

from config.constants import SHOP_MATCH, STORE_MATCH

from .category_affinity import is_vetoed
from .store_identity import StoreIdentity
from .store_index import StoreIndex
from .store_text import normalize, strip_boilerplate, strip_town, tokenize
# The one-to-one word pairing, shared with the strict matcher: without it a single merchant
# word can answer for both halves of a two-word shop name and look like a perfect fit.
from .store_name_matcher import _align
from .vocabularies import as_hebrew_town, place_words

logger = logging.getLogger(__name__)

EXACT = "EXACT"        # the names are the same name
STRONG = "STRONG"      # rare words in common — this is the shop
SIMILAR = "SIMILAR"    # a line-of-business word in common — somewhere like it
WEAK = "WEAK"          # too thin to say either way; kept for debugging, not for users

SURFACEABLE = (EXACT, STRONG, SIMILAR)
CONFIDENT = (EXACT, STRONG)


@dataclass
class ShopMatch:
    """One shop this purchase could have earned a coupon at, and how sure we are."""

    identity: StoreIdentity
    band: str
    store_coverage: float
    shared_tokens: List[str] = field(default_factory=list)

    @property
    def is_confident(self) -> bool:
        """True when this is the shop itself rather than one merely like it."""
        return self.band in CONFIDENT

    @property
    def deals(self) -> List:
        return self.identity.deals


class DealShopFinder:
    """Looks a merchant name up against the shops that are running deals."""

    def __init__(self, identities: Sequence[StoreIdentity]):
        self._with_deals = [identity for identity in identities if identity.has_deal]
        self._by_key = {identity.store_id: identity for identity in self._with_deals}
        self._index = StoreIndex(self._with_deals)

        logger.info(
            "Deal-shop finder ready",
            extra={
                "reason": "Data preparation for missed-savings analysis",
                "extra_data": {
                    "identities_with_deals": len(self._with_deals),
                    "identities_seen": len(identities),
                },
            },
        )

    def __len__(self) -> int:
        return len(self._with_deals)

    def find(
        self,
        merchant_name: str | None,
        town_name: str | None = None,
        transaction_category: str | None = None,
        limit: int = SHOP_MATCH.MAX_SUGGESTIONS,
    ) -> List[ShopMatch]:
        """Every deal-running shop this merchant name could be, best first."""
        normalized = normalize(merchant_name)
        if not normalized or len(normalized) < SHOP_MATCH.MIN_QUERY_LENGTH:
            return []

        # An identical name is the end of the argument. It is not put to the category check:
        # the feed's own category is unreliable enough that it must never overrule the name
        # itself agreeing exactly.
        exact_key = self._index.store_id_by_exact_name(normalized.replace(" ", ""))
        if exact_key and exact_key in self._by_key:
            return [ShopMatch(self._by_key[exact_key], EXACT, 1.0, [])]

        all_words = set(tokenize(normalized))
        identifying = self._identifying_words(all_words, town_name)
        if not identifying:
            return []

        # A name that boils down to one word half the high street shares is a category label
        # ('מסעדה'), and would otherwise match every shop in that category at once.
        if (
            len(identifying) == 1
            and self._index.document_frequency(identifying[0]) >= SHOP_MATCH.LOW_INFORMATION_DF
        ):
            return []

        # A word in no shop name at all is a name we cannot account for. It cannot point at a
        # shop, but its presence means the merchant is called something we have not explained.
        carries_unknown = any(
            not self._index.is_known(word) and len(word) >= SHOP_MATCH.MIN_SHARED_TOKEN_LENGTH
            for word in identifying
        )

        candidates = self._index.candidate_store_ids(set(identifying), SHOP_MATCH.CANDIDATE_DF_CAP)
        if not candidates:
            return []

        matches: List[ShopMatch] = []
        for key in candidates:
            identity = self._by_key.get(key)
            if identity is None:
                continue
            scored = self._score(key, all_words)
            if scored is None:
                continue
            coverage, shared, shop_tokens = scored

            # The category is a safety net, not a selector, and it only gets a say when the
            # name evidence is a single word. Given more than that the name wins: a shop
            # tagged with a real category would otherwise lose to one tagged only
            # 'SHOPPING_OTHER', which is exactly backwards.
            if len(shared) == 1 and is_vetoed(transaction_category, identity.categories):
                continue

            matches.append(
                ShopMatch(
                    identity=identity,
                    band=self._band(shared, carries_unknown, identifying, shop_tokens),
                    store_coverage=coverage,
                    shared_tokens=shared,
                )
            )

        order = {EXACT: 0, STRONG: 1, SIMILAR: 2, WEAK: 3}
        matches.sort(
            key=lambda match: (
                order[match.band],
                -match.store_coverage,
                -len(match.deals),
                match.identity.store_id,
            )
        )
        return matches[:limit]

    # ── the pieces ────────────────────────────────────────────────────────────

    def _identifying_words(self, all_words: set, town_name: str | None) -> List[str]:
        """
        What the merchant is *called*, with where it is taken out.

        The town comes from the purchase itself, so it does not have to be guessed — but the
        feed writes it in Latin about a third of the time, and a Latin town never matches a
        Hebrew word, so it is put back into Hebrew first.

        Callers keep the unstripped words too: a shop may carry a place in its own name
        ('VERT לגון נתניה') and still has to be able to match on it.
        """
        without_town = strip_town(strip_boilerplate(all_words), as_hebrew_town(town_name))
        known_places = place_words()
        kept = [word for word in without_town if word not in known_places]
        return kept or without_town

    def _score(self, key: str, all_words: set):
        """How much of this shop's name the merchant string accounts for, at its best."""
        best = None
        for store_tokens in self._index.token_groups(key):
            token_set = set(store_tokens)
            aligned = _align(token_set, all_words)
            if not aligned:
                continue

            shared = [store_token for store_token, _, _ in aligned]
            if not any(len(token) >= SHOP_MATCH.MIN_SHARED_TOKEN_LENGTH for token in shared):
                continue

            shared_mass = sum(
                self._index.rarity(store_token) * (1.0 if is_exact else STORE_MATCH.FUZZY_MASS_DISCOUNT)
                for store_token, _, is_exact in aligned
            )
            whole_name_mass = sum(self._index.rarity(token) for token in token_set)
            coverage = shared_mass / whole_name_mass if whole_name_mass else 0.0
            if coverage < SHOP_MATCH.STORE_COVERAGE_MIN:
                continue
            if best is None or coverage > best[0]:
                best = (coverage, shared, token_set)
        return best

    def _trades(self, tokens) -> set:
        """The words among these that name a line of business rather than a shop."""
        return {
            token
            for token in tokens
            if self._index.is_known(token)
            and self._index.rarity(token) <= SHOP_MATCH.LINE_OF_BUSINESS_RARITY_MAX
        }

    def _band(
        self, shared: List[str], carries_unknown: bool, merchant_words, shop_tokens
    ) -> str:
        """How much weight this match will bear."""
        rarest = max(self._index.rarity(token) for token in shared)

        # Each side says what trade it is in, and they disagree: 'קפה רוטשילד' against
        # 'פיצה רוטשילד' is a café and a pizzeria that happen to share a street name. Still
        # worth offering — both sell food — but never as the shop the user walked into.
        merchant_trades, shop_trades = self._trades(merchant_words), self._trades(shop_tokens)
        trades_disagree = bool(merchant_trades and shop_trades and not (merchant_trades & shop_trades))

        if not trades_disagree and (len(shared) >= 2 or rarest >= SHOP_MATCH.SOLO_RARITY_MIN):
            # One shared word, and a name of its own we could not place, is the shape behind
            # every bad match found in the audit: 'דוקטור גונזו' -> 'דוקטור K'. The word that
            # should have ruled the shop out is the very word we had to set aside.
            if len(shared) == 1 and carries_unknown:
                return WEAK
            return STRONG

        if trades_disagree or rarest <= SHOP_MATCH.LINE_OF_BUSINESS_RARITY_MAX:
            return SIMILAR

        return WEAK
