from dataclasses import dataclass, field
from typing import List, Set, Tuple

from rapidfuzz import fuzz

from config.constants import STORE_MATCH
from models.db.entities import Store

from .place_vocabulary import EMPTY as NO_PLACE_WORDS, PlaceVocabulary
from .store_index import StoreIndex
from .store_text import normalize, strip_boilerplate, strip_town, tokenize

# Why the match was turned down, for the debug view.
NO_NAME = "NO_NAME"
TOO_SHORT = "TOO_SHORT"
NO_KNOWN_WORDS = "NO_KNOWN_WORDS"
NO_CANDIDATES = "NO_CANDIDATES"
QUERY_NOT_EXPLAINED = "QUERY_NOT_EXPLAINED"
STORE_NOT_EXPLAINED = "STORE_NOT_EXPLAINED"
EVIDENCE_TOO_WEAK = "EVIDENCE_TOO_WEAK"
AMBIGUOUS = "AMBIGUOUS"

EXACT = "EXACT"
MATCHED = "MATCHED"
NO_MATCH = "NO_MATCH"


@dataclass
class StoreMatch:
    """What we concluded about one merchant name, and why."""

    status: str                                   # EXACT | MATCHED | NO_MATCH
    store: Store | None = None
    normalized_name: str = ""
    store_coverage: float | None = None           # how much of the shop's name we explained
    query_coverage: float | None = None           # how much of the merchant's name it explained
    shared_tokens: List[str] = field(default_factory=list)
    rejected_by: str | None = None                # which rule turned it down
    runner_up: Store | None = None                # closest shop we considered, match or not
    runner_up_coverage: float | None = None


@dataclass
class _Candidate:
    store_id: str
    score: float
    exact_word_count: int
    name_length: int
    store_coverage: float
    query_coverage: float
    shared: List[str]


def _align(store_tokens: Set[str], merchant_tokens: Set[str]) -> List[Tuple[str, str, bool]]:
    """
    Pair up the shop's words with the merchant's, best pairs first, each word used once.

    Using each word once is the whole point. Without it a single merchant word 'פארמ'
    answers for *both* halves of the shop 'פארמר פארם', which then looks like a perfect
    match when really only half of it lined up.
    """
    pairs: List[Tuple[float, bool, str, str]] = []
    for store_token in store_tokens:
        for merchant_token in merchant_tokens:
            if store_token == merchant_token:
                pairs.append((100.0, True, store_token, merchant_token))
            elif abs(len(merchant_token) - len(store_token)) <= 2:
                score = fuzz.ratio(store_token, merchant_token)
                if score >= STORE_MATCH.TOKEN_FUZZ_MIN:
                    pairs.append((score, False, store_token, merchant_token))

    pairs.sort(key=lambda pair: (-pair[0], not pair[1]))

    spoken_for_store: Set[str] = set()
    spoken_for_merchant: Set[str] = set()
    aligned: List[Tuple[str, str, bool]] = []
    for _, is_exact, store_token, merchant_token in pairs:
        if store_token in spoken_for_store or merchant_token in spoken_for_merchant:
            continue
        spoken_for_store.add(store_token)
        spoken_for_merchant.add(merchant_token)
        aligned.append((store_token, merchant_token, is_exact))
    return aligned


def match_store(
    merchant_name: str | None,
    town_name: str | None,
    index: StoreIndex,
    place_words: PlaceVocabulary = NO_PLACE_WORDS,
) -> StoreMatch:
    """
    Work out which shop, if any, a card-feed merchant name refers to.

    The question is not "how alike are these two strings" — that is what used to be asked,
    and it is why 'נאור סקה עיצוב שיער' came back as 'דן עיצוב שיער' with full confidence.
    It is "do these two names share enough *rare* words to be the same shop, and does
    neither one have identifying words left over that the other cannot account for".
    """
    normalized = normalize(merchant_name)
    if not normalized:
        return StoreMatch(status=NO_MATCH, rejected_by=NO_NAME)
    if len(normalized) < STORE_MATCH.MIN_QUERY_LENGTH:
        return StoreMatch(status=NO_MATCH, normalized_name=normalized, rejected_by=TOO_SHORT)

    squashed = normalized.replace(" ", "")
    exact_store_id = index.store_id_by_exact_name(squashed)
    if exact_store_id:
        return StoreMatch(
            status=EXACT,
            store=index.get_store(exact_store_id),
            normalized_name=normalized,
            store_coverage=1.0,
            query_coverage=1.0,
        )

    all_words = set(tokenize(normalized))

    # Two views of the merchant name. `identifying_words` is what the merchant is *called*
    # — the branch's town taken out, because that describes where it is, not who it is.
    # `all_words` keeps the town, because a shop is allowed to carry it in its own name
    # and still has to be able to match on it ('לגון נתניה' -> 'VERT לגון נתניה').
    identifying_words = set(place_words.strip(strip_town(strip_boilerplate(all_words), town_name)))
    if not identifying_words:
        return StoreMatch(status=NO_MATCH, normalized_name=normalized, rejected_by=TOO_SHORT)

    # A word that appears in no shop name cannot tell us which shop this is, so it is set
    # aside rather than counted for or against. Such a word is genuinely ambiguous — it is
    # as likely to be a mall or a street ('קניון ערים', 'הנשיאים') as another brand
    # ('זוזה'), and nothing in the store list can tell those apart. Treating it as a brand
    # and refusing to match would throw away far more real savings than it would prevent
    # wrong ones. Telling the two apart needs a learned vocabulary of place words.
    known_words = {word for word in identifying_words if index.is_known(word)}
    if not known_words:
        return StoreMatch(status=NO_MATCH, normalized_name=normalized, rejected_by=NO_KNOWN_WORDS)

    # The merchant's own identifying words: known, long enough to be a real word rather
    # than a truncation, and rare enough to mean something.
    distinctive_words = {
        word
        for word in known_words
        if len(word) >= STORE_MATCH.MIN_DISTINCT_TOKEN_LENGTH
        and index.rarity(word) >= STORE_MATCH.DISTINCT_RARITY_FLOOR
    }
    distinctive_mass = sum(index.rarity(word) for word in distinctive_words)

    candidate_ids = index.candidate_store_ids(known_words, STORE_MATCH.CANDIDATE_DF_CAP)
    if not candidate_ids:
        return StoreMatch(status=NO_MATCH, normalized_name=normalized, rejected_by=NO_CANDIDATES)

    accepted: List[_Candidate] = []
    nearest: _Candidate | None = None
    last_rejection: str | None = None

    for store_id in candidate_ids:
        for store_tokens in index.token_groups(store_id):
            token_set = set(store_tokens)
            aligned = _align(token_set, all_words)
            if not aligned:
                continue

            shared = [store_token for store_token, _, _ in aligned]
            answered_for = {merchant_token for _, merchant_token, _ in aligned}
            exact_word_count = sum(1 for _, _, is_exact in aligned if is_exact)

            # A typo-match is real evidence, but weaker than an exact one.
            shared_mass = sum(
                index.rarity(store_token) * (1.0 if is_exact else STORE_MATCH.FUZZY_MASS_DISCOUNT)
                for store_token, _, is_exact in aligned
            )
            whole_name_mass = sum(index.rarity(token) for token in token_set)
            store_coverage = shared_mass / whole_name_mass if whole_name_mass else 0.0
            query_coverage = (
                sum(index.rarity(word) for word in distinctive_words & answered_for) / distinctive_mass
                if distinctive_mass
                else 1.0
            )

            candidate = _Candidate(
                store_id=store_id,
                score=store_coverage * shared_mass,
                exact_word_count=exact_word_count,
                name_length=len(token_set),
                store_coverage=store_coverage,
                query_coverage=query_coverage,
                shared=shared,
            )
            if nearest is None or candidate.score > nearest.score:
                nearest = candidate

            if query_coverage < STORE_MATCH.QUERY_COVERAGE_MIN:
                last_rejection = QUERY_NOT_EXPLAINED
                continue
            if store_coverage < STORE_MATCH.STORE_COVERAGE_MIN:
                last_rejection = STORE_NOT_EXPLAINED
                continue
            if not _evidence_is_strong_enough(shared, shared_mass, store_coverage, index):
                last_rejection = EVIDENCE_TOO_WEAK
                continue

            accepted.append(candidate)
            break  # one verdict per shop, from whichever of its written forms fits best

    if not accepted:
        return StoreMatch(
            status=NO_MATCH,
            normalized_name=normalized,
            rejected_by=last_rejection or NO_CANDIDATES,
            runner_up=index.get_store(nearest.store_id) if nearest else None,
            runner_up_coverage=nearest.store_coverage if nearest else None,
        )

    accepted.sort(
        key=lambda candidate: (
            -candidate.score,
            -candidate.exact_word_count,
            candidate.name_length,
            candidate.store_id,
        )
    )
    best = accepted[0]
    rivals = [candidate for candidate in accepted if candidate.store_id != best.store_id]

    # Two different shops fitting equally well means the name does not actually pick one
    # out. Saying nothing is better than naming the wrong shop.
    if rivals and (best.score - rivals[0].score) / best.score < STORE_MATCH.AMBIGUITY_MARGIN:
        return StoreMatch(
            status=NO_MATCH,
            normalized_name=normalized,
            rejected_by=AMBIGUOUS,
            runner_up=index.get_store(rivals[0].store_id),
            runner_up_coverage=rivals[0].store_coverage,
        )

    return StoreMatch(
        status=MATCHED,
        store=index.get_store(best.store_id),
        normalized_name=normalized,
        store_coverage=best.store_coverage,
        query_coverage=best.query_coverage,
        shared_tokens=best.shared,
        runner_up=index.get_store(rivals[0].store_id) if rivals else None,
        runner_up_coverage=rivals[0].store_coverage if rivals else None,
    )


def _evidence_is_strong_enough(
    shared: List[str], shared_mass: float, store_coverage: float, index: StoreIndex
) -> bool:
    """
    Is what the two names have in common actually worth anything?

    Words shared by lots of shops carry almost no weight, so an overlap made only of them
    is not evidence however neatly it lines up. The exception is a shop whose name is
    *entirely* made of such words — 'סופר פארם' is two ordinary words, and the brand only
    exists in having both of them.
    """
    distinctive = [
        token for token in shared if index.rarity(token) >= STORE_MATCH.DISTINCT_RARITY_FLOOR
    ]

    if not distinctive:
        return (
            store_coverage > 0.999
            and len(shared) >= 2
            and shared_mass >= STORE_MATCH.EVIDENCE_RARITY_MIN
        )

    if len(shared) == 1 and index.rarity(shared[0]) < STORE_MATCH.SOLO_RARITY_MIN:
        return False

    strongest = max(index.rarity(token) for token in distinctive)
    return shared_mass >= STORE_MATCH.EVIDENCE_RARITY_MIN or strongest >= STORE_MATCH.SOLO_RARITY_MIN


def find_store(
    merchant_name: str | None,
    town_name: str | None,
    index: StoreIndex,
    place_words: PlaceVocabulary = NO_PLACE_WORDS,
) -> Store | None:
    """The shop this merchant name refers to, or nothing. For callers that only want the answer."""
    return match_store(merchant_name, town_name, index, place_words).store
