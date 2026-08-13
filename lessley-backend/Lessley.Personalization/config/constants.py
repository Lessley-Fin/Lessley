class LIMITS:
    TOP_CATEGORIES = 20
    TOP_ACCOUNTS = 10
    TOP_STORES = 50
    MAX_PAGE_SIZE = 1000
    DAYS = 90
    HIT_THRESHOLD = 0.20


class SHOP_MATCH:
    """
    Thresholds for finding a shop that runs a deal, given a card-feed merchant name.

    Deliberately more forgiving than ``STORE_MATCH``. That one answers "is this definitely the
    same shop", and refuses when unsure. This one answers "is there a coupon the user could
    have used", where landing on a different coffee shop still tells them something true —
    both sell coffee — and saying nothing tells them nothing.

    The one rule not carried over is ``STORE_MATCH.QUERY_COVERAGE_MIN``, which demands the
    merchant's own leftover words be accounted for. It is what rejects 'קפה ברלין' against
    'קפה קפה', and it alone caused 42 of 122 rejections on a year of real transactions.
    """

    # How much of the *shop's* name the merchant string has to account for. Kept from
    # STORE_MATCH: without it a single stray shared word matches almost anything.
    STORE_COVERAGE_MIN = 0.65

    # A two-letter overlap is feed truncation, never a name.
    MIN_SHARED_TOKEN_LENGTH = 3
    MIN_QUERY_LENGTH = 3

    # A lone shared word this rare identifies a shop on its own.
    SOLO_RARITY_MIN = 0.671

    # A shared word this common names a line of business ('קפה', 'פיצה', 'בר') rather than a
    # shop. Still worth showing — but as "somewhere similar", not "here".
    LINE_OF_BUSINESS_RARITY_MAX = 0.55

    # A merchant name that boils down to one word this many shops share is a category label,
    # not a shop. Bare 'מסעדה' otherwise matches every restaurant at once.
    LOW_INFORMATION_DF = 10

    # Words this common are useless for narrowing candidates down.
    CANDIDATE_DF_CAP = 400

    # Most shops we will ever hand back for one merchant name. Generous on purpose: a shop
    # the user could have saved at is worth showing, and the bands already say how much each
    # one is worth. The ranking puts the best first, so a low cap only ever hides good ones.
    MAX_SUGGESTIONS = 25

    # Most shops in the whole by-store answer, across every purchase. A ceiling rather than a
    # trim — it exists so one pathological feed cannot return thousands, not to be reached.
    MAX_SHOPS = 50


class STORE_MATCH:
    """
    Thresholds for matching a card-feed merchant name to a shop in our store list.

    Tuned against 152 real merchant names (~25 of which have a genuine match). That is a
    small sample, so treat these as a starting point to be re-checked against production
    data rather than as settled values.
    """

    # How much of the *shop's* name the merchant string has to account for. A shop whose
    # own brand word is missing from the merchant string is not that shop:
    # 'נאור סקה עיצוב שיער' covers only 0.62 of 'דן עיצוב שיער', because 'דן' is absent.
    STORE_COVERAGE_MIN = 0.65

    # How much of the *merchant's* own identifying words the shop has to account for.
    # This is the one that catches 'קפה ברלין' -> 'קפה קפה': the shop's name is fully
    # covered, but 'ברלין' — the word that actually names the merchant — is left over.
    QUERY_COVERAGE_MIN = 0.75

    # Two shops scoring within this margin of each other means the name is ambiguous,
    # and we would rather say nothing than guess.
    AMBIGUITY_MARGIN = 0.02

    TOKEN_FUZZ_MIN = 88          # word-level typo tolerance ('Games' ~ 'game')
    TOWN_FUZZ_MIN = 85           # feeds misspell town names ('גלילות' arriving as 'מלילות')
    FUZZY_MASS_DISCOUNT = 0.75   # a typo-match is weaker evidence than an exact one

    # Rarity floors, on the index's 0..1 scale (0 = in every shop name, 1 = in none).
    # A word shared by many shops (קפה, פיצה) says nothing about *which* shop this is,
    # however neatly the strings line up.
    DISTINCT_RARITY_FLOOR = 0.615   # below this a word cannot identify a shop on its own
    SOLO_RARITY_MIN = 0.671         # a one-word match has to be rarer still
    EVIDENCE_RARITY_MIN = 1.006     # total rarity a match must carry overall

    MIN_QUERY_LENGTH = 3
    MIN_DISTINCT_TOKEN_LENGTH = 3   # 2-letter words are feed truncation, never a brand

    # Words this common are useless for narrowing candidates down; skip them when
    # gathering shops to score.
    CANDIDATE_DF_CAP = 400
